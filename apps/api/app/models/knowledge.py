from sqlalchemy import Column, String, Integer, Text, DateTime, Index
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from app.core.database import Base


class KnowledgeChunk(Base):
    """文档分块及其向量，用于公司级 RAG 问答（768 维，本地 bge）。"""
    __tablename__ = "knowledge_chunks"

    id = Column(String, primary_key=True, default=lambda: f"k_{uuid.uuid4().hex[:10]}")
    company_id = Column(String, index=True, nullable=False)
    document_id = Column(String, index=True)        # 关联 company_documents.id（来源）
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_chunks_company", "company_id"),
    )
