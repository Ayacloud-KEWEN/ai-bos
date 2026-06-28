from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class CompanyDueDiligenceReport(Base):
    """公司级尽职调查报告（每公司一行，覆盖式更新）。对应 Agent 07。"""
    __tablename__ = "company_due_diligence_reports"

    id = Column(String, primary_key=True, default=lambda: f"dd_{uuid.uuid4().hex[:8]}")
    company_id = Column(String, index=True, unique=True, nullable=False)

    overall_score = Column(Integer, default=0)       # 0-100 综合评分（越高越好）
    recommendation = Column(Text)                    # 投资/收购建议
    executive_summary = Column(Text)
    language = Column(String, default="en")          # 输出语言（跟随源文档）

    # 五大风险维度： [{key, label, score(0-100, 越高风险越大), summary, findings[]}]
    risk_categories = Column(JSONB)
    red_flags = Column(JSONB)        # [str]
    opportunities = Column(JSONB)    # [str]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
