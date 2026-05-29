.PHONY: install test build dev docker-up docker-down lint clean help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install Python dependencies with uv
	uv sync --extra dev

install-frontend: ## Install frontend dependencies
	cd frontend && npm ci

test: test-backend test-engine ## Run all tests

test-backend: ## Run backend tests
	uv run --extra dev python -m pytest backend/tests/ -v --tb=short

test-engine: ## Run engine tests
	uv run --extra dev python -m pytest engine/tests/ -v --tb=short

test-integration: ## Run integration tests
	@if [ -d "integration" ]; then \
		uv run --extra dev python -m pytest integration/test_adversarial.py -v --tb=short; \
	else \
		echo "No integration tests found"; \
	fi

build: build-frontend ## Build all artifacts

build-frontend: ## Build frontend
	cd frontend && npm run build

dev: dev-backend dev-frontend ## Start dev servers (background)

dev-backend: ## Start backend dev server
	cd backend && uv run uvicorn main:create_app --factory --reload --host 0.0.0.0 --port 8000 &

dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev &

docker-up: ## Start with docker-compose
	docker compose up -d --build

docker-down: ## Stop docker-compose
	docker compose down

docker-logs: ## View docker-compose logs
	docker compose logs -f

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Run Python linters
	@if command -v ruff > /dev/null 2>&1; then \
		ruff check backend/ engine/; \
	else \
		echo "ruff not installed, skipping Python lint"; \
	fi

lint-frontend: ## Run frontend linter
	cd frontend && npm run lint 2>/dev/null || echo "No lint script configured"

clean: ## Clean caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/.next 2>/dev/null || true
	rm -rf frontend/node_modules/.cache 2>/dev/null || true
	rm -rf .venv 2>/dev/null || true
