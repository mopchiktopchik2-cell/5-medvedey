# Первичная настройка окружения (Windows, PowerShell).

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'

if (-not (Test-Path (Join-Path $root '.env'))) {
    Copy-Item (Join-Path $root '.env.example') (Join-Path $root '.env')
    Write-Host 'Создан .env из .env.example'
}

Push-Location $backend
if (-not (Test-Path '.venv')) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location

Push-Location $frontend
npm install
Pop-Location

Write-Host 'Готово. Запуск: .\scripts\dev.ps1'
