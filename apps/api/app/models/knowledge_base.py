from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from app.core.database import Base


class KnowledgeBaseDocument(Base):
    """组织级知识库文档（Module 5）：框架/案例/研究等，跨公司复用。"""
    __tablename__ = "kb_documents"

    id = Column(String, primary_key=True, default=lambda: f"kbd_{uuid.uuid4().hex[:8]}")
    title = Column(String, nullable=False)
    filename = Column(String)
    stored_path = Column(String)
    content_type = Column(String, default="application/pdf")
    size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="Indexing")  # Indexing / Ready / Failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KnowledgeBaseChunk(Base):
    """知识库分块向量（768 维，本地 bge）。"""
    __tablename__ = "kb_chunks"

    id = Column(String, primary_key=True, default=lambda: f"kbc_{uuid.uuid4().hex[:10]}")
    document_id = Column(String, index=True, nullable=False)
    title = Column(String)            # 冗余存文档标题，便于检索结果展示
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
