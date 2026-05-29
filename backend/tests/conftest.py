"""Shared test fixtures for the backend test suite."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure project root is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.main import create_app  # noqa: E402
from backend.services.event_store import EventStore  # noqa: E402
from backend.services.job_manager import JobManager  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def app(tmp_path, monkeypatch):
    """Fresh FastAPI app for each test."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    application = create_app()
    async with application.router.lifespan_context(application):
        yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    """Async HTTP client bound to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def job_manager() -> JobManager:
    return JobManager()


@pytest_asyncio.fixture
async def event_store() -> EventStore:
    return EventStore()
