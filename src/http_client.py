"""HTTP client factory and unified request headers for crawlers."""

from typing import Any, Self

import httpx

# Unified User-Agent simulating a modern Chrome desktop browser
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/156.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="156", "Google Chrome";v="156"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def get_default_headers(
    user_agent: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build unified HTTP request headers, allowing custom user-agent or extra headers."""
    headers = dict(DEFAULT_HEADERS)
    if user_agent:
        headers["User-Agent"] = user_agent
    if extra_headers:
        headers.update(extra_headers)
    return headers


def create_http_client(
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
    user_agent: str | None = None,
    **kwargs: Any,
) -> httpx.Client:
    """Create a configured httpx.Client with unified headers, HTTP/2, and redirect following."""
    merged_headers = get_default_headers(user_agent=user_agent, extra_headers=headers)
    kwargs.setdefault("http2", True)
    kwargs.setdefault("follow_redirects", True)
    return httpx.Client(timeout=timeout, headers=merged_headers, **kwargs)


class BaseCrawlerClient:
    """Base crawler client providing unified HTTP client lifecycle management."""

    def __init__(
        self,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
        headers: dict[str, str] | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.client = client or create_http_client(
            timeout=self.timeout,
            headers=headers,
            user_agent=user_agent,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

