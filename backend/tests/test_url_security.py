import httpx
import pytest

from shipsense.url_security import (
    UnsafeUrlError,
    safe_request,
    validate_public_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://localhost",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.1.1",
        "http://[::1]",
        "file:///etc/passwd",
        "https://user:pass@example.com",
        "https://example.com:8443",
    ],
)
def test_private_and_unsafe_urls_are_rejected(url):
    with pytest.raises(UnsafeUrlError):
        validate_public_url(url)


def test_public_url_is_accepted_with_public_dns():
    assert validate_public_url(
        "https://example.com/path",
        resolver=lambda _hostname: {"93.184.216.34"},
    ) == "https://example.com/path"


def test_mixed_public_and_private_dns_is_rejected():
    with pytest.raises(UnsafeUrlError):
        validate_public_url(
            "https://example.com",
            resolver=lambda _hostname: {"93.184.216.34", "127.0.0.1"},
        )


def test_redirect_target_is_validated(monkeypatch):
    monkeypatch.setattr(
        "shipsense.url_security.resolve_host",
        lambda hostname: (
            {"93.184.216.34"}
            if hostname == "example.com"
            else {"127.0.0.1"}
        ),
    )

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def request(self, _method, _url, headers=None):
            return httpx.Response(
                302,
                headers={"location": "http://internal.example/admin"},
            )

    monkeypatch.setattr("shipsense.url_security.httpx.Client", FakeClient)

    with pytest.raises(UnsafeUrlError):
        safe_request("GET", "https://example.com", timeout=5)
