@echo off
setlocal
set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\market-backend"
set "FRONTEND=%~dp0frontend"
set "VENV=%~dp0.venv\Scripts\python.exe"
set "PORT=8080"
set "OFFLINE_MODE=true"
set "ALLOW_MONGOMOCK=false"
set "OFFLINE_DB_PATH=%~dp0data\market_db.json"
set "BACKUP_DIR=%~dp0data\backups"
set "FRONTEND_DIR=%FRONTEND%"
set "PYTHONPATH=%BACKEND%"

if not exist "%VENV%" (
  echo Run windows\install-offline.ps1 first.
  pause
  exit /b 1
)

if not exist "%FRONTEND%\index.html" (
  echo The bundled frontend is missing from windows\frontend.
  pause
  exit /b 1
)

cd /d "%BACKEND%"
start "Mini Market - Offline API" /min "%VENV%" -m uvicorn server:app --host 127.0.0.1 --port %PORT%
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:%PORT%/login"
echo Mini Market is running at http://127.0.0.1:%PORT%
echo Close the API window or run windows\stop-offline.bat to stop it.
endlocal