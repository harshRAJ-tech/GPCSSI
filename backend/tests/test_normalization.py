# File: backend/tests/test_normalization.py
"""
Unit tests for value normalization.

WHY: Normalization is the foundation of correlation. If two forms of the
same artifact normalize differently, the unique constraint splits them
into two entities and correlation silently misses links. These tests lock
the canonical forms in place.
"""
import pytest

from app.models.enums import EntityType
from app.services.normalization import normalize


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+91-9876543210", "9876543210"),
        ("919876543210", "9876543210"),
        ("09876543210", "9876543210"),
        ("9876543210", "9876543210"),
        ("+91 98765 43210", "9876543210"),
    ],
)
def test_phone_collapses_to_national_form(raw: str, expected: str) -> None:
    assert normalize(EntityType.PHONE, raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://www.Example.com/", "https://example.com"),
        ("http://Example.com", "http://example.com"),
        ("https://example.com/path/", "https://example.com/path"),
    ],
)
def test_url_normalization(raw: str, expected: str) -> None:
    assert normalize(EntityType.URL, raw) == expected


def test_domain_strips_www_and_lowercases() -> None:
    assert normalize(EntityType.DOMAIN, "WWW.Fake-Bank.IN") == "fake-bank.in"


def test_email_and_upi_lowercased() -> None:
    assert normalize(EntityType.EMAIL, "Victim@Gmail.com") == "victim@gmail.com"
    assert normalize(EntityType.UPI, "Fraud@YBL") == "fraud@ybl"


def test_ifsc_uppercased() -> None:
    assert normalize(EntityType.IFSC, "sbin0001234") == "SBIN0001234"


def test_telegram_strips_at_and_lowercases() -> None:
    assert normalize(EntityType.TELEGRAM, "@FraudSupport") == "fraudsupport"


def test_crypto_preserves_case() -> None:
    # Checksummed ETH addresses are case-sensitive; must not be altered.
    addr = "0xAbC1230000000000000000000000000000000000"
    assert normalize(EntityType.CRYPTO_WALLET, addr) == addr


@pytest.mark.parametrize(
    "entity_type,value",
    [
        (EntityType.PHONE, "9876543210"),
        (EntityType.EMAIL, "victim@gmail.com"),
        (EntityType.UPI, "fraud@ybl"),
        (EntityType.DOMAIN, "fake-bank.in"),
        (EntityType.IFSC, "SBIN0001234"),
    ],
)
def test_normalization_is_idempotent(entity_type: EntityType, value: str) -> None:
    # Normalizing an already-canonical value must return it unchanged.
    once = normalize(entity_type, value)
    assert normalize(entity_type, once) == once
