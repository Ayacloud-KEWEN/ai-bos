"""数据源连接器统一接口。

每个连接器（SEC EDGAR / 巨潮 / HKEX / Companies House / Firecrawl / Exa）实现：
- search(name): 按名称/代码搜索候选公司
- fetch(candidate): 抓取该公司的可分析文本、(可选)结构化财务、原始文件

网络 I/O 用同步实现，调用方通过 asyncio.to_thread 包装，避免阻塞事件循环。
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Candidate:
    source: str
    name: str
    external_id: str                 # CIK / orgId / 股票代码 等
    extra: dict = field(default_factory=dict)   # ticker, exchange, region...


@dataclass
class SourceDoc:
    title: str
    url: Optional[str] = None
    content: Optional[bytes] = None  # 已下载的文件字节（PDF），用于存为附件
    content_type: str = "application/pdf"
    suffix: str = ".pdf"


@dataclass
class FetchResult:
    name: str
    profile: dict = field(default_factory=dict)   # {industry, sector, location, website, summary}
    text: str = ""                                # 供分析的文本（业务/财务叙述）
    financial_periods: Optional[List[dict]] = None  # 结构化财务期间（如 SEC XBRL），可直接入库
    currency: str = "USD"
    source_docs: List[SourceDoc] = field(default_factory=list)


class SourceConnector:
    key: str = "base"
    label: str = "Base"
    regions: List[str] = []
    needs_key: bool = False

    def search(self, name: str, limit: int = 8) -> List[Candidate]:
        raise NotImplementedError

    def fetch(self, candidate: Candidate) -> FetchResult:
        raise NotImplementedError

    def latest_marker(self, external_id: str) -> str | None:
        """返回该公司"最新披露"的轻量标记（不下载文件），用于监控变动检测。"""
        return None
