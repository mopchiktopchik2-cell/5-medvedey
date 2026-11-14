# Запускает сервис для внутренней сети через Docker (HTTP, порт 8080).
# Используется для пилота или показа заказчику с другого компьютера.
# Останавливать: .\scripts\stop-lan.ps1

param(
    [switch]$NoBrowser,
    [switch]$NoBuild
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root '.env'

function Test-AppImages {
    & docker image inspect 5-medvedey-backend:latest *> $null
    if ($LASTEXITCODE -ne 0) { return $false }
    & docker image inspect 5-medvedey-frontend:latest *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host 'Docker не найден. Установите Docker Desktop или запустите .\scripts\dev.ps1'
    exit 1
}

if ($NoBuild -and -not (Test-AppImages)) {
    Write-Host 'Локальные образы не найдены. Сначала загрузите архив:'
    Write-Host '  .\scripts\import-images.ps1 -Archive <путь к 5-medvedey-images.tar>'
    exit 1
}

if (-not (Test-Path $envPath)) {
    Copy-Item (Join-Path $root '.env.example') $envPath
    Write-Host 'Создан .env из .env.example'
}

# Без SECRET_KEY контейнер не стартует, поэтому генерируем его при первом запуске.
$envLines = @(Get-Content $envPath)
if (-not ($envLines | Where-Object { $_ -match '^\s*SECRET_KEY\s*=\s*\S' })) {
    $secret = & python -c "import secrets; print(secrets.token_urlsafe(48))"
    if (-not $secret) {
        $secret = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    }
    $envLines = $envLines | Where-Object { $_ -notmatch '^\s*#?\s*SECRET_KEY\s*=' }
    $envLines += "SECRET_KEY=$secret"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($envPath, $envLines, $utf8)
    Write-Host 'Сгенерирован SECRET_KEY в .env'
}

Push-Location $root
# Docker пишет прогресс сборки в stderr; в Windows PowerShell это ошибки,
# поэтому на время вызова отключаем Stop, иначе скрипт упадёт на «Building».
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'

$composeArgs = @('-f', 'docker-compose.yml', '-f', 'docker-compose.lan.yml', 'up', '-d')
if (-not $NoBuild) {
    $composeArgs += '--build'
}

try {
    & docker compose @composeArgs
    $composeExit = $LASTEXITCODE

    # Docker Hub может быть недоступен (TLS handshake timeout). Если образы
    # уже загружены на компьютер, поднимаем их без сборки.
    if ($composeExit -ne 0 -and -not $NoBuild -and (Test-AppImages)) {
        Write-Host ''
        Write-Host 'Сборка не удалась — похоже, Docker Hub недоступен.'
        Write-Host 'Запускаем уже загруженные образы без сборки…'
        & docker compose -f docker-compose.yml -f docker-compose.lan.yml up -d
        $composeExit = $LASTEXITCODE
    }
} finally {
    $ErrorActionPreference = $previousPreference
    Pop-Location
}

if ($composeExit -ne 0) {
    Write-Host "Не удалось собрать и запустить контейнеры (код $composeExit)."
    Write-Host 'Если ошибка про registry-1.docker.io или TLS handshake timeout — Docker Hub недоступен.'
    Write-Host 'Почините доступ: .\scripts\fix-docker-access.ps1'
    Write-Host 'Или перенесите готовые образы с другого компьютера:'
    Write-Host '  на рабочем компьютере: .\scripts\export-images.ps1'
    Write-Host '  здесь:                 .\scripts\import-images.ps1 -Archive <путь к tar>'
    Write-Host '  затем:                 .\scripts\start-lan.ps1 -NoBuild'
    exit 1
}

Write-Host 'Ждём готовности сервиса…'
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        # Проверяем через nginx: так же, как это делает браузер сотрудника.
        $response = Invoke-WebRequest -UseBasicParsing 'http://localhost:8080/api/health' -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    Write-Host 'Сервис не ответил за 2 минуты. Логи: docker compose logs backend'
    exit 1
}

# Основной IP в локальной сети — по нему заходят другие компьютеры.
$ip = (Get-NetIPConfiguration |
    Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
    Select-Object -First 1).IPv4Address.IPAddress
if (-not $ip) {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
        Select-Object -First 1).IPAddress
}

Write-Host ''
Write-Host "Сайт на этом компьютере: http://localhost:8080"
if ($ip) {
    Write-Host "Сайт в локальной сети:    http://${ip}:8080"
}
Write-Host ''
Write-Host 'Демо-доступы:'
Write-Host '  менеджер  — manager@mir.ru / manager123'
Write-Host '  технолог  — technologist@mir.ru / technolog123'
Write-Host ''
Write-Host 'Если с другого компьютера сайт не открывается, разрешите порт 8080'
Write-Host 'в брандмауэре Windows (PowerShell от администратора):'
Write-Host '  New-NetFirewallRule -DisplayName "5-medvedey LAN" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow'
Write-Host ''
Write-Host 'Остановка: .\scripts\stop-lan.ps1'

$openUrl = if ($ip) { "http://${ip}:8080" } else { 'http://localhost:8080' }
if (-not $NoBrowser) {
    Start-Process $openUrl
}
