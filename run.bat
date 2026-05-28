@echo off
setlocal enabledelayedexpansion

set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "CYAN=[96m"
set "BOLD=[1m"
set "NC=[0m"

cd /d "%~dp0"

echo.
echo %CYAN%%BOLD%  =============================================%NC%
echo %CYAN%%BOLD%     Market Intelligence Agent — Launcher      %NC%
echo %CYAN%%BOLD%  =============================================%NC%
echo.

:: ── Check .env ────────────────────────────────────────────────────────────
if not exist .env (
    echo %RED%[ERR]%NC%   .env file not found.
    echo   copy .env.example .env ^&^& notepad .env
    echo.
    pause
    exit /b 1
)
echo %GREEN%[OK]%NC%    .env found

:: ── Check uv ──────────────────────────────────────────────────────────────
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo %RED%[ERR]%NC%   uv not found. Install it:
    echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    pause
    exit /b 1
)
echo %GREEN%[OK]%NC%    uv found
echo.

:: ── Choose mode ───────────────────────────────────────────────────────────
echo   1) Docker Compose
echo   2) Local (uv + Node)
echo.
set /p "MODE=  Mode [1]: "
if "!MODE!"=="" set "MODE=1"

if "!MODE!"=="1" (
    echo.
    echo %BLUE%[INFO]%NC%  Starting with Docker Compose...
    docker compose up --build -d
    echo.
    echo %GREEN%[OK]%NC%    Running!
    echo   %BOLD%Frontend:%NC% http://localhost:3000
    echo   %BOLD%Backend:%NC%  http://localhost:8000
    echo.
    echo %BLUE%[INFO]%NC%  Logs: docker compose logs -f
    echo %BLUE%[INFO]%NC%  Stop: docker compose down
)

if "!MODE!"=="2" (
    echo.
    echo %BLUE%[INFO]%NC%  Installing Python dependencies with uv...
    uv sync
    echo %BLUE%[INFO]%NC%  Installing frontend dependencies...
    cd frontend && npm ci --silent && cd ..
    echo.
    echo %BLUE%[INFO]%NC%  Starting backend...
    start "Backend" cmd /c "cd backend && uv run python -m uvicorn main:create_app --factory --host 0.0.0.0 --port 8000"
    echo %BLUE%[INFO]%NC%  Starting frontend...
    start "Frontend" cmd /c "cd frontend && npm run dev"
    echo.
    echo %GREEN%[OK]%NC%    Running!
    echo   %BOLD%Frontend:%NC% http://localhost:3000
    echo   %BOLD%Backend:%NC%  http://localhost:8000
    echo.
    echo %BLUE%[INFO]%NC%  Close the Backend/Frontend windows to stop.
)

echo.
pause
