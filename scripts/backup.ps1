# Резервная копия данных сервиса.
#
#   .\scripts\backup.ps1                 # в папку backups\
#   .\scripts\backup.ps1 -OutDir D:\bkp  # в указанную папку
#
# Понимает три режима и выбирает нужный сам:
#   * Docker + PostgreSQL  — pg_dump;
#   * Docker + SQLite      — согласованный снимок через sqlite3 backup;
#   * локальный запуск     — снимок backend\data\app.db без остановки сервера.
# В архив попадают база, логотип (uploads) и письма из outbox, если они есть.

param(
    [string]$OutDir = ""
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

if (-not $OutDir) {
    $OutDir = Join-Path $root 'backups'
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$staging = Join-Path $env:TEMP "mir-backup-$stamp"
New-Item -ItemType Directory -Force -Path $staging | Out-Null

# Docker пишет прогресс в stderr, а PowerShell 5.1 считает это ошибкой.
# Поэтому docker-команды выполняем с Continue и проверяем код возврата сами.
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
$mode = ''

Push-Location $root
try {
    if ($dbUp) {
        $mode = 'postgres'
        Write-Host 'Режим: Docker + PostgreSQL'
        $code = Invoke-Docker {
            docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db `
                sh -c 'pg_dump --clean --if-exists -U mir -d mir > /tmp/mir-backup.sql'
        }
        if ($code -ne 0) { throw 'pg_dump завершился с ошибкой' }
        $code = Invoke-Docker { docker compose cp 'db:/tmp/mir-backup.sql' (Join-Path $staging 'postgres.sql') }
        if ($code -ne 0) { throw 'Не удалось забрать дамп из контейнера' }
        Invoke-Docker { docker compose exec -T db rm -f /tmp/mir-backup.sql } | Out-Null
    }
    elseif ($backendUp) {
        $mode = 'docker-sqlite'
        Write-Host 'Режим: Docker + SQLite'
        $snapshot = "import sqlite3; s=sqlite3.connect('/app/data/app.db'); d=sqlite3.connect('/app/data/backup-snapshot.db'); s.backup(d); d.close(); s.close()"
        $code = Invoke-Docker { docker compose exec -T backend python -c $snapshot }
        if ($code -ne 0) { throw 'Не удалось сделать снимок базы в контейнере' }
        $code = Invoke-Docker {
            docker compose cp 'backend:/app/data/backup-snapshot.db' (Join-Path $staging 'app.db')
        }
        if ($code -ne 0) { throw 'Не удалось забрать снимок базы из контейнера' }
        Invoke-Docker { docker compose exec -T backend rm -f /app/data/backup-snapshot.db } | Out-Null

        foreach ($name in @('uploads', 'outbox')) {
            $destination = Join-Path $staging $name
            $code = Invoke-Docker { docker compose cp "backend:/app/data/$name" $destination }
            if ($code -ne 0 -and (Test-Path $destination)) {
                Remove-Item -Recurse -Force $destination
            }
        }
    }
    elseif (Test-Path (Join-Path $root 'backend\data\app.db')) {
        $mode = 'local'
        Write-Host 'Режим: локальный запуск'
        $python = Join-Path $root 'backend\.venv\Scripts\python.exe'
        if (-not (Test-Path $python)) { $python = 'python' }
        $source = Join-Path $root 'backend\data\app.db'
        $target = Join-Path $staging 'app.db'
        & $python -c "import sqlite3, sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" $source $target
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось сделать снимок backend\data\app.db' }

        foreach ($name in @('uploads', 'outbox')) {
            $path = Join-Path $root "backend\data\$name"
            if (Test-Path $path) {
                Copy-Item -Recurse -Force $path (Join-Path $staging $name)
            }
        }
    }
    else {
        throw 'Не нашёл ни запущенный стек, ни backend\data\app.db. Запустите сервис или укажите данные вручную.'
    }
}
finally {
    Pop-Location
}

$manifest = @(
    "created: $(Get-Date -Format o)"
    "mode: $mode"
    "commit: $(git -C $root rev-parse --short HEAD 2>$null)"
    'files:'
)
Push-Location $staging
try {
    Get-ChildItem -Recurse -File | ForEach-Object {
        $relative = (Resolve-Path -Relative $_.FullName).Replace('\', '/')
        $manifest += "  $relative ($($_.Length) bytes)"
    }
} finally {
    Pop-Location
}
$manifest | Set-Content -Path (Join-Path $staging 'manifest.txt') -Encoding UTF8

$archive = Join-Path $OutDir "5-medvedey-$stamp.zip"
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $archive -Force
Remove-Item -Recurse -Force $staging

$bytes = (Get-Item $archive).Length
$size = if ($bytes -ge 1MB) { '{0:N1} МБ' -f ($bytes / 1MB) } else { '{0:N0} КБ' -f ($bytes / 1KB) }
Write-Host ''
Write-Host "Готово: $archive ($size)"
Write-Host "Режим: $mode"
Write-Host 'Восстановление: .\scripts\restore.ps1 -Archive <путь к архиву>'
