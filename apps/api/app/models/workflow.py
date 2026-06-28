from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Workflow(Base):
    """工作流定义（Module 3）：可视化节点图。nodes/edges 为 React Flow 结构。"""
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: f"w_{uuid.uuid4().hex[:8]}")
    name = Column(String, nullable=False)
    description = Column(Text)
    nodes = Column(JSONB)   # [{id, type, position:{x,y}, config:{}}]
    edges = Column(JSONB)   # [{id, source, target}]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkflowRun(Base):
    """工作流执行实例。LangGraph 编排执行，逐节点更新状态。"""
    __tablename__ = "workflow_runs"

    id = Column(String, primary_key=True, default=lambda: f"wr_{uuid.uuid4().hex[:10]}")
    workflow_id = Column(String, index=True, nullable=False)
    company_id = Column(String, index=True)
    status = Column(String, default="running")     # running / completed / failed
    node_states = Column(JSONB)                    # {node_id: {status, summary, error}}
    logs = Column(JSONB)                           # [str]
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
