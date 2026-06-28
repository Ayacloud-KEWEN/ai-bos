from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class CompanyExecutiveBriefing(Base):
    """CEO 执行简报（Agent 08）。每公司一行，覆盖式。综合财务/竞争/尽调。"""
    __tablename__ = "company_executive_briefings"

    id = Column(String, primary_key=True, default=lambda: f"eb_{uuid.uuid4().hex[:8]}")
    company_id = Column(String, index=True, unique=True, nullable=False)
    language = Column(String, default="en")

    summary = Column(Text)            # 一句话标题结论
    what_happened = Column(Text)
    why_it_matters = Column(Text)
    recommended_actions = Column(JSONB)   # [str]
    key_risks = Column(JSONB)             # [str]
    opportunities = Column(JSONB)         # [str]
    next_actions = Column(JSONB)          # [str]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
