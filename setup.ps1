$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating the project environment with Python 3.11..."
    & py -3.11 -m venv (Join-Path $projectRoot ".venv")
}

Write-Host "Installing backend and Streamlit dependencies..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $projectRoot "requirements.txt")

Write-Host "Setup complete. Start the app with: .\run.ps1"
