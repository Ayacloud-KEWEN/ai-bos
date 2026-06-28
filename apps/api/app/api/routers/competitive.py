"""竞争情报接口：存储 / 读取 SWOT、竞争矩阵与战卡。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.competitive import CompanyCompetitiveReport
from app.models.company import Company
from app.services.taxonomy import classify_sector

router = APIRouter()


async def _link_competitor_company(db: AsyncSession, name: str, description: str) -> str | None:
    """为竞品查找或创建一个轻量公司档案 (stub)，返回其 company_id。
    已存在同名公司则直接复用，实现竞品与公司库的双向联动。"""
    name = (name or "").strip()
    if not name:
        return None
    # 不区分大小写匹配现有公司
    existing = (
        await db.execute(select(Company).where(func.lower(Company.name) == name.lower()))
    ).scalar_one_or_none()
    if existing:
        return existing.id

    stub = Company(
        name=name,
        industry="(discovered competitor)",
        # 按名称+描述归一标准行业，便于组织与浏览；同行对标侧已按"有财务数据"过滤，stub 不会干扰
        sector=classify_sector(f"{name} {description}"),
        location="Unknown",
        status="Discovered (Competitor)",
        intelligence_score=0,
        documents_analyzed=0,
        summary=(description or f"{name} — auto-discovered via competitive intelligence.")[:500],
    )
    db.add(stub)
    await db.flush()  # 取得 stub.id
    return stub.id


async def persist_competitive(db: AsyncSession, company_id: str, comp: dict):
    """将 analyzer 产出的 CompetitiveIntelligence dict 落库（覆盖式）。
    同时为每个竞品自动建立/关联公司档案，写回 company_id 实现可点击联动。"""
    # 竞品自动建公司 + 回填 company_id
    competitors = comp.get("competitors", []) or []
    for c in competitors:
        if isinstance(c, dict):
            c["company_id"] = await _link_competitor_company(db, c.get("name", ""), c.get("description", ""))

    existing = (
        await db.execute(
            select(CompanyCompetitiveReport).where(CompanyCompetitiveReport.company_id == company_id)
        )
    ).scalar_one_or_none()

    fields = dict(
        market_position=comp.get("market_position", ""),
        positioning_score=comp.get("positioning_score", 0),
        strengths=comp.get("strengths", []),
        weaknesses=comp.get("weaknesses", []),
        opportunities=comp.get("opportunities", []),
        threats=comp.get("threats", []),
        competitors=comp.get("competitors", []),
        battlecards=comp.get("battlecards", []),
        technology_trends=comp.get("technology_trends", []),
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(CompanyCompetitiveReport(company_id=company_id, **fields))


@router.get("/{company_id}/competitive", tags=["Competitive Intelligence"])
async def get_competitive(company_id: str, db: AsyncSession = Depends(get_db)):
    company = (
        await db.execute(select(Company).where(Company.id == company_id))
    ).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    report = (
        await db.execute(
            select(CompanyCompetitiveReport).where(CompanyCompetitiveReport.company_id == company_id)
        )
    ).scalar_one_or_none()

    return {
        "company_id": company_id,
        "company_name": company.name,
        "has_data": bool(report),
        "market_position": report.market_position if report else None,
        "positioning_score": report.positioning_score if report else 0,
        "swot": {
            "strengths": (report.strengths if report else []) or [],
            "weaknesses": (report.weaknesses if report else []) or [],
            "opportunities": (report.opportunities if report else []) or [],
            "threats": (report.threats if report else []) or [],
        },
        "competitors": (report.competitors if report else []) or [],
        "battlecards": (report.battlecards if report else []) or [],
        "technology_trends": (report.technology_trends if report else []) or [],
    }
