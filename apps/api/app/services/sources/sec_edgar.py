"""SEC EDGAR 连接器（美股，免 Key）。
- 搜索：company_tickers.json 名称/代码匹配 → CIK
- 抓取：submissions(概况+近期文件) + companyfacts(XBRL 结构化财务)
"""
from .base import SourceConnector, Candidate, SourceDoc, FetchResult
from .http_util import get_json

_TICKERS_CACHE: list | None = None


def _load_tickers():
    global _TICKERS_CACHE
    if _TICKERS_CACHE is None:
        data = get_json("https://www.sec.gov/files/company_tickers.json")
        _TICKERS_CACHE = list(data.values())  # [{cik_str, ticker, title}]
    return _TICKERS_CACHE


# us-gaap 概念到我们字段的映射（按优先级取第一个有值的）
_CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "gross_profit": ["GrossProfit"],
    "operating_profit": ["OperatingIncomeLoss"],
    "net_profit": ["NetIncomeLoss"],
    "rnd_spending": ["ResearchAndDevelopmentExpense"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
}


def _annual_values(facts: dict, concepts: list[str]) -> dict[int, float]:
    """返回 {fiscalYear: value}，取年报(10-K, FY) USD 数据。"""
    gaap = facts.get("us-gaap", {})
    out: dict[int, float] = {}
    for concept in concepts:
        node = gaap.get(concept)
        if not node:
            continue
        for item in node.get("units", {}).get("USD", []):
            if item.get("fp") == "FY" and item.get("form") in ("10-K", "10-K/A") and item.get("fy"):
                out[int(item["fy"])] = item["val"]  # 后到的覆盖（取最新口径）
        if out:
            break
    return out


class SECEdgarConnector(SourceConnector):
    key = "sec_edgar"
    label = "SEC EDGAR (US)"
    regions = ["US"]
    needs_key = False

    def search(self, name: str, limit: int = 8) -> list[Candidate]:
        q = name.strip().lower()
        rows = _load_tickers()
        scored = []
        for r in rows:
            title = (r.get("title") or "").lower()
            ticker = (r.get("ticker") or "").lower()
            if q == ticker:
                scored.append((0, r))
            elif title.startswith(q):
                scored.append((1, r))
            elif q in title:
                scored.append((2, r))
        scored.sort(key=lambda x: x[0])
        # 按 CIK 去重：同一公司可能有多个股票代码（如普通股+认股权证），共用一个 CIK
        out, seen = [], set()
        for _, r in scored:
            cik = str(r["cik_str"]).zfill(10)
            if cik in seen:
                continue
            seen.add(cik)
            out.append(Candidate(
                source=self.key, name=r["title"], external_id=cik,
                extra={"ticker": r.get("ticker"), "region": "US"},
            ))
            if len(out) >= limit:
                break
        return out

    def latest_marker(self, external_id: str) -> str | None:
        try:
            sub = get_json(f"https://data.sec.gov/submissions/CIK{external_id.zfill(10)}.json")
            r = sub.get("filings", {}).get("recent", {})
            if r.get("accessionNumber"):
                return f"{r['form'][0]} {r['filingDate'][0]} {r['accessionNumber'][0]}"
        except Exception as e:
            print(f"[sec] marker failed: {e}")
        return None

    def fetch(self, candidate: Candidate) -> FetchResult:
        cik = candidate.external_id.zfill(10)
        sub = get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
        name = sub.get("name", candidate.name)
        sic_desc = sub.get("sicDescription", "")
        addr = (sub.get("addresses", {}) or {}).get("business", {}) or {}
        location = ", ".join(filter(None, [addr.get("city"), addr.get("stateOrCountry")]))

        # 结构化财务（XBRL）
        periods = []
        try:
            facts = get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").get("facts", {})
            by_field = {f: _annual_values(facts, cs) for f, cs in _CONCEPTS.items()}
            years = sorted({y for vals in by_field.values() for y in vals})[-5:]
            for y in years:
                p = {"period": f"FY{y}", "year": y, "quarter": None}
                for f in _CONCEPTS:
                    p[f] = by_field[f].get(y)
                periods.append(p)
        except Exception as e:
            print(f"[sec] XBRL fetch failed: {e}")

        # 供 LLM 竞争/尽调分析的文本（SEC 结构化数据 + 近期文件清单）
        recent = sub.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])[:12]
        dates = recent.get("filingDate", [])[:12]
        filings_txt = "\n".join(f"- {d} {f}" for f, d in zip(forms, dates))
        fin_txt = ""
        if periods:
            latest = periods[-1]
            fin_txt = (f"Latest fiscal year {latest['year']}: revenue={latest.get('revenue')}, "
                       f"net income={latest.get('net_profit')}, total assets={latest.get('total_assets')}, "
                       f"operating cash flow={latest.get('operating_cash_flow')} (USD).")
        text = (f"Company: {name}\nIndustry (SIC): {sic_desc}\nLocation: {location}\n"
                f"Ticker: {candidate.extra.get('ticker')}\n\nFinancial summary: {fin_txt}\n\n"
                f"Recent SEC filings:\n{filings_txt}\n")

        return FetchResult(
            name=name,
            profile={"industry": sic_desc or "Public Company", "sector": None,
                     "location": location or "United States", "summary": text[:600]},
            text=text,
            financial_periods=periods or None,
            currency="USD",
            source_docs=[SourceDoc(
                title=f"{name} — SEC profile & financials",
                content=text.encode("utf-8"), content_type="text/plain", suffix=".txt",
            )],
        )
