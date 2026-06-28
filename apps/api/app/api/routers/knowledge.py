"""组织级知识库接口（Module 5）：上传/索引、语义检索、跨文档问答。"""
import os
import uuid
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete, func
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.database import get_db, AsyncSessionLocal
from app.models.knowledge_base import KnowledgeBaseDocument, KnowledgeBaseChunk
from app.services import rag
from app.services.storage import save_document, delete_document_file
from app.services.extract import extract_text
from app.services.llm import build_text_llm

router = APIRouter()
_MAX_CHUNKS = 800


async def _index_document(doc_id: str, path: str):
    try:
        text = await asyncio.to_thread(extract_text, path)
        chunks = rag.split_text(text)[:_MAX_CHUNKS]
        async with AsyncSessionLocal() as db:
            doc = (await db.execute(select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == doc_id))).scalar_one_or_none()
            title = doc.title if doc else ""
            if chunks:
                vecs = await rag.embed_documents(chunks)
                for i, (content, vec) in enumerate(zip(chunks, vecs)):
                    db.add(KnowledgeBaseChunk(document_id=doc_id, title=title, chunk_index=i, content=content, embedding=vec))
            if doc:
                doc.chunk_count = len(chunks)
                doc.status = "Ready" if chunks else "Failed"
            await db.commit()
        print(f"[kb] indexed {len(chunks)} chunks for {doc_id}")
    except Exception as e:
        print(f"[kb] index failed {doc_id}: {e}")
        async with AsyncSessionLocal() as db:
            doc = (await db.execute(select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == doc_id))).scalar_one_or_none()
            if doc:
                doc.status = "Failed"; await db.commit()


@router.post("/documents", tags=["Knowledge Base"])
async def upload_document(background_tasks: BackgroundTasks, title: str = Form(...),
                          file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    doc_id = f"kbd_{uuid.uuid4().hex[:8]}"
    suffix = os.path.splitext(file.filename or "")[1].lower() or ".pdf"
    path = save_document("_knowledge", doc_id, content, suffix=suffix)
    db.add(KnowledgeBaseDocument(id=doc_id, title=title, filename=file.filename or title,
                                 stored_path=path, content_type=file.content_type or "application/octet-stream",
                                 size=len(content), status="Indexing"))
    await db.commit()
    background_tasks.add_task(_index_document, doc_id, path)
    return {"id": doc_id, "status": "Indexing"}


@router.get("/documents", tags=["Knowledge Base"])
async def list_documents(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(KnowledgeBaseDocument).order_by(KnowledgeBaseDocument.created_at.desc()))).scalars().all()
    return [{"id": d.id, "title": d.title, "filename": d.filename, "size": d.size,
             "chunk_count": d.chunk_count, "status": d.status,
             "created_at": d.created_at.isoformat() if d.created_at else None} for d in rows]


@router.get("/documents/{doc_id}/file", tags=["Knowledge Base"])
async def get_file(doc_id: str, db: AsyncSession = Depends(get_db)):
    d = (await db.execute(select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == doc_id))).scalar_one_or_none()
    if not d or not os.path.exists(d.stored_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(d.stored_path, media_type=d.content_type, filename=d.filename, content_disposition_type="inline")


@router.delete("/documents/{doc_id}", tags=["Knowledge Base"])
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    d = (await db.execute(select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == doc_id))).scalar_one_or_none()
    if d:
        delete_document_file(d.stored_path)
    await db.execute(sa_delete(KnowledgeBaseChunk).where(KnowledgeBaseChunk.document_id == doc_id))
    await db.execute(sa_delete(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == doc_id))
    await db.commit()
    return {"msg": "deleted"}


async def _retrieve(db: AsyncSession, query: str, k: int = 6):
    qvec = await rag.embed_query(query)
    return (await db.execute(
        select(KnowledgeBaseChunk).order_by(KnowledgeBaseChunk.embedding.cosine_distance(qvec)).limit(k)
    )).scalars().all()


class QueryInput(BaseModel):
    query: str
    k: int | None = 6


@router.post("/search", tags=["Knowledge Base"])
async def search(body: QueryInput, db: AsyncSession = Depends(get_db)):
    rows = await _retrieve(db, body.query, body.k or 6)
    return {"results": [{"document_id": r.document_id, "title": r.title,
                         "snippet": r.content[:300]} for r in rows]}


_kb_prompt = PromptTemplate(
    template=("你是企业知识库助手。请**仅根据**下面的知识库资料回答问题；资料中没有就说\"知识库中未找到\"。"
              "用与问题相同的语言作答，可引用来源标题。\n\n资料：\n{context}\n\n问题：{question}\n\n回答："),
    input_variables=["context", "question"],
)


class AskInput(BaseModel):
    question: str


@router.post("/ask", tags=["Knowledge Base"])
async def ask(body: AskInput, db: AsyncSession = Depends(get_db)):
    q = (body.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty question")
    rows = await _retrieve(db, q, 6)
    if not rows:
        return {"answer": "知识库为空或未找到相关内容，请先上传文档。", "sources": []}
    context = "\n\n---\n\n".join(f"[{r.title}] {r.content}" for r in rows)
    chain = _kb_prompt | build_text_llm(None, 0.2) | StrOutputParser()
    answer = await chain.ainvoke({"context": context, "question": q})
    seen, sources = set(), []
    for r in rows:
        if r.document_id not in seen:
            seen.add(r.document_id); sources.append({"document_id": r.document_id, "title": r.title, "snippet": r.content[:160]})
    return {"answer": answer, "sources": sources}
