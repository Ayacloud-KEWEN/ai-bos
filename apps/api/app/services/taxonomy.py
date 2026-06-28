"""行业分类标准 (Sector Taxonomy)。

用于把 LLM 抽取出的自由文本 industry（可能是中文/英文、写法各异）归一到一套
固定的标准行业枚举上，使同行业对标 (peer comparison) 能正确匹配。
"""
from typing import Optional

# 标准行业枚举（GICS 风格，精简到 16 个）
SECTORS = [
    "Software & Cloud",
    "Semiconductors & Hardware",
    "Artificial Intelligence",
    "Robotics & Automation",
    "Internet & E-Commerce",
    "Telecommunications",
    "Financial Services",
    "Healthcare & Pharma",
    "Biotechnology",
    "Industrials & Manufacturing",
    "Energy & Utilities",
    "Automotive & Mobility",
    "Consumer & Retail",
    "Media & Entertainment",
    "Real Estate & Construction",
    "Other",
]

_SECTOR_SET = set(SECTORS)

# 关键词 → 标准行业（小写匹配，含常见中英文写法）。用于回填历史数据与兜底。
_KEYWORDS: list[tuple[list[str], str]] = [
    (["robot", "robotic", "automation", "机器人", "自动化"], "Robotics & Automation"),
    (["semiconductor", "chip", "foundry", "wafer", "hardware", "芯片", "半导体", "硬件"], "Semiconductors & Hardware"),
    (["artificial intelligence", "machine learning", "deep learning", " ai ", "llm", "人工智能", "大模型", "智能"], "Artificial Intelligence"),
    (["cloud", "saas", "software", "platform", "enterprise software", "云", "软件", "平台"], "Software & Cloud"),
    (["e-commerce", "ecommerce", "marketplace", "internet", "online retail", "电商", "互联网"], "Internet & E-Commerce"),
    (["telecom", "5g", "network operator", "通信", "电信"], "Telecommunications"),
    (["bank", "fintech", "insurance", "payment", "asset management", "金融", "银行", "保险", "支付"], "Financial Services"),
    (["pharma", "hospital", "medical device", "healthcare", "clinic", "医疗", "制药", "医药"], "Healthcare & Pharma"),
    (["biotech", "genomics", "life science", "生物", "基因"], "Biotechnology"),
    (["manufactur", "industrial", "machinery", "factory", "制造", "工业"], "Industrials & Manufacturing"),
    (["energy", "oil", "gas", "solar", "renewable", "utility", "power", "能源", "电力", "光伏"], "Energy & Utilities"),
    (["automotive", "vehicle", "ev ", "electric vehicle", "mobility", "汽车", "电动车"], "Automotive & Mobility"),
    (["retail", "consumer", "fmcg", "apparel", "food", "beverage", "零售", "消费"], "Consumer & Retail"),
    (["media", "entertainment", "gaming", "game", "streaming", "传媒", "游戏", "娱乐"], "Media & Entertainment"),
    (["real estate", "construction", "property", "地产", "建筑", "房地产"], "Real Estate & Construction"),
]


def is_valid_sector(value: Optional[str]) -> bool:
    return value in _SECTOR_SET


def classify_sector(text: Optional[str]) -> str:
    """根据自由文本（行业 / 描述）关键词匹配出标准行业。匹配不到返回 'Other'。"""
    if not text:
        return "Other"
    # 已经是标准枚举则直接返回
    if text in _SECTOR_SET:
        return text
    low = f" {text.lower()} "
    for keywords, sector in _KEYWORDS:
        if any(k in low for k in keywords):
            return sector
    return "Other"


def normalize_sector(llm_sector: Optional[str], industry_text: Optional[str]) -> str:
    """优先采用 LLM 给出的标准行业；若不在枚举内，则用关键词回退分类。"""
    if is_valid_sector(llm_sector):
        return llm_sector  # type: ignore[return-value]
    # LLM 可能给了接近但非精确的写法，先按 LLM 文本分类，再按原始 industry 分类
    by_llm = classify_sector(llm_sector)
    if by_llm != "Other":
        return by_llm
    return classify_sector(industry_text)
