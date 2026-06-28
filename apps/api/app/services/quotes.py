"""上市公司股价 + 详情站点链接。行情用雅虎财经（免 Key，覆盖美/中/港）。"""
import json
import urllib.request

_CIK_TICKER: dict | None = None


def _cik_to_ticker(cik: str) -> str | None:
    global _CIK_TICKER
    if _CIK_TICKER is None:
        from app.services.sources.sec_edgar import _load_tickers
        _CIK_TICKER = {str(r["cik_str"]).zfill(10): r.get("ticker") for r in _load_tickers()}
    return _CIK_TICKER.get(cik.zfill(10))


def resolve(source: str | None, external_id: str | None) -> dict | None:
    """根据数据源 + 外部 id 解析出 yahoo symbol、展示代码、详情链接。"""
    if not source or not external_id:
        return None

    if source == "sec_edgar":
        ticker = _cik_to_ticker(external_id)
        if not ticker:
            return None
        return {
            "symbol": ticker, "display": ticker, "market": "US",
            "detail_url": f"https://finance.yahoo.com/quote/{ticker}",
            "filings_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={external_id}&type=10-K",
            "filings_label": "SEC EDGAR",
        }

    if source == "cninfo":
        code = external_id.split(":")[0]
        org = external_id.split(":")[1] if ":" in external_id else ""
        suffix = ".SS" if code[:1] in ("6", "9") else ".SZ"
        return {
            "symbol": f"{code}{suffix}", "display": code, "market": "CN",
            "detail_url": f"http://www.cninfo.com.cn/new/disclosure/stock?stockCode={code}&orgId={org}",
            "filings_url": f"https://quote.eastmoney.com/{'sh' if suffix=='.SS' else 'sz'}{code}.html",
            "filings_label": "巨潮/东方财富",
        }

    if source == "hkex":
        code4 = external_id.lstrip("0").zfill(4)
        return {
            "symbol": f"{code4}.HK", "display": external_id, "market": "HK",
            "detail_url": f"https://finance.yahoo.com/quote/{code4}.HK",
            "filings_url": f"https://www1.hkexnews.hk/search/titlesearch.xhtml",
            "filings_label": "HKEXnews",
        }
    return None


def fetch_quote(symbol: str) -> dict | None:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "replace"))
        m = d["chart"]["result"][0]["meta"]
    except Exception as e:
        print(f"[quote] fetch failed {symbol}: {e}")
        return None
    price = m.get("regularMarketPrice")
    prev = m.get("chartPreviousClose") or m.get("previousClose")
    change = (price - prev) if (price is not None and prev is not None) else None
    pct = (change / prev * 100) if (change is not None and prev) else None
    return {
        "price": price, "currency": m.get("currency"), "previous_close": prev,
        "change": round(change, 2) if change is not None else None,
        "change_pct": round(pct, 2) if pct is not None else None,
        "exchange": m.get("exchangeName"), "market_state": m.get("marketState"),
        "market_time": m.get("regularMarketTime"),
    }
