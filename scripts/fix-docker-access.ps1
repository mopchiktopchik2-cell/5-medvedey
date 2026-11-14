# Проверяет доступ Docker к Docker Hub и, если он недоступен, настраивает
# зеркало реестра в Docker Desktop.
#
#   .\scripts\fix-docker-access.ps1
#   .\scripts\fix-docker-access.ps1 -CheckOnly
#   .\scripts\fix-docker-access.ps1 -Mirror https://dockerhub.timeweb.cloud
#
# Скрипт меняет только %USERPROFILE%\.docker\daemon.json (делает резервную
# копию) и перезапускает Docker Desktop. Сайт на время перезапуска недоступен.

param(
    [string]$Mirror = '',
    [switch]$Force,
    [switch]$CheckOnly,
    [switch]$NoRestart,
    [string]$DaemonConfigPath = ''
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {
}

$desktopExe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
$mirrorCandidates = @(
    'https://mirror.gcr.io',
    'https://dockerhub.timeweb.cloud',
    'https://huecker.io',
    'https://docker.m.daocloud.io'
)

function Test-RegistryUrl {
    param([string]$Url)

    $probe = $Url.TrimEnd('/') + '/v2/'
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
        $code = & curl.exe -s -o NUL -w '%{http_code}' --max-time 12 $probe 2>$null
        return ($code -in @('200', '401'))
    }

    try {
        $null = Invoke-WebRequest -UseBasicParsing -Uri $probe -TimeoutSec 12 -ErrorAction Stop
        return $true
    } catch {
        $status = $null
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        return ($status -in @(200, 401))
    }
}

function Test-DockerEngine {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & docker info 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $previous
    }
}

function Wait-DockerEngine {
    param([int]$TimeoutSec = 180)

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerEngine) {
            return $true
        }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Invoke-DockerPull {
    param(
        [string]$Image = 'hello-world:latest',
        [int]$TimeoutSec = 90
    )

    $job = Start-Job -ScriptBlock {
        param($img)
        $output = & docker pull $img 2>&1 | Out-String
        [pscustomobject]@{
            ExitCode = $LASTEXITCODE
            Output   = $output
        }
    } -ArgumentList $Image

    if (Wait-Job $job -Timeout $TimeoutSec) {
        $result = Receive-Job $job
        Remove-Job $job -Force
        return $result
    }

    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    return [pscustomobject]@{
        ExitCode = 124
        Output   = "таймаут $TimeoutSec с"
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host 'Docker не найден. Установите Docker Desktop и запустите скрипт снова.'
    exit 1
}

if (-not (Test-DockerEngine)) {
    Write-Host 'Docker Desktop не запущен — запускаю…'
    if (-not (Test-Path $desktopExe)) {
        Write-Host "Не найден $desktopExe. Запустите Docker Desktop вручную и повторите."
        exit 1
    }
    Start-Process $desktopExe | Out-Null
    if (-not (Wait-DockerEngine 240)) {
        Write-Host 'Docker Desktop не запустился за 4 минуты. Перезагрузите компьютер и повторите.'
        exit 1
    }
}

Write-Host 'Проверяю Docker Hub…'
$hubOk = Test-RegistryUrl 'https://registry-1.docker.io'
$pull = $null

if ($hubOk) {
    Write-Host 'Docker Hub отвечает, проверяю скачивание образа…'
    $pull = Invoke-DockerPull
    if ($pull.ExitCode -eq 0 -and -not $Force) {
        Write-Host ''
        Write-Host 'Доступ к Docker Hub работает — менять настройки не нужно.'
        exit 0
    }
    if ($pull.ExitCode -eq 0) {
        Write-Host 'Доступ работает, но включён -Force: всё равно пропишу зеркало.'
    } else {
        Write-Host "Docker Hub отвечает, но скачать образ не удалось (код $($pull.ExitCode)):"
        ($pull.Output -split "`r?`n" | Select-Object -Last 3) | ForEach-Object {
            Write-Host "  $_"
        }
    }
} else {
    Write-Host 'Docker Hub недоступен (сеть, TLS или блокировка).'
}

if ($CheckOnly) {
    Write-Host ''
    Write-Host 'Режим проверки: настройки не меняю.'
    Write-Host 'Для починки запустите без -CheckOnly.'
    exit 1
}

$candidates = if ($Mirror) { @($Mirror) } else { $mirrorCandidates }
$chosen = $null
foreach ($candidate in $candidates) {
    Write-Host "Проверяю зеркало $candidate …"
    if (Test-RegistryUrl $candidate) {
        $chosen = $candidate
        break
    }
}

if (-not $chosen) {
    Write-Host ''
    Write-Host 'Ни Docker Hub, ни зеркала не отвечают.'
    Write-Host 'Варианты:'
    Write-Host '  1. Включите VPN или пропишите прокси: Docker Desktop → Settings → Resources → Proxies.'
    Write-Host '  2. Перенесите готовые образы с другого компьютера:'
    Write-Host '     .\scripts\export-images.ps1  →  .\scripts\import-images.ps1'
    Write-Host '  3. Запустите сайт без Docker Hub: .\start-site-offline.cmd'
    exit 1
}

Write-Host ''
Write-Host "Выбрано зеркало: $chosen"

if (-not $DaemonConfigPath) {
    $DaemonConfigPath = Join-Path $env:USERPROFILE '.docker\daemon.json'
}

$configDir = Split-Path -Parent $DaemonConfigPath
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Force -Path $configDir | Out-Null
}

$hadConfig = Test-Path $DaemonConfigPath
$backup = $null
if ($hadConfig) {
    $backup = "$DaemonConfigPath.bak-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
    Copy-Item $DaemonConfigPath $backup
    Write-Host "Резервная копия: $backup"

    try {
        $config = Get-Content $DaemonConfigPath -Raw | ConvertFrom-Json
    } catch {
        Write-Host "Не удалось разобрать $DaemonConfigPath. Исправьте файл вручную и повторите."
        exit 1
    }
} else {
    $config = New-Object psobject
}

if ($config.PSObject.Properties.Name -contains 'registry-mirrors') {
    $config.'registry-mirrors' = @($chosen)
} else {
    $config | Add-Member -NotePropertyName 'registry-mirrors' -NotePropertyValue @($chosen)
}

$json = $config | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText(
    $DaemonConfigPath,
    $json + "`n",
    (New-Object System.Text.UTF8Encoding($false))
)
Write-Host "Зеркало записано в $DaemonConfigPath"

if ($NoRestart) {
    Write-Host ''
    Write-Host 'Перезапуск пропущен (-NoRestart). Примените настройку командой: docker desktop restart'
    exit 0
}

Write-Host 'Перезапускаю Docker Desktop…'
& docker desktop restart 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0 -and (Test-Path $desktopExe)) {
    Stop-Process -Name 'Docker Desktop' -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Start-Process $desktopExe | Out-Null
}

if (-not (Wait-DockerEngine 240)) {
    Write-Host 'Docker Desktop не поднялся после перезапуска. Перезагрузите компьютер.'
    exit 1
}

$activeMirrors = & docker info --format '{{json .RegistryConfig.Mirrors}}' 2>$null
Write-Host "Зеркала в движке: $activeMirrors"

Write-Host 'Проверяю скачивание через зеркало…'
$verify = Invoke-DockerPull 'hello-world:latest' 120
if ($verify.ExitCode -eq 0) {
    Write-Host ''
    Write-Host 'Готово: Docker скачивает образы. Можно запускать .\start-site.cmd'
    exit 0
}

Write-Host "Скачивание через зеркало не удалось (код $($verify.ExitCode))."
($verify.Output -split "`r?`n" | Select-Object -Last 3) | ForEach-Object {
    Write-Host "  $_"
}

if ($hadConfig -and $backup) {
    Copy-Item $backup $DaemonConfigPath -Force
    Write-Host 'Вернул прежнюю настройку.'
} elseif (-not $hadConfig) {
    Remove-Item $DaemonConfigPath -Force -ErrorAction SilentlyContinue
}

Write-Host 'Перезапускаю Docker Desktop с прежними настройками…'
& docker desktop restart 2>&1 | Out-Null
$null = Wait-DockerEngine 240

Write-Host ''
Write-Host 'Зеркало не помогло. Включите VPN/прокси для Docker Desktop или перенесите образы:'
Write-Host '  .\scripts\export-images.ps1  →  .\scripts\import-images.ps1  →  .\start-site-offline.cmd'
exit 1
