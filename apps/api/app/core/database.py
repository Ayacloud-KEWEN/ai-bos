import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库连接 URL：优先读环境变量 DATABASE_URL（生产），否则用本地 Docker 默认。
# 使用 postgresql+psycopg:// 实现异步高性能连接。
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:bos_admin_123@127.0.0.1:5435/ai_bos_db",
)

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)

# 创建异步 Session 工厂
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

# 依赖注入获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session