"""Scraper agent — fetches and cleans competitor web pages (v2)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import random
import socket
import ssl
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional
from urllib.parse import quote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, SecretStr
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from contracts.engine import ScrapeRequest, ScrapeResult, ScrapedContent

logger = logging.getLogger(__name__)

MAX_PAGE_CONTENT_CHARS = 100_000
MAX_REDIRECTS = 5
BRIGHT_DATA_PROXY_HOST = "brd.superproxy.io"
BRIGHT_DATA_PROXY_PORT = 33335


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        logger.warning("Invalid float for %s; using %.2f", name, default)
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return _parse_bool(value, default)


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


REQUEST_DELAY_SECONDS = max(0.0, _env_float("REQUEST_DELAY_SECONDS", 1.0))


class BrightDataConfig(BaseModel):
    """Runtime configuration for Bright Data Web Unlocker proxy access."""

    customer_id: str = Field(min_length=1)
    zone: str = Field(min_length=1)
    password: SecretStr
    host: str = BRIGHT_DATA_PROXY_HOST
    port: int = BRIGHT_DATA_PROXY_PORT
    country: str | None = None
    debug: bool = True
    verify_ssl: bool | str = False

    @property
    def username(self) -> str:
        parts = [f"brd-customer-{self.customer_id}", f"zone-{self.zone}"]
        if self.country:
            parts.append(f"country-{self.country.lower()}")
        if self.debug:
            parts.append("debug-full")
        return "-".join(parts)

    @property
    def proxy_url(self) -> str:
        username = quote(self.username, safe="")
        password = quote(self.password.get_secret_value(), safe="")
        return f"http://{username}:{password}@{self.host}:{self.port}"


class FetchOutcome(BaseModel):
    """HTTP fetch output kept small and explicit for downstream parsing."""

    html: str
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)

_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; CrOS x86_64 15633.42.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

_PAGE_TYPE_PATTERNS: dict[str, list[str]] = {
    "pricing": ["/pricing", "/plans", "/price", "/subscribe", "/buy"],
    "about": ["/about", "/company", "/team", "/our-team", "/leadership", "/our-story"],
    "blog": ["/blog", "/news", "/articles", "/press", "/resources", "/insights"],
    "jobs": ["/jobs", "/careers", "/hiring", "/join", "/openings", "/positions"],
    "features": ["/features", "/product", "/platform", "/solutions", "/capabilities", "/services"],
    "contact": ["/contact", "/support", "/help", "/demo"],
    "docs": ["/docs", "/documentation", "/api", "/developers", "/reference"],
}

_CONTENT_KEYWORDS: dict[str, list[str]] = {
    "pricing": [
        "pricing", "per month", "per year", "/mo", "/yr", "free tier", "free plan",
        "enterprise", "starter plan", "pro plan", "business plan", "get started",
        "add to cart", "subscribe now", "billing", "annual pricing",
    ],
    "about": [
        "our mission", "founded in", "our team", "leadership", "who we are",
        "our story", "about us", "company overview", "headquarters",
    ],
    "blog": [
        "published on", "read more", "author:", "categories:", "latest posts",
        "blog post", "article", "comments", "share this",
    ],
    "jobs": [
        "open positions", "we're hiring", "join our team", "apply now",
        "job description", "requirements:", "benefits:", "remote friendly",
        "engineering team", "job opening",
    ],
    "features": [
        "key features", "how it works", "platform overview", "integrations",
        "use cases", "workflow", "automation", "dashboard", "analytics",
    ],
}


def _classify_url(url: str) -> str:
    """Classify a page by its URL path patterns."""
    path = urlparse(url).path.lower()
    for page_type, patterns in _PAGE_TYPE_PATTERNS.items():
        if any(pattern in path for pattern in patterns):
            return page_type
    return "unknown"


def _classify_content(text: str) -> str:
    """Classify page type by content keywords.

    Returns the page type with the highest keyword match count,
    or 'unknown' if no type has 2+ matches.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for page_type, keywords in _CONTENT_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[page_type] = count
    if not scores:
        return "unknown"
    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] >= 2 else "unknown"


def _combined_classify(url: str, content: str) -> str:
    """Classify using both URL patterns and content analysis.

    URL-based classification takes priority. Falls back to content-based.
    """
    url_type = _classify_url(url)
    return url_type if url_type != "unknown" else _classify_content(content)


def _content_quality_score(text: str, page_type: str) -> float:
    """Rate the usefulness of a page's content on a 0.0-1.0 scale."""
    if not text or len(text.strip()) < 20:
        return 0.0
    score = 0.0
    text_lower = text.lower()
    word_count = len(text.split())
    if word_count < 50:
        score += 0.1
    elif word_count < 200:
        score += 0.3
    elif word_count < 5000:
        score += 0.5
    else:
        score += 0.3
    if any(marker in text for marker in ["|", "\t"]):
        score += 0.05
    if text.count("\n") > 10:
        score += 0.05
    if page_type in _CONTENT_KEYWORDS:
        keywords = _CONTENT_KEYWORDS[page_type]
        keyword_hits = sum(1 for kw in keywords if kw in text_lower)
        keyword_density = keyword_hits / max(len(keywords), 1)
        score += min(keyword_density * 0.3, 0.3)
    boilerplate_markers = [
        "cookie policy", "privacy policy", "terms of service",
        "subscribe to our newsletter", "all rights reserved",
    ]
    boilerplate_count = sum(1 for m in boilerplate_markers if m in text_lower)
    if boilerplate_count >= 3:
        score -= 0.2
    return max(0.0, min(1.0, score))


def _content_hash(text: str) -> str:
    """Return a hash of the normalised content for deduplication."""
    normalised = " ".join(text.lower().split())
    return hashlib.sha256(normalised.encode()).hexdigest()[:16]


def _truncate_content(text: str) -> str:
    """Keep scraped page text within the analyzer's safe input budget."""
    if len(text) <= MAX_PAGE_CONTENT_CHARS:
        return text
    return text[:MAX_PAGE_CONTENT_CHARS] + "\n...[truncated]"


def _parse_page(html: str, base_url: str = "") -> tuple[str, Optional[str], dict[str, Optional[str]], list[str]]:
    """Single-pass HTML parse: returns (clean_text, title, metadata, links)."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    metadata: dict[str, Optional[str]] = {"description": None, "og_image": None, "canonical_url": None}
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag and desc_tag.get("content"):
        metadata["description"] = desc_tag["content"].strip()
    og_img_tag = soup.find("meta", attrs={"property": "og:image"})
    if og_img_tag and og_img_tag.get("content"):
        metadata["og_image"] = og_img_tag["content"].strip()
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    if canonical_tag and canonical_tag.get("href"):
        metadata["canonical_url"] = canonical_tag["href"].strip()
    links: list[str] = []
    if base_url:
        parsed_base = urlparse(base_url)
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            if parsed.netloc and parsed.netloc != parsed_base.netloc:
                continue
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean += f"?{parsed.query}"
            if clean not in seen:
                seen.add(clean)
                links.append(clean)
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return clean_text, title, metadata, links


def _clean_html(html: str) -> str:
    """Strip scripts, styles, and return clean visible text."""
    return _parse_page(html)[0]


def _extract_title(html: str) -> Optional[str]:
    """Extract the page <title>."""
    return _parse_page(html)[1]


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract and normalize all same-domain <a href> links."""
    return _parse_page(html, base_url)[3]


def _mk_page(
    url: str, title: Optional[str], text: str, page_type: str, *,
    links: list[str] | None = None, metadata: dict[str, Optional[str]] | None = None,
    quality: float = 0.0, c_hash: str | None = None, anti_bot: str | None = None,
) -> ScrapedContent:
    """Construct a ScrapedContent with consistent defaults."""
    return ScrapedContent(
        url=url, title=title, html_text=text, page_type=page_type,
        links_found=links or [], scraped_at=datetime.now(timezone.utc),
        metadata=metadata or {}, content_quality=quality,
        content_hash=c_hash or _content_hash(text), robots_respected=True,
        anti_bot_detected=anti_bot,
    )


def _prioritize_links(links: list[str], focus_areas: list[str], max_pages: int) -> list[str]:
    def _priority(url: str) -> int:
        pt = _classify_url(url)
        return 0 if pt in focus_areas else (2 if pt == "unknown" else 1)
    return sorted(links, key=_priority)[:max_pages]


def _detect_anti_bot(html: str, status_code: int, *, via_proxy: bool = False) -> Optional[str]:
    """Detect common anti-bot patterns. Returns description or None.

    When via_proxy=True (Bright Data Web Unlocker), detection is skipped
    entirely. The proxy has already handled anti-bot challenges — if it
    returned content, we trust it.
    """
    if via_proxy:
        return None

    html_lower = html.lower()
    cloudflare_markers = [
        "cf-browser-verification", "cloudflare", "checking your browser",
        "ray id", "cf-challenge", "just a moment",
    ]
    if sum(1 for m in cloudflare_markers if m in html_lower) >= 2:
        return "cloudflare_challenge"
    captcha_markers = [
        "captcha", "recaptcha", "hcaptcha", "are you human",
        "prove you are not a robot", "security check",
    ]
    if any(m in html_lower for m in captcha_markers):
        return "captcha"
    if status_code in (403, 429) and len(html) < 5000:
        return f"blocked_{status_code}"
    return None


def _get_bright_data_config(environ: Mapping[str, str] | None = None) -> BrightDataConfig | None:
    """Build Bright Data config from env, returning None for direct dev scraping."""
    env = os.environ if environ is None else environ
    customer_id = (env.get("BRIGHT_DATA_CUSTOMER_ID") or "").strip()
    zone = (env.get("BRIGHT_DATA_ZONE") or "").strip()
    password = (env.get("BRIGHT_DATA_PASSWORD") or "").strip()

    if not any((customer_id, zone, password)):
        return None
    if not all((customer_id, zone, password)):
        missing = [
            name for name, value in (
                ("BRIGHT_DATA_CUSTOMER_ID", customer_id),
                ("BRIGHT_DATA_ZONE", zone),
                ("BRIGHT_DATA_PASSWORD", password),
            )
            if not value
        ]
        logger.warning(
            "Bright Data configuration incomplete; falling back to direct scraping. missing=%s",
            ",".join(missing),
        )
        return None

    try:
        port = int(env.get("BRIGHT_DATA_PORT") or BRIGHT_DATA_PROXY_PORT)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid BRIGHT_DATA_PORT; using default %d",
            BRIGHT_DATA_PROXY_PORT,
        )
        port = BRIGHT_DATA_PROXY_PORT

    ca_cert = (env.get("BRIGHT_DATA_CA_CERT") or "").strip()
    verify_ssl: bool | str = ca_cert or _parse_bool(env.get("BRIGHT_DATA_VERIFY_SSL"), False)

    return BrightDataConfig(
        customer_id=customer_id,
        zone=zone,
        password=SecretStr(password),
        host=(env.get("BRIGHT_DATA_HOST") or BRIGHT_DATA_PROXY_HOST).strip(),
        port=port,
        country=(env.get("BRIGHT_DATA_COUNTRY") or "").strip() or None,
        debug=_parse_bool(env.get("BRIGHT_DATA_DEBUG"), True),
        verify_ssl=verify_ssl,
    )


def _bright_data_metadata(
    config: BrightDataConfig | None,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Optional[str]]:
    """Metadata persisted with each page and forwarded to SSE events."""
    if config is None:
        return {
            "scrape_provider": "direct_httpx",
            "bright_data_enabled": "false",
        }

    metadata: dict[str, Optional[str]] = {
        "scrape_provider": "bright_data_web_unlocker",
        "bright_data_enabled": "true",
        "bright_data_zone": config.zone,
        "bright_data_proxy_host": config.host,
        "bright_data_debug_enabled": "true" if config.debug else "false",
    }
    if config.country:
        metadata["bright_data_country"] = config.country.lower()

    headers = headers or {}
    debug_header = headers.get("x-brd-debug") or headers.get("X-BRD-Debug")
    if debug_header:
        metadata["bright_data_debug"] = debug_header[:1000]
    return metadata


def _client_kwargs(config: BrightDataConfig | None) -> dict:
    kwargs: dict = {"max_redirects": MAX_REDIRECTS}
    if config is not None:
        kwargs["proxy"] = config.proxy_url
        # httpx accepts bool or ssl.SSLContext for verify, not a string path.
        if isinstance(config.verify_ssl, str) and config.verify_ssl:
            try:
                ctx = ssl.create_default_context(cafile=config.verify_ssl)
                kwargs["verify"] = ctx
            except (FileNotFoundError, ssl.SSLError) as exc:
                raise ValueError(f"Invalid Bright Data CA cert path '{config.verify_ssl}': {exc}") from exc
        else:
            kwargs["verify"] = config.verify_ssl
    return kwargs


async def _check_robots_txt(client: httpx.AsyncClient, base_url: str) -> Optional[RobotFileParser]:
    """Fetch and parse robots.txt. Returns None if unavailable."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        resp = await client.get(robots_url, timeout=10.0)
        if resp.status_code == 200:
            rp = RobotFileParser()
            rp.parse(resp.text.splitlines())
            return rp
    except Exception as exc:
        logger.debug("robots.txt lookup failed for %s: %s", robots_url, exc)
    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    reraise=True,
)
async def _fetch_page(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0,
) -> FetchOutcome:
    """Fetch a single URL with retry logic. Streams body to enforce size limit."""
    MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MB
    headers = {"User-Agent": random.choice(_USER_AGENTS)}
    async with client.stream("GET", url, headers=headers, timeout=timeout, follow_redirects=True) as resp:
        resp.raise_for_status()
        final_url = str(resp.url)
        if final_url != url:
            from contracts.api import CompetitorInput
            try:
                CompetitorInput.validate_url.__func__(CompetitorInput, final_url)
            except ValueError as e:
                raise ValueError(f"Redirect to blocked URL: {final_url} ({e})")
        ct = resp.headers.get("content-type", "")
        if ct and not any(t in ct.lower() for t in ("text/html", "text/plain", "application/xhtml", "text/")):
            raise ValueError(f"Non-HTML content-type: {ct}")
        cl = resp.headers.get("content-length")
        if cl:
            try:
                content_length = int(cl)
            except ValueError:
                content_length = None
            if content_length and content_length > MAX_BODY_BYTES:
                raise ValueError(f"Response too large: {content_length} bytes")
        body = b""
        async for chunk in resp.aiter_bytes(8192):
            body += chunk
            if len(body) > MAX_BODY_BYTES:
                raise ValueError(f"Response exceeds {MAX_BODY_BYTES} bytes")
    return FetchOutcome(
        html=body.decode(resp.encoding or "utf-8", errors="replace"),
        status_code=resp.status_code,
        headers=dict(getattr(resp, "headers", {}) or {}),
    )


async def scrape_competitor(
    request: ScrapeRequest,
    *,
    cancelled_check: Optional[Callable[[], bool]] = None,
) -> ScrapeResult:
    """Scrape a competitor website and return cleaned page content.

    Features (v2):
    - Content-based page classification (in addition to URL patterns)
    - Metadata extraction (description, og:image, canonical URL)
    - Link scoring by relevance
    - robots.txt respect
    - Anti-bot detection (Cloudflare, CAPTCHA)
    - Content quality scoring
    - Page deduplication by content hash

    Args:
        request: ScrapeRequest with the target URL, focus areas, and page limit.
        cancelled_check: Optional callable returning True if pipeline was cancelled.

    Returns:
        ScrapeResult with all scraped pages and any errors encountered.
    """
    pages: list[ScrapedContent] = []
    errors: list[str] = []
    attempted = 0
    visited: set[str] = set()
    seen_hashes: set[str] = set()
    robots_respected = True
    bright_data_config = _get_bright_data_config()
    result_metadata = _bright_data_metadata(bright_data_config)

    def _is_cancelled() -> bool:
        return cancelled_check() if cancelled_check else False

    if bright_data_config:
        logger.info(
            "Bright Data Web Unlocker enabled for scraper",
            extra={
                "bright_data_zone": bright_data_config.zone,
                "bright_data_proxy_host": bright_data_config.host,
                "bright_data_debug": bright_data_config.debug,
            },
        )
    else:
        logger.info("Bright Data credentials not configured; using direct httpx scraping")

    async with httpx.AsyncClient(**_client_kwargs(bright_data_config)) as client:
        homepage_url = request.url.rstrip("/")
        if "://" not in homepage_url:
            homepage_url = f"https://{homepage_url}"
        elif not homepage_url.startswith(("http://", "https://")):
            raise ValueError(f"Unsupported URL scheme: {homepage_url}")

        # Re-resolve DNS to close TOCTOU window between URL validation and fetch
        parsed_check = urlparse(homepage_url)
        hostname_check = (parsed_check.hostname or "").lower().rstrip(".")
        if hostname_check:
            try:
                from contracts.api import CompetitorInput
                addrinfos = socket.getaddrinfo(hostname_check, None, proto=socket.IPPROTO_TCP)
                for _, _, _, _, sockaddr in addrinfos:
                    reason = CompetitorInput._is_blocked_ip(sockaddr[0])
                    if reason:
                        raise ValueError(f"SSRF blocked at fetch time: {reason}")
            except socket.gaierror:
                pass  # DNS failure — scraper will get a network error, which is fine

        ignore_robots = _env_bool("IGNORE_ROBOTS_TXT", True)
        if ignore_robots:
            logger.info("Ignoring robots.txt for %s (IGNORE_ROBOTS_TXT=True)", homepage_url)
            robots_parser = None
        else:
            robots_parser = await _check_robots_txt(client, homepage_url)

        try:
            if _is_cancelled():
                return ScrapeResult(
                    competitor_url=homepage_url, pages=pages,
                    errors=["Pipeline cancelled before scraping started"],
                    total_pages_attempted=0,
                    metadata=result_metadata,
                )

            if robots_parser and not robots_parser.can_fetch("*", homepage_url):
                robots_respected = False
                errors.append(f"Blocked by robots.txt: {homepage_url}")
                logger.warning("Blocked by robots.txt: %s", homepage_url)
            else:
                attempted += 1
                homepage_fetch = await _fetch_page(client, homepage_url)
                visited.add(homepage_url)

                anti_bot = _detect_anti_bot(homepage_fetch.html, homepage_fetch.status_code, via_proxy=bright_data_config is not None)
                if anti_bot:
                    errors.append(f"Anti-bot detected on homepage: {anti_bot}")
                    logger.warning("Anti-bot detected on %s: %s", homepage_url, anti_bot)

                clean_text, title, metadata, links = _parse_page(homepage_fetch.html, homepage_url)
                clean_text = _truncate_content(clean_text)
                metadata.update(_bright_data_metadata(bright_data_config, homepage_fetch.headers))
                quality = 0.0 if anti_bot else _content_quality_score(clean_text, "homepage")
                c_hash = _content_hash(clean_text)
                seen_hashes.add(c_hash)

                pages.append(_mk_page(
                    homepage_url, title, clean_text, "homepage",
                    links=[] if anti_bot else links,
                    metadata=metadata, quality=quality, c_hash=c_hash,
                    anti_bot=anti_bot,
                ))

                if not anti_bot:
                    prioritized = _prioritize_links(links, request.focus_areas, request.max_pages - 1)

                    for link in prioritized:
                        if _is_cancelled():
                            errors.append("Pipeline cancelled during scraping")
                            break
                        if link in visited:
                            continue
                        visited.add(link)

                        if robots_parser and not robots_parser.can_fetch("*", link):
                            robots_respected = False
                            errors.append(f"Blocked by robots.txt: {link}")
                            continue

                        try:
                            await asyncio.sleep(REQUEST_DELAY_SECONDS)
                            attempted += 1
                            fetch = await _fetch_page(client, link)

                            anti_bot = _detect_anti_bot(fetch.html, fetch.status_code, via_proxy=bright_data_config is not None)
                            if anti_bot:
                                errors.append(f"Anti-bot detected: {anti_bot} at {link}")
                                logger.warning("Anti-bot detected on %s: %s", link, anti_bot)
                                continue

                            clean_text, title, metadata, _ = _parse_page(fetch.html, link)
                            clean_text = _truncate_content(clean_text)
                            metadata.update(_bright_data_metadata(bright_data_config, fetch.headers))

                            c_hash = _content_hash(clean_text)
                            if c_hash in seen_hashes:
                                logger.info("Skipping duplicate page: %s", link)
                                continue
                            seen_hashes.add(c_hash)

                            page_type = _combined_classify(link, clean_text)
                            quality = _content_quality_score(clean_text, page_type)
                            pages.append(_mk_page(
                                link, title, clean_text, page_type,
                                metadata=metadata, quality=quality, c_hash=c_hash,
                            ))
                            logger.info("Scraped %s (%s, quality=%.2f)", link, page_type, quality)
                        except httpx.HTTPStatusError as exc:
                            msg = f"HTTP {exc.response.status_code} for {link}"
                        except (httpx.TimeoutException, httpx.NetworkError) as exc:
                            msg = f"Network error for {link}: {exc}"
                        except Exception as exc:
                            msg = f"Unexpected error scraping {link}: {exc}"
                        else:
                            msg = None
                        if msg:
                            logger.warning(msg)
                            errors.append(msg)

        except httpx.HTTPStatusError as exc:
            msg = f"HTTP {exc.response.status_code} for homepage {homepage_url}"
            logger.error(msg)
            errors.append(msg)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            msg = f"Network error fetching homepage {homepage_url}: {exc}"
            logger.error(msg)
            errors.append(msg)
        except Exception as exc:
            msg = f"Unexpected error scraping homepage {homepage_url}: {exc}"
            logger.error(msg)
            errors.append(msg)

    parsed = urlparse(homepage_url)
    competitor_name = parsed.netloc.replace("www.", "").split(".")[0].capitalize()

    return ScrapeResult(
        competitor_url=homepage_url,
        competitor_name=competitor_name,
        pages=pages,
        errors=errors,
        total_pages_attempted=attempted,
        robots_respected=robots_respected,
        metadata=result_metadata,
    )
