"""Caching utilities for TWIZZY.

Provides caching for expensive operations like file reads and command execution.
"""
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry:
    """A single cache entry."""

    key: str
    value: Any
    created_at: float
    expires_at: float | None
    metadata: dict[str, Any]


class SimpleCache:
    """Simple in-memory cache with optional disk persistence."""

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float | None = 300,  # 5 minutes default
        persistent: bool = False,
        cache_dir: Path | None = None,
    ):
        """Initialize the cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live in seconds (None = no expiry)
            persistent: Whether to persist cache to disk
            cache_dir: Directory for persistent cache
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.persistent = persistent
        self.cache_dir = cache_dir or Path.home() / ".twizzy" / "cache"

        if persistent:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._cache: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

        if persistent:
            self._load_from_disk()

    def _make_key(self, *args, **kwargs) -> str:
        """Create a cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        # Check expiry
        if entry.expires_at is not None and time.time() > entry.expires_at:
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
            metadata: Optional metadata
        """
        now = time.time()
        expires = None

        if ttl is not None:
            expires = now + ttl
        elif self.default_ttl is not None:
            expires = now + self.default_ttl

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=expires,
            metadata=metadata or {},
        )

        self._cache[key] = entry

        # Evict oldest if over max size
        if len(self._cache) > self.max_size:
            self._evict_oldest()

        if self.persistent:
            self._save_to_disk()

    def get_or_compute(
        self,
        key: str,
        compute: Callable[[], T],
        ttl: float | None = None,
    ) -> T:
        """Get from cache or compute and cache the value.

        Args:
            key: Cache key
            compute: Function to compute the value if not cached
            ttl: Time-to-live in seconds

        Returns:
            The cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value

        value = compute()
        self.set(key, value, ttl)
        return value

    def invalidate(self, key: str) -> bool:
        """Remove a key from the cache.

        Args:
            key: Cache key

        Returns:
            True if key was in cache
        """
        if key in self._cache:
            del self._cache[key]
            if self.persistent:
                self._save_to_disk()
            return True
        return False

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        if self.persistent:
            self._save_to_disk()
        logger.info("Cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }

    def _evict_oldest(self) -> None:
        """Evict the oldest entries to make room."""
        # Remove 10% of entries
        to_remove = max(1, self.max_size // 10)
        sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].created_at)

        for key, _ in sorted_entries[:to_remove]:
            del self._cache[key]

    def _save_to_disk(self) -> None:
        """Save cache to disk."""
        cache_file = self.cache_dir / "cache.json"
        try:
            data = {
                key: {
                    "value": entry.value,
                    "created_at": entry.created_at,
                    "expires_at": entry.expires_at,
                    "metadata": entry.metadata,
                }
                for key, entry in self._cache.items()
                if entry.expires_at is None or time.time() < entry.expires_at
            }
            with open(cache_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        cache_file = self.cache_dir / "cache.json"
        if not cache_file.exists():
            return

        try:
            with open(cache_file) as f:
                data = json.load(f)

            now = time.time()
            for key, entry_data in data.items():
                # Skip expired entries
                expires_at = entry_data.get("expires_at")
                if expires_at is not None and now > expires_at:
                    continue

                self._cache[key] = CacheEntry(
                    key=key,
                    value=entry_data["value"],
                    created_at=entry_data["created_at"],
                    expires_at=expires_at,
                    metadata=entry_data.get("metadata", {}),
                )

            logger.info(f"Loaded {len(self._cache)} entries from cache")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")


class ToolCache:
    """Cache specifically for tool results."""

    def __init__(self):
        """Initialize tool cache with appropriate TTLs."""
        self.file_cache = SimpleCache(
            max_size=500,
            default_ttl=60,  # Files change often
            persistent=False,
        )
        self.command_cache = SimpleCache(
            max_size=200,
            default_ttl=30,  # Commands change frequently
            persistent=False,
        )
        self.app_cache = SimpleCache(
            max_size=100,
            default_ttl=300,  # Apps change less often
            persistent=True,
        )

    def get_file(self, path: str) -> Any | None:
        """Get cached file content."""
        return self.file_cache.get(f"file:{path}")

    def set_file(self, path: str, content: Any) -> None:
        """Cache file content."""
        self.file_cache.set(f"file:{path}", content)

    def get_command(self, command: str) -> Any | None:
        """Get cached command result."""
        return self.command_cache.get(f"cmd:{command}")

    def set_command(self, command: str, result: Any, ttl: float = 30) -> None:
        """Cache command result."""
        self.command_cache.set(f"cmd:{command}", result, ttl=ttl)

    def get_app_info(self, app_name: str) -> Any | None:
        """Get cached app info."""
        return self.app_cache.get(f"app:{app_name}")

    def set_app_info(self, app_name: str, info: Any) -> None:
        """Cache app info."""
        self.app_cache.set(f"app:{app_name}", info)

    def invalidate_file(self, path: str) -> None:
        """Invalidate a cached file."""
        self.file_cache.invalidate(f"file:{path}")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "file_cache": self.file_cache.get_stats(),
            "command_cache": self.command_cache.get_stats(),
            "app_cache": self.app_cache.get_stats(),
        }


# Global tool cache instance
_tool_cache: ToolCache | None = None


def get_tool_cache() -> ToolCache:
    """Get the global tool cache instance."""
    global _tool_cache
    if _tool_cache is None:
        _tool_cache = ToolCache()
    return _tool_cache
