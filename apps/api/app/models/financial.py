from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class CompanyFinancial(Base):
    """单期财务数据（时间序列）。每个公司每个报告期（年/季）一行。"""
    __tablename__ = "company_financials"

    id = Column(String, primary_key=True, default=lambda: f"f_{uuid.uuid4().hex[:8]}")
    company_id = Column(String, index=True, nullable=False)

    # 报告期标识
    period = Column(String, nullable=False)        # 例如 "FY2023" / "Q3 2024"
    year = Column(Integer, index=True)
    quarter = Column(Integer)                       # 1-4；为空表示年报
    currency = Column(String, default="USD")

    # 利润表 (Income Statement)
    revenue = Column(Float)
    gross_profit = Column(Float)
    operating_profit = Column(Float)
    net_profit = Column(Float)
    rnd_spending = Column(Float)

    # 资产负债表 (Balance Sheet)
    total_assets = Column(Float)
    total_liabilities = Column(Float)
    total_debt = Column(Float)
    cash_and_equivalents = Column(Float)

    # 现金流量表 (Cash Flow)
    operating_cash_flow = Column(Float)
    free_cash_flow = Column(Float)

    employee_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_financials_company_period", "company_id", "year", "quarter"),
    )


class CompanyFinancialReport(Base):
    """公司级财务分析报告（每公司一行，覆盖式更新）。存储 AI 生成的评分、洞察等。"""
    __tablename__ = "company_financial_reports"

    id = Column(String, primary_key=True, default=lambda: f"fr_{uuid.uuid4().hex[:8]}")
    company_id = Column(String, index=True, unique=True, nullable=False)

    # AI 评分 (0-100)
    financial_health_score = Column(Integer, default=0)
    growth_score = Column(Integer, default=0)
    profitability_score = Column(Integer, default=0)
    liquidity_score = Column(Integer, default=0)
    risk_score = Column(Integer, default=0)

    currency = Column(String, default="USD")
    fiscal_year = Column(String)

    # 结构化洞察 (JSON 数组)
    executive_summary = Column(Text)
    key_findings = Column(JSONB)          # [str]
    growth_drivers = Column(JSONB)        # [str]
    risks = Column(JSONB)                 # [str]
    opportunities = Column(JSONB)         # [str]
    segment_revenue = Column(JSONB)       # [{name, value}]
    geographic_revenue = Column(JSONB)    # [{region, value}]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
