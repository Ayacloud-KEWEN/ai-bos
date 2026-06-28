from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class CompanySalesReport(Base):
    """销售情报报告（Agent 04）。每公司一行，覆盖式。"""
    __tablename__ = "company_sales_reports"

    id = Column(String, primary_key=True, default=lambda: f"sa_{uuid.uuid4().hex[:8]}")
    company_id = Column(String, index=True, unique=True, nullable=False)
    language = Column(String, default="en")

    executive_summary = Column(Text)
    icp = Column(JSONB)              # [{segment, description, why_fit}]
    buyer_personas = Column(JSONB)   # [{role, goals, pain_points[]}]
    pain_points = Column(JSONB)      # [str]
    buying_triggers = Column(JSONB)  # [str]
    sales_opportunities = Column(JSONB)  # [str]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CompanyMarketReport(Base):
    """市场情报报告（Agent 05）。每公司一行，覆盖式。"""
    __tablename__ = "company_market_reports"

    id = Column(String, primary_key=True, default=lambda: f"mk_{uuid.uuid4().hex[:8]}")
    company_id = Column(String, index=True, unique=True, nullable=False)
    language = Column(String, default="en")

    executive_summary = Column(Text)
    tam = Column(String)
    sam = Column(String)
    som = Column(String)
    market_growth = Column(String)
    trends = Column(JSONB)           # [str]
    drivers = Column(JSONB)          # [str]
    barriers = Column(JSONB)         # [str]
    segments = Column(JSONB)         # [{name, description}]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
