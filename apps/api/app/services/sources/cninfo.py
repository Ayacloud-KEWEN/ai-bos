"""巨潮资讯 CNINFO 连接器（A 股，免 Key）。
- 搜索：topSearch/query → 股票代码 + orgId
- 抓取：hisAnnouncement/query 取最新年度报告 → 下载 PDF（走现有 PDF 分析流水线）
"""
from .base import SourceConnector, Candidate, SourceDoc, FetchResult
from .http_util import post_json, http_get

_SEARCH = "http://www.cninfo.com.cn/new/information/topSearch/query"
_ANN = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
_STATIC = "http://static.cninfo.com.cn/"
_HDR = {"Referer": "http://www.cninfo.com.cn/", "User-Agent": "Mozilla/5.0"}


class CNInfoConnector(SourceConnector):
    key = "cninfo"
    label = "巨潮资讯 CNINFO (A股)"
    regions = ["CN"]
    needs_key = False

    def search(self, name: str, limit: int = 8) -> list[Candidate]:
        rows = post_json(_SEARCH, {"keyWord": name.strip(), "maxNum": str(limit)}, _HDR)
        out = []
        for r in rows if isinstance(rows, list) else []:
            code = r.get("code")
            org = r.get("orgId")
            if not code or not org:
                continue
            out.append(Candidate(
                source=self.key,
                name=r.get("zwjc") or r.get("pinyin") or code,
                external_id=f"{code}:{org}",
                extra={"code": code, "orgId": org, "category": r.get("category"), "region": "CN"},
            ))
        return out

    def latest_marker(self, external_id: str) -> str | None:
        try:
            code, org = external_id.split(":")
            resp = post_json(_ANN, {
                "stock": f"{code},{org}", "tabName": "fulltext", "pageSize": "5", "pageNum": "1",
                "column": "szse", "category": "", "plate": "", "seDate": "", "searchkey": "",
                "secid": "", "sortName": "", "sortType": "", "isHLtitle": "true",
            }, _HDR)
            anns = resp.get("announcements") or []
            if anns:
                a = anns[0]
                return f"{a.get('announcementTime')} {a.get('announcementTitle','')[:30]}"
        except Exception as e:
            print(f"[cninfo] marker failed: {e}")
        return None

    def fetch(self, candidate: Candidate) -> FetchResult:
        code = candidate.extra["code"]
        org = candidate.extra["orgId"]
        body = {
            "stock": f"{code},{org}", "tabName": "fulltext", "pageSize": "30", "pageNum": "1",
            "column": "szse", "category": "category_ndbg_szsh;", "plate": "", "seDate": "",
            "searchkey": "", "secid": "", "sortName": "", "sortType": "", "isHLtitle": "true",
        }
        resp = post_json(_ANN, body, _HDR)
        anns = resp.get("announcements") or []
        # 选最新的正式年度报告（排除摘要/英文/已取消）
        pick = None
        sec_name = candidate.name
        for a in anns:
            title = a.get("announcementTitle", "")
            sec_name = a.get("secName") or sec_name
            if "年度报告" in title and not any(k in title for k in ("摘要", "英文", "已取消", "提示")):
                pick = a
                break
        if not pick and anns:
            pick = anns[0]

        source_docs = []
        if pick and pick.get("adjunctUrl"):
            try:
                pdf = http_get(_STATIC + pick["adjunctUrl"], _HDR, timeout=60)
                source_docs.append(SourceDoc(
                    title=pick.get("announcementTitle", "年度报告"),
                    url=_STATIC + pick["adjunctUrl"], content=pdf,
                    content_type="application/pdf", suffix=".pdf",
                ))
            except Exception as e:
                print(f"[cninfo] pdf download failed: {e}")

        return FetchResult(
            name=sec_name,
            profile={"industry": candidate.extra.get("category") or "A股上市公司",
                     "location": "中国", "summary": f"{sec_name}（{code}）A股上市公司"},
            text="",  # 分析来自下载的年报 PDF
            currency="CNY",
            source_docs=source_docs,
        )
