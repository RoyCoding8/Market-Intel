#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
echo "Market Intelligence Agent v1"
echo ""

[ -f .env ] || { echo "Missing .env — copy .env.example to .env first"; exit 1; }

echo "1) Docker Compose"
echo "2) Direct Launch (no install)"
echo "3) Install deps + validate"
read -rp "Mode [2]: " mode
mode=${mode:-2}

if [ "$mode" = "1" ]; then
    docker compose up --build -d
    echo ""
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:8000"
    echo "  Logs:     docker compose logs -f"

elif [ "$mode" = "2" ]; then
    echo "Starting backend and frontend..."
    uv run python -m backend.main &
    BACKEND_PID=$!
    (cd frontend && npm run dev) &
    FRONTEND_PID=$!
    echo ""
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:8000"
    echo ""
    echo "Press Ctrl+C to stop..."
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
    wait

elif [ "$mode" = "3" ]; then
    echo "Installing dependencies..."
    uv sync --extra dev
    (cd frontend && npm ci)
    echo ""
    echo "Running lint..."
    uv run python -m ruff check engine/ backend/ contracts/
    echo ""
    echo "Running tests..."
    uv run python -m pytest engine/tests/ backend/tests/ integration/ -q
    (cd frontend && npx vitest run)

else
    echo "Invalid choice"; exit 1
fi
