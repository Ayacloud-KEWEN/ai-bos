"""战略情报接口（Agent 06）：综合各维度生成战略选项、排序建议、波特五力。"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, AsyncSessionLocal
from app.models.company import Company
from app.models.strategy import CompanyStrategyReport
from app.services.intel import gather_intelligence, intelligence_to_text
from app.services.analyzer import generate_strategy

router = APIRouter()


async def persist_strategy(db: AsyncSession, company_id: str, s: dict):
    existing = (await db.execute(
        select(CompanyStrategyReport).where(CompanyStrategyReport.company_id == company_id)
    )).scalar_one_or_none()
    fields = dict(
        language=s.get("language", "en"),
        executive_summary=s.get("executive_summary", ""),
        strategic_options=s.get("strategic_options", []),
        recommendations=s.get("recommendations", []),
        porters_five_forces=s.get("porters_five_forces", []),
        growth_opportunities=s.get("growth_opportunities", []),
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(CompanyStrategyReport(company_id=company_id, **fields))


async def build_and_store_strategy(company_id: str):
    async with AsyncSessionLocal() as db:
        intel = await gather_intelligence(db, company_id)
        if not intel:
            return
        text = intelligence_to_text(intel)
    s = await generate_strategy(text)
    async with AsyncSessionLocal() as db:
        await persist_strategy(db, company_id, s)
        await db.commit()
    print(f"[strategy] generated for {company_id}")


@router.post("/{company_id}/strategy/generate", tags=["Strategy Intelligence"])
async def generate(company_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    background_tasks.add_task(build_and_store_strategy, company_id)
    return {"msg": "Strategy generation started", "company_id": company_id}


@router.get("/{company_id}/strategy", tags=["Strategy Intelligence"])
async def get_strategy(company_id: str, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(
        select(CompanyStrategyReport).where(CompanyStrategyReport.company_id == company_id)
    )).scalar_one_or_none()
    return {
        "company_id": company_id,
        "has_data": bool(s),
        "language": s.language if s else "en",
        "executive_summary": s.executive_summary if s else None,
        "strategic_options": (s.strategic_options if s else []) or [],
        "recommendations": (s.recommendations if s else []) or [],
        "porters_five_forces": (s.porters_five_forces if s else []) or [],
        "growth_opportunities": (s.growth_opportunities if s else []) or [],
    }
