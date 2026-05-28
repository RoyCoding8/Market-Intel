# Deployment Guide

## Quick Start (Docker Compose)

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your API keys

# 2. Start services
docker compose up -d --build

# 3. Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Health check: http://localhost:8000/api/health
```

## Architecture

```
┌──────────────┐     ┌──────────────┐
│   Frontend   │────►│   Backend    │
│  (Next.js)   │     │  (FastAPI)   │
│  Port 3000   │     │  Port 8000   │
└──────────────┘     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │    SQLite    │
                     │  (volume)    │
                     └──────────────┘
```

## Docker

### Backend (`Dockerfile.backend`)
- Multi-stage build (builder + runtime)
- Python 3.11-slim base
- Non-root user (`appuser`)
- Health check via `urllib.request`
- Uses `uv export` for dependency installation

### Frontend (`Dockerfile.frontend`)
- Multi-stage build (builder + runner)
- Node 20-slim base
- Next.js standalone output
- Non-root user (`nextjs`)
- Health check via `fetch()`

## Render.com

`render.yaml` configures both services:

### Backend
- Runtime: Python
- Build: `pip install uv && uv sync --frozen`
- Start: `uvicorn backend.main:create_app --factory --host 0.0.0.0 --port $PORT`
- Disk: 1GB persistent storage for SQLite
- Health check: `/api/health`

### Frontend
- Runtime: Node
- Root directory: `frontend`
- Build: `npm ci && npm run build`
- Start: `npm start`
- Env: `NEXT_PUBLIC_API_URL=https://market-intel-backend.onrender.com`

## Environment Variables

### Required
| Variable | Description |
|----------|-------------|
| `LLM_MODEL` | Model identifier (e.g., `openai/gpt-4o`) |
| `OPENAI_API_KEY` | API key for the selected provider |

### Optional — Engine
| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_PAGES_PER_COMPETITOR` | `20` | Max pages to scrape per competitor |
| `VERIFICATION_PASSES` | `2` | Multi-pass verification count |
| `REQUEST_DELAY_SECONDS` | `1.0` | Delay between scrape requests |
| `LLM_TIMEOUT_SECONDS` | `60` | Per-LLM-call timeout |
| `MAX_CONCURRENT_JOBS` | `5` | Max parallel analysis jobs |
| `MAX_COMPETITORS_PER_JOB` | `10` | Max competitors per job |

### Optional — Bright Data
| Variable | Description |
|----------|-------------|
| `BRIGHT_DATA_CUSTOMER_ID` | Bright Data customer ID |
| `BRIGHT_DATA_ZONE` | Web Unlocker zone name |
| `BRIGHT_DATA_PASSWORD` | Zone password |
| `BRIGHT_DATA_COUNTRY` | Country code for geo-targeting |
| `BRIGHT_DATA_DEBUG` | Enable debug headers (`true`/`false`) |

### Optional — Backend
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/market_intel.db` | Database connection string |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `TRUSTED_PROXIES` | (empty) | Comma-separated proxy IPs for X-Forwarded-For trust |
| `LOG_LEVEL` | `INFO` | Logging level |

## Local Development

```bash
# Install dependencies
make install

# Start backend (with auto-reload)
make dev-backend

# Start frontend (with auto-reload)
make dev-frontend

# Run tests
make test

# Run linters
make lint
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):

1. **backend-tests** — Python 3.11, runs backend + engine tests
2. **frontend-build** — Node 20, builds frontend
3. **integration-tests** — Runs after backend + frontend pass
4. **docker-build** — Builds both Docker images, verifies backend starts

## SQLite Considerations

- WAL mode enabled for concurrent reads
- 30-second busy timeout
- Data persisted to `/app/data/` in Docker (volume mount)
- For production with high concurrency, consider migrating to PostgreSQL

## Scaling

The current architecture is single-process:
- One FastAPI worker handles all requests
- Pipeline runs as background asyncio tasks
- SQLite limits concurrent writes

For higher scale:
1. Use Gunicorn with multiple Uvicorn workers
2. Migrate to PostgreSQL for concurrent write support
3. Use Redis for event pub/sub instead of in-memory EventStore
4. Add Celery for background task processing
