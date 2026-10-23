# Solana AI Trading Desk - one-shot launcher (Windows PowerShell)
# Installs dependencies if missing, builds the frontend if needed,
# starts the backend on http://127.0.0.1:8765 and opens the dashboard.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# ---- backend venv ----
if (-not (Test-Path "backend\.venv\Scripts\python.exe")) {
    Write-Host "[1/4] Creating backend virtual environment (Python 3.14)..." -ForegroundColor Cyan
    py -3.14 -m venv backend\.venv
    & backend\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
}
& backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# ---- frontend build ----
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "[2/4] Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location frontend
    npm install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    Pop-Location
}
Write-Host "[3/4] Building frontend..." -ForegroundColor Cyan
Push-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) { throw "npm build failed" }
Pop-Location

# ---- run ----
Write-Host "[4/4] Starting backend at http://127.0.0.1:8765 ..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8765"
& backend\.venv\Scripts\python.exe backend\run.py --port 8765
