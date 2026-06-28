from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class CompanyStrategyReport(Base):
    """战略情报报告（Agent 06）。每公司一行，覆盖式。综合各维度给出战略选项与建议。"""
    __tablename__ = "company_strategy_reports"

    id = Column(String, primary_key=True, default=lambda: f"st_{uuid.uuid4().hex[:8]}")
    company_id = Column(String, index=True, unique=True, nullable=False)
    language = Column(String, default="en")

    executive_summary = Column(Text)
    # [{title, description, impact(1-5), feasibility(1-5), risk(1-5), investment, rationale}]
    strategic_options = Column(JSONB)
    # [{title, rationale, expected_outcome}]，顺序即优先级
    recommendations = Column(JSONB)
    # [{force, level(0-100, 越高=该力越强/越不利), summary}]
    porters_five_forces = Column(JSONB)
    growth_opportunities = Column(JSONB)  # [str]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
