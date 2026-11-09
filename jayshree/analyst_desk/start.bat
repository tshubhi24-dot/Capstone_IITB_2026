@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker Desktop is required. Install it, then run this script again.
    exit /b 1
)

docker info >nul 2>nul
if not errorlevel 1 goto engine_ready

set "DOCKER_DESKTOP=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if not exist "%DOCKER_DESKTOP%" (
    echo Docker Desktop is not installed. Install it, then run this file again.
    exit /b 1
)

echo Starting Docker Desktop...
start "" "%DOCKER_DESKTOP%"
set /a ENGINE_ATTEMPTS=0
:wait_for_engine
docker info >nul 2>nul
if not errorlevel 1 goto engine_ready
set /a ENGINE_ATTEMPTS+=1
if %ENGINE_ATTEMPTS% GEQ 150 (
    echo Docker Desktop did not become ready within 5 minutes.
    echo Open Docker Desktop and check that its Linux engine is running.
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto wait_for_engine

:engine_ready
if not exist ".env" goto missing_env

where git >nul 2>nul
if errorlevel 1 goto missing_git

if not "%~2"=="" goto invalid_usage
if not "%~1"=="" goto selected_commit

echo Checking the latest main commit...
git fetch --quiet origin main
if errorlevel 1 goto git_fetch_failed
set "MAIN_SHA="
for /f "delims=" %%i in ('git rev-parse --short^=7 FETCH_HEAD') do set "MAIN_SHA=%%i"
if not defined MAIN_SHA goto git_fetch_failed
goto pull_image

:selected_commit
set "MAIN_SHA="
for /f "delims=" %%i in ('git rev-parse --short^=7 "%~1^{commit}" 2^>nul') do set "MAIN_SHA=%%i"
if not defined MAIN_SHA goto invalid_version
echo Using the selected commit %MAIN_SHA%...

:pull_image
set "ANALYSTDESK_IMAGE=ghcr.io/tshubhi24-dot/analyst-desk:sha-%MAIN_SHA%"
echo Checking for the image built from commit %MAIN_SHA%...
docker pull "%ANALYSTDESK_IMAGE%"
if not errorlevel 1 goto image_ready

echo The image is not available yet. Retrying once in 60 seconds...
timeout /t 60 /nobreak >nul
docker pull "%ANALYSTDESK_IMAGE%"
if errorlevel 1 goto image_unavailable

:image_ready
echo Starting the full stack with %ANALYSTDESK_IMAGE%...
docker compose up -d --wait --wait-timeout 900
if errorlevel 1 goto startup_failed

echo Checking Analyst Desk and monitoring services...
call :wait_for_url http://127.0.0.1:7861/readyz "Analyst Desk"
if errorlevel 1 goto startup_failed
call :wait_for_url http://127.0.0.1:7861/api/alerts "In-app alerts and Prometheus connection"
if errorlevel 1 goto outdated_image
call :wait_for_url http://127.0.0.1:9090/-/ready "Prometheus"
if errorlevel 1 goto startup_failed
call :wait_for_url http://127.0.0.1:3000/api/health "Grafana"
if errorlevel 1 goto startup_failed
call :wait_for_url http://127.0.0.1:16686/ "Jaeger"
if errorlevel 1 goto startup_failed

echo.
echo Analyst Desk and monitoring are ready:
echo   UI:        http://127.0.0.1:7861
echo   Prometheus:http://127.0.0.1:9090
echo   Grafana:   http://127.0.0.1:3000
echo   Jaeger:    http://127.0.0.1:16686
start "" "http://127.0.0.1:7861"
exit /b 0

:missing_env
echo .env was not found. Copy .env.example to .env, add your OPENROUTER_API_KEY, then retry.
exit /b 1

:missing_git
echo Git is required to check the latest main commit. Install Git, then retry.
exit /b 1

:invalid_usage
echo Usage: start.bat [commit-sha]
exit /b 1

:invalid_version
echo Could not resolve "%~1" to a commit in this checkout.
echo Fetch the commit first, or run start.bat without an argument for the latest main image.
exit /b 1

:git_fetch_failed
echo Could not fetch origin/main or determine its commit. Check the Git remote and network, then retry.
exit /b 1

:image_unavailable
echo The image for commit %MAIN_SHA% was not available after 2 attempts.
echo Check that the commit has a published image, then run start.bat again.
exit /b 1

:outdated_image
echo The shared image does not include the current Analyst Desk alert API yet.
echo This change becomes available after it is merged to main and the image is published.
echo Check the team image workflow, then run start.bat again.
docker compose ps
exit /b 1

:startup_failed
echo Startup or a health check failed. Current service status:
docker compose ps
echo Review service logs with: docker compose logs
exit /b 1

:wait_for_url
set "CHECK_URL=%~1"
set "CHECK_NAME=%~2"
set /a ATTEMPTS=0
:wait_loop
curl.exe --fail --silent --show-error "%CHECK_URL%" >nul 2>nul
if not errorlevel 1 exit /b 0
set /a ATTEMPTS+=1
if %ATTEMPTS% GEQ 30 goto wait_failed
timeout /t 2 /nobreak >nul
goto wait_loop

:wait_failed
echo %CHECK_NAME% did not become ready at %CHECK_URL%.
exit /b 1
