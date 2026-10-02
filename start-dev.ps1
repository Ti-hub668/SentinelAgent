$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       SentinelAgent Development" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------
# Basic checks
# -----------------------------

if (-not (Test-Path $backend)) {
    Write-Host "[ERROR] Backend directory not found:" -ForegroundColor Red
    Write-Host $backend
    exit 1
}

if (-not (Test-Path $frontend)) {
    Write-Host "[ERROR] Frontend directory not found:" -ForegroundColor Red
    Write-Host $frontend
    exit 1
}

if (-not (Test-Path $python)) {
    Write-Host "[ERROR] Backend virtual environment not found." -ForegroundColor Red
    Write-Host "Expected:"
    Write-Host $python
    Write-Host ""
    Write-Host "Please create backend\.venv first."
    exit 1
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "[ERROR] frontend\node_modules not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Run this first:"
    Write-Host "cd $frontend"
    Write-Host "npm install"
    exit 1
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] npm not found. Install Node.js and reopen PowerShell." -ForegroundColor Red
    exit 1
}

# -----------------------------
# Helper
# -----------------------------

function Test-PortListening {
    param(
        [int]$Port
    )

    $connection = Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue

    return $null -ne $connection
}

# -----------------------------
# Dependency status
# -----------------------------

Write-Host "Checking dependencies..." -ForegroundColor Yellow

if (Test-PortListening 3306) {
    Write-Host "[OK] MySQL appears to be running on port 3306." -ForegroundColor Green
}
else {
    Write-Host "[WARN] Nothing is listening on MySQL port 3306." -ForegroundColor Yellow
    Write-Host "       If SentinelAgent uses local MySQL, make sure MySQL is running."
}

if (Test-PortListening 11434) {
    Write-Host "[OK] Ollama appears to be running on port 11434." -ForegroundColor Green
}
else {
    Write-Host "[WARN] Ollama does not appear to be running on port 11434." -ForegroundColor Yellow
    Write-Host "       AI investigation features may not work until Ollama is started."
}

Write-Host ""

# -----------------------------
# Backend
# -----------------------------

if (Test-PortListening 18080) {
    Write-Host "[SKIP] Backend port 18080 is already in use." -ForegroundColor Yellow
}
else {
    Write-Host "Starting FastAPI backend..." -ForegroundColor Cyan

    $backendCommand = @"
Set-Location '$backend'
Write-Host 'SentinelAgent Backend' -ForegroundColor Cyan
Write-Host 'http://127.0.0.1:18080' -ForegroundColor Green
Write-Host ''
& '$python' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18080
"@

    Start-Process `
        powershell.exe `
        -WindowStyle Hidden `
        -ArgumentList "-NoExit", "-Command", $backendCommand
}

# -----------------------------
# Frontend
# -----------------------------

if (Test-PortListening 5173) {
    Write-Host "[SKIP] Frontend port 5173 is already in use." -ForegroundColor Yellow
}
else {
    Write-Host "Starting Vue frontend..." -ForegroundColor Cyan

    $frontendCommand = @"
Set-Location '$frontend'
Write-Host 'SentinelAgent Frontend' -ForegroundColor Cyan
Write-Host 'http://127.0.0.1:5173' -ForegroundColor Green
Write-Host ''
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
"@

    Start-Process `
        powershell.exe `
        -WindowStyle Hidden `
        -ArgumentList "-NoExit", "-Command", $frontendCommand
}

# -----------------------------
# Wait for services
# -----------------------------

Write-Host ""
Write-Host "Waiting for SentinelAgent services..." -ForegroundColor Yellow

$maxAttempts = 20

for ($i = 1; $i -le $maxAttempts; $i++) {
    $frontendReady = Test-PortListening 5173
    $backendReady = Test-PortListening 18080

    if ($frontendReady -and $backendReady) {
        break
    }

    Start-Sleep -Seconds 1
}

Write-Host ""

if (Test-PortListening 18080) {
    Write-Host "[OK] Backend  : http://127.0.0.1:18080" -ForegroundColor Green
    Write-Host "[OK] Swagger  : http://127.0.0.1:18080/docs" -ForegroundColor Green
}
else {
    Write-Host "[WARN] Backend has not started yet." -ForegroundColor Yellow
}

if (Test-PortListening 5173) {
    Write-Host "[OK] Frontend : http://127.0.0.1:5173" -ForegroundColor Green
}
else {
    Write-Host "[WARN] Frontend has not started yet." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " SentinelAgent startup sequence completed" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------
# Open browser
# -----------------------------

if (Test-PortListening 5173) {
    Start-Process "http://127.0.0.1:5173"
}