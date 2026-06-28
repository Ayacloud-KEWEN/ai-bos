"""销售情报（Agent 04）与市场情报（Agent 05）接口。"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, AsyncSessionLocal
from app.models.company import Company
from app.models.sales_market import CompanySalesReport, CompanyMarketReport
from app.services.intel import gather_intelligence, intelligence_to_text
from app.services.analyzer import generate_sales, generate_market

router = APIRouter()


# ---------------- Sales (Agent 04) ----------------
async def persist_sales(db: AsyncSession, company_id: str, s: dict):
    existing = (await db.execute(select(CompanySalesReport).where(CompanySalesReport.company_id == company_id))).scalar_one_or_none()
    fields = dict(
        language=s.get("language", "en"), executive_summary=s.get("executive_summary", ""),
        icp=s.get("icp", []), buyer_personas=s.get("buyer_personas", []),
        pain_points=s.get("pain_points", []), buying_triggers=s.get("buying_triggers", []),
        sales_opportunities=s.get("sales_opportunities", []),
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(CompanySalesReport(company_id=company_id, **fields))


async def build_and_store_sales(company_id: str):
    async with AsyncSessionLocal() as db:
        intel = await gather_intelligence(db, company_id)
        if not intel:
            return
        text = intelligence_to_text(intel)
    s = await generate_sales(text)
    async with AsyncSessionLocal() as db:
        await persist_sales(db, company_id, s)
        await db.commit()
    print(f"[sales] generated for {company_id}")


# ---------------- Market (Agent 05) ----------------
async def persist_market(db: AsyncSession, company_id: str, m: dict):
    existing = (await db.execute(select(CompanyMarketReport).where(CompanyMarketReport.company_id == company_id))).scalar_one_or_none()
    fields = dict(
        language=m.get("language", "en"), executive_summary=m.get("executive_summary", ""),
        tam=m.get("tam", ""), sam=m.get("sam", ""), som=m.get("som", ""),
        market_growth=m.get("market_growth", ""), trends=m.get("trends", []),
        drivers=m.get("drivers", []), barriers=m.get("barriers", []), segments=m.get("segments", []),
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(CompanyMarketReport(company_id=company_id, **fields))


async def build_and_store_market(company_id: str):
    async with AsyncSessionLocal() as db:
        intel = await gather_intelligence(db, company_id)
        if not intel:
            return
        text = intelligence_to_text(intel)
    m = await generate_market(text)
    async with AsyncSessionLocal() as db:
        await persist_market(db, company_id, m)
        await db.commit()
    print(f"[market] generated for {company_id}")


async def _check(db, company_id):
    c = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")


@router.post("/{company_id}/sales/generate", tags=["Sales Intelligence"])
async def gen_sales(company_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await _check(db, company_id)
    background_tasks.add_task(build_and_store_sales, company_id)
    return {"msg": "Sales intelligence generation started", "company_id": company_id}


@router.get("/{company_id}/sales", tags=["Sales Intelligence"])
async def get_sales(company_id: str, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(CompanySalesReport).where(CompanySalesReport.company_id == company_id))).scalar_one_or_none()
    return {
        "company_id": company_id, "has_data": bool(s),
        "executive_summary": s.executive_summary if s else None,
        "icp": (s.icp if s else []) or [], "buyer_personas": (s.buyer_personas if s else []) or [],
        "pain_points": (s.pain_points if s else []) or [], "buying_triggers": (s.buying_triggers if s else []) or [],
        "sales_opportunities": (s.sales_opportunities if s else []) or [],
    }


@router.post("/{company_id}/market/generate", tags=["Market Intelligence"])
async def gen_market(company_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await _check(db, company_id)
    background_tasks.add_task(build_and_store_market, company_id)
    return {"msg": "Market intelligence generation started", "company_id": company_id}


@router.get("/{company_id}/market", tags=["Market Intelligence"])
async def get_market(company_id: str, db: AsyncSession = Depends(get_db)):
    m = (await db.execute(select(CompanyMarketReport).where(CompanyMarketReport.company_id == company_id))).scalar_one_or_none()
    return {
        "company_id": company_id, "has_data": bool(m),
        "executive_summary": m.executive_summary if m else None,
        "tam": m.tam if m else None, "sam": m.sam if m else None, "som": m.som if m else None,
        "market_growth": m.market_growth if m else None,
        "trends": (m.trends if m else []) or [], "drivers": (m.drivers if m else []) or [],
        "barriers": (m.barriers if m else []) or [], "segments": (m.segments if m else []) or [],
    }
