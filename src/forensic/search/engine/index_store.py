"""
Index storage and persistence

Handles saving and loading search indexes to/from disk.
"""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

from forensic.search.models import IndexStats


class IndexStore:
    """
    Stores and retrieves search indexes from disk.

    Supports both JSON and pickle formats for index persistence.
    """

    def __init__(
        self,
        index_path: Path | str | None = None,
        format: str = "pickle",
    ) -> None:
        """
        Initialize the index store.

        Args:
            index_path: Directory or file path for storing indexes
            format: Storage format ("pickle" or "json")
        """
        if isinstance(index_path, str):
            index_path = Path(index_path)

        self._index_path: Path | None = index_path
        self._format: str = format

        if self._index_path and not self._index_path.exists():
            self._index_path.mkdir(parents=True, exist_ok=True)

    def save_index(
        self,
        index: Any,
        stats: IndexStats,
        name: str = "default",
    ) -> Path:
        """
        Save an index to disk.

        Args:
            index: The index object to save (InvertedIndex or similar)
            stats: Index statistics
            name: Name for this index

        Returns:
            Path where the index was saved
        """
        if not self._index_path:
            raise RuntimeError("Index path not configured")

        # Prepare data
        data = {
            "name": name,
            "stats": stats.model_dump(mode="json"),
            "saved_at": datetime.now().isoformat(),
        }

        if self._format == "json":
            # For JSON, we need to serialize the index
            index_file = self._index_path / f"{name}.json"
            data["index"] = self._serialize_index_json(index)
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        else:  # pickle
            index_file = self._index_path / f"{name}.pkl"
            data["index"] = index
            with open(index_file, "wb") as f:
                pickle.dump(data, f)

        return index_file

    def load_index(
        self,
        name: str = "default",
    ) -> tuple[Any, IndexStats]:
        """
        Load an index from disk.

        Args:
            name: Name of the index to load

        Returns:
            Tuple of (index, stats)
        """
        if not self._index_path:
            raise RuntimeError("Index path not configured")

        if self._format == "json":
            index_file = self._index_path / f"{name}.json"
            if not index_file.exists():
                raise FileNotFoundError(f"Index not found: {index_file}")

            with open(index_file, encoding="utf-8") as f:
                data = json.load(f)

            stats = IndexStats(**data["stats"])
            index = self._deserialize_index_json(data.get("index", {}))

        else:  # pickle
            index_file = self._index_path / f"{name}.pkl"
            if not index_file.exists():
                raise FileNotFoundError(f"Index not found: {index_file}")

            with open(index_file, "rb") as f:
                data = pickle.load(f)

            stats = data["stats"]
            index = data["index"]

        return index, stats

    def index_exists(self, name: str = "default") -> bool:
        """
        Check if an index exists on disk.

        Args:
            name: Name of the index

        Returns:
            True if the index file exists
        """
        if not self._index_path:
            return False

        if self._format == "json":
            index_file = self._index_path / f"{name}.json"
        else:
            index_file = self._index_path / f"{name}.pkl"

        return index_file.exists()

    def delete_index(self, name: str = "default") -> bool:
        """
        Delete an index from disk.

        Args:
            name: Name of the index to delete

        Returns:
            True if the index was deleted
        """
        if not self._index_path:
            return False

        if self._format == "json":
            index_file = self._index_path / f"{name}.json"
        else:
            index_file = self._index_path / f"{name}.pkl"

        if index_file.exists():
            index_file.unlink()
            return True

        return False

    def list_indexes(self) -> list[str]:
        """
        List all available indexes.

        Returns:
            List of index names
        """
        if not self._index_path or not self._index_path.exists():
            return []

        ext = ".json" if self._format == "json" else ".pkl"
        indexes = [f.stem for f in self._index_path.glob(f"*{ext}") if f.is_file()]

        return indexes

    def get_stats(self, name: str = "default") -> IndexStats | None:
        """
        Get statistics for a stored index without loading it.

        Args:
            name: Name of the index

        Returns:
            IndexStats if available, None otherwise
        """
        if not self._index_path:
            return None

        try:
            if self._format == "json":
                index_file = self._index_path / f"{name}.json"
                if not index_file.exists():
                    return None

                with open(index_file, encoding="utf-8") as f:
                    data = json.load(f)

                return IndexStats(**data.get("stats", {}))

            else:  # pickle
                # For pickle, we need to load the whole file
                index, stats = self.load_index(name)
                return stats

        except Exception:
            return None

    def _serialize_index_json(self, index: Any) -> dict[str, Any]:
        """
        Serialize index to JSON-compatible format.

        Args:
            index: Index object to serialize

        Returns:
            JSON-compatible dictionary
        """
        result: dict[str, Any] = {
            "terms": {},
            "metadata": {},
        }

        # Try to extract index data
        if hasattr(index, "_entries"):
            for term, entry in index._entries.items():
                result["terms"][term] = {
                    "document_ids": list(entry.document_ids),
                    "segment_ids": list(entry.segment_ids),
                    "evidence_ids": list(entry.evidence_ids),
                    "frequency": entry.frequency,
                }

        if hasattr(index, "_total_docs"):
            result["metadata"]["total_docs"] = index._total_docs
        if hasattr(index, "_total_segments"):
            result["metadata"]["total_segments"] = index._total_segments

        return result

    def _deserialize_index_json(self, data: dict[str, Any]) -> Any:
        """
        Deserialize index from JSON format.

        Args:
            data: JSON dictionary

        Returns:
            Reconstructed index object
        """
        from forensic.search.engine.index_builder import IndexEntry, InvertedIndex

        index = InvertedIndex()

        terms = data.get("terms", {})
        for term, term_data in terms.items():
            entry = IndexEntry(term)
            entry.document_ids = set(term_data.get("document_ids", []))
            entry.segment_ids = set(term_data.get("segment_ids", []))
            entry.evidence_ids = set(term_data.get("evidence_ids", []))
            entry.frequency = term_data.get("frequency", 0)
            index._entries[term] = entry

        metadata = data.get("metadata", {})
        index._total_docs = metadata.get("total_docs", 0)
        index._total_segments = metadata.get("total_segments", 0)

        return index


class IndexCache:
    """
    In-memory cache for frequently used indexes.
    """

    def __init__(self, max_size: int = 5) -> None:
        """
        Initialize the index cache.

        Args:
            max_size: Maximum number of indexes to cache
        """
        self._cache: dict[str, tuple[Any, IndexStats]] = {}
        self._access_times: dict[str, datetime] = {}
        self._max_size: int = max_size

    def get(self, name: str) -> tuple[Any, IndexStats] | None:
        """
        Get an index from the cache.

        Args:
            name: Name of the index

        Returns:
            Tuple of (index, stats) if cached, None otherwise
        """
        if name in self._cache:
            self._access_times[name] = datetime.now()
            return self._cache[name]

        return None

    def put(self, name: str, index: Any, stats: IndexStats) -> None:
        """
        Put an index in the cache.

        Args:
            name: Name of the index
            index: The index object
            stats: Index statistics
        """
        # Evict if at capacity
        if len(self._cache) >= self._max_size and name not in self._cache:
            self._evict_lru()

        self._cache[name] = (index, stats)
        self._access_times[name] = datetime.now()

    def remove(self, name: str) -> bool:
        """
        Remove an index from the cache.

        Args:
            name: Name of the index

        Returns:
            True if the index was removed
        """
        if name in self._cache:
            del self._cache[name]
            del self._access_times[name]
            return True

        return False

    def clear(self) -> None:
        """Clear all cached indexes."""
        self._cache.clear()
        self._access_times.clear()

    def _evict_lru(self) -> None:
        """Evict the least recently used index from the cache."""
        if not self._access_times:
            return

        # Find LRU
        lru_name = min(self._access_times, key=lambda k: self._access_times[k])
        self.remove(lru_name)

    @property
    def size(self) -> int:
        """Get number of cached indexes."""
        return len(self._cache)


__all__ = [
    "IndexStore",
    "IndexCache",
]
