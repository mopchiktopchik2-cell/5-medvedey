# Останавливает сервис, запущенный через .\scripts\start-lan.ps1.
# Данные в томе backend-data сохраняются.

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
try {
    docker compose -f docker-compose.yml -f docker-compose.lan.yml down
    Write-Host 'Сервис остановлен. Данные остались в томе backend-data.'
} finally {
    Pop-Location
}
