# 互联网医疗中心平台 · 本地运行时一键引导（M1）
# 用法（在 code/infra 目录）：
#   pwsh ./scripts/bootstrap.ps1
# 行为：启动依赖 → 等待 PG → 迁移 → 种子 → 启动后端（后台）
# 退出码：0 成功；非 0 任一步失败。

$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot/.."
$backend = Resolve-Path "$root/../backend"

function Fail($msg) { Write-Error $msg; exit 1 }

Write-Host "[1/5] 启动本地依赖（docker compose）..." -ForegroundColor Cyan
Push-Location $root
try {
  docker compose up -d
} catch { Fail "docker compose 启动失败，请确认 Docker Desktop 已运行" }
Pop-Location

Write-Host "[2/5] 等待 PostgreSQL 健康检查..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
  $st = docker inspect -f '{{.State.Health.Status}}' ihm-postgres 2>$null
  if ($st -eq 'healthy') { $ok = $true; break }
  Start-Sleep -Seconds 2
}
if (-not $ok) { Fail "PostgreSQL 在 60s 内未就绪" }

Write-Host "[3/5] 数据库迁移（alembic upgrade head）..." -ForegroundColor Cyan
Push-Location $backend
try {
  alembic upgrade head
} catch { Fail "alembic 迁移失败，请确认已 pip install 依赖且 .env 存在" }

Write-Host "[4/5] 初始化种子数据（seed）..." -ForegroundColor Cyan
try {
  python -c "from app.db.seed import seed_all; import asyncio; asyncio.run(seed_all())"
} catch { Fail "seed 失败" }
Pop-Location

Write-Host "[5/5] 启动后端（uvicorn，后台）..." -ForegroundColor Cyan
Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app","--host","127.0.0.1","--port","8000","--reload" `
  -WorkingDirectory $backend -RedirectStandardOutput "$backend/backend.out" -RedirectStandardError "$backend/backend.err"

# 等待就绪
$ready = $false
for ($i = 0; $i -lt 25; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { $ready = $true; break }
  } catch {}
  Start-Sleep -Seconds 2
}
if (-not $ready) { Fail "后端未在 50s 内就绪，详见 backend/backend.err" }

Write-Host "✅ 运行时已就绪：http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "   Swagger: http://127.0.0.1:8000/docs  ·  Prometheus: http://localhost:9090" -ForegroundColor Green
