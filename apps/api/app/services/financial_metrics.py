"""派生财务指标计算：利润率、同比/环比增长、CAGR、杠杆率等。
纯函数，不依赖数据库，便于单测。"""
from typing import List, Dict, Any, Optional


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b in (None, 0):
        return None
    return a / b


def _pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """返回 a 相对 b 的增长百分比 (round 1 位)。"""
    if a is None or b in (None, 0):
        return None
    return round((a - b) / abs(b) * 100, 1)


def compute_period_metrics(period: Dict[str, Any]) -> Dict[str, Any]:
    """为单期补充利润率等比率（百分比）。"""
    rev = period.get("revenue")
    gm = _safe_div(period.get("gross_profit"), rev)
    om = _safe_div(period.get("operating_profit"), rev)
    nm = _safe_div(period.get("net_profit"), rev)
    return {
        **period,
        "gross_margin": round(gm * 100, 1) if gm is not None else None,
        "operating_margin": round(om * 100, 1) if om is not None else None,
        "net_margin": round(nm * 100, 1) if nm is not None else None,
        "debt_to_assets": (
            round(_safe_div(period.get("total_debt"), period.get("total_assets")) * 100, 1)
            if _safe_div(period.get("total_debt"), period.get("total_assets")) is not None
            else None
        ),
        "rnd_intensity": (
            round(_safe_div(period.get("rnd_spending"), rev) * 100, 1)
            if _safe_div(period.get("rnd_spending"), rev) is not None
            else None
        ),
    }


def _sort_key(p: Dict[str, Any]):
    return (p.get("year") or 0, p.get("quarter") or 0)


def build_trend_analysis(periods: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算时间序列趋势：逐期增长、YoY、CAGR。periods 应已含基础字段。"""
    ordered = sorted(periods, key=_sort_key)
    enriched = [compute_period_metrics(p) for p in ordered]

    # 逐期（环比）增长
    for i, p in enumerate(enriched):
        prev = enriched[i - 1] if i > 0 else None
        p["revenue_growth"] = _pct(p.get("revenue"), prev.get("revenue")) if prev else None
        p["net_profit_growth"] = _pct(p.get("net_profit"), prev.get("net_profit")) if prev else None

    summary: Dict[str, Any] = {
        "latest_revenue": None,
        "yoy_revenue_growth": None,
        "revenue_cagr": None,
        "latest_net_margin": None,
        "latest_gross_margin": None,
        "periods_count": len(enriched),
    }

    if enriched:
        latest = enriched[-1]
        summary["latest_revenue"] = latest.get("revenue")
        summary["latest_net_margin"] = latest.get("net_margin")
        summary["latest_gross_margin"] = latest.get("gross_margin")

        # 同比：找去年同季度（或上一年报）
        if len(enriched) >= 2:
            summary["yoy_revenue_growth"] = _pct(
                latest.get("revenue"), enriched[-2].get("revenue")
            )

        # CAGR（首末年报口径，按周期数近似）
        first = enriched[0]
        n = len(enriched) - 1
        r0, rN = first.get("revenue"), latest.get("revenue")
        if r0 and rN and n >= 1 and r0 > 0:
            summary["revenue_cagr"] = round(((rN / r0) ** (1 / n) - 1) * 100, 1)

    return {"periods": enriched, "summary": summary}
