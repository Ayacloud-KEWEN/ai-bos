"""多公司对比 / M&A 视图：并排关键情报指标。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.intel import gather_intelligence

router = APIRouter()


def _comparable(intel: dict) -> dict:
    c = intel["company"]
    f = intel.get("financial") or {}
    fsum = (f.get("trend") or {}).get("summary", {})
    dd = intel.get("due_diligence") or {}
    comp = intel.get("competitive") or {}
    return {
        "id": c["id"], "name": c["name"], "sector": c.get("sector"), "industry": c.get("industry"),
        "intelligence_score": c.get("intelligence_score"),
        "currency": f.get("currency") or "USD",
        "financial_scores": f.get("scores") or {},
        "latest_revenue": fsum.get("latest_revenue"),
        "yoy_revenue_growth": fsum.get("yoy_revenue_growth"),
        "revenue_cagr": fsum.get("revenue_cagr"),
        "net_margin": fsum.get("latest_net_margin"),
        "gross_margin": fsum.get("latest_gross_margin"),
        "dd_score": dd.get("overall_score"),
        "dd_recommendation": dd.get("recommendation"),
        "positioning_score": comp.get("positioning_score"),
        "market_position": comp.get("market_position"),
        "strengths": (comp.get("swot") or {}).get("strengths", [])[:3],
        "risks": (dd.get("red_flags") or [])[:3] or (f.get("risks") or [])[:3],
    }


@router.get("", tags=["Compare"])
async def compare(ids: str, db: AsyncSession = Depends(get_db)):
    """ids: 逗号分隔的公司 id（2-4 家）。"""
    id_list = [x.strip() for x in (ids or "").split(",") if x.strip()][:4]
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 company ids")
    out = []
    for cid in id_list:
        intel = await gather_intelligence(db, cid)
        if intel:
            out.append(_comparable(intel))
    return {"companies": out}
