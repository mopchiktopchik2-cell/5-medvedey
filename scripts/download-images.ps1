# Скачивает готовые Docker-образы с GitHub Releases и загружает их.
# Нужен для запуска на компьютере без доступа к Docker Hub.
#
#   .\scripts\download-images.ps1
#   .\scripts\download-images.ps1 -Force
#   .\scripts\download-images.ps1 -Archive D:\5-medvedey-images-linux-amd64.tar.gz
#
# Архив выбирается по архитектуре Docker: amd64 или arm64.

param(
    [string]$Archive = '',
    [string]$Url = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {
}

$root = Split-Path -Parent $PSScriptRoot
$releaseBase = 'https://github.com/mopchiktopchik2-cell/5-medvedey/releases/download/images'

function Get-DockerArch {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $arch = (& docker version --format '{{.Server.Arch}}' 2>$null | Out-String).Trim()
    } finally {
        $ErrorActionPreference = $previous
    }
    if (-not $arch) {
        throw 'Docker не запущен. Запустите Docker Desktop и повторите.'
    }
    return $arch
}

function Test-AppImages {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & docker image inspect 5-medvedey-backend:latest *> $null
        if ($LASTEXITCODE -ne 0) { return $false }
        & docker image inspect 5-medvedey-frontend:latest *> $null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $previous
    }
}

$arch = Get-DockerArch
if ($arch -notin @('amd64', 'arm64')) {
    throw "Неподдерживаемая архитектура Docker: $arch. Нужна amd64 или arm64."
}

if (-not $Archive) {
    $distDir = Join-Path $root 'dist'
    New-Item -ItemType Directory -Force -Path $distDir | Out-Null
    $Archive = Join-Path $distDir "5-medvedey-images-linux-$arch.tar.gz"

    if ($Force -or -not (Test-Path $Archive)) {
        if (-not $Url) {
            $Url = "$releaseBase/5-medvedey-images-linux-$arch.tar.gz"
        }
        if (Test-Path $Archive) {
            Remove-Item $Archive -Force
        }

        Write-Host "Скачиваю готовые образы для $arch с GitHub…"
        Write-Host "  $Url"
        Write-Host 'Это может занять несколько минут.'

        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            & curl.exe --location --fail --silent --show-error --connect-timeout 30 --max-time 900 --retry 4 --retry-delay 3 --output $Archive $Url
            $downloadExit = $LASTEXITCODE
        } else {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Archive -TimeoutSec 900
            $downloadExit = 0
        }

        if ($downloadExit -ne 0 -or -not (Test-Path $Archive)) {
            if (Test-Path $Archive) {
                Remove-Item $Archive -Force -ErrorAction SilentlyContinue
            }
            throw "Не удалось скачать архив с GitHub (код $downloadExit). Проверьте интернет или используйте offline-архив."
        }
    } else {
        Write-Host "Использую уже скачанный архив: $Archive"
    }
} else {
    if (-not (Test-Path $Archive)) {
        throw "Не найден архив: $Archive"
    }
    Write-Host "Загружаю образы из $Archive"
}

$sizeMb = [math]::Round((Get-Item $Archive).Length / 1MB)
Write-Host "Размер архива: $sizeMb МБ"
Write-Host 'Загружаю образы в Docker…'

& docker load -i $Archive
if ($LASTEXITCODE -ne 0) {
    throw 'docker load завершился с ошибкой'
}

if (-not (Test-AppImages)) {
    throw 'После загрузки не найдены образы 5-medvedey-backend:latest и 5-medvedey-frontend:latest.'
}

Write-Host ''
Write-Host 'Образы готовы. Запуск: .\start-site.cmd'
