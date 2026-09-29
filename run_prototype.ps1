<#
.SYNOPSIS
    HimDrishti One-Click Local Prototype Runner
    SIH 2026 · Problem Statement 26059

.DESCRIPTION
    Launches both the FastAPI backend (port 8000) and the Vite frontend (port 5173)
    in parallel, verifies health, displays URLs, and keeps both running until interrupted.

.EXAMPLE
    .\run_prototype.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
if (-not $repoRoot) {
    $repoRoot = (Get-Location).Path
}
Set-Location $repoRoot

# ── Clean-up helper for shutdown ──────────────────────────────────────────────
$script:backendProc = $null
$script:frontendProc = $null

function Stop-PrototypeServices {
    Write-Host "`nStopping HimDrishti prototype services..." -ForegroundColor Yellow

    # Stop frontend process tree
    if ($script:frontendProc -and -not $script:frontendProc.HasExited) {
        taskkill /PID $script:frontendProc.Id /T /F 2>$null | Out-Null
    }
    $connFrontend = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
    if ($connFrontend) {
        foreach ($c in $connFrontend) {
            taskkill /PID $c.OwningProcess /T /F 2>$null | Out-Null
        }
    }

    # Stop backend process tree
    if ($script:backendProc -and -not $script:backendProc.HasExited) {
        taskkill /PID $script:backendProc.Id /T /F 2>$null | Out-Null
    }
    $connBackend = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($connBackend) {
        foreach ($c in $connBackend) {
            taskkill /PID $c.OwningProcess /T /F 2>$null | Out-Null
        }
    }

    Write-Host "Services stopped cleanly." -ForegroundColor Green
}

# ── Check for stale port bindings ─────────────────────────────────────────────
foreach ($port in @(8000, 5173)) {
    $existing = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Warning "Port $port is currently in use by process $($existing[0].OwningProcess). Terminating stale process..."
        foreach ($c in $existing) {
            taskkill /PID $c.OwningProcess /T /F 2>$null | Out-Null
        }
        Start-Sleep -Milliseconds 500
    }
}

# ── Resolve Python / Uvicorn executable ───────────────────────────────────────
$venvUvicorn = Join-Path $repoRoot ".venv\Scripts\uvicorn.exe"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (Test-Path $venvUvicorn) {
    $backendCmd = $venvUvicorn
    $backendArgs = "backend.main:app --reload --port 8000"
} elseif (Test-Path $venvPython) {
    $backendCmd = $venvPython
    $backendArgs = "-m uvicorn backend.main:app --reload --port 8000"
} else {
    $backendCmd = "uvicorn"
    $backendArgs = "backend.main:app --reload --port 8000"
}

# ── Start FastAPI Backend ─────────────────────────────────────────────────────
Write-Host "Starting FastAPI backend on port 8000..." -ForegroundColor Cyan
$script:backendProc = Start-Process -FilePath $backendCmd -ArgumentList $backendArgs -WorkingDirectory $repoRoot -NoNewWindow -PassThru

# Wait briefly for backend startup (poll /health)
$backendReady = $false
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while ($sw.ElapsedMilliseconds -lt 30000) {
    Start-Sleep -Milliseconds 400
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($res.status -eq "ok") {
            $backendReady = $true
            break
        }
    } catch {
        # continue waiting
    }
}

if (-not $backendReady) {
    Write-Error "Backend failed to respond on http://localhost:8000/health within 30 seconds."
    Stop-PrototypeServices
    exit 1
}

# ── Start Vite Frontend ───────────────────────────────────────────────────────
Write-Host "Starting Vite frontend on port 5173..." -ForegroundColor Cyan
$frontendDir = Join-Path $repoRoot "frontend"
$script:frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $frontendDir -NoNewWindow -PassThru

# Wait briefly for frontend startup
$frontendReady = $false
$sw.Restart()
while ($sw.ElapsedMilliseconds -lt 25000) {
    Start-Sleep -Milliseconds 400
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($res.StatusCode -eq 200) {
            $frontendReady = $true
            break
        }
    } catch {
        # continue waiting
    }
}

if (-not $frontendReady) {
    Write-Error "Frontend failed to respond on http://localhost:5173 within 25 seconds."
    Stop-PrototypeServices
    exit 1
}

# ── Display URLs ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "               HimDrishti Prototype Running                           " -ForegroundColor Green
Write-Host "     AI-Enabled Antarctic Decision Support System · SIH 2026          " -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ★ Frontend Prototype:   http://localhost:5173" -ForegroundColor Yellow
Write-Host "  ★ Backend API:           http://localhost:8000" -ForegroundColor Yellow
Write-Host "  ★ Health Endpoint:       http://localhost:8000/health" -ForegroundColor Yellow
Write-Host "  ★ Swagger API Docs:      http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Both processes running. Press Ctrl+C in this console to stop." -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# ── Keep running until user terminates or process exits ───────────────────────
try {
    while ($true) {
        if ($script:backendProc.HasExited) {
            Write-Warning "FastAPI backend process exited unexpectedly."
            break
        }
        if ($script:frontendProc.HasExited) {
            Write-Warning "Vite frontend process exited unexpectedly."
            break
        }
        Start-Sleep -Seconds 1
    }
} finally {
    Stop-PrototypeServices
}
