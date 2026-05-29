@echo off
cd /d "%~dp0"
cls
echo Market Intelligence Agent v1

if not exist .env (
    echo Missing .env — copy .env.example to .env first
    pause
    exit /b 1
)

echo 1^) Docker Compose
echo 2^) Local (uv + Node)
set /p MODE=Mode [1]: 
if "%MODE%"=="" set MODE=1

if "%MODE%"=="1" (
    docker compose up --build -d
    echo Frontend: http://localhost:3000
    echo Backend:  http://localhost:8000
    echo Logs:     docker compose logs -f
) else if "%MODE%"=="2" (
    uv sync --extra dev
    cd frontend && npm ci && cd ..
    start "Backend" cmd /c "cd backend && uv run python -m uvicorn main:create_app --factory --host 0.0.0.0 --port 8000"
    start "Frontend" cmd /c "cd frontend && npm run dev"
    echo Frontend: http://localhost:3000
    echo Backend:  http://localhost:8000
) else (
    echo Invalid choice
)

pause
