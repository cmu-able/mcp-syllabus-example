# -*- coding: utf-8 -*-
"""
Integration tests for cache integration with parse_syllabus.
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from syllabus_server.cache import SyllabusCache
from syllabus_server.models import ParsedSyllabus, Policies


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "test_syllabus.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\ntest syllabus content\n%%EOF")
    return str(pdf_path)


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for parse_syllabus."""
    return {
        "course_code": "TEST-101",
        "course_title": "Introduction to Testing",
        "term": "Fall 2025",
        "timezone": "America/New_York",
        "sections": [],
        "assignments": [],
        "schedule": [],
        "policies": {},
    }


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Provide temporary cache directory and set environment variable."""
    cache_dir = tmp_path / "integration_cache"
    return cache_dir


def test_parse_syllabus_caches_result(sample_pdf, temp_cache_dir, mock_llm_response, monkeypatch):
    """parse_syllabus() caches result on first call."""
    # Set required environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SYLLABUSMCP_CACHE_DIR", str(temp_cache_dir))
    
    # Need to reimport to pick up env var
    import importlib
    import syllabus_server.server as server_module
    importlib.reload(server_module)
    
    # Mock the LLM call and PDF extraction
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = str(mock_llm_response).replace("'", '"')
    
    with patch.object(server_module.client.chat.completions, 'create', return_value=mock_completion), \
         patch('syllabus_server.server.extract_pdf_pages', return_value=["Test syllabus content"]):
        # First call - should parse and cache
        # Access the underlying function from the MCP tool
        result1 = server_module.parse_syllabus.fn(sample_pdf)
        
        assert result1 is not None
        assert result1.course_code == "TEST-101"
        
        # Verify cache was populated
        cache = SyllabusCache(cache_dir=temp_cache_dir)
        stats = cache.get_statistics()
        assert stats["count"] == 1


def test_parse_syllabus_uses_cache(sample_pdf, temp_cache_dir, monkeypatch):
    """parse_syllabus() returns cached result on second call without calling LLM."""
    # Set required environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SYLLABUSMCP_CACHE_DIR", str(temp_cache_dir))
    
    # Create a cached entry
    cache = SyllabusCache(cache_dir=temp_cache_dir)
    cached_syllabus = ParsedSyllabus(
        course_code="CACHED-101",
        course_title="Cached Course",
        term="Spring 2025",
        timezone="America/New_York",
        sections=[],
        assignments=[],
        schedule=[],
        policies=Policies(),
    )
    cache.set(sample_pdf, cached_syllabus)
    
    # Need to reimport to pick up env var
    import importlib
    import syllabus_server.server as server_module
    importlib.reload(server_module)
    
    # Mock the LLM call - this should NOT be called
    mock_completion = MagicMock()
    
    with patch.object(server_module.client.chat.completions, 'create', return_value=mock_completion) as mock_llm:
        # Call parse_syllabus
        # Access the underlying function from the MCP tool
        result = server_module.parse_syllabus.fn(sample_pdf)
        
        # Should return cached result
        assert result.course_code == "CACHED-101"
        assert result.course_title == "Cached Course"
        
        # LLM should NOT have been called
        mock_llm.assert_not_called()


def test_parse_syllabus_cache_disable_flag(sample_pdf, temp_cache_dir, mock_llm_response, monkeypatch):
    """use_cache=False bypasses cache."""
    # Set required environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SYLLABUSMCP_CACHE_DIR", str(temp_cache_dir))
    
    # Create a cached entry
    cache = SyllabusCache(cache_dir=temp_cache_dir)
    cached_syllabus = ParsedSyllabus(
        course_code="CACHED-101",
        course_title="Cached Course",
        term="Spring 2025",
        timezone="America/New_York",
        sections=[],
        assignments=[],
        schedule=[],
        policies=Policies(),
    )
    cache.set(sample_pdf, cached_syllabus)
    
    # Need to reimport to pick up env var
    import importlib
    import syllabus_server.server as server_module
    importlib.reload(server_module)
    
    # Mock the LLM call and PDF extraction
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = str(mock_llm_response).replace("'", '"')
    
    with patch.object(server_module.client.chat.completions, 'create', return_value=mock_completion) as mock_llm, \
         patch('syllabus_server.server.extract_pdf_pages', return_value=["Test syllabus content"]):
        # Call with use_cache=False
        # Access the underlying function from the MCP tool
        result = server_module.parse_syllabus.fn(sample_pdf, use_cache=False)
        
        # Should return fresh parse, not cached
        assert result.course_code == "TEST-101"  # From mock_llm_response
        
        # LLM should have been called
        mock_llm.assert_called_once()


def test_parse_syllabus_with_env_disable(sample_pdf, mock_llm_response, monkeypatch):
    """SYLLABUSMCP_DISABLE_CACHE env var disables caching."""
    # Set required environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SYLLABUSMCP_DISABLE_CACHE", "1")
    
    # Need to reimport to pick up env var
    import importlib
    import syllabus_server.server as server_module
    importlib.reload(server_module)
    
    # Verify cache is disabled
    assert server_module._cache is None or not server_module._cache_enabled
    
    # Mock the LLM call and PDF extraction
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = str(mock_llm_response).replace("'", '"')
    
    with patch.object(server_module.client.chat.completions, 'create', return_value=mock_completion) as mock_llm, \
         patch('syllabus_server.server.extract_pdf_pages', return_value=["Test syllabus content"]):
        # Call parse_syllabus
        # Access the underlying function from the MCP tool
        result = server_module.parse_syllabus.fn(sample_pdf)
        
        # Should work but use LLM (no cache)
        assert result.course_code == "TEST-101"
        mock_llm.assert_called_once()


def test_cache_survives_multiple_calls(sample_pdf, temp_cache_dir, monkeypatch):
    """Cache persists across multiple parse_syllabus calls."""
    # Set required environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SYLLABUSMCP_CACHE_DIR", str(temp_cache_dir))
    
    # Pre-populate cache
    cache = SyllabusCache(cache_dir=temp_cache_dir)
    cached_syllabus = ParsedSyllabus(
        course_code="PERSIST-101",
        course_title="Persistent Course",
        term="Fall 2025",
        timezone="America/New_York",
        sections=[],
        assignments=[],
        schedule=[],
        policies=Policies(),
    )
    cache.set(sample_pdf, cached_syllabus)
    
    # Need to reimport to pick up env var
    import importlib
    import syllabus_server.server as server_module
    importlib.reload(server_module)
    
    # Mock LLM
    mock_completion = MagicMock()
    
    with patch.object(server_module.client.chat.completions, 'create', return_value=mock_completion) as mock_llm:
        # Call multiple times
        # Access the underlying function from the MCP tool
        result1 = server_module.parse_syllabus.fn(sample_pdf)
        result2 = server_module.parse_syllabus.fn(sample_pdf)
        result3 = server_module.parse_syllabus.fn(sample_pdf)
        
        # All should return cached result
        assert result1.course_code == "PERSIST-101"
        assert result2.course_code == "PERSIST-101"
        assert result3.course_code == "PERSIST-101"
        
        # LLM should never be called
        mock_llm.assert_not_called()
