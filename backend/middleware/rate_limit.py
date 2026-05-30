"""IP-based sliding-window rate limiting middleware."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

def _trusted_proxies() -> set[str]:
    """Return set of trusted proxy IPs from TRUSTED_PROXIES env var (comma-separated)."""
    raw = os.getenv("TRUSTED_PROXIES", "")
    return {ip.strip() for ip in raw.split(",") if ip.strip()}

class _SlidingWindow:
    """Simple sliding-window counter for a single IP."""
    __slots__ = ("timestamps",)

    def __init__(self) -> None:
        self.timestamps: list[float] = []

    def prune(self, window: float) -> None:
        cutoff = time.monotonic() - window
        self.timestamps = [t for t in self.timestamps if t > cutoff]

    def count(self, window: float) -> int:
        self.prune(window)
        return len(self.timestamps)

    def record(self) -> None:
        self.timestamps.append(time.monotonic())

    def remaining(self, limit: int, window: float) -> int:
        return max(0, limit - self.count(window))

    def reset_seconds(self, window: float) -> float:
        if not self.timestamps:
            return 0.0
        return max(0.0, window - (time.monotonic() - self.timestamps[0]))

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter.

    Parameters
    ----------
    general_limit:
        Requests per minute allowed for non-job-creation endpoints.
    job_creation_limit:
        Requests per minute allowed for ``POST /api/jobs``.
    window:
        Window size in seconds (default 60 = 1 minute).
    """

    def __init__(
        self, app, general_limit: int = 100, job_creation_limit: int = 10, window: float = 60.0,
    ) -> None:
        super().__init__(app)
        self.general_limit = general_limit
        self.job_creation_limit = job_creation_limit
        self.window = window
        self._windows: dict[str, _SlidingWindow] = defaultdict(_SlidingWindow)
        self._trusted = _trusted_proxies()

    def _client_ip(self, request: Request) -> str:
        direct_ip = request.client.host if request.client else None
        if direct_ip and direct_ip in self._trusted:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",")[0].strip()
        if direct_ip:
            return direct_ip
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return "unknown"

    def _is_job_creation(self, request: Request) -> bool:
        return request.method == "POST" and request.url.path.rstrip("/") == "/api/jobs"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in ("/api/health", "/docs", "/openapi.json", "/redoc") or request.method == "OPTIONS":
            return await call_next(request)

        is_job = self._is_job_creation(request)
        ip = self._client_ip(request)
        key = f"{ip}:{'job' if is_job else 'gen'}"
        window = self._windows[key]
        limit = self.job_creation_limit if is_job else self.general_limit

        window.prune(self.window)
        current = len(window.timestamps)
        remaining = max(0, limit - current)

        if current >= limit:
            retry_after = int(window.reset_seconds(self.window)) + 1
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests", "detail": f"Rate limit exceeded. Try again in {retry_after}s.", "status_code": 429},
                headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": str(limit),
                         "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(retry_after)},
            )

        window.record()
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        response.headers["X-RateLimit-Reset"] = str(int(self.window))
        return response
