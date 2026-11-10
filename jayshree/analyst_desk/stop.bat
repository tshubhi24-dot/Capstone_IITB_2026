@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker Desktop is required. Install it, then run this script again.
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo Docker's engine is not running. Start Docker Desktop, then retry.
    exit /b 1
)

docker compose down
if errorlevel 1 (
    echo Could not stop the Analyst Desk services. Check Docker Compose output above.
    exit /b 1
)

echo Analyst Desk services stopped. Persistent data volumes were kept.
