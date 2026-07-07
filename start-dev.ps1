# ============================================================
#  AI-BOS 一键开发启动脚本
#  启动：PostgreSQL(Docker) + Ollama 检查 + 后端(8000) + 前端(3300)
#  用法：双击 start-dev.bat，或在 PowerShell 运行  ./start-dev.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$ApiDir = Join-Path $Root "apps\api"
$WebDir = Join-Path $Root "apps\web"

function Info($m) { Write-Host "[AI-BOS] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[ OK ] $m"   -ForegroundColor Green }
function Warn($m) { Write-Host "[WARN] $m"   -ForegroundColor Yellow }

Write-Host "============================================" -ForegroundColor Magenta
Write-Host "        AI-BOS  Dev Launcher" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta

# --- 1. 数据库 (Docker) ---------------------------------------------------
Info "Checking Docker..."
$dockerOk = $false
try { docker info *> $null; if ($LASTEXITCODE -eq 0) { $dockerOk = $true } } catch {}

if (-not $dockerOk) {
    Warn "Docker is not running. Trying to start Docker Desktop..."
    $dd = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dd) {
        Start-Process $dd | Out-Null
        Info "Waiting for Docker to be ready (up to 90s)..."
        for ($i = 0; $i -lt 45; $i++) {
            Start-Sleep -Seconds 2
            try { docker info *> $null; if ($LASTEXITCODE -eq 0) { $dockerOk = $true; break } } catch {}
        }
    } else {
        Warn "Docker Desktop not found at default path. Please start it manually."
    }
}

if ($dockerOk) {
    Info "Starting PostgreSQL (pgvector) container..."
    docker compose -f (Join-Path $Root "docker-compose.yml") up -d | Out-Null
    Ok "Database up on localhost:5435"
} else {
    Warn "Skipping DB start - Docker unavailable. Backend will fail to connect until DB is up."
}

# --- 2. Ollama (本地默认模型) --------------------------------------------
Info "Checking Ollama (127.0.0.1:11434)..."
$ollamaOk = $false
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 -UseBasicParsing *> $null
    $ollamaOk = $true
} catch {}

if ($ollamaOk) {
    Ok "Ollama is running"
} else {
    Warn "Ollama not reachable. Trying to start 'ollama serve'..."
    try { Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden; Start-Sleep -Seconds 3; Ok "Launched ollama serve" }
    catch { Warn "Could not start Ollama. If you only use online models (DeepSeek etc.) this is fine." }
}

# --- 3. 后端 (FastAPI, 端口 8000) ----------------------------------------
Info "Starting backend (FastAPI) in a new window..."
$uvicorn = Join-Path $ApiDir "venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicorn)) {
    Warn "venv not found at apps\api\venv. Run: cd apps\api; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt"
} else {
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "`$Host.UI.RawUI.WindowTitle='AI-BOS API :8000'; Set-Location '$ApiDir'; .\venv\Scripts\uvicorn.exe app.main:app --reload --port 8000"
    )
    Ok "Backend launching (give it ~20s to load the embedding model)"
}

# --- 4. 前端 (Next.js, 端口 3300) ----------------------------------------
Info "Starting frontend (Next.js) in a new window..."
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$Host.UI.RawUI.WindowTitle='AI-BOS Web :3300'; Set-Location '$WebDir'; pnpm dev"
)
Ok "Frontend launching"

# --- 完成 ----------------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Ok "All services starting in separate windows."
Write-Host "  Frontend : http://localhost:3300"      -ForegroundColor White
Write-Host "  API docs : http://localhost:8000/docs"  -ForegroundColor White
Write-Host "  Database : localhost:5435"              -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
Write-Host "Tip: close a service's window or Ctrl+C in it to stop that service." -ForegroundColor DarkGray
Read-Host "Press Enter to close this launcher window"
