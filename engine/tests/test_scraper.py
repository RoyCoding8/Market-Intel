"""Tests for the scraper agent."""

from __future__ import annotations

import pytest
import httpx

from contracts.engine import ScrapeRequest
from engine.agents.scraper import (
    BRIGHT_DATA_PROXY_HOST,
    BRIGHT_DATA_PROXY_PORT,
    BrightDataConfig,
    _classify_url,
    _clean_html,
    _extract_links,
    _extract_title,
    _get_bright_data_config,
    _prioritize_links,
    scrape_competitor,
)


# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------


class TestClassifyUrl:
    def test_pricing_page(self):
        assert _classify_url("https://example.com/pricing") == "pricing"

    def test_about_page(self):
        assert _classify_url("https://example.com/about") == "about"

    def test_blog_page(self):
        assert _classify_url("https://example.com/blog") == "blog"

    def test_jobs_page(self):
        assert _classify_url("https://example.com/careers") == "jobs"

    def test_features_page(self):
        assert _classify_url("https://example.com/features") == "features"

    def test_unknown_page(self):
        assert _classify_url("https://example.com/xyzzy") == "unknown"

    def test_nested_path(self):
        assert _classify_url("https://example.com/product/pricing") == "pricing"


class TestCleanHtml:
    def test_strips_script_and_style(self):
        html = "<html><head><style>body{color:red}</style></head><body><p>Hello</p><script>alert(1)</script></body></html>"
        result = _clean_html(html)
        assert "Hello" in result
        assert "alert" not in result
        assert "color:red" not in result

    def test_strips_empty_lines(self):
        html = "<p>Line 1</p><p></p><p>Line 2</p>"
        result = _clean_html(html)
        assert result == "Line 1\nLine 2"

    def test_handles_empty_html(self):
        result = _clean_html("")
        assert result == ""


class TestExtractTitle:
    def test_extracts_title(self):
        html = "<html><head><title>My Page</title></head><body></body></html>"
        assert _extract_title(html) == "My Page"

    def test_no_title(self):
        html = "<html><body><p>Hi</p></body></html>"
        assert _extract_title(html) is None

    def test_title_with_whitespace(self):
        html = "<html><head><title>  Trimmed  </title></head></html>"
        assert _extract_title(html) == "Trimmed"


class TestExtractLinks:
    def test_extracts_same_domain_links(self):
        html = '<a href="/pricing">Pricing</a><a href="https://other.com/x">External</a>'
        links = _extract_links(html, "https://example.com")
        assert any("/pricing" in link for link in links)
        assert not any("other.com" in link for link in links)

    def test_skips_mailto_and_hash(self):
        html = '<a href="mailto:a@b.com">Email</a><a href="#top">Top</a>'
        links = _extract_links(html, "https://example.com")
        assert links == []

    def test_deduplicates(self):
        html = '<a href="/page">A</a><a href="/page">B</a>'
        links = _extract_links(html, "https://example.com")
        assert len(links) == 1


class TestPrioritizeLinks:
    def test_focus_areas_first(self):
        links = [
            "https://example.com/about",
            "https://example.com/pricing",
            "https://example.com/random",
        ]
        result = _prioritize_links(links, ["pricing"], 10)
        assert result[0] == "https://example.com/pricing"

    def test_respects_max_pages(self):
        links = [f"https://example.com/page{i}" for i in range(20)]
        result = _prioritize_links(links, [], 5)
        assert len(result) == 5


class TestBrightDataConfig:
    def test_disabled_when_credentials_missing(self):
        assert _get_bright_data_config({}) is None

    def test_partial_credentials_fall_back_to_direct(self):
        assert _get_bright_data_config({"BRIGHT_DATA_CUSTOMER_ID": "customer"}) is None

    def test_proxy_url_uses_bright_data_superproxy(self):
        config = BrightDataConfig(
            customer_id="customer",
            zone="unlocker",
            password="secret",
        )

        assert config.username == "brd-customer-customer-zone-unlocker-debug-full"
        assert config.proxy_url.startswith("http://brd-customer-customer-zone-unlocker-debug-full:")
        assert f"@{BRIGHT_DATA_PROXY_HOST}:{BRIGHT_DATA_PROXY_PORT}" in config.proxy_url

    def test_env_config_supports_country_and_debug_toggle(self):
        config = _get_bright_data_config({
            "BRIGHT_DATA_CUSTOMER_ID": "customer",
            "BRIGHT_DATA_ZONE": "unlocker",
            "BRIGHT_DATA_PASSWORD": "secret",
            "BRIGHT_DATA_COUNTRY": "US",
            "BRIGHT_DATA_DEBUG": "false",
        })

        assert config is not None
        assert config.username == "brd-customer-customer-zone-unlocker-country-us"


# ---------------------------------------------------------------------------
# Integration tests — scrape_competitor (with mocked HTTP)
# ---------------------------------------------------------------------------


MOCK_HOMEPAGE_HTML = """
<html>
<head><title>Acme Corp</title></head>
<body>
<nav><a href="/pricing">Pricing</a><a href="/about">About</a></nav>
<h1>Welcome to Acme Corp</h1>
<p>We build amazing widgets.</p>
</body>
</html>
"""

MOCK_PRICING_HTML = """
<html>
<head><title>Pricing - Acme Corp</title></head>
<body>
<h1>Pricing</h1>
<p>Starter: $9/mo</p>
<p>Pro: $29/mo</p>
<p>Enterprise: Custom</p>
</body>
</html>
"""


@pytest.fixture
def mock_httpx(monkeypatch):
    """Mock httpx.AsyncClient.stream to return canned responses."""

    class MockResponse:
        def __init__(self, text: str, status_code: int = 200, url: str = "https://example.com"):
            self.text = text
            self.content = text.encode("utf-8")
            self.status_code = status_code
            self.headers = {}
            self.encoding = "utf-8"
            self.url = url

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "error",
                    request=httpx.Request("GET", "https://example.com"),
                    response=httpx.Response(self.status_code),
                )

        async def aiter_bytes(self, chunk_size=8192):
            """Yield content in chunks for streaming."""
            for i in range(0, len(self.content), chunk_size):
                yield self.content[i:i + chunk_size]

    class MockStreamContext:
        """Async context manager that returns a MockResponse."""
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, *args):
            pass

    def mock_stream(self, method, url, **kwargs):
        if "pricing" in url:
            return MockStreamContext(MockResponse(MOCK_PRICING_HTML))
        return MockStreamContext(MockResponse(MOCK_HOMEPAGE_HTML))

    monkeypatch.setattr(httpx.AsyncClient, "stream", mock_stream)


@pytest.mark.asyncio
async def test_scrape_competitor_basic(mock_httpx):
    request = ScrapeRequest(url="https://example.com", focus_areas=["pricing"], max_pages=5)
    result = await scrape_competitor(request)

    assert result.competitor_url == "https://example.com"
    assert len(result.pages) >= 1
    assert result.pages[0].title == "Acme Corp"
    assert "Welcome to Acme Corp" in result.pages[0].html_text


@pytest.mark.asyncio
async def test_scrape_competitor_finds_pricing(mock_httpx):
    request = ScrapeRequest(url="https://example.com", focus_areas=["pricing"], max_pages=5)
    result = await scrape_competitor(request)

    pricing_pages = [p for p in result.pages if p.page_type == "pricing"]
    assert len(pricing_pages) >= 1
    assert "$9" in pricing_pages[0].html_text


@pytest.mark.asyncio
async def test_scrape_competitor_marks_bright_data_provider(mock_httpx, monkeypatch):
    monkeypatch.setenv("BRIGHT_DATA_CUSTOMER_ID", "customer")
    monkeypatch.setenv("BRIGHT_DATA_ZONE", "unlocker")
    monkeypatch.setenv("BRIGHT_DATA_PASSWORD", "secret")

    request = ScrapeRequest(url="https://example.com", focus_areas=["pricing"], max_pages=2)
    result = await scrape_competitor(request)

    assert result.pages
    assert result.pages[0].metadata["scrape_provider"] == "bright_data_web_unlocker"
    assert result.pages[0].metadata["bright_data_enabled"] == "true"
    assert result.pages[0].metadata["bright_data_zone"] == "unlocker"


@pytest.mark.asyncio
async def test_scrape_competitor_classifies_pages(mock_httpx):
    request = ScrapeRequest(url="https://example.com", focus_areas=["pricing", "about"], max_pages=5)
    result = await scrape_competitor(request)

    types = {p.page_type for p in result.pages}
    assert "homepage" in types


@pytest.mark.asyncio
async def test_scrape_competitor_handles_http_error(monkeypatch):
    class MockResponse:
        text = ""
        content = b""
        status_code = 404
        encoding = "utf-8"
        headers = {}

        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "not found",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(404),
            )

        async def aiter_bytes(self, chunk_size=8192):
            yield b""

    class MockStreamCtx:
        def __init__(self, resp):
            self._resp = resp
        async def __aenter__(self):
            return self._resp
        async def __aexit__(self, *args):
            pass

    def mock_stream(self, method, url, **kwargs):
        return MockStreamCtx(MockResponse())

    monkeypatch.setattr(httpx.AsyncClient, "stream", mock_stream)

    request = ScrapeRequest(url="https://example.com", focus_areas=["pricing"], max_pages=5)
    result = await scrape_competitor(request)

    assert len(result.pages) == 0
    assert len(result.errors) >= 1
