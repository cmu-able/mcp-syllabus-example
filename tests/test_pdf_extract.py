# -*- coding: utf-8 -*-
"""Tests for PDF extraction functionality."""
from pathlib import Path
from syllabus_server.pdf_utils import extract_pdf_text


def test_extract_pdf_text_from_local_file():
    """Test extracting text from a local PDF file."""
    pdf_path = "pdfs/17603.pdf"
    
    # Check that the test PDF exists
    assert Path(pdf_path).is_file(), f"Test PDF not found: {pdf_path}"
    
    # Extract text
    text = extract_pdf_text(pdf_path)
    
    # Basic assertions
    assert isinstance(text, str), "Extracted text should be a string"
    assert len(text) > 1000, "PDF should contain substantial text content"
    assert "17-603" in text, "PDF should contain course number"
    assert "Communications" in text, "PDF should contain course title"


def main():
    """Manual test runner for development."""
    text = extract_pdf_text("pdfs/17603.pdf")
    print("--- First 1000 chars ---")
    print(text)
    print("\n[OK] Length:", len(text))


if __name__ == "__main__":
    main()
