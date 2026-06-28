import os
import tempfile
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete

from app.core.database import get_db, AsyncSessionLocal
from app.models.company import Company
# 导入我们刚写的真实 LangChain 解析服务
from app.services.analyzer import (
    analyze_document, analyze_financials, analyze_competition, analyze_due_diligence,
    build_analysis_context,
)
from app.services.taxonomy import normalize_sector, classify_sector, SECTORS
from app.api.routers.financials import persist_financials
from app.api.routers.competitive import persist_competitive
from app.api.routers.due_diligence import persist_due_diligence
from app.models.financial import CompanyFinancial, CompanyFinancialReport
from app.models.competitive import CompanyCompetitiveReport
from app.models.due_diligence import CompanyDueDiligenceReport
from app.models.document import CompanyDocument
from app.services.financial_metrics import build_trend_analysis
from app.services.storage import save_document, delete_document_file
import uuid
from pydantic import BaseModel

router = APIRouter()


async def _set_status(company_id: str, status: str):
    try:
        async with AsyncSessionLocal() as db:
            company = (
                await db.execute(select(Company).where(Company.id == company_id))
            ).scalar_one_or_none()
            if company:
                company.status = status
                await db.commit()
    except Exception as e:
        print(f"[bg] set_status failed for {company_id}: {e}")


async def _run_deep_analysis(company_id: str, file_path: str, company_name: str):
    """后台任务：深度财报 + 竞争情报解析与落库。失败不影响主上传流程。
    使用独立 DB 会话（请求会话已随响应关闭）。结束后清理临时文件。"""
    failed = []

    # 0. 先构建分析上下文：长文档(如 71 页尽调报告)会做 map-reduce 摘要，
    #    确保后半部分的财务/风险/竞争信息都进入分析；构建一次供三项分析复用。
    try:
        context = await build_analysis_context(file_path)
    except Exception as e:
        print(f"[bg] context build failed for {company_id}: {e}")
        await _set_status(company_id, "Analysis Failed")
        if os.path.exists(file_path):
            os.remove(file_path)
        return

    # 1. 财报深度解析
    try:
        financials = await analyze_financials(context)
        async with AsyncSessionLocal() as db:
            await persist_financials(
                db, company_id, financials, currency=financials.get("currency", "USD")
            )
            await db.commit()
        print(f"[bg] financial analysis stored for {company_id}")
    except Exception as e:
        failed.append("financials")
        print(f"[bg] financial analysis failed for {company_id}: {e}")

    # 2. 竞争情报解析
    try:
        competitive = await analyze_competition(context, company_name)
        async with AsyncSessionLocal() as db:
            await persist_competitive(db, company_id, competitive)
            await db.commit()
        print(f"[bg] competitive analysis stored for {company_id}")
    except Exception as e:
        failed.append("competitive")
        print(f"[bg] competitive analysis failed for {company_id}: {e}")

    # 3. 尽职调查解析
    try:
        dd = await analyze_due_diligence(context)
        async with AsyncSessionLocal() as db:
            await persist_due_diligence(db, company_id, dd)
            await db.commit()
        print(f"[bg] due-diligence analysis stored for {company_id}")
    except Exception as e:
        failed.append("due-diligence")
        print(f"[bg] due-diligence analysis failed for {company_id}: {e}")

    # 3.5 建立 RAG 知识索引（分块向量化），供"与公司对话"使用
    try:
        from app.api.routers.chat import index_company
        await index_company(company_id)
    except Exception as e:
        failed.append("rag-index")
        print(f"[bg] rag indexing failed for {company_id}: {e}")

    # 3.6 综合各维度生成 CEO 执行简报
    try:
        from app.api.routers.briefing import build_and_store_briefing
        await build_and_store_briefing(company_id)
    except Exception as e:
        failed.append("briefing")
        print(f"[bg] briefing failed for {company_id}: {e}")

    # 3.7 战略情报（Agent 06）
    try:
        from app.api.routers.strategy import build_and_store_strategy
        await build_and_store_strategy(company_id)
    except Exception as e:
        failed.append("strategy")
        print(f"[bg] strategy failed for {company_id}: {e}")

    # 3.8 销售情报（Agent 04）与市场情报（Agent 05）
    try:
        from app.api.routers.sales_market import build_and_store_sales, build_and_store_market
        await build_and_store_sales(company_id)
        await build_and_store_market(company_id)
    except Exception as e:
        failed.append("sales/market")
        print(f"[bg] sales/market failed for {company_id}: {e}")

    # 4. 更新状态（原始文件已持久化为附件，后台不再删除）
    await _set_status(company_id, "Active Monitoring" if not failed else f"Partial: {','.join(failed)} unavailable")


def _store_document(db: AsyncSession, company_id: str, filename: str, content: bytes) -> str:
    """把上传内容持久化为公司附件并返回磁盘路径。调用方负责 commit。"""
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    suffix = os.path.splitext(filename or "")[1] or ".pdf"
    path = save_document(company_id, doc_id, content, suffix=suffix)
    db.add(CompanyDocument(
        id=doc_id, company_id=company_id, filename=filename or "document.pdf",
        stored_path=path, content_type="application/pdf", size=len(content),
    ))
    return path


@router.post("/upload", tags=["Company Intelligence"])
async def upload_and_analyze(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # 1. 接收前端文件并暂存到本地系统的临时目录，供 LangChain 加载
    #    注意：不在这里删除文件，深度财报解析的后台任务会复用它并负责清理。
    _suffix = os.path.splitext(file.filename or "")[1].lower() or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=_suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 2. 同步执行轻量级总体情报 + 向量化，确保上传可在数秒内返回
        intelligence, embedding_vector = await analyze_document(tmp_path)

        industry = intelligence.get("industry", "Unknown Sector")
        new_company = Company(
            name=name,
            industry=industry,
            sector=normalize_sector(intelligence.get("sector"), industry),
            location="Global",
            intelligence_score=intelligence.get("intelligence_score", 50),
            documents_analyzed=1,
            summary=intelligence.get("summary", "No summary generated."),
            embedding=embedding_vector,
            status="Analyzing Intelligence",  # 财报 + 竞争情报后台解析中
        )
        db.add(new_company)
        await db.commit()
        await db.refresh(new_company)

        # 把原始文件持久化为附件（供详情页查看），并作为后台分析的数据源
        stored_path = _store_document(db, new_company.id, file.filename, content)
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Core analysis failed: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)  # 仅清理同步概览用的临时文件；持久化副本已另存

    # 3. 把耗时的深度解析（财报 + 竞争情报）丢到后台执行，上传请求立即返回
    background_tasks.add_task(_run_deep_analysis, new_company.id, stored_path, name)

    return {
        "msg": "Company analyzed. Financial & competitive intelligence is processing in the background.",
        "company_id": new_company.id,
    }


@router.post("/{company_id}/reupload", tags=["Company Intelligence"])
async def reupload_and_reanalyze(
    company_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """重新上传财报/文档：在已有公司上叠加分析。
    刷新总体情报与向量，文档计数 +1，并在后台覆盖式重算财报与竞争情报。"""
    company = (
        await db.execute(select(Company).where(Company.id == company_id))
    ).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    _suffix = os.path.splitext(file.filename or "")[1].lower() or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=_suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        intelligence, embedding_vector = await analyze_document(tmp_path)
        industry = intelligence.get("industry") or company.industry
        company.industry = industry
        company.sector = normalize_sector(intelligence.get("sector"), industry)
        company.intelligence_score = intelligence.get("intelligence_score", company.intelligence_score)
        company.summary = intelligence.get("summary", company.summary)
        company.embedding = embedding_vector
        company.documents_analyzed = (company.documents_analyzed or 0) + 1
        company.status = "Analyzing Intelligence"
        await db.commit()
        await db.refresh(company)

        stored_path = _store_document(db, company.id, file.filename, content)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Re-analysis failed: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    background_tasks.add_task(_run_deep_analysis, company.id, stored_path, company.name)
    return {
        "msg": "Document re-analyzed. Financial & competitive intelligence is being refreshed.",
        "company_id": company.id,
        "documents_analyzed": company.documents_analyzed,
    }


@router.get("/sectors", tags=["Company Intelligence"])
async def list_sectors():
    """返回标准行业枚举，供前端补充信息时下拉选择。"""
    return {"sectors": SECTORS}


@router.get("/{company_id}/quote", tags=["Company Intelligence"])
async def get_quote(company_id: str, db: AsyncSession = Depends(get_db)):
    """上市公司当天股价 + 详情站点链接（联网建档公司）。"""
    from app.services import quotes
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    info = await asyncio.to_thread(quotes.resolve, company.source, company.source_external_id)
    if not info:
        return {"available": False}
    quote = await asyncio.to_thread(quotes.fetch_quote, info["symbol"])
    return {"available": True, **info, "quote": quote}


@router.get("/", tags=["Company Intelligence"])
async def list_companies(db: AsyncSession = Depends(get_db)):
    # 按照情报分数降序排列
    result = await db.execute(select(Company).order_by(Company.intelligence_score.desc()))
    companies = result.scalars().all()
    
    # 手动组装返回数据，过滤掉无法被 FastAPI 直接序列化的 embedding (向量) 字段
    # 同时这也极大节省了网络传输带宽
    return [
        {
            "id": c.id,
            "name": c.name,
            "industry": c.industry,
            "sector": c.sector,
            "location": c.location,
            "status": c.status,
            "intelligence_score": c.intelligence_score,
            "documents_analyzed": c.documents_analyzed,
            "summary": c.summary
        }
        for c in companies
    ]

# 2. 定义更新数据的 Schema（补充信息：基础资料可手动修正）
class CompanyUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    industry: str | None = None
    sector: str | None = None
    location: str | None = None

# 3. 追加以下三个新接口到文件最底部

@router.get("/{company_id}", tags=["Company Intelligence"])
async def get_company(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # 汇总各维度分析报告
    fin = (await db.execute(
        select(CompanyFinancialReport).where(CompanyFinancialReport.company_id == company_id)
    )).scalar_one_or_none()
    comp = (await db.execute(
        select(CompanyCompetitiveReport).where(CompanyCompetitiveReport.company_id == company_id)
    )).scalar_one_or_none()
    dd = (await db.execute(
        select(CompanyDueDiligenceReport).where(CompanyDueDiligenceReport.company_id == company_id)
    )).scalar_one_or_none()

    # 最新营收/利润率（从时间序列计算）
    fin_rows = (await db.execute(
        select(CompanyFinancial).where(CompanyFinancial.company_id == company_id)
    )).scalars().all()
    trend_summary = {}
    if fin_rows:
        raw = [{"period": r.period, "year": r.year, "quarter": r.quarter,
                "revenue": r.revenue, "gross_profit": r.gross_profit,
                "operating_profit": r.operating_profit, "net_profit": r.net_profit}
               for r in fin_rows]
        trend_summary = build_trend_analysis(raw)["summary"]

    base = company.intelligence_score

    # 雷达图：优先使用真实分析分数，缺失则回退到基础分波动
    if fin or comp or dd:
        radar_data = [
            {"subject": "Financial Health", "score": fin.financial_health_score if fin else base, "fullMark": 100},
            {"subject": "Growth", "score": fin.growth_score if fin else base, "fullMark": 100},
            {"subject": "Profitability", "score": fin.profitability_score if fin else base, "fullMark": 100},
            {"subject": "Market Position", "score": comp.positioning_score if comp else base, "fullMark": 100},
            {"subject": "DD Attractiveness", "score": dd.overall_score if dd else base, "fullMark": 100},
        ]
    else:
        radar_data = [
            {"subject": "Market Fit", "score": min(100, max(0, base + 5)), "fullMark": 100},
            {"subject": "Tech Stack", "score": min(100, max(0, base + 12)), "fullMark": 100},
            {"subject": "Financials", "score": min(100, max(0, base - 8)), "fullMark": 100},
            {"subject": "Team", "score": min(100, max(0, base + 3)), "fullMark": 100},
            {"subject": "Growth", "score": min(100, max(0, base - 5)), "fullMark": 100},
        ]

    # 关键风险：合并 DD 红旗 + 高风险维度 + 财务风险
    key_risks = list(dd.red_flags or []) if dd else []
    if dd and dd.risk_categories:
        for c in sorted(dd.risk_categories, key=lambda x: x.get("score", 0), reverse=True)[:2]:
            key_risks.append(f"{c.get('label', c.get('key'))}: {c.get('summary', '')}")
    if fin and fin.risks:
        key_risks += list(fin.risks)

    competitors_top = []
    if comp and comp.competitors:
        competitors_top = [
            {"name": c.get("name"), "company_id": c.get("company_id"), "threat_level": c.get("threat_level", 3)}
            for c in sorted(comp.competitors, key=lambda x: x.get("threat_level", 0), reverse=True)[:5]
        ]

    highlights = {
        "financial": {
            "health": fin.financial_health_score if fin else None,
            "growth": fin.growth_score if fin else None,
            "profitability": fin.profitability_score if fin else None,
            "currency": fin.currency if fin else "USD",
            "latest_revenue": trend_summary.get("latest_revenue"),
            "net_margin": trend_summary.get("latest_net_margin"),
            "yoy_growth": trend_summary.get("yoy_revenue_growth"),
        } if fin else None,
        "due_diligence": {
            "overall_score": dd.overall_score,
            "recommendation": dd.recommendation,
        } if dd else None,
        "competitive": {
            "positioning_score": comp.positioning_score,
            "market_position": comp.market_position,
            "strengths": (comp.strengths or [])[:3],
            "competitors": competitors_top,
        } if comp else None,
        "key_risks": key_risks[:5],
        "opportunities": (
            ((dd.opportunities or []) if dd else []) + ((fin.opportunities or []) if fin else [])
        )[:5],
    }

    return {
        "id": company.id,
        "name": company.name,
        "industry": company.industry,
        "location": company.location,
        "status": company.status,
        "sector": company.sector,
        "intelligence_score": company.intelligence_score,
        "documents_analyzed": company.documents_analyzed,
        "summary": company.summary,
        "radar_data": radar_data,
        "highlights": highlights,
    }

@router.patch("/{company_id}", tags=["Company Intelligence"])
async def update_company(company_id: str, update_data: CompanyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if update_data.name is not None:
        company.name = update_data.name
    if update_data.status is not None:
        company.status = update_data.status
    if update_data.location is not None:
        company.location = update_data.location
    if update_data.industry is not None:
        company.industry = update_data.industry
        # 行业被手动修正时，若未显式指定 sector，则按新行业重新归一
        if update_data.sector is None:
            company.sector = classify_sector(update_data.industry)
    if update_data.sector is not None:
        company.sector = update_data.sector

    await db.commit()
    return {"msg": "Updated successfully"}

@router.delete("/{company_id}", tags=["Company Intelligence"])
async def delete_company(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # 清理磁盘上的附件文件
    docs = (await db.execute(
        select(CompanyDocument).where(CompanyDocument.company_id == company_id)
    )).scalars().all()
    for d in docs:
        delete_document_file(d.stored_path)

    # 清理所有关联分析数据，避免孤儿行
    from app.models.knowledge import KnowledgeChunk
    from app.models.briefing import CompanyExecutiveBriefing
    from app.models.strategy import CompanyStrategyReport
    from app.models.sales_market import CompanySalesReport, CompanyMarketReport
    for model in (CompanyDocument, CompanyFinancial, CompanyFinancialReport,
                  CompanyCompetitiveReport, CompanyDueDiligenceReport, KnowledgeChunk,
                  CompanyExecutiveBriefing, CompanyStrategyReport,
                  CompanySalesReport, CompanyMarketReport):
        await db.execute(sa_delete(model).where(model.company_id == company_id))

    await db.delete(company)
    await db.commit()
    return {"msg": "Deleted successfully"}