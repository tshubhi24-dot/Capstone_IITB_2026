@echo off
setlocal
cd /d "%~dp0"

py -3 -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>nul
if errorlevel 1 (
    echo Python 3.12 or newer and the Python launcher are required.
    echo Install Python from https://www.python.org/downloads/ and try again.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo.
echo Setup complete. The project environment is in .venv.
