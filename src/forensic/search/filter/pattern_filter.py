"""
Pattern type filter for search results

Provides pattern type filtering for evidence items.
"""

from typing import TypeVar

from forensic.models import Evidence
from forensic.search.models import SearchHit

T = TypeVar("T", Evidence, SearchHit, dict)

# Common pattern types
PATTERN_TYPES = (
    "GASLIGHTING",
    "EMOTIONAL_MANIPULATION",
    "THREAT",
    "REPEATED_ABUSE",
    "DENIAL",
    "ISOLATION",
    "FINANCIAL_ABUSE",
    "OTHER",
)


class PatternFilter:
    """
    Pattern type filter for evidence and search results.

    Filters items based on pattern categories (GASLIGHTING, THREAT, etc.).
    """

    def __init__(self) -> None:
        """Initialize the pattern filter."""
        self._included_patterns: set[str] = set()
        self._excluded_patterns: set[str] = set()

    def include_patterns(self, patterns: list[str] | set[str]) -> None:
        """
        Set the pattern types to include.

        Args:
            patterns: List or set of pattern types to include
        """
        self._included_patterns = set(patterns)

    def exclude_patterns(self, patterns: list[str] | set[str]) -> None:
        """
        Set the pattern types to exclude.

        Args:
            patterns: List or set of pattern types to exclude
        """
        self._excluded_patterns = set(patterns)

    def add_pattern(self, pattern: str) -> None:
        """
        Add a pattern type to the inclusion list.

        Args:
            pattern: Pattern type to include
        """
        self._included_patterns.add(pattern.upper())

    def remove_pattern(self, pattern: str) -> None:
        """
        Remove a pattern type from the inclusion list.

        Args:
            pattern: Pattern type to remove
        """
        self._included_patterns.discard(pattern.upper())

    def exclude_pattern(self, pattern: str) -> None:
        """
        Add a pattern type to the exclusion list.

        Args:
            pattern: Pattern type to exclude
        """
        self._excluded_patterns.add(pattern.upper())

    def filter(self, items: list[T]) -> list[T]:
        """
        Filter items by pattern type.

        Args:
            items: List of items to filter

        Returns:
            Filtered items matching pattern criteria
        """
        result: list[T] = []

        for item in items:
            pattern = self._extract_pattern(item)

            if pattern is None:
                # Items without pattern are included only if no patterns specified
                if not self._included_patterns:
                    result.append(item)
                continue

            pattern_upper = pattern.upper()

            # Skip if pattern is excluded
            if pattern_upper in self._excluded_patterns:
                continue

            # Skip if included patterns are set and pattern is not included
            if self._included_patterns and pattern_upper not in self._included_patterns:
                continue

            result.append(item)

        return result

    def matches(self, item: T) -> bool:
        """
        Check if an item matches the pattern filter.

        Args:
            item: Item to check

        Returns:
            True if item matches the filter
        """
        pattern = self._extract_pattern(item)

        if pattern is None:
            return not self._included_patterns

        pattern_upper = pattern.upper()

        if pattern_upper in self._excluded_patterns:
            return False

        return not (self._included_patterns and pattern_upper not in self._included_patterns)

    def clear(self) -> None:
        """Clear all pattern filters."""
        self._included_patterns.clear()
        self._excluded_patterns.clear()

    def get_included_patterns(self) -> set[str]:
        """
        Get the currently included pattern types.

        Returns:
            Set of included pattern types
        """
        return self._included_patterns.copy()

    def get_excluded_patterns(self) -> set[str]:
        """
        Get the currently excluded pattern types.

        Returns:
            Set of excluded pattern types
        """
        return self._excluded_patterns.copy()

    def _extract_pattern(self, item: T) -> str | None:
        """Extract pattern type from an item."""
        if isinstance(item, Evidence):
            return str(item.category)
        elif isinstance(item, dict):
            return item.get("category") or item.get("pattern_type")
        elif isinstance(item, SearchHit):
            return item.metadata.get("category") or item.metadata.get("pattern_type")
        return None


class GaslightingFilter(PatternFilter):
    """
    Filter for gaslighting pattern only.

    Shortcut filter for gaslighting pattern detection.
    """

    def __init__(self) -> None:
        """Initialize the gaslighting filter."""
        super().__init__()
        self.add_pattern("GASLIGHTING")


class ThreatFilter(PatternFilter):
    """
    Filter for threat pattern only.

    Shortcut filter for threat pattern detection.
    """

    def __init__(self) -> None:
        """Initialize the threat filter."""
        super().__init__()
        self.add_pattern("THREAT")


class EmotionalManipulationFilter(PatternFilter):
    """
    Filter for emotional manipulation pattern only.

    Shortcut filter for emotional manipulation pattern detection.
    """

    def __init__(self) -> None:
        """Initialize the emotional manipulation filter."""
        super().__init__()
        self.add_pattern("EMOTIONAL_MANIPULATION")


class AbusePatternFilter(PatternFilter):
    """
    Combined filter for all abuse-related patterns.

    Includes GASLIGHTING, EMOTIONAL_MANIPULATION, THREAT, and REPEATED_ABUSE.
    """

    def __init__(self) -> None:
        """Initialize the abuse pattern filter."""
        super().__init__()
        for pattern in ["GASLIGHTING", "EMOTIONAL_MANIPULATION", "THREAT", "REPEATED_ABUSE"]:
            self.add_pattern(pattern)


__all__ = [
    "PatternFilter",
    "GaslightingFilter",
    "ThreatFilter",
    "EmotionalManipulationFilter",
    "AbusePatternFilter",
]
