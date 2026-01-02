"""Unit tests for split syllabus parsing stages."""
import pytest

from services.shared.models import StructureSyllabusRequest
from services.syllabus_service.app import _derive_schedule_text


def test_structure_request_requires_full_text():
    """StructureSyllabusRequest should reject empty full_text."""
    with pytest.raises(ValueError):
        StructureSyllabusRequest(full_text="   ")


def test_derive_schedule_text_detects_schedule_pages():
    """Schedule detection should pick pages with schedule cues."""
    pages = [
        "General info page",
        "Week 1 Date Topic\nWeek 2 Date Topic",
        "Assignments and grading",
    ]

    schedule_text = _derive_schedule_text(pages, provided_schedule_text=None)

    assert "Week 1" in schedule_text
    assert "Week 2" in schedule_text
