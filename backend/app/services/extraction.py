# File: backend/app/services/extraction.py
"""
Deterministic entity extraction.

WHY: Extraction is regex-based and rule-driven, NOT model-based. For a
law-enforcement tool that is a deliberate choice: it is auditable,
reproducible, fast, and cannot 'hallucinate' an entity that is not
literally present in the text.

Design notes:
- Patterns are anchored / length-bounded to avoid catastrophic
  backtracking (ReDoS) on adversarial input.
- More specific types (UPI, IFSC, UTR, crypto) are matched before generic
  ones, and matched character spans are 'claimed' so a single substring
  is not double-counted (e.g. a UPI handle is not also read as an email).
- Each match yields (EntityType, raw_value). Normalization happens later,
  keeping extraction and canonicalization independently testable.
"""
import re
from dataclasses import dataclass

from app.models.enums import EntityType


@dataclass(frozen=True)
class ExtractedEntity:
    entity_type: EntityType
    raw_value: str
    start: int
    end: int


# Patterns ordered from most specific to most generic. The order of this
# list is the precedence order used during extraction.
_PATTERNS: list[tuple[EntityType, re.Pattern[str]]] = [
    # IFSC: 4 letters, a 0, then 6 alphanumerics (e.g. SBIN0001234).
    (EntityType.IFSC, re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")),
    # UTR / RRN: a standalone 12-digit reference number.
    (EntityType.UTR, re.compile(r"\bUTR[:\s]*([0-9]{12})\b", re.IGNORECASE)),
    # UPI handle: localpart@psp where psp is alphabetic (ybl, oksbi, paytm).
    (EntityType.UPI, re.compile(r"\b[a-zA-Z0-9._-]{2,256}@[a-zA-Z]{2,64}\b")),
    # Email: requires a dotted TLD, which distinguishes it from a UPI handle.
    (EntityType.EMAIL, re.compile(r"\b[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]{1,255}\.[a-zA-Z]{2,24}\b")),
    # Crypto: BTC bech32 / legacy, or 0x-prefixed 40-hex (ETH/USDT-ERC20).
    (EntityType.CRYPTO_WALLET, re.compile(r"\b(?:bc1[a-z0-9]{11,71}|0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")),
    # IP address (IPv4). Range validation is applied in the validator below.
    (EntityType.IP_ADDRESS, re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    # URL with scheme.
    (EntityType.URL, re.compile(r"\bhttps?://[^\s<>\"']{1,2000}\b")),
    # Telegram handle.
    (EntityType.TELEGRAM, re.compile(r"(?<![\w@])@[a-zA-Z][a-zA-Z0-9_]{4,31}\b")),
    # Indian phone (optionally +91 / 0 prefixed), 10 digits starting 6-9.
    (EntityType.PHONE, re.compile(r"(?<!\d)(?:\+?91[-\s]?|0)?[6-9]\d{9}(?!\d)")),
    # Bank account: a standalone run of 9-18 digits.
    (EntityType.BANK_ACCOUNT, re.compile(r"(?<!\d)\d{9,18}(?!\d)")),
]


def _valid_ipv4(value: str) -> bool:
    """Reject dotted-quads with any octet > 255 (regex alone cannot)."""
    parts = value.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def extract(text: str) -> list[ExtractedEntity]:
    """
    Extract investigative entities from text.

    Returns a list of ExtractedEntity. Overlapping spans are resolved by
    pattern precedence: once a character range is claimed by a
    higher-precedence type, lower-precedence patterns cannot reuse it.
    """
    if not text:
        return []

    claimed: list[tuple[int, int]] = []
    results: list[ExtractedEntity] = []

    def _overlaps(start: int, end: int) -> bool:
        return any(start < c_end and end > c_start for c_start, c_end in claimed)

    for entity_type, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            # If the pattern captures a group (e.g. UTR), prefer the group.
            if match.groups():
                raw = match.group(1)
                start, end = match.span(1)
            else:
                raw = match.group(0)
                start, end = match.span(0)

            if _overlaps(start, end):
                continue
            if entity_type is EntityType.IP_ADDRESS and not _valid_ipv4(raw):
                continue

            claimed.append((start, end))
            results.append(
                ExtractedEntity(entity_type=entity_type, raw_value=raw, start=start, end=end)
            )

    return results
