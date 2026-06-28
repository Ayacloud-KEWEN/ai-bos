"""联网情报抓取：按公司名从权威数据源（SEC/巨潮/...）搜索并自动建档分析。"""
import os
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db, AsyncSessionLocal
from app.models.company import Company
from app.models.document import CompanyDocument
from app.services.sources import registry
from app.services.storage import save_document
from app.services.taxonomy import normalize_sector
from app.services.analyzer import (
    build_analysis_context, build_context_from_text,
    analyze_financials, analyze_competition, analyze_due_diligence,
)
from app.api.routers.financials import persist_financials
from app.api.routers.competitive import persist_competitive
from app.api.routers.due_diligence import persist_due_diligence

router = APIRouter()


@router.get("/sources", tags=["Online Scan"])
async def get_sources():
    return {"sources": registry.list_sources()}


class SearchInput(BaseModel):
    name: str
    source: str


@router.post("/search", tags=["Online Scan"])
async def search(body: SearchInput):
    conn = registry.get_connector(body.source)
    if not conn:
        raise HTTPException(status_code=400, detail="Unknown or unavailable source")
    try:
        cands = await asyncio.to_thread(conn.search, body.name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Source search failed: {e}")
    return {"candidates": [
        {"source": c.source, "name": c.name, "external_id": c.external_id, "extra": c.extra}
        for c in cands
    ]}


class ImportInput(BaseModel):
    source: str
    external_id: str
    name: str
    extra: dict | None = None


async def _run_scan_analysis(company_id: str, file_path: str | None, text: str,
                             financial_periods, currency: str, name: str):
    """联网抓取后的后台分析：构建上下文 → 财务(结构化优先)/竞争/尽调 → RAG 索引。"""
    failed = []
    try:
        context = (await build_analysis_context(file_path)) if file_path else (await build_context_from_text(text))
    except Exception as e:
        print(f"[scan] context build failed for {company_id}: {e}")
        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
            if c: c.status = "Analysis Failed"; await db.commit()
        return

    # 财务：有结构化期间(SEC XBRL)则用 LLM 评分 + 覆盖为权威数字
    try:
        fin = await analyze_financials(context)
        if financial_periods:
            fin["periods"] = financial_periods
            fin["currency"] = currency
        async with AsyncSessionLocal() as db:
            await persist_financials(db, company_id, fin, currency=fin.get("currency", currency))
            await db.commit()
    except Exception as e:
        failed.append("financials"); print(f"[scan] fin failed: {e}")

    try:
        comp = await analyze_competition(context, name)
        async with AsyncSessionLocal() as db:
            await persist_competitive(db, company_id, comp); await db.commit()
    except Exception as e:
        failed.append("competitive"); print(f"[scan] comp failed: {e}")

    try:
        dd = await analyze_due_diligence(context)
        async with AsyncSessionLocal() as db:
            await persist_due_diligence(db, company_id, dd); await db.commit()
    except Exception as e:
        failed.append("due-diligence"); print(f"[scan] dd failed: {e}")

    try:
        from app.api.routers.chat import index_company
        await index_company(company_id)
    except Exception as e:
        failed.append("rag-index"); print(f"[scan] rag failed: {e}")

    try:
        from app.api.routers.briefing import build_and_store_briefing
        await build_and_store_briefing(company_id)
    except Exception as e:
        failed.append("briefing"); print(f"[scan] briefing failed: {e}")

    try:
        from app.api.routers.strategy import build_and_store_strategy
        await build_and_store_strategy(company_id)
    except Exception as e:
        failed.append("strategy"); print(f"[scan] strategy failed: {e}")

    try:
        from app.api.routers.sales_market import build_and_store_sales, build_and_store_market
        await build_and_store_sales(company_id)
        await build_and_store_market(company_id)
    except Exception as e:
        failed.append("sales/market"); print(f"[scan] sales/market failed: {e}")

    async with AsyncSessionLocal() as db:
        c = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
        if c:
            c.status = "Active Monitoring" if not failed else f"Partial: {','.join(failed)} unavailable"
            await db.commit()


@router.post("/import", tags=["Online Scan"])
async def import_company(body: ImportInput, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    from app.services.sources.base import Candidate
    conn = registry.get_connector(body.source)
    if not conn:
        raise HTTPException(status_code=400, detail="Unknown or unavailable source")

    cand = Candidate(source=body.source, name=body.name, external_id=body.external_id, extra=body.extra or {})
    try:
        result = await asyncio.to_thread(conn.fetch, cand)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Source fetch failed: {e}")

    # 建公司
    industry = result.profile.get("industry") or "Unknown Sector"
    company = Company(
        name=result.name or body.name,
        industry=industry,
        sector=normalize_sector(result.profile.get("sector"), industry),
        location=result.profile.get("location") or "Global",
        intelligence_score=60,
        documents_analyzed=len(result.source_docs),
        summary=result.profile.get("summary") or f"Imported from {conn.label}.",
        status="Analyzing Intelligence",
        source=body.source,
        source_external_id=body.external_id,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)

    # 存原始文件为附件
    primary_pdf_path = None
    for sd in result.source_docs:
        if not sd.content:
            continue
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        path = save_document(company.id, doc_id, sd.content, suffix=sd.suffix)
        db.add(CompanyDocument(
            id=doc_id, company_id=company.id, filename=f"{sd.title}{sd.suffix}",
            stored_path=path, content_type=sd.content_type, size=len(sd.content),
        ))
        if sd.suffix.lower() == ".pdf" and primary_pdf_path is None:
            primary_pdf_path = path
    await db.commit()

    background_tasks.add_task(
        _run_scan_analysis, company.id, primary_pdf_path, result.text,
        result.financial_periods, result.currency, company.name,
    )
    return {"company_id": company.id, "name": company.name, "source": conn.label,
            "msg": "Imported. Intelligence is being analyzed in the background."}
