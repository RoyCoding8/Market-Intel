"""Optional API-key authentication middleware.

When ``API_KEY`` is set in the environment, every request (except health
checks and CORS preflight) must include a matching key via:
  - ``X-API-Key`` header, **or**
  - ``?api_key=`` query parameter.

When ``API_KEY`` is *not* set the middleware is a no-op — the app runs in
open-access mode, which is the default for local development and demos.
"""

from __future__ import annotations

import hmac
import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Paths that never require authentication.
_PUBLIC_PATHS = frozenset({"/api/health", "/docs", "/openapi.json", "/redoc"})

class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests that lack a valid API key (when one is configured)."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._api_key: str | None = os.getenv("API_KEY") or None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self._api_key is None:
            return await call_next(request)

        if request.url.path in _PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        supplied = (
            request.headers.get("x-api-key")
            or request.query_params.get("api_key")
        )

        if not supplied or not hmac.compare_digest(supplied, self._api_key):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "detail": "Missing or invalid API key. Set X-API-Key header or ?api_key= query parameter.",
                    "status_code": 401,
                },
            )

        return await call_next(request)
