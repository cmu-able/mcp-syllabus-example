# -*- coding: utf-8 -*-
"""
Caching layer for parsed syllabus data.

This module provides persistent caching of ParsedSyllabus objects to avoid
redundant PDF parsing and LLM API calls.
"""
from __future__ import annotations

import hashlib
import logging
import os
import pickle
import sys
import typing as t
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import ParsedSyllabus
from .pdf_utils import _load_pdf_path

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Metadata and data for a cached syllabus."""

    key: str  # SHA-256 hash of PDF bytes
    source: str  # Original path or URL
    cached_at: datetime  # When cached
    parsed_syllabus: ParsedSyllabus  # The cached data


def _get_default_cache_dir() -> Path:
    """Get platform-appropriate cache directory.

    Returns:
        Path to default cache directory based on platform
    """
    if os.name == "posix":  # macOS, Linux
        return Path.home() / ".cache" / "syllabusmcp"
    elif os.name == "nt":  # Windows
        local_app_data = os.getenv("LOCALAPPDATA", str(Path.home()))
        return Path(local_app_data) / "syllabusmcp" / "cache"
    else:
        return Path.home() / ".syllabusmcp_cache"


class SyllabusCache:
    """Manages caching of parsed syllabi.

    Provides persistent file-based caching using pickle serialization.
    Cache keys are SHA-256 hashes of raw PDF bytes for content-based caching.
    """

    def __init__(self, cache_dir: Path | None = None):
        """Initialize cache manager.

        Args:
            cache_dir: Cache directory path. If None, uses platform default.
        """
        if cache_dir is None:
            # Check for environment variable override
            env_cache_dir = os.getenv("SYLLABUSMCP_CACHE_DIR")
            if env_cache_dir:
                cache_dir = Path(env_cache_dir)
            else:
                cache_dir = _get_default_cache_dir()

        self.cache_dir = cache_dir
        self._syllabi_dir = cache_dir / "syllabi"

    def get(self, pdf_path_or_url: str) -> ParsedSyllabus | None:
        """Retrieve cached syllabus if available.

        Args:
            pdf_path_or_url: Path or URL to syllabus PDF

        Returns:
            Cached ParsedSyllabus or None if not cached or error occurred
        """
        try:
            key = self._compute_key(pdf_path_or_url)
            cache_file = self._syllabi_dir / f"{key}.pkl"

            if not cache_file.exists():
                logger.info(f"Cache MISS: {pdf_path_or_url} (key={key[:8]}...)")
                return None

            with open(cache_file, "rb") as f:
                entry: CacheEntry = pickle.load(f)

            logger.info(f"Cache HIT: {pdf_path_or_url} (key={key[:8]}...)")
            return entry.parsed_syllabus

        except Exception as e:
            # Graceful degradation - treat errors as cache miss
            logger.warning(f"Cache read error for {pdf_path_or_url}: {e}")
            print(f"Cache read error: {e}", file=sys.stderr)
            return None

    def set(self, pdf_path_or_url: str, parsed: ParsedSyllabus) -> None:
        """Cache a parsed syllabus.

        Args:
            pdf_path_or_url: Path or URL to syllabus PDF
            parsed: Parsed syllabus data to cache
        """
        try:
            key = self._compute_key(pdf_path_or_url)
            entry = CacheEntry(
                key=key,
                source=pdf_path_or_url,
                cached_at=datetime.now(),
                parsed_syllabus=parsed,
            )

            # Ensure directory exists
            self._syllabi_dir.mkdir(parents=True, exist_ok=True)

            cache_file = self._syllabi_dir / f"{key}.pkl"
            with open(cache_file, "wb") as f:
                pickle.dump(entry, f)

            logger.info(f"Cache SET: {pdf_path_or_url} (key={key[:8]}...)")

        except Exception as e:
            # Graceful degradation - caching is optional
            logger.warning(f"Cache write error for {pdf_path_or_url}: {e}")
            print(f"Cache write error: {e}", file=sys.stderr)

    def invalidate(self, pdf_path_or_url: str) -> bool:
        """Invalidate a specific cached syllabus.

        Args:
            pdf_path_or_url: Path or URL to syllabus PDF

        Returns:
            True if entry was found and removed, False otherwise
        """
        try:
            key = self._compute_key(pdf_path_or_url)
            cache_file = self._syllabi_dir / f"{key}.pkl"

            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Cache INVALIDATE: {pdf_path_or_url} (key={key[:8]}...)")
                return True

            return False

        except Exception as e:
            logger.warning(f"Cache invalidate error for {pdf_path_or_url}: {e}")
            print(f"Cache invalidate error: {e}", file=sys.stderr)
            return False

    def clear(self) -> int:
        """Clear all cached syllabi.

        Returns:
            Number of entries removed
        """
        try:
            if not self._syllabi_dir.exists():
                return 0

            cache_files = list(self._syllabi_dir.glob("*.pkl"))
            count = len(cache_files)

            for cache_file in cache_files:
                cache_file.unlink()

            logger.info(f"Cache CLEAR: removed {count} entries")
            return count

        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
            print(f"Cache clear error: {e}", file=sys.stderr)
            return 0

    def list_keys(self) -> list[str]:
        """List all cached syllabus keys.

        Returns:
            List of cache keys (SHA-256 hashes)
        """
        try:
            if not self._syllabi_dir.exists():
                return []

            cache_files = list(self._syllabi_dir.glob("*.pkl"))
            # Extract key from filename (remove .pkl extension)
            return [f.stem for f in cache_files]

        except Exception as e:
            logger.warning(f"Cache list_keys error: {e}")
            print(f"Cache list_keys error: {e}", file=sys.stderr)
            return []

    def get_statistics(self) -> dict[str, t.Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats:
            - count: number of cached entries
            - total_size: total size in bytes
            - cache_dir: cache directory path
            - syllabi_dir: syllabi subdirectory path
        """
        try:
            if not self._syllabi_dir.exists():
                return {
                    "count": 0,
                    "total_size": 0,
                    "cache_dir": str(self.cache_dir),
                    "syllabi_dir": str(self._syllabi_dir),
                }

            cache_files = list(self._syllabi_dir.glob("*.pkl"))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "count": len(cache_files),
                "total_size": total_size,
                "cache_dir": str(self.cache_dir),
                "syllabi_dir": str(self._syllabi_dir),
            }

        except Exception as e:
            logger.warning(f"Cache get_statistics error: {e}")
            print(f"Cache get_statistics error: {e}", file=sys.stderr)
            return {
                "count": 0,
                "total_size": 0,
                "cache_dir": str(self.cache_dir),
                "syllabi_dir": str(self._syllabi_dir),
            }

    def _compute_key(self, pdf_path_or_url: str) -> str:
        """Compute cache key from PDF content.

        Uses SHA-256 hash of raw PDF bytes for content-based caching.
        Same content produces same key regardless of filename or URL.

        Args:
            pdf_path_or_url: Path or URL to syllabus PDF

        Returns:
            SHA-256 hash of raw PDF bytes as hex string
        """
        # Get local file path (downloads if URL)
        local_path = _load_pdf_path(pdf_path_or_url)

        # Read raw PDF bytes
        with open(local_path, "rb") as f:
            pdf_bytes = f.read()

        # Compute SHA-256 hash
        return hashlib.sha256(pdf_bytes).hexdigest()
