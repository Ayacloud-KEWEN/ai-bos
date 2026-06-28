from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from app.core.database import Base

class Company(Base):
    __tablename__ = "companies"

    # 基础信息
    id = Column(String, primary_key=True, default=lambda: f"c_{uuid.uuid4().hex[:8]}", index=True)
    name = Column(String, index=True, nullable=False)
    industry = Column(String, index=True)        # 自由文本行业（用于展示）
    sector = Column(String, index=True)          # 标准化行业枚举（用于同行对标，见 services/taxonomy.py）
    location = Column(String)
    status = Column(String, default="Active Monitoring")
    
    # 扫描与情报指标
    intelligence_score = Column(Integer, default=0)
    documents_analyzed = Column(Integer, default=0)
    summary = Column(Text)

    # 持续监控：来源（联网建档时记录），用于定期复查新披露
    source = Column(String)                  # sec_edgar / cninfo / hkex / upload
    source_external_id = Column(String)      # CIK / "code:orgId" / 股票代码
    monitor_marker = Column(String)          # 最近一次复查记录的"最新披露标记"
    last_monitored_at = Column(DateTime(timezone=True))

    # 💡 核心武器：公司特征向量
    # 这里我们设定为 768 维。这是当前最高效的本地 Embedding 模型（如 Nomic-Embed 或 BGE）的标准维度，
    # 完美契合未来在你当前 Mac 芯片或配有 RTX 4070 Ti 的 PC 上，进行纯本地化、隐私隔离的离线向量计算与 RAG 检索流水线。
    embedding = Column(Vector(768))

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())