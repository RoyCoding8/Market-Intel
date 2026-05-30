"""Request body size limiter.

Rejects any request whose ``Content-Length`` exceeds a configurable cap
**before** FastAPI/Pydantic attempt to parse the payload.  This prevents
a malicious client from consuming unbounded memory with a giant POST body.

Default limit: 1 MB  (``MAX_BODY_BYTES`` env var).
"""

from __future__ import annotations

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_DEFAULT_MAX_BYTES = 1_048_576  # 1 MB

class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Return *413 Payload Too Large* when ``Content-Length`` exceeds the cap."""

    def __init__(self, app, *, max_bytes: int | None = None) -> None:
        super().__init__(app)
        if max_bytes is not None:
            self._max = max_bytes
        else:
            try:
                self._max = int(os.getenv("MAX_BODY_BYTES", str(_DEFAULT_MAX_BYTES)))
            except (TypeError, ValueError):
                self._max = _DEFAULT_MAX_BYTES

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl is not None:
                try:
                    if int(cl) > self._max:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": "Payload Too Large",
                                "detail": f"Request body exceeds {self._max} byte limit.",
                                "status_code": 413,
                            },
                        )
                except (TypeError, ValueError):
                    pass  # Malformed header — let downstream handle it.

        return await call_next(request)
