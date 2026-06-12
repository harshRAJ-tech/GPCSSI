# File: backend/app/services/normalization.py
"""
Entity value normalization.

WHY: Correlation only works if the same real-world artifact maps to a
single canonical string. '+91-9876543210', '919876543210' and
'9876543210' must all collapse to one value, otherwise the unique
constraint and the 'have we seen this before' lookup break.

Each normalizer is pure (no side effects) and total (always returns a
string), which makes it trivial to unit-test.
"""
import re

from app.models.enums import EntityType

_NON_DIGITS = re.compile(r"\D+")


def _normalize_phone(value: str) -> str:
    """Reduce an Indian phone number to its 10-digit national form."""
    digits = _NON_DIGITS.sub("", value)
    # Drop a leading country code (91) or trunk prefix if present.
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def _normalize_domain(value: str) -> str:
    """Lowercase a domain and strip a leading 'www.'."""
    host = value.strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _normalize_url(value: str) -> str:
    """
    Canonicalize a URL: lowercase the scheme AND host (case-insensitive
    per RFC 3986), strip a leading 'www.', and drop a trailing slash.
    The path is left case-sensitive and untouched.
    """
    url = value.strip()
    match = re.match(r"^(https?://)([^/]*)(.*)$", url, flags=re.IGNORECASE)
    if match is None:
        return url.rstrip("/")
    scheme, host, rest = match.groups()
    scheme = scheme.lower()
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return f"{scheme}{host}{rest}".rstrip("/")


def normalize(entity_type: EntityType, value: str) -> str:
    """Return the canonical form of a value for the given entity type."""
    v = value.strip()
    if entity_type is EntityType.PHONE:
        return _normalize_phone(v)
    if entity_type in (EntityType.EMAIL, EntityType.UPI):
        return v.lower()
    if entity_type is EntityType.DOMAIN:
        return _normalize_domain(v)
    if entity_type is EntityType.URL:
        return _normalize_url(v)
    if entity_type is EntityType.IFSC:
        return v.upper()
    if entity_type in (EntityType.IP_ADDRESS, EntityType.UTR, EntityType.BANK_ACCOUNT):
        return v
    if entity_type is EntityType.TELEGRAM:
        return v.lstrip("@").lower()
    if entity_type is EntityType.CRYPTO_WALLET:
        # Preserve case: some chains (e.g. checksummed ETH) are case-sensitive.
        return v
    return v
