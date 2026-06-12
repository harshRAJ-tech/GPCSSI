# File: backend/tests/test_extraction.py
"""
Unit tests for deterministic entity extraction.

WHY: Extraction accuracy directly determines correlation quality. These
tests pin down the hard disambiguations (UPI vs email, phone vs bank
account), reject invalid inputs (out-of-range IPv4), and verify that a
single substring is never double-counted across overlapping patterns.
"""
from app.models.enums import EntityType
from app.services.extraction import extract


def _types(text: str) -> set[EntityType]:
    return {e.entity_type for e in extract(text)}


def _values_of(text: str, etype: EntityType) -> set[str]:
    return {e.raw_value for e in extract(text) if e.entity_type is etype}


def test_empty_text_returns_nothing() -> None:
    assert extract("") == []


def test_extracts_phone() -> None:
    assert _values_of("call me on 9876543210 today", EntityType.PHONE) == {"9876543210"}


def test_upi_is_not_classified_as_email() -> None:
    # 'fraud@ybl' has no dotted TLD -> UPI, not email.
    result = extract("send to fraud@ybl now")
    types = {e.entity_type for e in result}
    assert EntityType.UPI in types
    assert EntityType.EMAIL not in types


def test_email_is_not_classified_as_upi() -> None:
    result = extract("contact victim@gmail.com please")
    types = {e.entity_type for e in result}
    assert EntityType.EMAIL in types
    # The email span is claimed, so it must not also appear as a UPI.
    assert EntityType.UPI not in types


def test_ifsc_extracted() -> None:
    assert _values_of("branch code SBIN0001234 confirmed", EntityType.IFSC) == {
        "SBIN0001234"
    }


def test_eth_wallet_extracted() -> None:
    addr = "0x" + "a" * 40
    assert addr in _values_of(f"wallet {addr} flagged", EntityType.CRYPTO_WALLET)


def test_invalid_ipv4_rejected() -> None:
    # 999.1.1.1 matches the shape but has an out-of-range octet.
    assert EntityType.IP_ADDRESS not in _types("host 999.1.1.1 down")


def test_valid_ipv4_accepted() -> None:
    assert _values_of("server 192.168.1.10 ok", EntityType.IP_ADDRESS) == {
        "192.168.1.10"
    }


def test_no_span_double_counting() -> None:
    # Every match must occupy a unique, non-overlapping character span.
    text = "upi fraud@ybl phone 9876543210 ifsc SBIN0001234"
    spans = [(e.start, e.end) for e in extract(text)]
    for i, (a_start, a_end) in enumerate(spans):
        for b_start, b_end in spans[i + 1 :]:
            assert a_start >= b_end or a_end <= b_start, "spans overlap"


def test_mixed_document_extracts_expected_types() -> None:
    text = (
        "Victim victim@gmail.com paid fraud@ybl from account 123456789012 "
        "IFSC SBIN0001234, contact 9876543210, site http://fake-bank.in"
    )
    found = _types(text)
    assert {
        EntityType.EMAIL,
        EntityType.UPI,
        EntityType.IFSC,
        EntityType.PHONE,
        EntityType.URL,
    } <= found
