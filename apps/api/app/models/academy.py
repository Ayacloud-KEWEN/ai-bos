from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Simulation(Base):
    """商业模拟实例（Module 7）。回合制，AI 推演 + 打分。"""
    __tablename__ = "academy_simulations"

    id = Column(String, primary_key=True, default=lambda: f"sim_{uuid.uuid4().hex[:10]}")
    scenario_key = Column(String)
    title = Column(String)
    track = Column(String)
    status = Column(String, default="active")   # active / completed
    round = Column(Integer, default=0)
    language = Column(String, default="zh")

    # current: {situation, options}
    current = Column(JSONB)
    # history: [{situation, options, decision, outcome, feedback, score}]
    history = Column(JSONB)
    final_assessment = Column(JSONB)  # {summary, scores:{dim:val}, grade}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
