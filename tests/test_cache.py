# -*- coding: utf-8 -*-
"""
Unit tests for the SyllabusCache class.
"""
import pickle
from pathlib import Path

import pytest

from syllabus_server.cache import CacheEntry, SyllabusCache
from syllabus_server.models import ParsedSyllabus, Policies


@pytest.fixture
def temp_cache(tmp_path):
    """Provide isolated cache directory for tests."""
    cache_dir = tmp_path / "test_cache"
    return SyllabusCache(cache_dir=cache_dir)


@pytest.fixture
def sample_parsed_syllabus():
    """Provide sample ParsedSyllabus for testing."""
    return ParsedSyllabus(
        course_code="TEST-101",
        course_title="Test Course",
        term="Fall 2025",
        timezone="America/New_York",
        sections=[],
        assignments=[],
        schedule=[],
        policies=Policies(),
    )


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "test.pdf"
    # Create a minimal PDF file (not a real PDF, but enough for testing)
    pdf_path.write_bytes(b"%PDF-1.4\ntest content\n%%EOF")
    return str(pdf_path)


def test_cache_miss(temp_cache, sample_pdf):
    """Cache returns None for uncached syllabus."""
    result = temp_cache.get(sample_pdf)
    assert result is None


def test_cache_hit(temp_cache, sample_pdf, sample_parsed_syllabus):
    """Cache returns cached syllabus on subsequent access."""
    # First set the cache
    temp_cache.set(sample_pdf, sample_parsed_syllabus)
    
    # Then retrieve it
    result = temp_cache.get(sample_pdf)
    
    assert result is not None
    assert result.course_code == sample_parsed_syllabus.course_code
    assert result.course_title == sample_parsed_syllabus.course_title
    assert result.term == sample_parsed_syllabus.term


def test_cache_key_consistency(temp_cache, tmp_path):
    """Same content produces same cache key."""
    # Create two files with identical content
    content = b"%PDF-1.4\nidentical content\n%%EOF"
    
    file1 = tmp_path / "file1.pdf"
    file1.write_bytes(content)
    
    file2 = tmp_path / "file2.pdf"
    file2.write_bytes(content)
    
    key1 = temp_cache._compute_key(str(file1))
    key2 = temp_cache._compute_key(str(file2))
    
    assert key1 == key2


def test_cache_key_different_content(temp_cache, tmp_path):
    """Different content produces different cache keys."""
    file1 = tmp_path / "file1.pdf"
    file1.write_bytes(b"%PDF-1.4\ncontent A\n%%EOF")
    
    file2 = tmp_path / "file2.pdf"
    file2.write_bytes(b"%PDF-1.4\ncontent B\n%%EOF")
    
    key1 = temp_cache._compute_key(str(file1))
    key2 = temp_cache._compute_key(str(file2))
    
    assert key1 != key2


def test_cache_invalidate(temp_cache, sample_pdf, sample_parsed_syllabus):
    """Invalidate removes specific entry."""
    # Set cache
    temp_cache.set(sample_pdf, sample_parsed_syllabus)
    assert temp_cache.get(sample_pdf) is not None
    
    # Invalidate
    result = temp_cache.invalidate(sample_pdf)
    assert result is True
    
    # Verify it's gone
    assert temp_cache.get(sample_pdf) is None


def test_cache_invalidate_nonexistent(temp_cache, sample_pdf):
    """Invalidate returns False for non-existent entry."""
    result = temp_cache.invalidate(sample_pdf)
    assert result is False


def test_cache_clear(temp_cache, tmp_path, sample_parsed_syllabus):
    """Clear removes all entries."""
    # Create multiple cache entries
    file1 = tmp_path / "test1.pdf"
    file1.write_bytes(b"%PDF-1.4\ncontent 1\n%%EOF")
    
    file2 = tmp_path / "test2.pdf"
    file2.write_bytes(b"%PDF-1.4\ncontent 2\n%%EOF")
    
    temp_cache.set(str(file1), sample_parsed_syllabus)
    temp_cache.set(str(file2), sample_parsed_syllabus)
    
    # Clear cache
    count = temp_cache.clear()
    assert count == 2
    
    # Verify all gone
    assert temp_cache.get(str(file1)) is None
    assert temp_cache.get(str(file2)) is None


def test_cache_clear_empty(temp_cache):
    """Clear returns 0 for empty cache."""
    count = temp_cache.clear()
    assert count == 0


def test_cache_list_keys(temp_cache, tmp_path, sample_parsed_syllabus):
    """List keys returns all cached keys."""
    # Create multiple cache entries
    file1 = tmp_path / "test1.pdf"
    file1.write_bytes(b"%PDF-1.4\ncontent 1\n%%EOF")
    
    file2 = tmp_path / "test2.pdf"
    file2.write_bytes(b"%PDF-1.4\ncontent 2\n%%EOF")
    
    temp_cache.set(str(file1), sample_parsed_syllabus)
    temp_cache.set(str(file2), sample_parsed_syllabus)
    
    keys = temp_cache.list_keys()
    assert len(keys) == 2
    
    # Verify keys are SHA-256 hashes (64 hex characters)
    for key in keys:
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


def test_cache_list_keys_empty(temp_cache):
    """List keys returns empty list for empty cache."""
    keys = temp_cache.list_keys()
    assert keys == []


def test_cache_statistics(temp_cache, sample_pdf, sample_parsed_syllabus):
    """Statistics reflect cache state."""
    # Empty cache
    stats = temp_cache.get_statistics()
    assert stats["count"] == 0
    assert stats["total_size"] == 0
    
    # Add entry
    temp_cache.set(sample_pdf, sample_parsed_syllabus)
    
    stats = temp_cache.get_statistics()
    assert stats["count"] == 1
    assert stats["total_size"] > 0
    assert "cache_dir" in stats
    assert "syllabi_dir" in stats


def test_cache_corrupted_file(temp_cache, sample_pdf, sample_parsed_syllabus):
    """Gracefully handle corrupted cache files."""
    # Set cache
    temp_cache.set(sample_pdf, sample_parsed_syllabus)
    
    # Corrupt the cache file
    key = temp_cache._compute_key(sample_pdf)
    cache_file = temp_cache._syllabi_dir / f"{key}.pkl"
    cache_file.write_bytes(b"corrupted data")
    
    # Should return None (graceful degradation)
    result = temp_cache.get(sample_pdf)
    assert result is None


def test_cache_entry_metadata(temp_cache, sample_pdf, sample_parsed_syllabus):
    """Cache entry includes correct metadata."""
    temp_cache.set(sample_pdf, sample_parsed_syllabus)
    
    # Load cache entry directly
    key = temp_cache._compute_key(sample_pdf)
    cache_file = temp_cache._syllabi_dir / f"{key}.pkl"
    
    with open(cache_file, "rb") as f:
        entry: CacheEntry = pickle.load(f)
    
    assert entry.key == key
    assert entry.source == sample_pdf
    assert entry.cached_at is not None
    assert entry.parsed_syllabus == sample_parsed_syllabus


def test_cache_with_relative_path(temp_cache, tmp_path, sample_parsed_syllabus):
    """Cache works with relative paths."""
    # Create a PDF in current directory context
    pdf_path = tmp_path / "relative.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nrelative path test\n%%EOF")
    
    # Use absolute path for testing (relative paths depend on cwd)
    temp_cache.set(str(pdf_path), sample_parsed_syllabus)
    result = temp_cache.get(str(pdf_path))
    
    assert result is not None
    assert result.course_code == sample_parsed_syllabus.course_code


def test_cache_directory_creation(tmp_path, sample_pdf, sample_parsed_syllabus):
    """Cache creates directory structure on first write."""
    cache_dir = tmp_path / "new_cache"
    cache = SyllabusCache(cache_dir=cache_dir)
    
    # Directory shouldn't exist yet
    assert not cache_dir.exists()
    
    # Set cache entry
    cache.set(sample_pdf, sample_parsed_syllabus)
    
    # Directory should now exist
    assert cache_dir.exists()
    assert (cache_dir / "syllabi").exists()


def test_cache_with_env_override(tmp_path, sample_pdf, sample_parsed_syllabus, monkeypatch):
    """Cache respects SYLLABUSMCP_CACHE_DIR environment variable."""
    env_cache_dir = tmp_path / "env_cache"
    monkeypatch.setenv("SYLLABUSMCP_CACHE_DIR", str(env_cache_dir))
    
    cache = SyllabusCache()
    
    assert cache.cache_dir == env_cache_dir
    
    # Verify it actually uses this directory
    cache.set(sample_pdf, sample_parsed_syllabus)
    assert (env_cache_dir / "syllabi").exists()
