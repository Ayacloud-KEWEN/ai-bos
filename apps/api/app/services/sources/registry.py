"""数据源注册表：按 key 取连接器、列出可用源。

已实现（免 Key）：SEC EDGAR、巨潮资讯 CNINFO、HKEX 港交所。
规划中：Companies House / Firecrawl / Exa（需 Key）。
"""
from .base import SourceConnector
from .sec_edgar import SECEdgarConnector
from .cninfo import CNInfoConnector
from .hkex import HKEXConnector

_CONNECTORS: dict[str, SourceConnector] = {
    c.key: c for c in [SECEdgarConnector(), CNInfoConnector(), HKEXConnector()]
}

# 规划中的源（前端展示为"即将支持"，不可选）
_PLANNED = [
    {"key": "companies_house", "label": "Companies House (UK)", "regions": ["UK"], "needs_key": True},
    {"key": "firecrawl", "label": "Firecrawl (任意网页)", "regions": ["*"], "needs_key": True},
    {"key": "exa", "label": "Exa (语义搜索)", "regions": ["*"], "needs_key": True},
]


def get_connector(key: str) -> SourceConnector | None:
    return _CONNECTORS.get(key)


def list_sources() -> list[dict]:
    available = [
        {"key": c.key, "label": c.label, "regions": c.regions,
         "needs_key": c.needs_key, "available": True}
        for c in _CONNECTORS.values()
    ]
    planned = [{**p, "available": False} for p in _PLANNED]
    return available + planned
