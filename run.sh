#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERR]${NC}   $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BOLD}${CYAN}"
echo "  ┌─────────────────────────────────────────────┐"
echo "  │     Market Intelligence Agent — Launcher     │"
echo "  └─────────────────────────────────────────────┘"
echo -e "${NC}"

# ── Check .env ──────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    err ".env file not found."
    echo "  cp .env.example .env && nano .env"
    exit 1
fi
ok ".env found"

# ── Check uv ────────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    err "uv not found. Install it:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
ok "uv found: $(uv --version)"

# ── Choose mode ─────────────────────────────────────────────────────────────
HAS_DOCKER=false
HAS_NODE=false
command -v docker &>/dev/null && HAS_DOCKER=true
command -v node   &>/dev/null && HAS_NODE=true

echo ""
echo "  1) Docker Compose"
if $HAS_NODE; then
    echo "  2) Local (uv + Node)"
fi
echo ""
echo -n "  Mode [1]: "
read -r mode
mode="${mode:-1}"

case "$mode" in
    1)
        if ! $HAS_DOCKER; then
            err "Docker not found."
            exit 1
        fi
        info "Starting with Docker Compose..."
        docker compose up --build -d
        echo ""
        ok "Running!"
        echo -e "  ${BOLD}Frontend:${NC} http://localhost:3000"
        echo -e "  ${BOLD}Backend:${NC}  http://localhost:8000"
        echo ""
        info "Logs: docker compose logs -f"
        info "Stop: docker compose down"
        ;;
    2)
        if ! $HAS_NODE; then
            err "Node.js not found."
            exit 1
        fi
        info "Installing Python dependencies with uv..."
        uv sync
        info "Installing frontend dependencies..."
        (cd frontend && npm ci --silent)

        echo ""
        info "Starting backend..."
        (cd backend && uv run python -m uvicorn main:create_app --factory --host 0.0.0.0 --port 8000) &
        info "Starting frontend..."
        (cd frontend && npm run dev) &

        echo ""
        ok "Running!"
        echo -e "  ${BOLD}Frontend:${NC} http://localhost:3000"
        echo -e "  ${BOLD}Backend:${NC}  http://localhost:8000"
        echo ""
        info "Ctrl+C to stop"
        trap "kill 0; exit 0" INT TERM
        wait
        ;;
    *)
        err "Invalid choice"
        exit 1
        ;;
esac
