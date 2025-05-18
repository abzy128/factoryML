# 1. Check if uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed. Please install it from https://github.com/astral-sh/uv"
    exit 1
}

# 2. Sync the repository
uv sync

# 3. Activate venv
$venvActivate = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
} else {
    Write-Host "Could not find venv activation script at $venvActivate"
    exit 1
}
# 
# 4. Run the server
uvicorn app.main:app --port 8001
