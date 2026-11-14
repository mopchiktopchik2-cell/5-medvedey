# Запуск сервиса «М.и.Р.» одним действием.
#
# Проверяет, установлен и запущен ли Docker, при необходимости сам открывает
# Docker Desktop и ждёт готовности движка. Затем вызывает штатный start-lan.ps1:
# тот создаёт .env, генерирует SECRET_KEY, скачивает готовые образы с GitHub
# (или собирает их), ждёт /api/health и открывает сайт в браузере.
#
# Обычно запускается двойным щелчком по start-site.cmd (или по ярлыку
# «М.и.Р. — сайт» на рабочем столе).

param(
    [switch]$NoBrowser,
    [switch]$NoBuild,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Test-DockerEngine {
    try {
        & docker info --format '{{.ServerVersion}}' *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Find-DockerDesktop {
    $candidates = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    return $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

Push-Location $root
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host 'Docker не найден.'
        Write-Host 'Установите Docker Desktop: https://www.docker.com/products/docker-desktop/'
        Write-Host 'После установки запустите этот ярлык снова.'
        exit 1
    }

    if (-not (Test-DockerEngine)) {
        $desktop = Find-DockerDesktop
        if (-not $desktop) {
            Write-Host 'Docker установлен, но его движок не отвечает.'
            Write-Host 'Откройте Docker Desktop вручную, дождитесь статуса Running и повторите.'
            exit 1
        }

        Write-Host 'Docker ещё не запущен — открываем Docker Desktop…'
        Start-Process $desktop

        Write-Host 'Ждём готовности Docker (обычно 30–60 секунд, иногда до 4 минут)…'
        $ready = $false
        for ($i = 0; $i -lt 120; $i++) {
            Start-Sleep -Seconds 2
            if (Test-DockerEngine) {
                $ready = $true
                break
            }
            if ($i % 5 -eq 0) {
                Write-Host '.' -NoNewline
            }
        }
        Write-Host ''

        if (-not $ready) {
            Write-Host 'Docker не запустился за 4 минуты.'
            Write-Host 'Проверьте Docker Desktop: возможно, он просит обновление или включение WSL2.'
            exit 1
        }
    }

    & (Join-Path $PSScriptRoot 'start-lan.ps1') -NoBrowser:$NoBrowser -NoBuild:$NoBuild -Build:$Build
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        Write-Host 'Запуск не удался. Подробности выше и в логах:'
        Write-Host '  docker compose -f docker-compose.yml -f docker-compose.lan.yml logs backend'
        Write-Host ''
        Write-Host 'Если Docker не может скачать образы (TLS handshake timeout),'
        Write-Host 'почините доступ: .\scripts\fix-docker-access.ps1'
        Write-Host 'или перенесите образы с компьютера, где сборка уже работает:'
        Write-Host '  .\scripts\export-images.ps1  ->  .\scripts\import-images.ps1'
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
