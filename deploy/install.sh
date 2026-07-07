#!/usr/bin/env bash
# ============================================================================
# AI-BOS 一键安装脚本（后端 FastAPI + 前端 Next.js）
#
# 前提：数据库（PostgreSQL + pgvector，docker compose up -d）已在跑。
# 用法：
#   cd <站点根>/AI-BOS
#   chmod +x deploy/install.sh
#   ./deploy/install.sh                # 交互式，缺啥问啥
# 或非交互（先 export 变量再运行）：
#   DOMAIN=ai-bos.francego.fr DB_PASSWORD=xxx DEEPSEEK_API_KEY=sk-xxx \
#   ADMIN_USERNAME=admin@ai-bos.francego.fr ADMIN_PASSWORD=xxx ./deploy/install.sh
#
# 需要 sudo 来安装 systemd 服务（脚本会在需要时提示）。
# ============================================================================
set -euo pipefail

# ---- 路径与用户 -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_DIR="$REPO_ROOT/apps/api"
WEB_DIR="$REPO_ROOT/apps/web"
SITE_USER="${SUDO_USER:-$(whoami)}"

log()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

# 交互式取值：ask VAR "提示" "默认值"（若变量已由 env 提供则跳过）
ask() {
  local __var="$1" __prompt="$2" __default="${3:-}" __val
  if [ -n "${!__var:-}" ]; then return; fi
  if [ -n "$__default" ]; then
    read -rp "$__prompt [$__default]: " __val || true
    __val="${__val:-$__default}"
  else
    read -rp "$__prompt: " __val || true
  fi
  printf -v "$__var" '%s' "$__val"
}
ask_secret() {
  local __var="$1" __prompt="$2" __val
  if [ -n "${!__var:-}" ]; then return; fi
  read -rsp "$__prompt: " __val || true; echo
  printf -v "$__var" '%s' "$__val"
}

[ -d "$API_DIR" ] || die "找不到 $API_DIR —— 请在仓库根目录运行本脚本"
command -v python3 >/dev/null || die "未找到 python3"

# ---- 不要用 root 跑 -------------------------------------------------------
# 用站点用户跑（该用户需有 sudo 权限）：venv/.env/前端产物才会归站点用户所有，
# systemd 服务也才会以站点用户身份跑后端。脚本内部装服务时会自己调 sudo。
if [ "$(id -u)" -eq 0 ] && [ -z "${ALLOW_ROOT:-}" ]; then
  die "请不要用 root 直接运行。切到 CloudPanel 站点用户再跑，例如：
       su - <SITE_USER>   然后   cd $REPO_ROOT && ./deploy/install.sh
     （确有理由必须用 root，可 ALLOW_ROOT=1 强制，但不推荐）"
fi
command -v sudo >/dev/null || die "未找到 sudo —— 站点用户需要有 sudo 权限来安装 systemd 服务"

log "站点用户: $SITE_USER"
log "仓库路径: $REPO_ROOT"

# ---- 收集配置 -------------------------------------------------------------
ask DOMAIN            "域名"                         "ai-bos.francego.fr"
ask DB_PASSWORD       "数据库密码 (docker-compose 里的 POSTGRES_PASSWORD)" "bos_admin_123"
ask AIBOS_DEFAULT_PROVIDER "默认大模型 provider (deepseek/openai/qwen/ollama)" "deepseek"
ask_secret DEEPSEEK_API_KEY "DeepSeek API Key (deepseek 方案必填，其它可留空回车)"
ask ADMIN_USERNAME    "初始管理员用户名"             "admin@$DOMAIN"
ask_secret ADMIN_PASSWORD "初始管理员密码"
[ -n "${ADMIN_PASSWORD:-}" ] || die "管理员密码不能为空（否则没有登录门）"
SECRET_KEY="${SECRET_KEY:-$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')}"

# ============================================================================
# 1. 后端
# ============================================================================
log "[后端] 创建 venv 并安装依赖 (首次较慢，会下载 bge 向量模型依赖)…"
cd "$API_DIR"
# 建 venv；Debian/Ubuntu 上常缺 python3-venv / python3-pip，缺了就自动补装
if [ ! -x venv/bin/pip ]; then
  rm -rf venv
  if ! python3 -m venv venv 2>/tmp/venv_err || [ ! -x venv/bin/pip ]; then
    warn "venv 创建失败（多半缺 python3-venv）。尝试自动安装系统依赖…"
    PYVER="$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if command -v apt-get >/dev/null; then
      sudo apt-get update -qq
      sudo apt-get install -y "python${PYVER}-venv" python3-venv python3-pip python3-dev build-essential libpq-dev
    elif command -v dnf >/dev/null; then
      sudo dnf install -y python3-venv python3-pip python3-devel gcc postgresql-devel
    else
      die "无法自动安装 python venv 依赖，请手动安装 python3-venv 后重跑。错误：$(cat /tmp/venv_err 2>/dev/null)"
    fi
    rm -rf venv
    python3 -m venv venv || die "venv 仍创建失败，请查看 /tmp/venv_err"
  fi
fi
[ -x venv/bin/pip ] || die "venv/bin/pip 不存在，venv 创建异常"
./venv/bin/pip install -q -U pip
./venv/bin/pip install -q -r requirements.txt

if [ -f .env ]; then
  warn "$API_DIR/.env 已存在，跳过生成（如需重置请手动删除后重跑）"
else
  log "[后端] 写入 .env"
  cat > .env <<EOF
DATABASE_URL=postgresql+psycopg://postgres:${DB_PASSWORD}@127.0.0.1:5435/ai_bos_db
CORS_ORIGINS=https://${DOMAIN}
AIBOS_DEFAULT_PROVIDER=${AIBOS_DEFAULT_PROVIDER}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
SECRET_KEY=${SECRET_KEY}
HF_ENDPOINT=https://huggingface.co
EOF
  chmod 600 .env
fi

log "[后端] 安装 systemd 服务 aibos-api (需要 sudo)"
SERVICE_TMP="$(mktemp)"
sed -e "s#<SITE_USER>#${SITE_USER}#g" \
    -e "s#/home/${SITE_USER}/htdocs/ai-bos.francego.fr/AI-BOS#${REPO_ROOT}#g" \
    "$REPO_ROOT/deploy/aibos-api.service" > "$SERVICE_TMP"
# 上面第二条 sed 兜底把默认占位路径替换成真实 REPO_ROOT；若模板路径不同则用下面精确替换
sudo cp "$SERVICE_TMP" /etc/systemd/system/aibos-api.service
rm -f "$SERVICE_TMP"
sudo systemctl daemon-reload
sudo systemctl enable --now aibos-api

log "[后端] 等待启动（首启会下载 ~500MB bge 模型，最多 10 分钟）…"
for i in $(seq 1 120); do
  # 探免登录端点 /auth/status（/companies/* 启用登录门后会 401）
  if curl -fs http://127.0.0.1:8000/api/v1/auth/status >/dev/null 2>&1; then
    log "[后端] ✅ 已就绪 (127.0.0.1:8000)"; break
  fi
  sleep 5
  [ "$i" = 120 ] && warn "后端仍未响应，稍后用 'sudo journalctl -u aibos-api -f' 查看日志"
done

# ============================================================================
# 2. 前端
# ============================================================================
log "[前端] 配置并构建 Next.js"
cd "$WEB_DIR"
cat > .env.production <<EOF
NEXT_PUBLIC_API_URL=https://${DOMAIN}/api/v1
EOF

if command -v pnpm >/dev/null 2>&1; then PKG=pnpm; else PKG=npm; warn "未找到 pnpm，改用 npm"; fi
log "[前端] 安装依赖 ($PKG install)…"
$PKG install
log "[前端] 构建 ($PKG run build)…"
$PKG run build

# ============================================================================
# 完成
# ============================================================================
printf '\n\033[1;32m✔ 安装完成\033[0m\n'
cat <<DONE

后端： systemd 服务 aibos-api 已启用（127.0.0.1:8000）
前端： 已构建，启动命令 => $PKG start  （已配置 next start -p 3300）

还剩两步需要在 CloudPanel 面板里手动做：

  1) 站点 → Settings → App Start Command 设为:  $PKG start   (App Port = 3300)
  2) 站点 → Vhost 编辑器，参照 deploy/nginx-aibos.conf 增加:
       - client_max_body_size 50M;
       - location /api/ { proxy_pass http://127.0.0.1:8000; ... }   (放在 location / 之前)
     并签发 Let's Encrypt 证书。

然后打开 https://${DOMAIN} ，用 ${ADMIN_USERNAME} 登录。

常用命令:
  后端日志:   sudo journalctl -u aibos-api -f
  重启后端:   sudo systemctl restart aibos-api
  更新代码:   git pull && ./deploy/install.sh   (会复用已有 .env)
DONE
