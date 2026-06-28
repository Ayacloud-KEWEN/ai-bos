from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text  # <-- 1. 新增：用于执行原生 SQL

from app.api.routers import auth
from app.api.deps import get_current_user
from app.core.database import engine, Base, AsyncSessionLocal

from app.models.user import User
from app.models.company import Company  # <-- 2. 新增：导入刚才写好的公司情报模型
from app.models.financial import CompanyFinancial, CompanyFinancialReport  # 财报数据模型
from app.models.competitive import CompanyCompetitiveReport  # 竞争情报模型
from app.models.due_diligence import CompanyDueDiligenceReport  # 尽职调查模型
from app.models.document import CompanyDocument  # 原始文档附件模型
from app.models.app_setting import AppSetting  # 全局设置（大模型 Provider）
from app.models.knowledge import KnowledgeChunk  # RAG 分块向量
from app.models.briefing import CompanyExecutiveBriefing  # CEO 执行简报
from app.models.strategy import CompanyStrategyReport  # 战略情报
from app.models.sales_market import CompanySalesReport, CompanyMarketReport  # 销售/市场情报
from app.models.alert import Alert  # 监控告警
from app.models.project import Project, Playbook  # 执行层：项目 + Playbook
from app.models.workflow import Workflow, WorkflowRun  # 工作流引擎
from app.models.agent import Agent  # Agent Studio
from app.models.knowledge_base import KnowledgeBaseDocument, KnowledgeBaseChunk  # 组织级知识库
from app.models.academy import Simulation  # 商学院
from app.api.routers import (auth, companies, financials, competitive, due_diligence, documents,
                             settings, graph, chat, scan, briefing, report, strategy, sales_market,
                             monitoring, alerts, dashboard, projects, playbooks, workflows, assets, agents,
                             compare, knowledge, academy)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # <-- 3. 关键步骤：在建表前，必须先开启 PostgreSQL 的向量扩展！
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # 扫描并自动创建所有的表 (User 和 Company)
        await conn.run_sync(Base.metadata.create_all)

        # 轻量级迁移：为已存在的 companies 表补充新列（create_all 不会 ALTER 既有表）
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS sector VARCHAR"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS source VARCHAR"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS source_external_id VARCHAR"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS monitor_marker VARCHAR"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_monitored_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS use_knowledge_base BOOLEAN DEFAULT false"))

    # 回填历史数据：把没有标准行业的公司按其 industry 文本归一化
    from app.services.taxonomy import classify_sector
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                text("SELECT id, industry FROM companies WHERE sector IS NULL")
            )
        ).all()
        for cid, industry in rows:
            await session.execute(
                text("UPDATE companies SET sector = :s WHERE id = :id"),
                {"s": classify_sector(industry), "id": cid},
            )
        if rows:
            await session.commit()
            print(f"[migrate] backfilled sector for {len(rows)} companies")

        # 载入大模型 Provider 设置到运行时
        from app.api.routers.settings import load_settings_into_runtime
        await load_settings_into_runtime(session)
    yield

app = FastAPI(
    title="AI-BOS Backend",
    description="API for Business Operating System",
    version="1.0.0",
    lifespan=lifespan, # 挂载生命周期
)

# 1. 配置 CORS (跨域)
origins = [
    "http://localhost:3000",  # Next.js 本地开发地址
    # 未来这里可以加上生产环境的域名
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Company Intelligence"])
app.include_router(financials.router, prefix="/api/v1/companies", tags=["Financial Intelligence"])
app.include_router(competitive.router, prefix="/api/v1/companies", tags=["Competitive Intelligence"])
app.include_router(due_diligence.router, prefix="/api/v1/companies", tags=["Due Diligence"])
app.include_router(documents.router, prefix="/api/v1/companies", tags=["Company Documents"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["Knowledge Graph"])
app.include_router(chat.router, prefix="/api/v1/companies", tags=["RAG Chat"])
app.include_router(scan.router, prefix="/api/v1/scan", tags=["Online Scan"])
app.include_router(briefing.router, prefix="/api/v1/companies", tags=["Executive Briefing"])
app.include_router(report.router, prefix="/api/v1/companies", tags=["Report"])
app.include_router(strategy.router, prefix="/api/v1/companies", tags=["Strategy Intelligence"])
app.include_router(sales_market.router, prefix="/api/v1/companies", tags=["Sales & Market Intelligence"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["Monitoring"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(playbooks.router, prefix="/api/v1/playbooks", tags=["Playbooks"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])
app.include_router(assets.router, prefix="/api/v1/companies", tags=["Business Assets"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(compare.router, prefix="/api/v1/compare", tags=["Compare"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge Base"])
app.include_router(academy.router, prefix="/api/v1/academy", tags=["Academy"])

# 3. 写一个受保护的测试接口
@app.get("/api/v1/users/me", tags=["Users"])
def read_users_me(current_user: dict = Depends(get_current_user)):
    return {
        "msg": "Authentication successful!",
        "user_info": current_user,
        "active_workspace": "Aya Cloud"
    }