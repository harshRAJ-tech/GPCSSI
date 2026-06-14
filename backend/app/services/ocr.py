# File: backend/app/services/ocr.py
"""
OCR and Text Extraction Pipeline.

WHY: This service provides a single entrypoint to extract searchable text
from multiple formats of evidence (digital PDFs, scanned PDFs, images, and text/csv).
It uses PyMuPDF (fitz) for extremely fast native text parsing in digital PDFs,
and falls back to EasyOCR for scanned documents or image evidence.
The heavy ML dependencies (easyocr, torch) are loaded lazily to preserve
fast backend startup times and prevent crashes when OCR is not required.
"""
import logging
import os
from collections.abc import Generator

logger = logging.getLogger(__name__)

# Global cached OCR reader to avoid re-initializing PyTorch on every call
_ocr_reader = None


def _get_ocr_reader():
    """
    Lazily initialize and return the EasyOCR reader instance.
    
    This keeps application startup fast and ensures that the system works
    even if the user runs the app without installing easyocr or torch.
    """
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            logger.info("Initializing EasyOCR English reader...")
            # Initialize easyocr Reader with English language support
            _ocr_reader = easyocr.Reader(["en"], gpu=False)
            logger.info("EasyOCR initialized successfully.")
        except ImportError as e:
            logger.error(
                "Failed to import easyocr or torch. Image OCR is disabled. "
                "Error details: %s",
                e,
            )
            raise RuntimeError(
                "OCR engine is missing. Run 'pip install easyocr torch' to enable."
            ) from e
    return _ocr_reader


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.
    
    First, it attempts to extract native (digital) text page by page.
    If the extracted text is empty or extremely short (e.g. < 50 characters),
    it assumes the PDF is a scanned document, renders the pages to images,
    and runs EasyOCR on each page.
    """
    import fitz  # PyMuPDF

    logger.info("Attempting native text extraction on PDF: %s", file_path)
    doc = fitz.open(file_path)
    text_content = []
    
    for i, page in enumerate(doc):
        page_text = page.get_text()
        if page_text.strip():
            text_content.append(page_text)
            
    digital_text = "\n".join(text_content).strip()
    
    # If the PDF contains sufficient native text, return it.
    if len(digital_text) >= 50:
        logger.info(
            "Native PDF text extraction succeeded (%d characters).",
            len(digital_text),
        )
        return digital_text
        
    # Scanned PDF fallback
    logger.info("PDF contains insufficient native text (%d chars). Falling back to OCR...", len(digital_text))
    ocr_text_content = []
    
    try:
        reader = _get_ocr_reader()
        for page_num, page in enumerate(doc):
            logger.info("Running OCR on PDF page %d/%d", page_num + 1, len(doc))
            # Render page to a high-resolution image (300 DPI) for accurate OCR
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            
            # EasyOCR can read image bytes directly
            results = reader.readtext(img_bytes)
            # Join text segments from EasyOCR results
            page_text = " ".join([text for (_, text, _) in results])
            if page_text.strip():
                ocr_text_content.append(page_text)
    except Exception as e:
        logger.warning(
            "PDF OCR fallback failed or was disabled: %s. Returning raw digital text.",
            e,
        )
        return digital_text

    return "\n".join(ocr_text_content).strip()


def extract_text_from_image(file_path: str) -> str:
    """
    Extract text from a PNG/JPEG image using EasyOCR.
    """
    logger.info("Running OCR on image: %s", file_path)
    try:
        reader = _get_ocr_reader()
        results = reader.readtext(file_path)
        extracted = " ".join([text for (_, text, _) in results])
        return extracted.strip()
    except Exception as e:
        logger.error("Failed to run OCR on image %s: %s", file_path, e)
        return ""


def extract_text_from_csv(file_path: str) -> str:
    """
    Extract text from plain text or CSV files.
    
    Ensures safe reading and sanitization of text files.
    """
    logger.info("Reading text from flat file: %s", file_path)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            # Limit read to first 500KB to prevent memory exhaustion
            return f.read(500 * 1024).strip()
    except Exception as e:
        logger.error("Failed to read text file %s: %s", file_path, e)
        return ""


def extract_text_from_evidence(content_type: str, file_path: str) -> str:
    """
    Orchestrate text extraction depending on the evidence MIME type.
    
    Returns the extracted text, or an empty string if format is unsupported or failed.
    """
    if not os.path.exists(file_path):
        logger.error("File does not exist at path: %s", file_path)
        return ""

    c_type = content_type.lower()
    
    if c_type == "application/pdf":
        return extract_text_from_pdf(file_path)
    elif c_type in ("image/png", "image/jpeg"):
        return extract_text_from_image(file_path)
    elif c_type in ("text/csv", "text/plain"):
        return extract_text_from_csv(file_path)
    else:
        logger.warning(
            "MIME type %s does not support text/OCR extraction in this prototype.",
            content_type,
        )
        return ""
