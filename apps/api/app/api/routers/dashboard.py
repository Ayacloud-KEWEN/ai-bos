"""Dashboard 真实数据汇总。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.company import Company
from app.models.alert import Alert
from app.models.financial import CompanyFinancialReport
from app.models.due_diligence import CompanyDueDiligenceReport
from app.models.document import CompanyDocument

router = APIRouter()


@router.get("/summary", tags=["Dashboard"])
async def summary(db: AsyncSession = Depends(get_db)):
    companies = (await db.execute(select(Company))).scalars().all()
    real = [c for c in companies if not (c.status or "").startswith("Discovered")]

    # 行业分布
    sectors: dict[str, int] = {}
    for c in real:
        sectors[c.sector or "Uncategorized"] = sectors.get(c.sector or "Uncategorized", 0) + 1

    docs = (await db.execute(select(func.count()).select_from(CompanyDocument))).scalar_one()
    fin_n = (await db.execute(select(func.count()).select_from(CompanyFinancialReport))).scalar_one()
    dd_n = (await db.execute(select(func.count()).select_from(CompanyDueDiligenceReport))).scalar_one()
    unread = (await db.execute(
        select(func.count()).select_from(Alert).where(Alert.is_read == False)  # noqa: E712
    )).scalar_one()

    scores = [c.intelligence_score or 0 for c in real]
    avg_score = round(sum(scores) / len(scores)) if scores else 0

    top = sorted(real, key=lambda c: c.intelligence_score or 0, reverse=True)[:5]
    recent = sorted(real, key=lambda c: c.created_at or 0, reverse=True)[:6]

    recent_alerts = (await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(6)
    )).scalars().all()

    def card(c):
        return {"id": c.id, "name": c.name, "sector": c.sector, "industry": c.industry,
                "intelligence_score": c.intelligence_score, "status": c.status}

    return {
        "totals": {
            "companies": len(real), "documents": docs, "financial_reports": fin_n,
            "due_diligence_reports": dd_n, "monitored": sum(1 for c in real if c.source and c.source != "upload"),
            "unread_alerts": unread, "avg_intelligence_score": avg_score,
        },
        "sector_distribution": [{"sector": k, "count": v} for k, v in sorted(sectors.items(), key=lambda x: -x[1])],
        "top_companies": [card(c) for c in top],
        "recent_companies": [card(c) for c in recent],
        "recent_alerts": [
            {"id": a.id, "company_id": a.company_id, "company_name": a.company_name, "type": a.type,
             "severity": a.severity, "title": a.title, "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in recent_alerts
        ],
    }
