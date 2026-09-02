from collections.abc import Iterable
from urllib.parse import urlparse


def normalize_domain(domain: str) -> str:
    """Normalize a domain value for allowlist comparison."""
    return domain.strip().lower().rstrip(".")


def is_allowed_url(url: str, allowed_domains: Iterable[str]) -> bool:
    """Return whether an HTTP URL belongs to an allowed domain or subdomain."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.hostname:
        return False

    hostname = normalize_domain(parsed.hostname)
    for domain in allowed_domains:
        allowed = normalize_domain(domain)
        if hostname == allowed or hostname.endswith(f".{allowed}"):
            return True
    return False
