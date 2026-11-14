# Запускает бэкенд и фронтенд в отдельных окнах PowerShell.
# Требует выполненного setup.ps1.

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'

Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "cd '$backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000"
)

Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "cd '$frontend'; npm run dev"
)

Write-Host 'Бэкенд: http://localhost:8000/docs'
Write-Host 'Фронтенд: http://localhost:5173'
