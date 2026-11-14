# Сохраняет готовые Docker-образы в один tar-файл.
#
# Нужно, когда на другом компьютере Docker Hub недоступен (TLS handshake
# timeout) и собрать образы там нельзя. Запускать на компьютере, где сервис
# уже собрался и работает:
#
#   .\scripts\export-images.ps1
#   .\scripts\export-images.ps1 -OutDir D:\transfer
#
# Затем перенести tar на целевой компьютер и выполнить:
#   .\scripts\import-images.ps1 -Archive D:\transfer\5-medvedey-images.tar
#   .\start-site.cmd

param(
    [string]$OutDir = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

if (-not $OutDir) {
    $OutDir = Join-Path $root 'dist'
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$images = @(
    '5-medvedey-backend:latest',
    '5-medvedey-frontend:latest'
)

foreach ($image in $images) {
    & docker image inspect $image *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Образ $image не найден. Сначала соберите и запустите сервис: .\scripts\start-lan.ps1"
    }
}

$archive = Join-Path $OutDir '5-medvedey-images.tar'
Write-Host "Сохраняем образы в $archive …"
& docker save -o $archive @images
if ($LASTEXITCODE -ne 0) {
    throw 'docker save завершился с ошибкой'
}

$sizeMb = [math]::Round((Get-Item $archive).Length / 1MB)
Write-Host ''
Write-Host "Готово: $archive ($sizeMb МБ)"
Write-Host 'Перенесите этот файл на целевой компьютер и выполните там:'
Write-Host "  .\scripts\import-images.ps1 -Archive `"$archive`""
