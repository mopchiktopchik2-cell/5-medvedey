# Восстановление данных из архива, созданного .\scripts\backup.ps1.
#
#   .\scripts\restore.ps1 -Archive .\backups\5-medvedey-20261114-120000.zip
#   .\scripts\restore.ps1 -Archive ... -DataDir C:\tmp\data   # локальный режим
#
# Скрипт останавливает backend перед заменой базы и поднимает его обратно.
# Текущая база сохраняется рядом как app.db.before-restore-<дата>.

param(
    [Parameter(Mandatory = $true)]
    [string]$Archive,
    [switch]$Force,
    [string]$DataDir = ""
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $Archive)) {
    throw "Архив не найден: $Archive"
}
$Archive = (Resolve-Path $Archive).Path

if (-not $Force) {
    $answer = Read-Host 'Восстановление перезапишет текущие данные. Продолжить? Введите YES'
    if ($answer -ne 'YES') {
        Write-Host 'Отменено.'
        exit 0
    }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$staging = Join-Path $env:TEMP "mir-restore-$stamp"
Expand-Archive -Path $Archive -DestinationPath $staging -Force

$manifest = Join-Path $staging 'manifest.txt'
$mode = 'local'
if (Test-Path $manifest) {
    $modeLine = Get-Content $manifest | Where-Object { $_ -like 'mode:*' } | Select-Object -First 1
    if ($modeLine) { $mode = $modeLine.Split(':', 2)[1].Trim() }
}

function Invoke-Docker {
    param([scriptblock]$Action)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Action 2>&1 | ForEach-Object { Write-Verbose $_ }
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
}

$dockerAvailable = [bool](Get-Command docker -ErrorAction SilentlyContinue)
$running = @()
if ($dockerAvailable) {
    $running = @(& docker ps --format '{{.Names}}' 2>$null)
}
$backendUp = [bool]($running -match '-backend-1$')
$dbUp = [bool]($running -match '-db-1$')

Push-Location $root
try {
    if ($mode -eq 'postgres' -and $dbUp) {
        Write-Host 'Режим: Docker + PostgreSQL'
        $dump = Join-Path $staging 'postgres.sql'
        if (-not (Test-Path $dump)) { throw 'В архиве нет postgres.sql' }
        Invoke-Docker { docker compose -f docker-compose.yml -f docker-compose.postgres.yml stop backend } | Out-Null
        $code = Invoke-Docker { docker compose cp $dump 'db:/tmp/mir-restore.sql' }
        if ($code -ne 0) { throw 'Не удалось передать дамп в контейнер' }
        $code = Invoke-Docker {
            docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db `
                sh -c 'psql -v ON_ERROR_STOP=1 -U mir -d mir < /tmp/mir-restore.sql'
        }
        Invoke-Docker { docker compose exec -T db rm -f /tmp/mir-restore.sql } | Out-Null
        Invoke-Docker { docker compose -f docker-compose.yml -f docker-compose.postgres.yml start backend } | Out-Null
        if ($code -ne 0) { throw 'psql завершился с ошибкой' }
    }
    elseif ($mode -eq 'docker-sqlite' -and $backendUp) {
        Write-Host 'Режим: Docker + SQLite'
        $database = Join-Path $staging 'app.db'
        if (-not (Test-Path $database)) { throw 'В архиве нет app.db' }
        Invoke-Docker { docker compose stop backend } | Out-Null
        Invoke-Docker { docker compose cp 'backend:/app/data/app.db' (Join-Path $staging 'app.db.before-restore') } | Out-Null
        $code = Invoke-Docker { docker compose cp $database 'backend:/app/data/app.db' }
        if ($code -ne 0) {
            Invoke-Docker { docker compose start backend } | Out-Null
            throw 'Не удалось записать базу в контейнер'
        }
        foreach ($name in @('uploads', 'outbox')) {
            $path = Join-Path $staging $name
            if (Test-Path $path) {
                Invoke-Docker { docker compose cp $path "backend:/app/data/$name" } | Out-Null
            }
        }
        Invoke-Docker { docker compose start backend } | Out-Null
    }
    else {
        if (-not $DataDir) {
            $DataDir = Join-Path $root 'backend\data'
        }
        New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
        $database = Join-Path $staging 'app.db'
        if (-not (Test-Path $database)) { throw 'В архиве нет app.db' }

        $target = Join-Path $DataDir 'app.db'
        if (Test-Path $target) {
            Copy-Item -Force $target (Join-Path $DataDir "app.db.before-restore-$stamp")
        }
        Copy-Item -Force $database $target
        foreach ($name in @('uploads', 'outbox')) {
            $path = Join-Path $staging $name
            if (Test-Path $path) {
                Copy-Item -Recurse -Force $path (Join-Path $DataDir $name)
            }
        }
        Write-Host "Данные восстановлены в $DataDir"
    }
}
finally {
    Pop-Location
    Remove-Item -Recurse -Force $staging -ErrorAction SilentlyContinue
}

Write-Host 'Готово. Проверьте вход и один расчёт.'
