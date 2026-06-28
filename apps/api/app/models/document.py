from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class CompanyDocument(Base):
    """公司上传的原始文档（附件）。每次上传/重新上传都会保留一条，支持多文档。"""
    __tablename__ = "company_documents"

    id = Column(String, primary_key=True, default=lambda: f"doc_{uuid.uuid4().hex[:8]}")
    company_id = Column(String, index=True, nullable=False)

    filename = Column(String, nullable=False)       # 原始文件名（含中文）
    stored_path = Column(String, nullable=False)     # 服务器磁盘上的绝对路径
    content_type = Column(String, default="application/pdf")
    size = Column(Integer, default=0)                # 字节
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
