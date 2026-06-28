# AI-BOS 开发进展与维护说明

> AI Business Operating System —— 公司情报分析平台。
> 本文档记录架构、启动方式、已实现功能、关键设计与已知问题，方便日常调试与后续开发。

最后更新：2026-06-23（含联网抓取 SEC/巨潮/HKEX、RAG 问答、知识图谱、多模型切换）

---

## 1. 一键启动（重启 Windows 后调试）

双击根目录的 **`start-dev.bat`**（或在 PowerShell 里运行 `./start-dev.ps1`）。脚本会依次：

1. 启动 Docker 里的 PostgreSQL（pgvector）；
2. 检查本地 Ollama 是否在跑（不在则尝试拉起）；
3. 在**独立窗口**启动后端（FastAPI / uvicorn，端口 8000）；
4. 在**独立窗口**启动前端（Next.js，端口 3000）。

两个服务各自一个窗口，方便看日志、按 `Ctrl+C` 单独重启。启动后访问：

| 服务 | 地址 |
|---|---|
| 前端 | http://localhost:3000 |
| 后端 API 文档 (Swagger) | http://localhost:8000/docs |
| 数据库 | localhost:**5435**（容器内 5432） |
| Ollama | http://127.0.0.1:11434 |

> 首次或重装依赖后，见 [第 6 节](#6-初次环境搭建)。

---

## 2. 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Next.js 15 (App Router, Turbopack) · TypeScript · Tailwind · shadcn/Radix · TanStack Query · Recharts · React Flow · next-intl |
| 后端 | FastAPI · SQLAlchemy (async, psycopg) · LangChain |
| 数据库 | PostgreSQL 16 + **pgvector**（Docker，端口 5435） |
| AI（可切换） | 本地 **Ollama qwen2.5**（默认）/ DeepSeek / OpenAI / 通义千问 / Claude |
| 向量化 | 本地 HuggingFace `BAAI/bge-base-en-v1.5`（768 维，始终本地） |
| 包管理 | 前端 **pnpm**（workspace）· 后端 **venv + pip** |

---

## 3. 目录结构

```
AI-BOS/
├─ docker-compose.yml        # PostgreSQL + pgvector
├─ start-dev.ps1 / .bat      # 一键启动脚本
├─ DEVELOPMENT.md            # 本文档
├─ apps/
│  ├─ api/                   # 后端 FastAPI
│  │  ├─ app/
│  │  │  ├─ main.py          # 入口、路由注册、启动迁移、加载模型设置
│  │  │  ├─ core/            # database.py(连接) / security.py / config.py
│  │  │  ├─ models/          # SQLAlchemy 模型
│  │  │  ├─ api/routers/     # 路由
│  │  │  └─ services/        # analyzer / llm / financial_metrics / taxonomy / storage
│  │  ├─ storage/documents/  # 上传的原始文件（按 company 存）
│  │  ├─ venv/               # Python 虚拟环境
│  │  └─ requirements.txt    # 后端依赖（pip freeze）
│  └─ web/                   # 前端 Next.js
│     ├─ app/[locale]/...    # 页面（dashboard / company-intelligence / settings ...）
│     ├─ components/         # UI 与各分析面板
│     └─ lib/                # api-client(axios) / format / utils
```

---

## 4. 已实现功能（公司情报模块为主）

公司详情页有 9 个标签：**Overview / Financials / Peer Comparison / Competitors / Due Diligence / Strategy / Sales / Market / Chat**。Overview 顶部含 CEO 执行简报；右上角"Export Report"导出可打印 HTML 报告（含全部 7 个分析章节）。

| 功能 | 说明 | 关键文件 |
|---|---|---|
| 文档上传 + AI 建档 | 上传 PDF → 概览/向量秒回，财报/竞争/尽调后台分析 | `routers/companies.py`、`services/analyzer.py` |
| **联网建档（SEC/巨潮/HKEX）** | 搜公司名 → 权威源抓取（SEC 给结构化 XBRL 财务；巨潮/HKEX 下载年报 PDF）→ 自动建档分析，免上传 | `services/sources/`、`routers/scan.py`、`online-scan-dialog.tsx` |
| **与公司对话 RAG** | 文档分块向量库 → 检索 top-k → 当前模型作答 + 来源引用 | `models/knowledge.py`、`services/rag.py`、`routers/chat.py`、`company-chat.tsx` |
| 财务情报 | 多期财报抽取 + 派生指标（利润率/YoY/CAGR）+ 5 维评分 + 图表 | `routers/financials.py`、`services/financial_metrics.py`、`components/financials/` |
| 财报人工校正 | 逐期增删改财务数据，趋势实时重算 | `financial-data-editor.tsx`、`POST/PATCH/DELETE .../financials/periods` |
| 竞争情报 | SWOT、竞争矩阵、战卡、技术趋势；**竞品自动建公司并互联** | `routers/competitive.py`、`components/competitive/` |
| 尽职调查 | 五大风险评分、红旗、投资建议（**中文文档输出中文**） | `routers/due_diligence.py`、`components/due-diligence/` |
| 同行业对标 | 按标准行业(sector)对比同行财务指标与百分位 | `routers/financials.py` `get_peers` |
| 行业标准化 | LLM 归一 + 关键词兜底，使对标可匹配 | `services/taxonomy.py` |
| Overview 重点提炼 | 跨维度评分、投资建议、关键风险/机会、可点击竞品 | `routers/companies.py` `get_company`、`overview-highlights.tsx` |
| 原始文件附件 | 详情页列出并内联打开原始 PDF | `routers/documents.py`、`services/storage.py`、`company-documents.tsx` |
| 公司列表分类 | 搜索 + 行业筛选 + 隐藏竞品 stub + 按行业分组 | `company-intelligence/companies/page.tsx` |
| 重新上传 / 补充信息 | 卡片管理弹窗：重传财报 / 改基础信息 | `manage-company-dialog.tsx`、`POST .../reupload`、`PATCH .../{id}` |
| **多模型切换** | 本地/在线 provider 运行时切换，Key 存 DB 不回显 | `services/llm.py`、`routers/settings.py`、`settings/page.tsx` |
| **知识图谱** | 公司-竞品关系网络（React Flow，点节点跳转） | `routers/graph.py`、`knowledge-graph/page.tsx` |

---

## 5. 关键设计与"踩过的坑"

- **后台分析不阻塞上传**：上传只做轻量概览 + 向量化即提交返回（~2s），财报/竞争/尽调走 FastAPI BackgroundTask，各自独立 DB 会话与 try/except，失败不回滚公司。
- **长文档 map-reduce**：>14k 字的文档分块（8k）逐块提炼"稠密事实摘要"再合并分析（Ollama 默认 `num_ctx` 仅 2048，已显式设 16384）。**超大文档**（如几百页招股书 = 46 块）按关键词密度只取最关键的 ~14 块，避免本地串行 Ollama 跑 20 分钟。
- **事件循环不被阻塞**：PyPDF 解析是同步阻塞，已用 `asyncio.to_thread` 放到线程池——否则连传几份会让整个 API 失去响应（HTTP 000）。
- **多 Provider**：`analyzer` 每次按当前激活 provider 动态建链；DeepSeek/OpenAI/Qwen 走 OpenAI 兼容接口，Claude 走 Anthropic。向量化始终本地。
- **行业对标按标准 sector 匹配**，且只纳入"有财务数据"的公司，避免无财报的竞品 stub 撑空表。
- **删除公司**级联清理财报/竞争/尽调/文档/向量行 + 磁盘文件。
- **联网数据源**：可插拔连接器层 `services/sources/`（base/registry/http_util + sec_edgar/cninfo/hkex）。SEC 免 Key 且给**结构化 XBRL 财务**（直接入库，绕过 LLM 抽取）；巨潮/HKEX 下载官方年报 PDF 走现有流水线。HKEX 关键：servlet 的 `stockId` 就是股票代码整数。
- **RAG**：`knowledge_chunks` 表（每块 768 维 bge 向量），检索用 pgvector `cosine_distance`；上传/建档后自动建索引；问答用当前激活模型，严格基于检索、同语言、附来源。

---

## 6. 初次环境搭建

```powershell
# 1. 数据库
docker compose up -d

# 2. 后端
cd apps\api
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

# 3. 前端
cd ..\web
pnpm install        # 或在根目录 pnpm install（workspace）

# 4. Ollama 模型（本地默认 provider）
ollama pull qwen2.5
```

> 在线模型（DeepSeek 等）无需本地模型，在前端 **Settings** 页填 API Key 后切换即可。

---

## 7. 配置与密钥

- **数据库连接**：`apps/api/app/core/database.py` 硬编码为 `postgresql+psycopg://postgres:bos_admin_123@127.0.0.1:5435/ai_bos_db`（与 `docker-compose.yml` 一致）。
- **大模型**：在 Settings 页配置；持久化在 `app_settings` 表（API Key 仅存不回显）。默认本地 Ollama。
- **前端 API 地址**：`NEXT_PUBLIC_API_URL`（默认 `http://localhost:8000/api/v1`）。

---

## 8. 已知问题 / 注意事项

- **本地 Ollama 单实例串行**：连续上传多份大文档会排队很久，期间分析慢。切到在线 provider（DeepSeek）可并发提速。
- **尽调报告财务稀疏**：DD 报告非结构化年报，Financials 标签可能只有少量周期；精确财务建议另传年报/招股书。
- **竞品 stub 轮询**：未分析的竞品 stub 的财报/竞争/尽调接口 `has_data=false`，前端会每 5s 轮询（小量空请求）。
- **删除竞态**：公司在后台分析进行中被删，可能残留孤儿分析行（知识图谱已过滤孤儿边）。
- **数据库凭据硬编码**：仅适合本地开发，生产需改为环境变量。

---

## 9. 后续路线（待办）

- [x] **与公司对话 RAG**：`knowledge_chunks` 分块向量库 + 检索 + 当前模型问答（Chat 标签）。
- [x] **知识图谱**：公司-竞品关系网络（React Flow）。
- [x] **搜公司名联网建档（SEC EDGAR + 巨潮 + HKEX）**：权威数据源连接器层 `services/sources/`，"Search Online" 入口。SEC 提供结构化 XBRL 财务；巨潮/HKEX 下载官方年报。
- [ ] **联网建档补全**：Companies House / Firecrawl / Exa（需 Key，入 Settings）。
- [x] **报告导出 + CEO 执行简报**：`GET /companies/{id}/report` 渲染可打印 HTML（浏览器存 PDF）；Agent 08 执行简报综合财务/竞争/尽调，上传/建档后自动生成，Overview 顶部展示。
- [x] **业务资产生成器（Module 6）**：从情报一键导出投资备忘录(Word)、销售 Deck(PPT)、Battlecard(Word)、外联邮件(Text)。详情页"Assets"下拉。(`services/asset_builder.py`, `routers/assets.py`)
- [x] **文档摄取：DOCX/PPTX/XLSX/TXT + 扫描件 OCR**（`services/extract.py`，PyMuPDF + RapidOCR 本地）。
- [x] **战略情报（Agent 06）**：战略选项(impact/feasibility/risk 评分) + 排序建议 + 波特五力 + 增长机会；Strategy 标签 + 报告章节，上传/建档后自动生成。
- [x] **销售情报（Agent 04）+ 市场情报（Agent 05）**：ICP/买家画像/痛点/买点/机会；TAM/SAM/SOM/趋势/驱动/壁垒。Sales、Market 标签 + 报告章节，上传/建档后自动生成。
- [x] **Dashboard 真实数据 + 持续监控告警**：组合统计/行业分布/评分榜；监控复查联网建档公司的最新披露（SEC/巨潮/HKEX 的 `latest_marker`），变动生成告警；再分析时检测财务变动（营收±/新期间/风险上升）。注：本地无调度器，监控由 Dashboard"Run monitoring"手动触发（可接 cron）。
- [ ] 定时自动监控（接 cron/Temporal 调用 `/monitoring/run`）。
- [x] **执行层 MVP：Projects + Playbook（Agent 09）+ 步骤执行跟踪**。项目关联公司→从情报生成可执行 playbook（步骤含 owner/交付物/KPI）→ 勾选步骤推进状态、项目进度汇总。(`models/project.py`, `routers/projects.py`+`playbooks.py`, `/projects` 与 `/projects/[id]` 页)
- [x] **Workflow 引擎（LangGraph 自动编排 + 可视化 builder）**：节点图编译成 LangGraph DAG 自动执行（财务/竞争/尽调/战略/销售/市场/简报/playbook 节点），逐节点回写状态；React Flow 拖拽建图、保存、选公司运行、节点按执行状态实时上色。(`services/workflow_engine.py`, `routers/workflows.py`, `/workflows` + builder 页)
- [x] **Agent Studio（Module 4）**：可配置 AI 助手（角色/目标/系统提示词/模型/温度/公司知识库 RAG）+ 对话；5 个预设模板。(`models/agent.py`, `routers/agents.py`, `/agents/library` + `/agents/[id]`)
- [x] **多公司对比 / M&A 视图**：选 2-4 家公司并排对比（情报分/营收/利润率/财务评分/尽调/护城河 + 评分柱状图 + 最优项高亮 + 优势/建议）。(`routers/compare.py`, `/company-intelligence/compare`)
- [x] **组织级知识库（Module 5）**：上传框架/案例/研究（支持多格式+OCR）→ 分块向量化 → 跨文档语义检索 + 问答。(`models/knowledge_base.py`, `routers/knowledge.py`, `/knowledge/documents`)
- [x] **商学院（Module 7）MVP：AI 商业模拟**。回合制场景（创业/融资/进入市场/产品发布/危机）→ 学员决策 → AI 推演后果+打分+教练反馈 → 结束综合评估（多维评分）。AI 导师复用 Agent Studio。(`models/academy.py`, `routers/academy.py`, `/academy/courses` + `/academy/simulations/[id]`)
- [ ] 多文档历史对比（需版本化数据模型）。
- [ ] 认证 + 多租户（Auth.js / 组织隔离 / RBAC）——生产化前置。

---

## 10. 常见排错

| 现象 | 处理 |
|---|---|
| 前端报 401/网络错误 | 后端没起或端口不对，确认 8000 在跑、CORS 含 localhost:3000 |
| 上传后一直 "Analyzing" | 本地 Ollama 在排队/大文档慢；看后端窗口日志；切在线 provider |
| API 全部超时 (HTTP 000) | 事件循环被阻塞或后台任务堆积；重启后端窗口 |
| `vector` 扩展报错 | 用的镜像须为 `ankane/pgvector`；启动迁移会 `CREATE EXTENSION` |
| 切换在线模型分析失败 | Settings 里 Key 是否正确、模型名是否有效 |
| 中文 PDF 无内容 | 已支持扫描件 OCR（RapidOCR 本地）+ DOCX/PPTX/XLSX；仍空则文档可能损坏 |
```
