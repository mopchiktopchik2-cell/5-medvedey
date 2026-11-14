# Загружает Docker-образы из tar-файла, созданного export-images.ps1.
#
#   .\scripts\import-images.ps1
#   .\scripts\import-images.ps1 -Archive D:\transfer\5-medvedey-images.tar
#
# После этого сервис запускается без сборки и без Docker Hub:
#   .\start-site.cmd            (сам использует образы, если сборка недоступна)
#   .\scripts\start-lan.ps1 -NoBuild   (сразу без попытки сборки)

param(
    [string]$Archive = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

if (-not $Archive) {
    $Archive = Join-Path $root 'dist\5-medvedey-images.tar'
}
if (-not (Test-Path $Archive)) {
    throw "Не найден архив: $Archive. Укажите путь через -Archive."
}

Write-Host "Загружаем образы из $Archive …"
& docker load -i $Archive
if ($LASTEXITCODE -ne 0) {
    throw 'docker load завершился с ошибкой'
}

Write-Host ''
Write-Host 'Образы загружены. Запуск:'
Write-Host '  .\scripts\start-lan.ps1 -NoBuild'
