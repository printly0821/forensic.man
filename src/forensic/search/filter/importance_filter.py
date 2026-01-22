"""
Importance filter for search results

Provides importance-based filtering for evidence items.
"""

from typing import TypeVar

from forensic.models import Evidence
from forensic.search.models import SearchHit

T = TypeVar("T", Evidence, SearchHit, dict)

# Valid importance levels
IMPORTANCE_LEVELS = ("HIGH", "MEDIUM", "LOW")


class ImportanceFilter:
    """
    Importance-based filter for evidence and search results.

    Filters items based on importance levels (HIGH, MEDIUM, LOW).
    """

    def __init__(self) -> None:
        """Initialize the importance filter."""
        self._included_levels: set[str] = set()
        self._min_importance: str | None = None
        self._max_importance: str | None = None

    def set_levels(self, levels: list[str] | set[str]) -> None:
        """
        Set the importance levels to include.

        Args:
            levels: List of importance levels (HIGH, MEDIUM, LOW)
        """
        self._included_levels = set(levels)
        self._included_levels.intersection_update(IMPORTANCE_LEVELS)

    def set_min_importance(self, level: str) -> None:
        """
        Set minimum importance level (inclusive).

        Items with importance >= this level will be included.

        Args:
            level: Minimum importance level (LOW, MEDIUM, or HIGH)
        """
        if level in IMPORTANCE_LEVELS:
            self._min_importance = level

    def set_max_importance(self, level: str) -> None:
        """
        Set maximum importance level (inclusive).

        Items with importance <= this level will be included.

        Args:
            level: Maximum importance level (LOW, MEDIUM, or HIGH)
        """
        if level in IMPORTANCE_LEVELS:
            self._max_importance = level

    def set_range(self, min_level: str, max_level: str) -> None:
        """
        Set importance range.

        Args:
            min_level: Minimum importance level
            max_level: Maximum importance level
        """
        self.set_min_importance(min_level)
        self.set_max_importance(max_level)

    def filter(self, items: list[T]) -> list[T]:
        """
        Filter items by importance level.

        Args:
            items: List of items to filter

        Returns:
            Filtered items matching importance criteria
        """
        result: list[T] = []

        for item in items:
            importance = self._extract_importance(item)

            if importance is None:
                # If no importance, check if we should include
                if not self._included_levels and not self._min_importance:
                    result.append(item)
                continue

            # Check specific levels
            if self._included_levels and importance not in self._included_levels:
                continue

            # Check min importance
            if (
                self._min_importance
                and self._compare_importance(importance, self._min_importance) < 0
            ):
                continue

            # Check max importance
            if (
                self._max_importance
                and self._compare_importance(importance, self._max_importance) > 0
            ):
                continue

            result.append(item)

        return result

    def matches(self, item: T) -> bool:
        """
        Check if an item matches the importance filter.

        Args:
            item: Item to check

        Returns:
            True if item matches the filter
        """
        importance = self._extract_importance(item)

        if importance is None:
            return not self._included_levels and not self._min_importance

        if self._included_levels and importance not in self._included_levels:
            return False

        if self._min_importance and self._compare_importance(importance, self._min_importance) < 0:
            return False

        return not (
            self._max_importance and self._compare_importance(importance, self._max_importance) > 0
        )

    def clear(self) -> None:
        """Clear all importance filters."""
        self._included_levels.clear()
        self._min_importance = None
        self._max_importance = None

    def get_levels(self) -> set[str]:
        """
        Get the currently included importance levels.

        Returns:
            Set of included importance levels
        """
        return self._included_levels.copy()

    def _extract_importance(self, item: T) -> str | None:
        """Extract importance from an item."""
        if isinstance(item, Evidence):
            return item.importance
        elif isinstance(item, dict):
            return item.get("importance")
        elif isinstance(item, SearchHit):
            return item.metadata.get("importance")
        return None

    def _compare_importance(self, level1: str, level2: str) -> int:
        """
        Compare two importance levels.

        Args:
            level1: First importance level
            level2: Second importance level

        Returns:
            -1 if level1 < level2, 0 if equal, 1 if level1 > level2
        """
        order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

        v1 = order.get(level1, -1)
        v2 = order.get(level2, -1)

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        return 0


class HighImportanceFilter(ImportanceFilter):
    """
    Filter for high importance items only.

    Shortcut filter for commonly used HIGH importance filtering.
    """

    def __init__(self) -> None:
        """Initialize the high importance filter."""
        super().__init__()
        self.set_levels(["HIGH"])


class MediumHighImportanceFilter(ImportanceFilter):
    """
    Filter for medium and high importance items.

    Shortcut filter for MEDIUM and HIGH importance filtering.
    """

    def __init__(self) -> None:
        """Initialize the medium-high importance filter."""
        super().__init__()
        self.set_min_importance("MEDIUM")


__all__ = [
    "ImportanceFilter",
    "HighImportanceFilter",
    "MediumHighImportanceFilter",
]
