"""CEO 执行简报接口：综合各维度情报生成/读取简报。"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, AsyncSessionLocal
from app.models.company import Company
from app.models.briefing import CompanyExecutiveBriefing
from app.services.intel import gather_intelligence, intelligence_to_text
from app.services.analyzer import generate_briefing

router = APIRouter()


async def persist_briefing(db: AsyncSession, company_id: str, b: dict):
    existing = (await db.execute(
        select(CompanyExecutiveBriefing).where(CompanyExecutiveBriefing.company_id == company_id)
    )).scalar_one_or_none()
    fields = dict(
        language=b.get("language", "en"),
        summary=b.get("summary", ""),
        what_happened=b.get("what_happened", ""),
        why_it_matters=b.get("why_it_matters", ""),
        recommended_actions=b.get("recommended_actions", []),
        key_risks=b.get("key_risks", []),
        opportunities=b.get("opportunities", []),
        next_actions=b.get("next_actions", []),
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(CompanyExecutiveBriefing(company_id=company_id, **fields))


async def build_and_store_briefing(company_id: str):
    """汇总情报 → 生成简报 → 落库。供后台任务复用。"""
    async with AsyncSessionLocal() as db:
        intel = await gather_intelligence(db, company_id)
        if not intel:
            return
        text = intelligence_to_text(intel)
    b = await generate_briefing(text)
    async with AsyncSessionLocal() as db:
        await persist_briefing(db, company_id, b)
        await db.commit()
    print(f"[briefing] generated for {company_id}")


@router.post("/{company_id}/briefing/generate", tags=["Executive Briefing"])
async def generate(company_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    background_tasks.add_task(build_and_store_briefing, company_id)
    return {"msg": "Briefing generation started", "company_id": company_id}


@router.get("/{company_id}/briefing", tags=["Executive Briefing"])
async def get_briefing(company_id: str, db: AsyncSession = Depends(get_db)):
    b = (await db.execute(
        select(CompanyExecutiveBriefing).where(CompanyExecutiveBriefing.company_id == company_id)
    )).scalar_one_or_none()
    return {
        "company_id": company_id,
        "has_data": bool(b),
        "language": b.language if b else "en",
        "summary": b.summary if b else None,
        "what_happened": b.what_happened if b else None,
        "why_it_matters": b.why_it_matters if b else None,
        "recommended_actions": (b.recommended_actions if b else []) or [],
        "key_risks": (b.key_risks if b else []) or [],
        "opportunities": (b.opportunities if b else []) or [],
        "next_actions": (b.next_actions if b else []) or [],
    }
