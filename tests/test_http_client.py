"""Unit tests for unified HTTP client and headers."""

from src.draytek_client import DrayTekClient
from src.hikvision_client import HikvisionClient
from src.http_client import (
    DEFAULT_USER_AGENT,
    BaseCrawlerClient,
    create_http_client,
    get_default_headers,
)
from src.tplink_client import TPLinkClient


def test_default_user_agent_format():
    assert "Mozilla/5.0" in DEFAULT_USER_AGENT
    assert "Safari/537.36" in DEFAULT_USER_AGENT
    assert "Chrome/" in DEFAULT_USER_AGENT


def test_get_default_headers_basic():
    headers = get_default_headers()
    assert headers["User-Agent"] == DEFAULT_USER_AGENT
    assert "Accept" in headers
    assert "Accept-Language" in headers
    assert "sec-ch-ua" in headers


def test_get_default_headers_custom_user_agent():
    custom_ua = "MyCustomBot/1.0"
    headers = get_default_headers(user_agent=custom_ua)
    assert headers["User-Agent"] == custom_ua


def test_get_default_headers_extra_headers():
    extra = {"X-Custom-Header": "TestValue", "Accept": "application/json"}
    headers = get_default_headers(extra_headers=extra)
    assert headers["X-Custom-Header"] == "TestValue"
    assert headers["Accept"] == "application/json"
    assert headers["User-Agent"] == DEFAULT_USER_AGENT


def test_create_http_client_defaults():
    client = create_http_client(timeout=10.0)
    try:
        assert client.timeout.read == 10.0
        assert client.headers["User-Agent"] == DEFAULT_USER_AGENT
    finally:
        client.close()


def test_base_crawler_client_context_manager():
    with BaseCrawlerClient(timeout=12.0) as client:
        assert client.timeout == 12.0
        assert client.client.headers["User-Agent"] == DEFAULT_USER_AGENT
        assert not client.client.is_closed

    assert client.client.is_closed


def test_all_clients_use_unified_user_agent():
    draytek = DrayTekClient()
    hikvision = HikvisionClient()
    tplink = TPLinkClient()

    try:
        assert draytek.client.headers["User-Agent"] == DEFAULT_USER_AGENT
        assert hikvision.client.headers["User-Agent"] == DEFAULT_USER_AGENT
        assert tplink.client.headers["User-Agent"] == DEFAULT_USER_AGENT
    finally:
        draytek.close()
        hikvision.close()
        tplink.close()
