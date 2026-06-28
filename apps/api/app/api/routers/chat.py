"""公司 RAG 问答接口：建立知识索引、查询状态、对话。"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from pydantic import BaseModel

from app.core.database import get_db, AsyncSessionLocal
from app.models.company import Company
from app.models.document import CompanyDocument
from app.models.knowledge import KnowledgeChunk
from app.services import rag
from app.services.analyzer import _load_text

router = APIRouter()


def _load_any(path: str) -> str:
    """统一文档抽取（PDF含OCR / DOCX / PPTX / XLSX / TXT…）。"""
    from app.services.extract import extract_text
    return extract_text(path)

_MAX_CHUNKS_PER_COMPANY = 600  # 控制超大文档的向量化规模


async def index_company(company_id: str):
    """从公司所有原始文档重建知识分块向量（覆盖式）。供后台调用。"""
    async with AsyncSessionLocal() as db:
        docs = (await db.execute(
            select(CompanyDocument).where(CompanyDocument.company_id == company_id)
        )).scalars().all()

        contents: list[str] = []
        meta: list[tuple[str, int]] = []
        for d in docs:
            try:
                text = await asyncio.to_thread(_load_any, d.stored_path)
            except Exception as e:
                print(f"[rag] load failed for {d.stored_path}: {e}")
                continue
            for i, c in enumerate(rag.split_text(text)):
                contents.append(c)
                meta.append((d.id, i))
                if len(contents) >= _MAX_CHUNKS_PER_COMPANY:
                    break
            if len(contents) >= _MAX_CHUNKS_PER_COMPANY:
                break

        # 覆盖式：先清旧块
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.company_id == company_id))

        if contents:
            vecs = await rag.embed_documents(contents)
            for (doc_id, idx), content, vec in zip(meta, contents, vecs):
                db.add(KnowledgeChunk(
                    company_id=company_id, document_id=doc_id,
                    chunk_index=idx, content=content, embedding=vec,
                ))
        await db.commit()
        print(f"[rag] indexed {len(contents)} chunks for {company_id}")


@router.post("/{company_id}/index", tags=["RAG Chat"])
async def build_index(company_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    background_tasks.add_task(index_company, company_id)
    return {"msg": "Indexing started", "company_id": company_id}


@router.get("/{company_id}/index/status", tags=["RAG Chat"])
async def index_status(company_id: str, db: AsyncSession = Depends(get_db)):
    count = (await db.execute(
        select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.company_id == company_id)
    )).scalar_one()
    return {"company_id": company_id, "indexed": count > 0, "chunk_count": count}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] | None = None


@router.post("/{company_id}/chat", tags=["RAG Chat"])
async def chat(company_id: str, body: ChatRequest, db: AsyncSession = Depends(get_db)):
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    q = (body.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty question")

    # 检索 top-k 相关分块
    qvec = await rag.embed_query(q)
    rows = (await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.company_id == company_id)
        .order_by(KnowledgeChunk.embedding.cosine_distance(qvec))
        .limit(6)
    )).scalars().all()

    if not rows:
        return {
            "answer": "尚未为该公司建立知识索引，请先点击「建立知识库」。/ No knowledge index yet — please build it first.",
            "sources": [], "indexed": False,
        }

    # 近几轮对话作为上下文
    history_text = ""
    if body.history:
        recent = body.history[-4:]
        lines = [f"{'用户' if m.role == 'user' else '助手'}：{m.content}" for m in recent]
        history_text = "之前对话：\n" + "\n".join(lines) + "\n\n"

    ans = await rag.answer(company.name, q, [r.content for r in rows], history_text)

    return {
        "answer": ans,
        "indexed": True,
        "sources": [
            {"document_id": r.document_id, "snippet": (r.content[:180] + ("…" if len(r.content) > 180 else ""))}
            for r in rows
        ],
    }
