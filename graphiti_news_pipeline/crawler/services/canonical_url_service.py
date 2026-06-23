from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


PLACEHOLDER_DOMAINS = {"example.com", "example.org", "example.net"}

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "from",
    "spm",
    "mkt_tok",
}


def canonicalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw

    parsed = urlparse(raw)
    if not _is_traceable_parsed_url(parsed):
        return ""
    filtered = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(filtered, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, ""))


def is_traceable_source_url(url: str) -> bool:
    raw = (url or "").strip()
    if not raw:
        return False
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return _is_traceable_parsed_url(urlparse(raw))


def _is_traceable_parsed_url(parsed) -> bool:
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    hostname = (parsed.hostname or "").lower()
    if hostname in PLACEHOLDER_DOMAINS or any(hostname.endswith(f".{domain}") for domain in PLACEHOLDER_DOMAINS):
        return False
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return False
    return True
