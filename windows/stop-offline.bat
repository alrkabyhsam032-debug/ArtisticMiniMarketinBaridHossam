@echo off
taskkill /FI "WINDOWTITLE eq Mini Market - Offline API*" /T /F >nul 2>&1
taskkill /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *Mini Market*" /T /F >nul 2>&1
echo Mini Market offline server stopped.