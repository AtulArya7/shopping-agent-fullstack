$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$streamlitApp = Join-Path $projectRoot "streamlit_app\app.py"
$backendDir = Join-Path $projectRoot "backend"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Project environment not found. Run .\setup.ps1 once, then run .\run.ps1."
}

if (-not $env:BACKEND_URL) {
    $env:BACKEND_URL = "http://127.0.0.1:8000"
}

if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    throw "Port 8000 is already in use. Stop the existing backend and run .\run.ps1 again."
}

Write-Host "Starting FastAPI at http://127.0.0.1:8000 ..."
$backendProcess = Start-Process `
    -FilePath $venvPython `
    -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $backendDir `
    -PassThru `
    -WindowStyle Hidden

try {
    $backendReady = $false
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        if ($backendProcess.HasExited) {
            throw "FastAPI stopped during startup."
        }
        try {
            $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 1
            $backendReady = $true
            break
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }

    if (-not $backendReady) {
        throw "FastAPI did not become ready within 30 seconds."
    }

    Write-Host "Starting Streamlit at http://localhost:8501 ..."
    & $venvPython -m streamlit run $streamlitApp --server.address 127.0.0.1 --server.port 8501
}
finally {
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id
    }
}
