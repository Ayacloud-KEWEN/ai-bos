"""财务情报接口：存储 / 读取公司财报数据与 AI 分析。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.models.financial import CompanyFinancial, CompanyFinancialReport
from app.models.company import Company
from app.services.financial_metrics import build_trend_analysis
from pydantic import BaseModel

router = APIRouter()

# 时间序列字段白名单（写入 CompanyFinancial 时使用）
_PERIOD_FIELDS = [
    "revenue", "gross_profit", "operating_profit", "net_profit", "rnd_spending",
    "total_assets", "total_liabilities", "total_debt", "cash_and_equivalents",
    "operating_cash_flow", "free_cash_flow", "employee_count",
]


def _latest_rev(periods):
    """从期间列表取最新一期的营收（按 year, quarter 排序）。"""
    best = None
    for p in periods:
        if p.get("revenue") is None:
            continue
        key = (p.get("year") or 0, p.get("quarter") or 0)
        if best is None or key > best[0]:
            best = (key, p.get("revenue"))
    return best[1] if best else None


async def persist_financials(db: AsyncSession, company_id: str, fin: dict, currency: str = "USD"):
    """将 analyzer 产出的 FinancialIntelligence dict 落库（覆盖式）。供 upload 调用。
    若为再分析（已有数据），检测财务变动并生成告警（Continuous Monitoring）。"""
    from app.services.alerts import create_alert
    currency = fin.get("currency") or currency

    # 0. 变动检测：捕获旧值（再分析时才有）
    old_rows = (await db.execute(
        select(CompanyFinancial).where(CompanyFinancial.company_id == company_id)
    )).scalars().all()
    old_report = (await db.execute(
        select(CompanyFinancialReport).where(CompanyFinancialReport.company_id == company_id)
    )).scalar_one_or_none()
    old_rev = _latest_rev([{"year": r.year, "quarter": r.quarter, "revenue": r.revenue} for r in old_rows])
    old_years = {r.year for r in old_rows if r.year}
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    cname = company.name if company else company_id

    # 1. 清掉旧的时间序列，重新写入
    await db.execute(delete(CompanyFinancial).where(CompanyFinancial.company_id == company_id))
    for p in fin.get("periods", []) or []:
        row = CompanyFinancial(
            company_id=company_id,
            period=p.get("period") or "N/A",
            year=p.get("year"),
            quarter=p.get("quarter"),
            currency=currency,
            **{k: p.get(k) for k in _PERIOD_FIELDS},
        )
        db.add(row)

    # 2. 覆盖式更新公司级分析报告
    existing = (
        await db.execute(
            select(CompanyFinancialReport).where(CompanyFinancialReport.company_id == company_id)
        )
    ).scalar_one_or_none()

    def _score(key):  # 评分字段必须为 0-100，绝不为 null（模型可能误返回 null）
        v = fin.get(key)
        return v if isinstance(v, (int, float)) else 0

    fields = dict(
        financial_health_score=_score("financial_health_score"),
        growth_score=_score("growth_score"),
        profitability_score=_score("profitability_score"),
        liquidity_score=_score("liquidity_score"),
        risk_score=_score("risk_score"),
        currency=currency,
        fiscal_year=str(fin.get("fiscal_year") or ""),
        executive_summary=fin.get("executive_summary", ""),
        key_findings=fin.get("key_findings", []),
        growth_drivers=fin.get("growth_drivers", []),
        risks=fin.get("risks", []),
        opportunities=fin.get("opportunities", []),
        segment_revenue=fin.get("segment_revenue", []),
        geographic_revenue=fin.get("geographic_revenue", []),
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(CompanyFinancialReport(company_id=company_id, **fields))

    # 2.5 变动检测告警（仅再分析时；首次分析 old_rows 为空，不告警）
    if old_rows:
        new_rev = _latest_rev(fin.get("periods", []) or [])
        if old_rev and new_rev and old_rev != 0:
            chg = (new_rev - old_rev) / abs(old_rev) * 100
            if abs(chg) >= 5:
                await create_alert(db, company_id, cname, "financial",
                    f"营收变动 {chg:+.1f}%",
                    f"最新营收 {new_rev} (此前 {old_rev})，{currency}。",
                    severity="warning" if abs(chg) >= 20 else "info")
        new_years = {p.get("year") for p in (fin.get("periods", []) or []) if p.get("year")}
        added = sorted(y for y in new_years - old_years if y)
        if added:
            await create_alert(db, company_id, cname, "financial",
                f"新增财报期间 {', '.join('FY'+str(y) for y in added)}",
                "检测到新的财务报告期。", severity="info")
        if old_report is not None:
            old_risk = old_report.risk_score or 0
            new_risk = fields["risk_score"]
            if new_risk - old_risk >= 15:
                await create_alert(db, company_id, cname, "risk",
                    f"财务风险评分上升 {old_risk}→{new_risk}",
                    "财务风险显著上升，建议复核。", severity="warning")


async def _company_metrics(db: AsyncSession, company_id: str, report: CompanyFinancialReport | None):
    """汇总单个公司用于对标的关键指标。"""
    rows = (
        await db.execute(
            select(CompanyFinancial).where(CompanyFinancial.company_id == company_id)
        )
    ).scalars().all()
    raw = [
        {"period": r.period, "year": r.year, "quarter": r.quarter,
         **{f: getattr(r, f) for f in _PERIOD_FIELDS}}
        for r in rows
    ]
    trend = build_trend_analysis(raw)
    s = trend["summary"]
    return {
        "revenue": s.get("latest_revenue"),
        "revenue_growth": s.get("yoy_revenue_growth"),
        "revenue_cagr": s.get("revenue_cagr"),
        "gross_margin": s.get("latest_gross_margin"),
        "net_margin": s.get("latest_net_margin"),
        "financial_health": report.financial_health_score if report else None,
        "growth_score": report.growth_score if report else None,
        "profitability_score": report.profitability_score if report else None,
    }


# 用于对标排名的指标（值越大越好）
_BENCH_METRICS = [
    "revenue", "revenue_growth", "revenue_cagr", "gross_margin",
    "net_margin", "financial_health", "growth_score", "profitability_score",
]


@router.get("/{company_id}/peers", tags=["Financial Intelligence"])
async def get_peers(company_id: str, db: AsyncSession = Depends(get_db)):
    """同行业对标：与同行业其他公司比较关键财务指标，并给出行业基准与百分位。"""
    target = (
        await db.execute(select(Company).where(Company.id == company_id))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Company not found")

    # 取同标准行业 (sector) 的所有公司；sector 为空时回退到自由文本 industry
    if target.sector:
        peers = (
            await db.execute(select(Company).where(Company.sector == target.sector))
        ).scalars().all()
    else:
        peers = (
            await db.execute(select(Company).where(Company.industry == target.industry))
        ).scalars().all()

    reports = {
        r.company_id: r
        for r in (await db.execute(select(CompanyFinancialReport))).scalars().all()
    }

    # 只纳入"有财务数据"的公司参与对标（目标公司始终保留），
    # 避免大量无财报的竞品 stub 把对标表撑成空行。
    rows = []
    for c in peers:
        if c.id != company_id and c.id not in reports:
            continue
        m = await _company_metrics(db, c.id, reports.get(c.id))
        rows.append({"company_id": c.id, "name": c.name, "is_target": c.id == company_id, **m})

    # 行业基准：每个指标的均值；以及目标公司的百分位
    benchmarks = {}
    target_row = next((r for r in rows if r["is_target"]), None)
    for metric in _BENCH_METRICS:
        vals = [r[metric] for r in rows if r.get(metric) is not None]
        avg = round(sum(vals) / len(vals), 1) if vals else None
        pctile = None
        if target_row and target_row.get(metric) is not None and len(vals) > 1:
            below = sum(1 for v in vals if v < target_row[metric])
            pctile = round(below / (len(vals) - 1) * 100)
        benchmarks[metric] = {"industry_avg": avg, "target_percentile": pctile}

    return {
        "company_id": company_id,
        "industry": target.sector or target.industry,
        "peer_count": len(rows),
        "peers": sorted(rows, key=lambda r: (r.get("revenue") or 0), reverse=True),
        "benchmarks": benchmarks,
        "has_peers": len(rows) > 1,
    }


@router.get("/{company_id}/financials", tags=["Financial Intelligence"])
async def get_financials(company_id: str, db: AsyncSession = Depends(get_db)):
    """返回公司财务全景：评分、洞察、时间序列（含派生指标与趋势）。"""
    company = (
        await db.execute(select(Company).where(Company.id == company_id))
    ).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    report = (
        await db.execute(
            select(CompanyFinancialReport).where(CompanyFinancialReport.company_id == company_id)
        )
    ).scalar_one_or_none()

    rows = (
        await db.execute(
            select(CompanyFinancial).where(CompanyFinancial.company_id == company_id)
        )
    ).scalars().all()

    raw_periods = [
        {
            "id": r.id,
            "period": r.period, "year": r.year, "quarter": r.quarter, "currency": r.currency,
            **{f: getattr(r, f) for f in _PERIOD_FIELDS},
        }
        for r in rows
    ]
    trend = build_trend_analysis(raw_periods)

    has_data = bool(report) or bool(raw_periods)

    return {
        "company_id": company_id,
        "company_name": company.name,
        "has_data": has_data,
        "currency": report.currency if report else "USD",
        "fiscal_year": report.fiscal_year if report else None,
        "scores": {
            "financial_health": report.financial_health_score if report else 0,
            "growth": report.growth_score if report else 0,
            "profitability": report.profitability_score if report else 0,
            "liquidity": report.liquidity_score if report else 0,
            "risk": report.risk_score if report else 0,
        } if report else None,
        "executive_summary": report.executive_summary if report else None,
        "key_findings": (report.key_findings if report else []) or [],
        "growth_drivers": (report.growth_drivers if report else []) or [],
        "risks": (report.risks if report else []) or [],
        "opportunities": (report.opportunities if report else []) or [],
        "segment_revenue": (report.segment_revenue if report else []) or [],
        "geographic_revenue": (report.geographic_revenue if report else []) or [],
        "trend": trend,
    }


# ==========================================================================
# 财报数据人工校正 (CRUD)：AI 抽取难免出错，允许逐期手动增删改
# ==========================================================================
class FinancialPeriodInput(BaseModel):
    period: str
    year: int | None = None
    quarter: int | None = None
    currency: str | None = "USD"
    revenue: float | None = None
    gross_profit: float | None = None
    operating_profit: float | None = None
    net_profit: float | None = None
    rnd_spending: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_debt: float | None = None
    cash_and_equivalents: float | None = None
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None
    employee_count: int | None = None


@router.post("/{company_id}/financials/periods", tags=["Financial Intelligence"])
async def add_financial_period(company_id: str, body: FinancialPeriodInput, db: AsyncSession = Depends(get_db)):
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    row = CompanyFinancial(
        company_id=company_id, period=body.period, year=body.year, quarter=body.quarter,
        currency=body.currency or "USD", **{f: getattr(body, f) for f in _PERIOD_FIELDS},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"msg": "Period added", "id": row.id}


@router.patch("/{company_id}/financials/periods/{period_id}", tags=["Financial Intelligence"])
async def update_financial_period(company_id: str, period_id: str, body: FinancialPeriodInput, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(
            select(CompanyFinancial).where(
                CompanyFinancial.id == period_id, CompanyFinancial.company_id == company_id
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Financial period not found")
    row.period = body.period
    row.year = body.year
    row.quarter = body.quarter
    if body.currency:
        row.currency = body.currency
    for f in _PERIOD_FIELDS:
        setattr(row, f, getattr(body, f))
    await db.commit()
    return {"msg": "Period updated"}


@router.delete("/{company_id}/financials/periods/{period_id}", tags=["Financial Intelligence"])
async def delete_financial_period(company_id: str, period_id: str, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(
            select(CompanyFinancial).where(
                CompanyFinancial.id == period_id, CompanyFinancial.company_id == company_id
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Financial period not found")
    await db.delete(row)
    await db.commit()
    return {"msg": "Period deleted"}
