import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx


ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {None, 80, 443}
MAX_REDIRECTS = 5


class UnsafeUrlError(ValueError):
    pass


def resolve_host(hostname):
    try:
        records = socket.getaddrinfo(
            hostname,
            None,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise UnsafeUrlError("The URL hostname could not be resolved") from exc
    return {record[4][0] for record in records}


def _is_public_address(value):
    address = ipaddress.ip_address(value)
    return address.is_global


def validate_public_url(url, resolver=None):
    if not isinstance(url, str) or not url.strip():
        raise UnsafeUrlError("A URL is required")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError("URL must use http:// or https://")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("URLs containing credentials are not allowed")
    if not parsed.hostname:
        raise UnsafeUrlError("URL must contain a hostname")
    if parsed.port not in ALLOWED_PORTS:
        raise UnsafeUrlError("Only standard HTTP and HTTPS ports are allowed")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UnsafeUrlError("Localhost URLs are not allowed")

    try:
        literal = ipaddress.ip_address(hostname)
        addresses = {str(literal)}
    except ValueError:
        addresses = (resolver or resolve_host)(hostname)

    if not addresses or any(not _is_public_address(value) for value in addresses):
        raise UnsafeUrlError(
            "The URL must resolve only to public internet addresses"
        )
    return url.strip()


def safe_request(
    method,
    url,
    *,
    timeout,
    headers=None,
    max_redirects=MAX_REDIRECTS,
):
    current_url = validate_public_url(url)
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            response = client.request(method, current_url, headers=headers)
            if not response.is_redirect:
                return response

            location = response.headers.get("location")
            if not location:
                return response
            current_url = validate_public_url(urljoin(current_url, location))

    raise UnsafeUrlError(f"URL exceeded {max_redirects} redirects")
