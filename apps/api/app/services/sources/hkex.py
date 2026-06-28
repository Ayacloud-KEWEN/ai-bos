"""HKEX 港交所 HKEXnews 连接器（港股，免 Key）。
- 搜索：activestock 列表（中英文名 + 代码）
- 抓取：titleSearchServlet（stockId = 股票代码整数）→ 最新年报 PDF
"""
import json
from .base import SourceConnector, Candidate, SourceDoc, FetchResult
from .http_util import http_get

_STOCK_C = "https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json"
_STOCK_E = "https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_e.json"
_SERVLET = ("https://www1.hkexnews.hk/search/titleSearchServlet.do?sortDir=0&sortByOptions=DateTime"
            "&category=0&market=SEHK&documentType=-1&fromDate=&toDate=&title=&t=&lang=en"
            "&rowRange=100&searchType=0&stockId=")
_BASE = "https://www1.hkexnews.hk"
_HDR = {"Referer": "https://www1.hkexnews.hk/search/titlesearch.xhtml", "User-Agent": "Mozilla/5.0"}

_STOCKS: list | None = None  # [{code, sid, name_zh, name_en}]


def _parse(raw: bytes) -> list:
    s = raw.decode("utf-8", "replace")
    i = s.find("[")
    return json.loads(s[i:]) if i >= 0 else json.loads(s)


def _load_stocks():
    """加载港股列表。注意：检索 servlet 的 stockId 是列表里的 `i`（内部序号），
    既不是股票代码、也不是 `s` 字段——用错会命中完全无关的公司。"""
    global _STOCKS
    if _STOCKS is None:
        by_code: dict[str, dict] = {}
        try:
            for x in _parse(http_get(_STOCK_E, _HDR, 30)):
                rec = by_code.setdefault(x["c"], {"code": x["c"], "sid": x.get("i"), "name_zh": "", "name_en": ""})
                rec["name_en"] = x.get("n", "")
                rec["sid"] = x.get("i")
        except Exception as e:
            print(f"[hkex] load EN failed: {e}")
        try:
            for x in _parse(http_get(_STOCK_C, _HDR, 30)):
                rec = by_code.setdefault(x["c"], {"code": x["c"], "sid": x.get("i"), "name_zh": "", "name_en": ""})
                rec["name_zh"] = x.get("n", "")
                if rec.get("sid") is None:
                    rec["sid"] = x.get("i")
        except Exception as e:
            print(f"[hkex] load ZH failed: {e}")
        _STOCKS = list(by_code.values())
    return _STOCKS


class HKEXConnector(SourceConnector):
    key = "hkex"
    label = "HKEX 港交所 (HK)"
    regions = ["HK"]
    needs_key = False

    def search(self, name: str, limit: int = 8) -> list[Candidate]:
        q = name.strip().lower()
        qd = q.lstrip("0")
        out = []
        for s in _load_stocks():
            code = s["code"]
            ne, nz = (s.get("name_en") or "").lower(), s.get("name_zh") or ""
            if q == code or qd == code.lstrip("0") or (q and (q in ne or q in nz)):
                out.append(Candidate(
                    source=self.key, name=s.get("name_en") or s.get("name_zh") or code,
                    external_id=code,
                    extra={"code": code, "sid": s.get("sid"), "name_zh": s.get("name_zh"), "region": "HK"},
                ))
            if len(out) >= limit:
                break
        return out

    def latest_marker(self, external_id: str) -> str | None:
        try:
            sid = None
            for s in _load_stocks():
                if s["code"] == external_id:
                    sid = s.get("sid"); break
            if sid is None:
                return None
            resp = json.loads(http_get(_SERVLET + str(sid), _HDR, 30).decode("utf-8", "replace"))
            res = resp.get("result")
            if isinstance(res, str):
                res = json.loads(res) if res not in ("null", "") else []
            if res:
                return f"{res[0].get('DATE_TIME')} {res[0].get('TITLE','')[:30]}"
        except Exception as e:
            print(f"[hkex] marker failed: {e}")
        return None

    def fetch(self, candidate: Candidate) -> FetchResult:
        code = candidate.extra.get("code", candidate.external_id)
        stock_id = candidate.extra.get("sid")
        if stock_id is None:  # 老候选/缺失时按代码回查内部 sid
            for s in _load_stocks():
                if s["code"] == code:
                    stock_id = s.get("sid")
                    break
        if stock_id is None:
            raise ValueError(f"Cannot resolve HKEX stockId for code {code}")
        resp = json.loads(http_get(_SERVLET + str(stock_id), _HDR, 30).decode("utf-8", "replace"))
        res = resp.get("result")
        if isinstance(res, str):
            res = json.loads(res) if res not in ("null", "") else []

        pick = None
        for r in res or []:
            t = (r.get("TITLE") or "").lower()
            if ("annual report" in t or "年報" in r.get("TITLE", "") or "年度報告" in r.get("TITLE", "")) \
                    and "summary" not in t and "摘要" not in r.get("TITLE", ""):
                pick = r
                break

        source_docs = []
        if pick and pick.get("FILE_LINK"):
            link = pick["FILE_LINK"]
            url = link if link.startswith("http") else _BASE + link
            try:
                pdf = http_get(url, _HDR, timeout=90)
                source_docs.append(SourceDoc(title=pick.get("TITLE", "Annual Report"), url=url,
                                             content=pdf, content_type="application/pdf", suffix=".pdf"))
            except Exception as e:
                print(f"[hkex] pdf download failed: {e}")

        name = candidate.name
        return FetchResult(
            name=name,
            profile={"industry": "HK-listed company", "location": "Hong Kong",
                     "summary": f"{name}（{code}.HK）港交所上市公司"},
            text="",
            currency="HKD",
            source_docs=source_docs,
        )
