from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class AppSetting(Base):
    """全局应用设置（单行，id=1）。当前用于持久化大模型 Provider 选择与各家配置。"""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    llm_provider = Column(String, default="ollama")
    llm_providers_config = Column(JSONB)  # {provider: {model, api_key}}
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
