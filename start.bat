@echo off
title ASTRA Backend
echo.
echo  ╔══════════════════════════╗
echo  ║   ASTRA v0.2  · start   ║
echo  ╚══════════════════════════╝
echo.

:: Killuj stary proces na porcie 8001
echo [1/2] Sprawdzam port 8001...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001 " ^| findstr "LISTENING"') do (
    echo       Killuje PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)

:: Uruchom serwer
echo [2/2] Startuje serwer...
echo.
cd /d "%~dp0backend"
python -m uvicorn main:app --port 8001

pause
