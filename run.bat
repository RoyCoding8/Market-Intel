@echo off
cd /d "%~dp0"
cls
echo Market Intelligence Agent v1
echo.

if not exist .env (
    echo Missing .env — copy .env.example to .env first
    pause
    exit /b 1
)

echo 1^) Docker Compose
echo 2^) Direct Launch (no install)
echo 3^) Install deps + validate
set /p MODE=Mode [2]: 
if "%MODE%"=="" set MODE=2

if "%MODE%"=="1" (
    docker compose up --build -d
    echo.
    echo   Frontend: http://localhost:3000
    echo   Backend:  http://localhost:8000
    echo   Logs:     docker compose logs -f
) else if "%MODE%"=="2" (
    echo Starting backend and frontend...
    start "Backend" cmd /c "uv run python -m backend.main"
    start "Frontend" cmd /c "cd frontend && npm run dev"
    echo.
    echo   Frontend: http://localhost:3000
    echo   Backend:  http://localhost:8000
    echo.
    echo Press any key to stop...
    pause >nul
    taskkill /FI "WINDOWTITLE eq Backend" >nul 2>&1
    taskkill /FI "WINDOWTITLE eq Frontend" >nul 2>&1
    exit /b 0
) else if "%MODE%"=="3" (
    echo Installing dependencies...
    call uv sync --extra dev
    cd frontend && call npm ci && cd ..
    echo.
    echo Running lint...
    call uv run python -m ruff check engine/ backend/ contracts/
    echo.
    echo Running tests...
    call uv run python -m pytest engine/tests/ backend/tests/ integration/ -q
    cd frontend && call npx vitest run && cd ..
) else (
    echo Invalid choice
)

pause
