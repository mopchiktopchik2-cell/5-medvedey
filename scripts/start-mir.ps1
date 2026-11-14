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
        $wingetArgs = 'install --id Docker.DockerDesktop -e --source winget --accept-package-agreements --accept-source-agreements'
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identity)
        $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

        if ($isAdmin) {
            $wingetProcess = Start-Process -FilePath $wingetExe -ArgumentList $wingetArgs -Wait -PassThru -NoNewWindow
        } else {
            try {
                $wingetProcess = Start-Process -FilePath $wingetExe -ArgumentList $wingetArgs -Wait -PassThru -Verb RunAs
            } catch {
                Write-Host "Не удалось запустить установку Docker Desktop (нужны права администратора): $($_.Exception.Message)"
                Write-Host 'Установите Docker Desktop вручную: https://www.docker.com/products/docker-desktop/'
                exit 1
            }
        }
        if ($wingetProcess.ExitCode -ne 0) {
            Write-Host "winget завершился с кодом $($wingetProcess.ExitCode). Установите Docker Desktop вручную: https://www.docker.com/products/docker-desktop/"
            exit 1
        }
        # После установки Docker Desktop/winget может занять время; ищем docker.exe и запускаем приложение.
        $desktop = Find-DockerDesktop
        if ($desktop -and -not (Test-DockerEngine)) {
            Start-Process $desktop | Out-Null
        }

        $dockerExe = $null
        for ($i = 0; $i -lt 60; $i++) {
            $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
            $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
            $env:Path = "$machinePath;$userPath;$env:Path"

            $dockerExe = @(
                (Get-Command docker -ErrorAction SilentlyContinue).Source,
                'C:\Program Files\Docker\Docker\resources\bin\docker.exe',
                'C:\Program Files\Docker\Docker\bin\docker.exe',
                'C:\Program Files\Docker\docker.exe'
            ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

            if ($dockerExe) { break }
            Start-Sleep -Seconds 5
        }

        if (-not $dockerExe) {
            Write-Host 'Docker Desktop установлен, но docker.exe не найден.'
            Write-Host 'Перезагрузите компьютер (если требуется установщиком), откройте Docker Desktop и запустите этот ярлык снова.'
            exit 1
        }

        $dockerBinDir = Split-Path -Parent $dockerExe
        if ($dockerBinDir -and ($env:Path -notlike "*$dockerBinDir*")) {
            $env:Path = "$env:Path;$dockerBinDir"
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
