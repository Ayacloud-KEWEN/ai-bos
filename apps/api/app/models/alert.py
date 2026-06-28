from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Alert(Base):
    """监控告警：财务变动、新披露、风险变化等（Continuous Monitoring）。"""
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: f"al_{uuid.uuid4().hex[:10]}")
    company_id = Column(String, index=True)          # 关联公司
    company_name = Column(String)
    type = Column(String, index=True)                # financial / disclosure / risk / news
    severity = Column(String, default="info")        # info / warning / critical
    title = Column(String, nullable=False)
    detail = Column(Text)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
