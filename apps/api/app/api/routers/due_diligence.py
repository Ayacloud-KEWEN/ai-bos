"""尽职调查接口：存储 / 读取五大风险评估与投资建议。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.due_diligence import CompanyDueDiligenceReport
from app.models.company import Company

router = APIRouter()

# 标准五大风险维度顺序与默认标签（用于补齐 LLM 可能漏掉的维度）
_CATEGORIES = ["financial", "legal", "operational", "commercial", "technology"]


async def persist_due_diligence(db: AsyncSession, company_id: str, dd: dict):
    """将 analyzer 产出的 DueDiligenceIntelligence dict 落库（覆盖式）。"""
    existing = (
        await db.execute(
            select(CompanyDueDiligenceReport).where(CompanyDueDiligenceReport.company_id == company_id)
        )
    ).scalar_one_or_none()

    fields = dict(
        overall_score=dd.get("overall_score", 0),
        recommendation=dd.get("recommendation", ""),
        executive_summary=dd.get("executive_summary", ""),
        language=dd.get("language", "en"),
        risk_categories=dd.get("risk_categories", []),
        red_flags=dd.get("red_flags", []),
        opportunities=dd.get("opportunities", []),
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(CompanyDueDiligenceReport(company_id=company_id, **fields))


@router.get("/{company_id}/due-diligence", tags=["Due Diligence"])
async def get_due_diligence(company_id: str, db: AsyncSession = Depends(get_db)):
    company = (
        await db.execute(select(Company).where(Company.id == company_id))
    ).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    report = (
        await db.execute(
            select(CompanyDueDiligenceReport).where(CompanyDueDiligenceReport.company_id == company_id)
        )
    ).scalar_one_or_none()

    return {
        "company_id": company_id,
        "company_name": company.name,
        "has_data": bool(report),
        "overall_score": report.overall_score if report else 0,
        "recommendation": report.recommendation if report else None,
        "executive_summary": report.executive_summary if report else None,
        "language": report.language if report else "en",
        "risk_categories": (report.risk_categories if report else []) or [],
        "red_flags": (report.red_flags if report else []) or [],
        "opportunities": (report.opportunities if report else []) or [],
    }
