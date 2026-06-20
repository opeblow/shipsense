import pytest


@pytest.fixture(autouse=True)
def stable_public_dns(monkeypatch):
    """Keep URL-security tests deterministic in network-restricted runners."""
    monkeypatch.setattr(
        "shipsense.url_security.resolve_host",
        lambda _hostname: {"93.184.216.34"},
    )
