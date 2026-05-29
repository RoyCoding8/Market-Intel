#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
echo "Market Intelligence Agent v1"

[ -f .env ] || { echo "Missing .env — copy .env.example to .env first"; exit 1; }

echo "1) Docker Compose"
echo "2) Local (uv + Node)"
read -rp "Mode [1]: " mode
mode=${mode:-1}

if [ "$mode" = "1" ]; then
    docker compose up --build -d
    echo "Frontend: http://localhost:3000"
    echo "Backend:  http://localhost:8000"
    echo "Logs:     docker compose logs -f"
elif [ "$mode" = "2" ]; then
    uv sync --extra dev
    (cd frontend && npm ci)
    (cd backend && uv run python -m uvicorn main:create_app --factory --host 0.0.0.0 --port 8000) &
    (cd frontend && npm run dev) &
    echo "Frontend: http://localhost:3000"
    echo "Backend:  http://localhost:8000"
    trap "kill 0; exit 0" INT TERM
    wait
else
    echo "Invalid choice"; exit 1
fi
