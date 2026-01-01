import base64
from pathlib import Path

from services.syllabus_service.mcp_server import get_syllabus_text


def test_get_syllabus_text_accepts_base64_upload():
    """Service entrypoint should process base64 PDF bytes and mark source as bytes."""
    fixture_path = Path("pdfs/17603.pdf")
    if not fixture_path.is_file():
        # Fixture missing in some environments; skip to avoid false negative
        import pytest
        pytest.skip(f"Fixture PDF not found: {fixture_path}")

    pdf_b64 = base64.b64encode(fixture_path.read_bytes()).decode("utf-8")

    # Access the underlying function from the FastMCP tool wrapper
    result = get_syllabus_text.fn(pdf_content_base64=pdf_b64)

    assert result.metadata.source == "bytes"
    assert result.metadata.page_count > 0
    assert result.full_text
