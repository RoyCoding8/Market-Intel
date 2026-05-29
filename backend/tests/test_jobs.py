"""Tests for job CRUD endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.routes.jobs import _configured_pipeline_kwargs


VALID_PAYLOAD = {
    "competitors": [
        {"url": "https://example.com", "name": "ExampleCorp", "focus_areas": ["pricing"]},
        {"url": "https://other.io", "name": "OtherIO"},
    ],
    "query": "pricing changes",
}


def test_pipeline_kwargs_read_environment(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "openai/mimo-v2.5-pro")
    monkeypatch.setenv("MAX_PAGES_PER_COMPETITOR", "7")
    monkeypatch.setenv("VERIFICATION_PASSES", "4")

    assert _configured_pipeline_kwargs() == {
        "llm_model": "openai/mimo-v2.5-pro",
        "max_pages_per_competitor": 7,
        "verification_passes": 4,
    }


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient):
    resp = await client.post("/api/jobs", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert "job_id" in body
    assert body["status"] == "pending"
    assert body["message"]


@pytest.mark.asyncio
async def test_create_job_requires_competitors(client: AsyncClient):
    resp = await client.post("/api/jobs", json={"competitors": []})
    assert resp.status_code == 422  # validation error


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient):
    # Create a couple of jobs
    await client.post("/api/jobs", json=VALID_PAYLOAD)
    await client.post("/api/jobs", json=VALID_PAYLOAD)

    resp = await client.get("/api/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert len(body["jobs"]) >= 2


@pytest.mark.asyncio
async def test_get_job(client: AsyncClient):
    create_resp = await client.post("/api/jobs", json=VALID_PAYLOAD)
    job_id = create_resp.json()["job_id"]

    resp = await client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job_id


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient):
    resp = await client.get("/api/jobs/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_not_completed(client: AsyncClient):
    create_resp = await client.post("/api/jobs", json=VALID_PAYLOAD)
    job_id = create_resp.json()["job_id"]

    resp = await client.get(f"/api/jobs/{job_id}/report")
    # Job is pending/running, not completed
    assert resp.status_code in (400, 404)


@pytest.mark.asyncio
async def test_get_report_nonexistent_job(client: AsyncClient):
    resp = await client.get("/api/jobs/nonexistent-id/report")
    assert resp.status_code == 404
