# AI-BOS 部署到 CloudPanel VPS（DeepSeek 在线模型方案）

面向 **CloudPanel 管理的 VPS**。前端走 CloudPanel 的 Node.js 站点，后端 FastAPI 用 systemd 常驻，
PostgreSQL+pgvector 用 Docker，Nginx 由 CloudPanel 反代 + Let's Encrypt。
AI 分析走 **在线 DeepSeek**（VPS 只跑本地 bge 向量 + OCR），2–4GB 内存即可起步。

> 下文把你的站点用户记为 `<SITE_USER>`、域名记为 `ai-bos.francego.fr`，站点根一般是
> `/home/<SITE_USER>/htdocs/ai-bos.francego.fr/`。代码放在该目录下的 `AI-BOS/`。

---

## 0. 准备
- 一台 VPS（**建议 ≥2 核 4GB**；OCR/向量吃内存），已装 CloudPanel。
- 一个域名解析到 VPS。
- 一个 **DeepSeek API Key**。
- VPS 已装 **Docker**（`curl -fsSL https://get.docker.com | sh`）、**Python 3.11+**、**Node 20+ / pnpm**（Node 可用 CloudPanel 站点自带版本）。

---

## 1. 在 CloudPanel 建站点
1. **Sites → Add Site → Create a Node.js Site**，域名填 `ai-bos.francego.fr`，App Port 填 `3300`，Node 版本选 20+。
2. 建站后 **SSL/TLS → Let's Encrypt** 一键签发证书。
3. 记下站点用户 `<SITE_USER>` 与站点根目录。

---

## 2. 拉代码
SSH 登录 VPS，切到站点根：
```bash
cd /home/<SITE_USER>/htdocs/ai-bos.francego.fr/
git clone https://github.com/Ayacloud-KEWEN/ai-bos.git AI-BOS
cd AI-BOS
```

---

## 3. 数据库（PostgreSQL + pgvector，Docker）
```bash
# 生产请先改 docker-compose.yml 里的 POSTGRES_PASSWORD 为强密码
docker compose up -d
docker ps            # 确认 ai_bos_postgres 在 0.0.0.0:5435 运行
```

---

## 4. 后端 FastAPI
```bash
cd apps/api
python3 -m venv venv
./venv/bin/pip install -U pip
./venv/bin/pip install -r requirements.txt
# 若某些包编译失败：sudo apt install -y build-essential libpq-dev

# 环境变量
cp .env.example .env
nano .env
```
`.env` 关键项：
```
DATABASE_URL=postgresql+psycopg://postgres:你的强密码@127.0.0.1:5435/ai_bos_db
CORS_ORIGINS=https://ai-bos.francego.fr
AIBOS_DEFAULT_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的key
HF_ENDPOINT=https://huggingface.co      # 海外 VPS 用官方源；国内可删掉这行用默认镜像
```
装成 systemd 服务：
```bash
# 编辑 deploy/aibos-api.service，把 <SITE_USER> 和路径改成实际值
sudo cp /home/<SITE_USER>/htdocs/ai-bos.francego.fr/AI-BOS/deploy/aibos-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aibos-api
sudo systemctl status aibos-api          # 首次启动会下载 bge 向量模型(~500MB)，等它 active
curl -s http://127.0.0.1:8000/api/v1/companies/sectors   # 通了说明后端 OK
```
> ⚠️ 保持 `--workers 1`（unit 里已设）——多 worker 会重复加载模型、设置不同步。

---

## 5. 前端 Next.js
```bash
cd /home/<SITE_USER>/htdocs/ai-bos.francego.fr/AI-BOS/apps/web
cp .env.example .env.production
nano .env.production      # NEXT_PUBLIC_API_URL=https://ai-bos.francego.fr/api/v1
pnpm install
pnpm build
```
在 CloudPanel **站点 → Settings**，把 **App Start Command** 设为：
```
pnpm start
```
（`package.json` 里已配成 `next start -p 3300`）。App Port 保持 **3300**。保存后 CloudPanel 会常驻它。

---

## 6. Nginx 反代（关键）
CloudPanel **站点 → Vhost 编辑器**，参照 `deploy/nginx-aibos.conf` 在 `server {}` 里补两处：
- `client_max_body_size 50M;`（否则上传大 PDF 会 413）
- 一段 `location /api/ { proxy_pass http://127.0.0.1:8000; ... }`（放在 `location /` 之前）

保存后 CloudPanel 自动 reload Nginx。

---

## 7. 首次验收
1. 打开 `https://ai-bos.francego.fr` → 应看到界面。
2. **Settings** 页：确认当前 Provider 是 **DeepSeek**（env 已自动播种 key）。若不是，手动切换。
3. 上传一个 PDF/Word 建档 → 几分钟后财务/竞争/尽调等出结果；或用"Search Online"从 SEC/巨潮/HKEX 联网建档。
4. Dashboard 点 "Run monitoring"、公司页导出报告/资产，逐个验收。

---

## 8. 日常更新
```bash
cd /home/<SITE_USER>/htdocs/ai-bos.francego.fr/AI-BOS
git pull
# 后端
cd apps/api && ./venv/bin/pip install -r requirements.txt && sudo systemctl restart aibos-api
# 前端
cd ../web && pnpm install && pnpm build   # CloudPanel 会自动重启 Node 应用（或在面板点 Restart）
```

---

## 9. 注意事项
- **数据持久化**：上传文档在 `apps/api/storage/`（已 gitignore，不会被 git pull 覆盖）；数据库在 Docker volume `ai_bos_pgdata_v3`。定期 `docker exec ai_bos_postgres pg_dump ...` 备份。
- **资源**：首启会下载 bge 模型；OCR/向量化吃内存，内存紧张就升配。DeepSeek 让分析并发更快。
- **无认证**：当前应用**没有登录**，任何人访问域名即可用。上线给外部前，务必加认证或至少用 CloudPanel 的 **Basic Auth**（站点 → Settings）先挡一层。
- **密钥安全**：API Key 存在数据库 `app_settings`，不入代码库；`.env` 已 gitignore。
- **监控自动化**：如需定时监控，加系统 cron：`*/30 * * * * curl -s -X POST http://127.0.0.1:8000/api/v1/monitoring/run`。
