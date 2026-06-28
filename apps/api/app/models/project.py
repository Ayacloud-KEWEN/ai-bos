from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Project(Base):
    """执行项目（Module 1）：组织目标、关联公司、KPI、生成的 playbook。"""
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: f"p_{uuid.uuid4().hex[:8]}")
    name = Column(String, nullable=False)
    objective = Column(Text)
    company_id = Column(String, index=True)   # 可选关联公司
    status = Column(String, default="Active")
    kpis = Column(JSONB)                       # [str]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Playbook(Base):
    """可执行业务方法论（Module 2，Agent 09 生成）。steps 为 JSONB，含每步状态。"""
    __tablename__ = "playbooks"

    id = Column(String, primary_key=True, default=lambda: f"pb_{uuid.uuid4().hex[:8]}")
    project_id = Column(String, index=True)    # 可选归属项目
    company_id = Column(String, index=True)    # 来源公司
    title = Column(String, nullable=False)
    objective = Column(Text)
    goal = Column(String)                      # 用户选定的目标（如"进入欧洲市场"）
    category = Column(String)
    difficulty = Column(String)
    estimated_time = Column(String)
    expected_outcome = Column(Text)
    status = Column(String, default="Generating")   # Generating / Ready / Failed
    language = Column(String, default="en")

    # [{id, order, title, objective, owner, deliverable, kpi, status(todo/doing/done)}]
    steps = Column(JSONB)
    deliverables = Column(JSONB)    # [str]
    kpis = Column(JSONB)            # [str]
    success_criteria = Column(JSONB)  # [str]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
