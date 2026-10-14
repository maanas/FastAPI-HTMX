# Setup for Windows, the same steps as the README: uv sync, .env, migrations.
# Run it from the repository root: .\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed. Install it from https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Red
    exit 1
}

Write-Host "Installing dependencies..." -ForegroundColor Blue
uv sync
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (Test-Path ".env") {
    Write-Host ".env already exists, left unchanged." -ForegroundColor Yellow
} else {
    Copy-Item ".env.example" ".env"
    # Replace the AUTH_SECRET placeholder with a random secret (never printed).
    $bytes = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $rng.Dispose()
    $secret = [Convert]::ToBase64String($bytes).Replace("+", "-").Replace("/", "_").TrimEnd("=")
    $lines = Get-Content ".env" | ForEach-Object {
        if ($_ -match "^AUTH_SECRET=") { "AUTH_SECRET=$secret" } else { $_ }
    }
    Set-Content ".env" $lines -Encoding ASCII
    Write-Host ".env created from .env.example. Edit it: replace the remaining change-me values." -ForegroundColor Green
}

Write-Host "Running database migrations..." -ForegroundColor Blue
& .venv\Scripts\alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Create a superuser:  .venv\Scripts\python -m app.commands.create_superuser"
Write-Host "Start the app:       .venv\Scripts\python main.py   (http://127.0.0.1:8080)"
