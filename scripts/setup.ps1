# Первичная настройка окружения (Windows, PowerShell).

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$envPath = Join-Path $root '.env'

if (-not (Test-Path $envPath)) {
    Copy-Item (Join-Path $root '.env.example') $envPath
    Write-Host 'Создан .env из .env.example'
}

# Генерируем SECRET_KEY один раз: с дефолтным ключом приложение
# не запустится в production (и подпись JWT слишком слабая).
$envLines = @(Get-Content $envPath)
$secretLine = $envLines | Where-Object { $_ -match '^\s*SECRET_KEY\s*=\s*\S' }
if (-not $secretLine) {
    $secret = & python -c "import secrets; print(secrets.token_urlsafe(48))"
    if (-not $secret) {
        $secret = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    }
    $envLines = $envLines | Where-Object { $_ -notmatch '^\s*#?\s*SECRET_KEY\s*=' }
    $envLines += "SECRET_KEY=$secret"
    # UTF-8 без BOM: с BOM ломается первый ключ в .env.
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($envPath, $envLines, $utf8)
    Write-Host 'Сгенерирован SECRET_KEY в .env'
}

Push-Location $backend
if (-not (Test-Path '.venv')) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location

Push-Location $frontend
npm install
Pop-Location

Write-Host 'Готово. Запуск: .\scripts\dev.ps1'
