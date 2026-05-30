"""Adversarial QA tests for the Market Intelligence Agent.

Tests edge cases, failure modes, input validation, and security concerns.
These tests verify the system's behavior under adversarial conditions —
they do NOT modify implementation code.

Run with: pytest integration/test_adversarial.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure project root is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.main import create_app  # noqa: E402

# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture
async def app(tmp_path, monkeypatch):
    """Fresh FastAPI app for each test."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    application = create_app(rate_limit_general=10000, rate_limit_job_creation=10000)
    async with application.router.lifespan_context(application):
        yield application

@pytest_asyncio.fixture
async def client(app) -> AsyncClient:
    """Async HTTP client bound to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# ── 1. Empty / Missing Input ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_empty_competitors_list(client: AsyncClient):
    """POST /api/jobs with empty competitors list should be rejected."""
    resp = await client.post("/api/jobs", json={"competitors": []})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

@pytest.mark.asyncio
async def test_post_missing_competitors_field(client: AsyncClient):
    """POST /api/jobs without competitors field should be rejected."""
    resp = await client.post("/api/jobs", json={"query": "pricing"})
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_post_empty_body(client: AsyncClient):
    """POST /api/jobs with empty JSON body should be rejected."""
    resp = await client.post("/api/jobs", json={})
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_post_competitor_missing_url(client: AsyncClient):
    """POST /api/jobs with competitor missing url should be rejected."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"name": "NoURL"}]},
    )
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_get_nonexistent_job(client: AsyncClient):
    """GET /api/jobs/nonexistent-id should return 404."""
    resp = await client.get("/api/jobs/nonexistent-id")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_get_report_nonexistent_job(client: AsyncClient):
    """GET /api/jobs/nonexistent-id/report should return 404."""
    resp = await client.get("/api/jobs/nonexistent-id/report")
    assert resp.status_code == 404

# ── 2. Malformed Data ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_malformed_json(client: AsyncClient):
    """POST /api/jobs with malformed JSON body should be rejected."""
    resp = await client.post(
        "/api/jobs",
        content=b"{{{not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_post_wrong_type_competitors(client: AsyncClient):
    """POST /api/jobs with competitors as a string instead of list."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": "not-a-list"},
    )
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_post_wrong_type_url(client: AsyncClient):
    """POST /api/jobs with url as integer instead of string."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": 12345}]},
    )
    # Pydantic may coerce int to str, so this might pass validation
    # The key test is that it doesn't crash
    assert resp.status_code in (201, 422)

@pytest.mark.asyncio
async def test_post_very_long_url(client: AsyncClient):
    """POST /api/jobs with a very long URL (>2KB) — should be rejected
    (max_length=2048 on url field)."""
    long_url = "https://example.com/" + "A" * 3000
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": long_url}]},
    )
    assert resp.status_code == 422, f"Expected 422 (URL too long), got {resp.status_code}"

@pytest.mark.asyncio
async def test_post_special_characters_in_url(client: AsyncClient):
    """POST /api/jobs with special characters in URL — scheme validation."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "https://example.com/path?q=<script>alert(1)</script>"}]},
    )
    # Valid https URL with query params — should be accepted
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_post_unicode_in_name(client: AsyncClient):
    """POST /api/jobs with Unicode characters in competitor name."""
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [
                {"url": "https://example.com", "name": "\u202edlrow olleH\u202c"}
            ]
        },
    )
    # Unicode allowed, RTL override chars kept (not HTML) — accepted
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_post_xss_in_name(client: AsyncClient):
    """POST /api/jobs with script tags in competitor name — tags should be stripped."""
    xss_name = "<script>alert(document.cookie)</script>"
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [{"url": "https://example.com", "name": xss_name}]
        },
    )
    assert resp.status_code == 201
    # Server strips HTML tags — name should be empty after stripping, name falls back to None
    job_id = resp.json()["job_id"]
    job_resp = await client.get(f"/api/jobs/{job_id}")
    assert job_resp.status_code == 200

@pytest.mark.asyncio
async def test_post_null_bytes_in_name(client: AsyncClient):
    """POST /api/jobs with null bytes in competitor name — should be stripped."""
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [
                {"url": "https://example.com", "name": "test\x00malicious"}
            ]
        },
    )
    # Null bytes are stripped by validator — should accept with sanitized name
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_post_extremely_long_name(client: AsyncClient):
    """POST /api/jobs with a very long competitor name — should be rejected (max_length=200)."""
    long_name = "A" * 300
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [{"url": "https://example.com", "name": long_name}]
        },
    )
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_post_11_competitors_over_limit(client: AsyncClient):
    """POST /api/jobs with 11 competitors should be rejected (max_length=10)."""
    competitors = [{"url": f"https://example{i}.com"} for i in range(11)]
    resp = await client.post("/api/jobs", json={"competitors": competitors})
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_post_exactly_10_competitors(client: AsyncClient):
    """POST /api/jobs with exactly 10 competitors should be accepted."""
    competitors = [{"url": f"https://example{i}.com"} for i in range(10)]
    resp = await client.post("/api/jobs", json={"competitors": competitors})
    assert resp.status_code == 201

# ── 3. SSRF / Security ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ssrf_localhost_url(client: AsyncClient):
    """POST /api/jobs with http://localhost URL — SSRF protection blocks it."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "http://127.0.0.1:8000/api/jobs"}]},
    )
    assert resp.status_code == 422, "SSRF protection should block localhost"

@pytest.mark.asyncio
async def test_ssrf_aws_metadata_url(client: AsyncClient):
    """POST /api/jobs with AWS metadata URL — SSRF protection blocks it."""
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [
                {"url": "http://169.254.169.254/latest/meta-data/"}
            ]
        },
    )
    assert resp.status_code == 422, "SSRF protection should block metadata endpoint"

@pytest.mark.asyncio
async def test_ssrf_ipv6_loopback(client: AsyncClient):
    """POST /api/jobs with IPv6 loopback URL — SSRF protection blocks it."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "http://[::1]:8000/"}]},
    )
    assert resp.status_code == 422, "SSRF protection should block IPv6 loopback"

@pytest.mark.asyncio
async def test_ssrf_private_ip_range(client: AsyncClient):
    """POST /api/jobs with private IP ranges — SSRF protection blocks them."""
    for ip in ["10.0.0.1", "172.16.0.1", "192.168.1.1"]:
        resp = await client.post(
            "/api/jobs",
            json={"competitors": [{"url": f"http://{ip}/"}]},
        )
        assert resp.status_code == 422, f"SSRF protection should block {ip}"

@pytest.mark.asyncio
async def test_ssrf_file_scheme(client: AsyncClient):
    """POST /api/jobs with file:// URL — rejected (scheme validation)."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "file:///etc/passwd"}]},
    )
    assert resp.status_code == 422, "Should reject file:// scheme"

@pytest.mark.asyncio
async def test_ssrf_javascript_scheme(client: AsyncClient):
    """POST /api/jobs with javascript: URL — rejected (scheme validation)."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "javascript:alert(1)"}]},
    )
    assert resp.status_code == 422, "Should reject javascript: scheme"

@pytest.mark.asyncio
async def test_ssrf_ftp_scheme(client: AsyncClient):
    """POST /api/jobs with ftp:// URL — rejected (scheme validation)."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "ftp://internal-server/files/"}]},
    )
    assert resp.status_code == 422, "Should reject ftp:// scheme"

@pytest.mark.asyncio
async def test_ssrf_not_a_url(client: AsyncClient):
    """POST /api/jobs with completely invalid URL string — rejected."""
    for bad_url in ["not-a-url", "", "   ", "hello world", "://missing-scheme"]:
        resp = await client.post(
            "/api/jobs",
            json={"competitors": [{"url": bad_url}]},
        )
        assert resp.status_code == 422, f"Should reject bad URL: {bad_url!r}"

# ── 4. Job Lifecycle ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_job_status_transitions(client: AsyncClient):
    """Verify job starts as pending and transitions through states."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "https://httpbin.org/status/404"}]},
    )
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]
    assert resp.json()["status"] == "pending"

    # Immediately check — should be pending or scraping
    status_resp = await client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in ("pending", "scraping", "failed")

@pytest.mark.asyncio
async def test_report_before_completion(client: AsyncClient):
    """GET /api/jobs/{id}/report before job completes should fail."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "https://example.com"}]},
    )
    job_id = resp.json()["job_id"]

    # Immediately try to get report — job won't be completed yet
    report_resp = await client.get(f"/api/jobs/{job_id}/report")
    assert report_resp.status_code in (400, 404)

@pytest.mark.asyncio
async def test_list_jobs_returns_created_jobs(client: AsyncClient):
    """Verify list endpoint returns all created jobs."""
    # Create 3 jobs
    for i in range(3):
        await client.post(
            "/api/jobs",
            json={"competitors": [{"url": f"https://example{i}.com"}]},
        )

    resp = await client.get("/api/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["jobs"]) >= 3

@pytest.mark.asyncio
async def test_multiple_simultaneous_jobs(client: AsyncClient):
    """Create multiple jobs simultaneously — no concurrent job limit exists.

    FINDING [MEDIUM]: No limit on concurrent running jobs.
    """
    import asyncio

    async def create_job(i: int):
        return await client.post(
            "/api/jobs",
            json={"competitors": [{"url": f"https://example{i}.com"}]},
        )

    responses = await asyncio.gather(*[create_job(i) for i in range(20)])
    for resp in responses:
        assert resp.status_code == 201

# ── 5. SSE Edge Cases ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sse_nonexistent_job(client: AsyncClient):
    """GET /api/jobs/nonexistent/stream — returns 404 for nonexistent jobs.

    The SSE endpoint checks for job existence before subscribing.
    """
    resp = await client.get("/api/jobs/nonexistent-id/stream")
    assert resp.status_code == 404

# ── 6. Edge Cases in Pydantic Validation ────────────────────────────────

@pytest.mark.asyncio
async def test_query_field_null(client: AsyncClient):
    """POST /api/jobs with query=null should succeed (optional field)."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "https://example.com"}], "query": None},
    )
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_focus_areas_empty_list(client: AsyncClient):
    """POST /api/jobs with empty focus_areas — should use defaults."""
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [{"url": "https://example.com", "focus_areas": []}]
        },
    )
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_focus_areas_invalid_values(client: AsyncClient):
    """POST /api/jobs with non-standard focus areas — should be accepted."""
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [
                {
                    "url": "https://example.com",
                    "focus_areas": ["hacking", "exploits", "malware"],
                }
            ]
        },
    )
    # No validation on focus area values — accepted
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_nested_competitor_fields(client: AsyncClient):
    """POST /api/jobs with extra unknown fields in competitor — should be ignored or rejected."""
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [
                {
                    "url": "https://example.com",
                    "name": "Test",
                    "unknown_field": "should_be_ignored",
                    "another": 123,
                }
            ]
        },
    )
    # Pydantic with default config may reject or ignore extra fields
    assert resp.status_code in (201, 422)

@pytest.mark.asyncio
async def test_schedule_custom_without_cron(client: AsyncClient):
    """POST /api/jobs with schedule CUSTOM but no cron_expression."""
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [{"url": "https://example.com"}],
            "schedule": {"frequency": "custom"},
        },
    )
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_schedule_invalid_frequency(client: AsyncClient):
    """POST /api/jobs with invalid schedule frequency."""
    resp = await client.post(
        "/api/jobs",
        json={
            "competitors": [{"url": "https://example.com"}],
            "schedule": {"frequency": "every-5-minutes"},
        },
    )
    assert resp.status_code == 422

# ── 7. Job ID Edge Cases ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_job_with_path_traversal_chars(client: AsyncClient):
    """GET /api/jobs with path traversal characters in job_id."""
    resp = await client.get("/api/jobs/..%2F..%2Fetc%2Fpasswd")
    # Should return 404 (job doesn't exist)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_get_job_with_very_long_id(client: AsyncClient):
    """GET /api/jobs with a very long job ID."""
    long_id = "A" * 10000
    resp = await client.get(f"/api/jobs/{long_id}")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_get_job_with_special_characters(client: AsyncClient):
    """GET /api/jobs with special characters in job_id."""
    # Note: null bytes are rejected by httpx client before reaching the server,
    # and path traversal is URL-encoded by httpx. We test printable special chars.
    for special_id in ["test%00null", "test/../../../etc", "test<script>", "test;drop table"]:
        resp = await client.get(f"/api/jobs/{special_id}")
        # Should return 404, not crash
        assert resp.status_code in (404, 422), f"Unexpected status for job_id={special_id!r}: {resp.status_code}"

# ── 8. Response Format Validation ───────────────────────────────────────

@pytest.mark.asyncio
async def test_create_job_response_format(client: AsyncClient):
    """Verify create job response has all required fields."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "https://example.com"}]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "job_id" in body
    assert "status" in body
    assert "message" in body
    assert isinstance(body["job_id"], str)
    assert len(body["job_id"]) > 0

@pytest.mark.asyncio
async def test_job_status_response_format(client: AsyncClient):
    """Verify job status response has all required fields."""
    resp = await client.post(
        "/api/jobs",
        json={"competitors": [{"url": "https://example.com"}]},
    )
    job_id = resp.json()["job_id"]
    status_resp = await client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    body = status_resp.json()

    required_fields = [
        "job_id", "status", "progress", "current_step",
        "competitors_found", "pages_scraped", "findings_count",
    ]
    for field in required_fields:
        assert field in body, f"Missing field: {field}"

    assert 0.0 <= body["progress"] <= 1.0
    assert body["job_id"] == job_id

@pytest.mark.asyncio
async def test_list_jobs_response_format(client: AsyncClient):
    """Verify list jobs response has correct format."""
    resp = await client.get("/api/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert "jobs" in body
    assert "total" in body
    assert isinstance(body["jobs"], list)
    assert isinstance(body["total"], int)
    assert body["total"] == len(body["jobs"])

@pytest.mark.asyncio
async def test_error_response_format(client: AsyncClient):
    """Verify 404 error response format."""
    resp = await client.get("/api/jobs/nonexistent")
    assert resp.status_code == 404
    body = resp.json()
    assert "detail" in body

@pytest.mark.asyncio
async def test_validation_error_response_format(client: AsyncClient):
    """Verify 422 validation error response format."""
    resp = await client.post("/api/jobs", json={})
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body
