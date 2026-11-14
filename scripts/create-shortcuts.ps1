# Создаёт на рабочем столе ярлыки «М.и.Р. — сайт» и «М.и.Р. — остановить».
#
# Запускать один раз после переноса папки проекта на рабочий компьютер:
#   .\scripts\create-shortcuts.ps1
#
# Ярлыки ссылаются на файлы start-site.cmd и stop-site.cmd в корне проекта,
# поэтому папку проекта можно перемещать только вместе с повторным запуском
# этого скрипта.

param(
    [string]$DesktopDir = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

$desktop = if ($DesktopDir) { $DesktopDir } else { [Environment]::GetFolderPath('Desktop') }
if (-not (Test-Path $desktop)) {
    New-Item -ItemType Directory -Force -Path $desktop | Out-Null
}

$launchTarget = Join-Path $root 'start-site.cmd'
$stopTarget = Join-Path $root 'stop-site.cmd'
foreach ($path in @($launchTarget, $stopTarget)) {
    if (-not (Test-Path $path)) {
        throw "Не найден файл: $path"
    }
}

$shell = New-Object -ComObject WScript.Shell

function New-DesktopShortcut {
    param(
        [string]$Name,
        [string]$TargetPath,
        [string]$Description
    )

    $path = Join-Path $desktop $Name
    $shortcut = $shell.CreateShortcut($path)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = $root
    $shortcut.Description = $Description
    $shortcut.WindowStyle = 1
    $shortcut.Save()
    Write-Host "Готово: $path"
}

New-DesktopShortcut `
    -Name 'М.и.Р. — сайт.lnk' `
    -TargetPath $launchTarget `
    -Description 'Запустить калькулятор себестоимости и открыть сайт'

New-DesktopShortcut `
    -Name 'М.и.Р. — остановить.lnk' `
    -TargetPath $stopTarget `
    -Description 'Остановить калькулятор себестоимости (данные сохранятся)'

Write-Host ''
Write-Host 'Теперь сайт запускается двойным щелчком по ярлыку «М.и.Р. — сайт».'
