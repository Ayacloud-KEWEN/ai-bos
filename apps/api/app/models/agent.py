from sqlalchemy import Column, String, Text, Float, Boolean, DateTime
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Agent(Base):
    """可配置 AI 助手（Module 4）。角色/目标/提示词/模型/知识库范围。"""
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: f"ag_{uuid.uuid4().hex[:8]}")
    name = Column(String, nullable=False)
    role = Column(String)                  # e.g. AI CFO Assistant
    goal = Column(Text)
    system_prompt = Column(Text)
    provider = Column(String, default="")  # 空=用当前激活 provider；否则指定 deepseek/openai/...
    temperature = Column(Float, default=0.3)
    knowledge_company_id = Column(String)  # 可选：绑定某公司文档作为知识库(RAG)
    use_knowledge_base = Column(Boolean, default=False)  # 可选：使用组织级知识库
    icon = Column(String, default="Bot")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
