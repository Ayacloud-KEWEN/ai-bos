"""公司文档（附件）接口：列出与在线查看原始文件。"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.document import CompanyDocument

router = APIRouter()


@router.get("/{company_id}/documents", tags=["Company Documents"])
async def list_documents(company_id: str, db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(CompanyDocument)
            .where(CompanyDocument.company_id == company_id)
            .order_by(CompanyDocument.uploaded_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "content_type": d.content_type,
            "size": d.size,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
        }
        for d in rows
    ]


@router.get("/{company_id}/documents/{doc_id}/file", tags=["Company Documents"])
async def get_document_file(company_id: str, doc_id: str, db: AsyncSession = Depends(get_db)):
    """以 inline 方式返回原始文件，浏览器可直接打开预览。"""
    doc = (
        await db.execute(
            select(CompanyDocument).where(
                CompanyDocument.id == doc_id, CompanyDocument.company_id == company_id
            )
        )
    ).scalar_one_or_none()
    if not doc or not os.path.exists(doc.stored_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    return FileResponse(
        doc.stored_path,
        media_type=doc.content_type or "application/pdf",
        filename=doc.filename,
        content_disposition_type="inline",
    )
