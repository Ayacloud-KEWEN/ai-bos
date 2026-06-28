"""汇总单个公司的全维度情报（财务/竞争/尽调/简报），供 CEO 简报与报告导出复用。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.financial import CompanyFinancial, CompanyFinancialReport
from app.models.competitive import CompanyCompetitiveReport
from app.models.due_diligence import CompanyDueDiligenceReport
from app.services.financial_metrics import build_trend_analysis

_PERIOD_FIELDS = [
    "revenue", "gross_profit", "operating_profit", "net_profit", "rnd_spending",
    "total_assets", "total_liabilities", "total_debt", "cash_and_equivalents",
    "operating_cash_flow", "free_cash_flow", "employee_count",
]


async def gather_intelligence(db: AsyncSession, company_id: str) -> dict | None:
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        return None

    fin = (await db.execute(select(CompanyFinancialReport).where(CompanyFinancialReport.company_id == company_id))).scalar_one_or_none()
    comp = (await db.execute(select(CompanyCompetitiveReport).where(CompanyCompetitiveReport.company_id == company_id))).scalar_one_or_none()
    dd = (await db.execute(select(CompanyDueDiligenceReport).where(CompanyDueDiligenceReport.company_id == company_id))).scalar_one_or_none()

    rows = (await db.execute(select(CompanyFinancial).where(CompanyFinancial.company_id == company_id))).scalars().all()
    raw = [{"period": r.period, "year": r.year, "quarter": r.quarter,
            **{f: getattr(r, f) for f in _PERIOD_FIELDS}} for r in rows]
    trend = build_trend_analysis(raw) if raw else {"periods": [], "summary": {}}

    # 延迟导入避免循环
    from app.models.briefing import CompanyExecutiveBriefing
    from app.models.strategy import CompanyStrategyReport
    from app.models.sales_market import CompanySalesReport, CompanyMarketReport
    brief = (await db.execute(select(CompanyExecutiveBriefing).where(CompanyExecutiveBriefing.company_id == company_id))).scalar_one_or_none()
    strat = (await db.execute(select(CompanyStrategyReport).where(CompanyStrategyReport.company_id == company_id))).scalar_one_or_none()
    sales = (await db.execute(select(CompanySalesReport).where(CompanySalesReport.company_id == company_id))).scalar_one_or_none()
    market = (await db.execute(select(CompanyMarketReport).where(CompanyMarketReport.company_id == company_id))).scalar_one_or_none()

    return {
        "company": {
            "id": company.id, "name": company.name, "industry": company.industry,
            "sector": company.sector, "location": company.location, "status": company.status,
            "intelligence_score": company.intelligence_score, "summary": company.summary,
            "documents_analyzed": company.documents_analyzed,
        },
        "financial": None if not fin else {
            "currency": fin.currency, "fiscal_year": fin.fiscal_year,
            "scores": {"financial_health": fin.financial_health_score, "growth": fin.growth_score,
                       "profitability": fin.profitability_score, "liquidity": fin.liquidity_score,
                       "risk": fin.risk_score},
            "executive_summary": fin.executive_summary, "key_findings": fin.key_findings or [],
            "growth_drivers": fin.growth_drivers or [], "risks": fin.risks or [],
            "opportunities": fin.opportunities or [], "segment_revenue": fin.segment_revenue or [],
            "geographic_revenue": fin.geographic_revenue or [], "trend": trend,
        },
        "competitive": None if not comp else {
            "market_position": comp.market_position, "positioning_score": comp.positioning_score,
            "swot": {"strengths": comp.strengths or [], "weaknesses": comp.weaknesses or [],
                     "opportunities": comp.opportunities or [], "threats": comp.threats or []},
            "competitors": comp.competitors or [], "battlecards": comp.battlecards or [],
            "technology_trends": comp.technology_trends or [],
        },
        "due_diligence": None if not dd else {
            "overall_score": dd.overall_score, "recommendation": dd.recommendation,
            "executive_summary": dd.executive_summary, "risk_categories": dd.risk_categories or [],
            "red_flags": dd.red_flags or [], "opportunities": dd.opportunities or [],
        },
        "briefing": None if not brief else {
            "summary": brief.summary, "what_happened": brief.what_happened,
            "why_it_matters": brief.why_it_matters, "recommended_actions": brief.recommended_actions or [],
            "key_risks": brief.key_risks or [], "opportunities": brief.opportunities or [],
            "next_actions": brief.next_actions or [], "language": brief.language,
        },
        "strategy": None if not strat else {
            "executive_summary": strat.executive_summary,
            "strategic_options": strat.strategic_options or [],
            "recommendations": strat.recommendations or [],
            "porters_five_forces": strat.porters_five_forces or [],
            "growth_opportunities": strat.growth_opportunities or [],
        },
        "sales": None if not sales else {
            "executive_summary": sales.executive_summary, "icp": sales.icp or [],
            "buyer_personas": sales.buyer_personas or [], "pain_points": sales.pain_points or [],
            "buying_triggers": sales.buying_triggers or [], "sales_opportunities": sales.sales_opportunities or [],
        },
        "market": None if not market else {
            "executive_summary": market.executive_summary, "tam": market.tam, "sam": market.sam,
            "som": market.som, "market_growth": market.market_growth, "trends": market.trends or [],
            "drivers": market.drivers or [], "barriers": market.barriers or [], "segments": market.segments or [],
        },
    }


def intelligence_to_text(intel: dict) -> str:
    """把汇总情报压成一段文本，供 CEO 简报 LLM 综合。"""
    c = intel["company"]
    parts = [f"公司: {c['name']} | 行业: {c.get('industry')} | 地区: {c.get('location')}",
             f"概要: {c.get('summary')}"]
    f = intel.get("financial")
    if f:
        s = f["trend"]["summary"]
        parts.append(f"\n[财务] 评分(健康/成长/盈利/流动/风险): {f['scores']}")
        parts.append(f"最新营收: {s.get('latest_revenue')} {f['currency']}, 同比: {s.get('yoy_revenue_growth')}%, "
                     f"CAGR: {s.get('revenue_cagr')}%, 净利率: {s.get('latest_net_margin')}%")
        if f["key_findings"]:
            parts.append("财务发现: " + "; ".join(f["key_findings"][:5]))
        if f["risks"]:
            parts.append("财务风险: " + "; ".join(f["risks"][:5]))
    comp = intel.get("competitive")
    if comp:
        parts.append(f"\n[竞争] 定位: {comp['market_position']} (护城河 {comp['positioning_score']})")
        parts.append("优势: " + "; ".join(comp["swot"]["strengths"][:4]))
        parts.append("劣势: " + "; ".join(comp["swot"]["weaknesses"][:4]))
        parts.append("威胁: " + "; ".join(comp["swot"]["threats"][:4]))
        parts.append("主要竞品: " + ", ".join(x.get("name", "") for x in comp["competitors"][:6]))
    dd = intel.get("due_diligence")
    if dd:
        parts.append(f"\n[尽调] 综合吸引力 {dd['overall_score']}/100，建议: {dd['recommendation']}")
        if dd["red_flags"]:
            parts.append("红旗: " + "; ".join(dd["red_flags"][:5]))
        for rc in (dd["risk_categories"] or [])[:5]:
            parts.append(f"{rc.get('label', rc.get('key'))} 风险({rc.get('score')}): {rc.get('summary')}")
    return "\n".join(parts)
