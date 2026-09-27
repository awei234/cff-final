"""Shared validation helpers for model configuration values."""

from __future__ import annotations

from urllib.parse import urlparse

PLACEHOLDER_API_BASES = frozenset({"https://example.com/compatible-mode/v1"})
EXAMPLE_DOMAINS = frozenset({"example.com", "example.org", "example.net"})


def is_placeholder_api_base(api_base: str) -> bool:
    """Return True when api_base is a documentation placeholder URL."""
    value = str(api_base or "").strip()
    if not value:
        return False
    if value in PLACEHOLDER_API_BASES:
        return True
    try:
        host = urlparse(value).hostname or ""
    except Exception:
        return False
    if not host:
        return False
    return any(host == domain or host.endswith(f".{domain}") for domain in EXAMPLE_DOMAINS)


def is_valid_api_base(api_base: str) -> bool:
    """Return whether *api_base* is a usable absolute HTTP(S) endpoint."""
    value = str(api_base or "").strip()
    if not value or is_placeholder_api_base(value):
        return False
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
