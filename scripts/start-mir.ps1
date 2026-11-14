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
        Write-Host 'Docker не найден — устанавливаю Docker Desktop через winget…'

        $wingetExe = $null
        $wingetCandidates = @(
            (Get-Command winget -ErrorAction SilentlyContinue).Source,
            (Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\winget.exe'),
            'C:\Program Files\WindowsApps\winget.exe'
        )
        foreach ($candidate in $wingetCandidates) {
            if ($candidate -and (Test-Path $candidate)) {
                $wingetExe = $candidate
                break
            }
        }

        if (-not $wingetExe) {
            Write-Host 'winget не найден. Установите Docker Desktop вручную:'
            Write-Host '  https://www.docker.com/products/docker-desktop/'
            Write-Host '  или: winget install --id Docker.DockerDesktop -e'
            exit 1
        }

        Write-Host 'Устанавливаю Docker Desktop через winget (может занять несколько минут)…'
        $wingetStartInfo = New-Object System.Diagnostics.ProcessStartInfo
        $wingetStartInfo.FileName = $wingetExe
        $wingetStartInfo.Arguments = '-install --id Docker.DockerDesktop --source winget --accept-package-agreements --accept-source-agreements'
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identity)
        $wingetStartInfo.UseShellExecute = $true
        if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
            $wingetStartInfo.Verb = 'runAs'
        }
        $wingetProcess = [System.Diagnostics.Process]::Start($wingetStartInfo)
        $wingetProcess.WaitForExit()
        if ($wingetProcess.ExitCode -ne 0) {
            Write-Host "winget завершился с кодом $($wingetProcess.ExitCode). Установите Docker Desktop вручную: https://www.docker.com/products/docker-desktop/"
            exit 1
        }
        Start-Sleep -Seconds 30

        # Docker Desktop устанавливается в Program Files — подгружаем его в PATH текущего процесса.
        $dockerExe = @(
            (Get-Command docker -ErrorAction SilentlyContinue).Source,
            'C:\Program Files\Docker\Docker\resources\bin\docker.exe',
            'C:\Program Files\Docker\Docker\bin\docker.exe',
            'C:\Program Files\Docker\docker.exe'
        ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
        if (-not $dockerExe) {
            Write-Host 'Docker Desktop установился, но docker.exe не найден в ожидаемых местах.'
            Write-Host 'Откройте Docker Desktop и запустите этот ярлык снова.'
            exit 1
        }
        $dockerBinDir = Split-Path -Parent $dockerExe
        if ($dockerBinDir) {
            [Environment]::SetEnvironmentVariable('Path', $env:Path + ';' + $dockerBinDir, 'Process')
        }
        Write-Host 'Docker Desktop установлен.'
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
            Write-Host 'Если открыто окно лицензии или первоначальной настройки — примите его и повторите.'
            exit 1
        }
    }

    # Docker Desktop может быть переключён в режим Windows-контейнеров.
    # Наши образы — Linux, в этом режиме они не запустятся.
    $osType = ''
    try {
        $osType = (& docker info --format '{{.OSType}}' 2>$null | Out-String).Trim()
    } catch {
    }
    if ($osType -and $osType -ne 'linux') {
        Write-Host "Docker Desktop работает в режиме Windows-контейнеров ($osType)."
        Write-Host 'Переключите его на Linux containers: правый клик по иконке Docker в трее'
        Write-Host '→ «Switch to Linux containers…», дождитесь статуса Running и запустите ярлык снова.'
        exit 1
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
