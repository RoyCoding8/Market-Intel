# Security Model

## SSRF Protection

The system has multi-layered SSRF (Server-Side Request Forgery) defense:

### Layer 1: URL Validation at Job Creation (`contracts/api.py`)

When a user submits a `CreateJobRequest`, each competitor URL goes through:

1. **Scheme enforcement** — Only `http://` and `https://` allowed
2. **Hostname validation** — Must be a valid domain or IP literal
3. **Localhost blocking** — `localhost`, `127.0.0.1`, `::1` rejected
4. **Private IP blocking** — RFC 1918 ranges, link-local, reserved IPs rejected
5. **Cloud metadata blocking** — `169.254.169.254`, `metadata.google.internal` rejected
6. **Octal/hex bypass detection** — Non-canonical IP representations like `0177.0.0.1` rejected
7. **DNS resolution check** — Hostname resolved via `socket.getaddrinfo()`, all resolved IPs checked against blocked ranges
8. **Wildcard DNS blocking** — Services like `nip.io` and `sslip.io` caught by IP resolution check

### Layer 2: DNS Re-validation at Fetch Time (`engine/agents/scraper.py`)

Before making the actual HTTP request, the scraper:
1. Re-resolves DNS for the target hostname
2. Checks all resolved IPs against blocked ranges
3. Rejects the request if any IP is in a blocked range

This closes the TOCTOU (Time-of-Check-Time-of-Use) window where DNS could change between validation and fetching.

### Layer 3: Redirect Validation (`engine/agents/scraper.py`)

After each HTTP redirect:
1. The final URL is extracted from the response
2. The same URL validation (from Layer 1) is applied to the redirect target
3. If the redirect target is blocked, the request is aborted

### Layer 4: Content-Type Enforcement

Non-HTML responses (images, JSON, binary) are rejected early to prevent downloading large files or triggering unintended behavior.

### Layer 5: Response Size Limits

- `MAX_BODY_BYTES = 5 MB` — Streaming download aborts if exceeded
- `MAX_PAGE_CONTENT_CHARS = 100,000` — Text truncated before analysis

## Rate Limiting

IP-based sliding-window rate limiter (`backend/middleware/rate_limit.py`):

| Endpoint | Default Limit | Window |
|----------|--------------|--------|
| General API | 100 requests | 60 seconds |
| Job creation (`POST /api/jobs`) | 10 requests | 60 seconds |
| Health check | Unlimited | — |

**Proxy support:** When `TRUSTED_PROXIES` environment variable is set (comma-separated IPs), the middleware trusts `X-Forwarded-For` headers from those IPs for real client identification.

## Input Sanitization

### Competitor Names
- HTML tags stripped via regex
- Control characters removed
- Empty names normalized to `None`

### Job IDs
- Generated as `uuid.uuid4().hex` (32 hex characters)
- Sanitized for file paths in export: only alphanumeric + `-` and `_` allowed

### SQL Injection Prevention
- All database queries use parameterized statements
- `update_job()` and `update_schedule()` use allowlisted column sets — unknown columns silently ignored
- No dynamic table or column names in queries

## Export Security

### PDF Export (`backend/services/export.py`)
- `job_id` sanitized to prevent path traversal: only `[a-zA-Z0-9_-]` allowed, max 64 chars
- Export directory created with `os.makedirs(exist_ok=True)`
- Static file serving via FastAPI's `StaticFiles` (no directory traversal)

### Download URLs
- Frontend validates download URLs: must start with `/` and not `//` (prevents open redirect)
- Only relative paths opened; absolute URLs rejected

## CORS

Configured via `CORS_ORIGINS` environment variable:
- Default: `http://localhost:3000,http://localhost:3001`
- Wildcard `*` is explicitly rejected with a warning
- Credentials allowed for authenticated requests
- Methods: `GET, POST, DELETE, PATCH, OPTIONS`

## Error Sanitization

Pipeline errors are sanitized before reaching API consumers:
```python
error_msg = f"Pipeline failed: {type(exc).__name__}"
```
Internal stack traces and exception messages are logged but never exposed to the frontend.

## Authentication (Optional)

Not enabled by default. When `AUTH_ENABLED=true`:
- JWT-based authentication
- `AUTH_SECRET_KEY` for token signing
- `AUTH_TOKEN_EXPIRY_HOURS` for token lifetime
