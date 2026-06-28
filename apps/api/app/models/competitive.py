from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class CompanyCompetitiveReport(Base):
    """公司级竞争情报报告（每公司一行，覆盖式更新）。对应 Agent 03。"""
    __tablename__ = "company_competitive_reports"

    id = Column(String, primary_key=True, default=lambda: f"cr_{uuid.uuid4().hex[:8]}")
    company_id = Column(String, index=True, unique=True, nullable=False)

    market_position = Column(Text)          # 市场定位一句话总结
    positioning_score = Column(Integer, default=0)  # 0-100 竞争强度/护城河

    # SWOT
    strengths = Column(JSONB)               # [str]
    weaknesses = Column(JSONB)              # [str]
    opportunities = Column(JSONB)           # [str]
    threats = Column(JSONB)                 # [str]

    # 竞争对手矩阵： [{name, type, description, strengths[], weaknesses[], threat_level(1-5)}]
    competitors = Column(JSONB)
    # 战卡： [{competitor, why_we_win[], why_we_lose[], objection_handling[]}]
    battlecards = Column(JSONB)
    technology_trends = Column(JSONB)       # [str]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
