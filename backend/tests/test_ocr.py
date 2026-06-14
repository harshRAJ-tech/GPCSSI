# File: backend/tests/test_ocr.py
"""
Unit tests for the OCR and Text Extraction service.

WHY: Text extraction is a crucial precursor to entity extraction.
We test:
1. Native text extraction from plain files/CSVs.
2. Digital PDF text extraction (using a dynamically created test PDF).
3. Image OCR and Scanned PDF fallbacks using mocked EasyOCR responses
   to avoid heavy ML model loading and guarantee fast test execution.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF
import pytest

from app.services import ocr


@pytest.fixture()
def temp_pdf(tmp_path: Path) -> Path:
    """Dynamically create a valid digital PDF for testing."""
    pdf_path = tmp_path / "test_digital.pdf"
    doc = fitz.open()
    page = doc.new_page()
    # Write a dummy narrative containing seed entities
    page.insert_text(
        (50, 50),
        "Victim was told to send Rs 50000 to UPI fraud@ybl. Contact phone: 9812345678.",
    )
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_extract_text_from_csv(tmp_path: Path) -> None:
    """Verify text file reading handles content extraction safely."""
    csv_path = tmp_path / "evidence.csv"
    content = "phone,upi,account\n9810012345,fraud@ybl,100200300400"
    csv_path.write_text(content, encoding="utf-8")
    
    extracted = ocr.extract_text_from_csv(str(csv_path))
    assert extracted == content


def test_extract_text_from_pdf_digital(temp_pdf: Path) -> None:
    """Verify native text is successfully extracted from digital PDFs."""
    extracted = ocr.extract_text_from_pdf(str(temp_pdf))
    assert "UPI fraud@ybl" in extracted
    assert "9812345678" in extracted


def test_extract_text_from_image_mocked(tmp_path: Path) -> None:
    """Test image text extraction with a mocked EasyOCR reader."""
    img_path = tmp_path / "evidence.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")  # Dummy PNG bytes

    with patch("app.services.ocr._get_ocr_reader") as mock_get_reader:
        mock_reader = MagicMock()
        # Mock easyocr result structure: list of (bbox, text, confidence)
        mock_reader.readtext.return_value = [
            (None, "UPI", 0.99),
            (None, "fraud@ybl", 0.95),
            (None, "9812345678", 0.97),
        ]
        mock_get_reader.return_value = mock_reader
        
        extracted = ocr.extract_text_from_image(str(img_path))
        
        assert "UPI" in extracted
        assert "fraud@ybl" in extracted
        assert "9812345678" in extracted
        mock_reader.readtext.assert_called_once_with(str(img_path))


def test_extract_text_from_scanned_pdf_mocked(tmp_path: Path) -> None:
    """Verify scanned PDFs (having no text) fall back to page-image OCR."""
    scanned_pdf_path = tmp_path / "scanned.pdf"
    
    # Create a PDF with a page containing no text (only draw a rectangle to simulate an image)
    doc = fitz.open()
    page = doc.new_page()
    page.draw_rect(fitz.Rect(10, 10, 100, 100), color=(1, 0, 0), fill=(1, 0, 0))
    doc.save(str(scanned_pdf_path))
    doc.close()

    # The PDF contains 0 native characters, triggering the OCR fallback
    with patch("app.services.ocr._get_ocr_reader") as mock_get_reader:
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            (None, "Scanned", 0.99),
            (None, "9812345678", 0.97),
        ]
        mock_get_reader.return_value = mock_reader
        
        extracted = ocr.extract_text_from_pdf(str(scanned_pdf_path))
        
        assert "Scanned" in extracted
        assert "9812345678" in extracted
        # Verify easyocr readtext was called for the page bytes
        assert mock_reader.readtext.call_count == 1
