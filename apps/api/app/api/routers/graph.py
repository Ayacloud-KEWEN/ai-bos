"""知识图谱接口：把公司与竞品的关系组织成可视化网络。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.company import Company
from app.models.competitive import CompanyCompetitiveReport

router = APIRouter()


@router.get("", tags=["Knowledge Graph"])
async def get_graph(db: AsyncSession = Depends(get_db)):
    """返回全局公司关系网络：节点=公司，边=竞争关系（competes_with）。"""
    companies = (await db.execute(select(Company))).scalars().all()
    reports = (await db.execute(select(CompanyCompetitiveReport))).scalars().all()

    nodes = [
        {
            "id": c.id,
            "name": c.name,
            "sector": c.sector or "Uncategorized",
            "status": c.status,
            "intelligence_score": c.intelligence_score or 0,
            "is_stub": (c.status or "").startswith("Discovered"),
        }
        for c in companies
    ]
    node_ids = {n["id"] for n in nodes}

    edges = []
    seen = set()
    for r in reports:
        if r.company_id not in node_ids:  # 跳过已删除公司的孤儿报告
            continue
        for comp in (r.competitors or []):
            tgt = comp.get("company_id")
            if not tgt or tgt not in node_ids or tgt == r.company_id:
                continue
            key = (r.company_id, tgt)
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "source": r.company_id,
                "target": tgt,
                "type": "competes_with",
                "threat_level": comp.get("threat_level", 3),
            })

    return {"nodes": nodes, "edges": edges}
