$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $PSScriptRoot ".venv"
$Wheelhouse = Join-Path $PSScriptRoot "wheels"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.11+ is required. Install Python from python.org, then run this script again."
  }
  $Python = "python"
} else {
  $Python = "py"
}

if (-not (Test-Path $Venv)) {
  & $Python -3 -m venv $Venv
}

$VenvPython = Join-Path $Venv "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip

if (Test-Path $Wheelhouse) {
  & $VenvPython -m pip install --no-index --find-links $Wheelhouse -r (Join-Path $PSScriptRoot "requirements-offline.txt")
} else {
  Write-Host "No local wheelhouse found; downloading dependencies for the first setup."
  & $VenvPython -m pip install -r (Join-Path $PSScriptRoot "requirements-offline.txt")
}

New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot "data") | Out-Null
Write-Host "Offline installation completed."