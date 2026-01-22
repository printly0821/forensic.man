"""
Filter engine for search results

Provides the main FilterEngine class for applying filters
to search results based on various criteria.
"""

from datetime import date, datetime
from typing import Any, TypeVar

from forensic.models import Evidence, Segment, Transcript
from forensic.search.models import FilterConfig, FilterLogicalOperator

T = TypeVar("T", Segment, Evidence, Transcript, dict)


class FilterEngine:
    """
    Main filter engine for search results.

    Applies various filters to segments, evidence, and transcripts.
    """

    def __init__(self) -> None:
        """Initialize the filter engine."""
        self._active_config: FilterConfig = FilterConfig()

    def apply_filters(
        self,
        items: list[T],
        config: FilterConfig,
    ) -> list[T]:
        """
        Apply all filters from config to items.

        Args:
            items: List of items to filter
            config: Filter configuration

        Returns:
            Filtered list of items
        """
        if not config.has_filters:
            return items

        result = items

        # Apply date range filter
        if config.date_range:
            result = self.filter_by_date_range(
                result,  # type: ignore
                config.date_range[0],
                config.date_range[1],
            )

        # Apply speaker filter
        if config.speakers:
            result = self.filter_by_speakers(result, config.speakers)  # type: ignore

        # Apply importance filter
        if config.importance:
            result = self.filter_by_importance(result, config.importance)  # type: ignore

        # Apply pattern type filter
        if config.pattern_types:
            result = self.filter_by_pattern_types(result, config.pattern_types)  # type: ignore

        # Apply time range filter
        if config.time_range:
            result = self.filter_by_time_range(
                result,  # type: ignore
                config.time_range[0],
                config.time_range[1],
            )

        # Apply category filter
        if config.categories:
            result = self.filter_by_categories(result, config.categories)  # type: ignore

        # Apply transcript ID filter
        if config.transcript_ids:
            result = self.filter_by_transcript_ids(result, config.transcript_ids)  # type: ignore

        # Apply confidence filter
        if config.confidence_min > 0 or config.confidence_max < 1.0:
            result = self.filter_by_confidence(
                result,  # type: ignore
                config.confidence_min,
                config.confidence_max,
            )

        # Apply duration filter
        if config.duration_min > 0 or config.duration_max < float("inf"):
            result = self.filter_by_duration(
                result,  # type: ignore
                config.duration_min,
                config.duration_max,
            )

        return result

    def filter_by_date_range(
        self,
        items: list[T],
        start_date: date,
        end_date: date,
    ) -> list[T]:
        """
        Filter items by date range.

        Args:
            items: List of items to filter
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Filtered items
        """
        result: list[T] = []

        for item in items:
            item_date = self._extract_date(item)
            if item_date and start_date <= item_date <= end_date:
                result.append(item)

        return result

    def filter_by_speakers(
        self,
        items: list[T],
        speakers: list[str],
    ) -> list[T]:
        """
        Filter items by speaker IDs.

        Args:
            items: List of items to filter
            speakers: List of speaker IDs to include

        Returns:
            Filtered items
        """
        speaker_set = set(speakers)
        result: list[T] = []

        for item in items:
            speaker = self._extract_speaker(item)
            if speaker in speaker_set:
                result.append(item)

        return result

    def filter_by_importance(
        self,
        items: list[T],
        importance_levels: list[str],
    ) -> list[T]:
        """
        Filter items by importance levels.

        Args:
            items: List of items to filter (evidence)
            importance_levels: List of importance levels to include

        Returns:
            Filtered items
        """
        importance_set = set(importance_levels)
        result: list[T] = []

        for item in items:
            importance = self._extract_importance(item)
            if importance in importance_set:
                result.append(item)

        return result

    def filter_by_pattern_types(
        self,
        items: list[T],
        pattern_types: list[str],
    ) -> list[T]:
        """
        Filter items by pattern types.

        Args:
            items: List of items to filter (evidence)
            pattern_types: List of pattern types to include

        Returns:
            Filtered items
        """
        pattern_set = set(pattern_types)
        result: list[T] = []

        for item in items:
            pattern_type = self._extract_pattern_type(item)
            if pattern_type in pattern_set:
                result.append(item)

        return result

    def filter_by_time_range(
        self,
        items: list[T],
        start_time: float,
        end_time: float,
    ) -> list[T]:
        """
        Filter segments by time range within recording.

        Args:
            items: List of segments to filter
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Filtered segments
        """
        result: list[T] = []

        for item in items:
            if (
                isinstance(item, Segment)
                and item.end_time > start_time
                and item.start_time < end_time
            ):
                # Check if segment overlaps with time range
                result.append(item)  # type: ignore

        return result

    def filter_by_categories(
        self,
        items: list[T],
        categories: list[str],
    ) -> list[T]:
        """
        Filter items by evidence categories.

        Args:
            items: List of items to filter (evidence)
            categories: List of categories to include

        Returns:
            Filtered items
        """
        category_set = set(categories)
        result: list[T] = []

        for item in items:
            category = self._extract_category(item)
            if category in category_set:
                result.append(item)

        return result

    def filter_by_transcript_ids(
        self,
        items: list[T],
        transcript_ids: list[str],
    ) -> list[T]:
        """
        Filter items by transcript IDs.

        Args:
            items: List of items to filter
            transcript_ids: List of transcript IDs to include

        Returns:
            Filtered items
        """
        id_set = set(transcript_ids)
        result: list[T] = []

        for item in items:
            transcript_id = self._extract_transcript_id(item)
            if transcript_id in id_set:
                result.append(item)

        return result

    def filter_by_confidence(
        self,
        items: list[T],
        min_confidence: float,
        max_confidence: float,
    ) -> list[T]:
        """
        Filter items by confidence range.

        Args:
            items: List of items to filter
            min_confidence: Minimum confidence (inclusive)
            max_confidence: Maximum confidence (inclusive)

        Returns:
            Filtered items
        """
        result: list[T] = []

        for item in items:
            confidence = self._extract_confidence(item)
            if confidence is not None and min_confidence <= confidence <= max_confidence:
                result.append(item)

        return result

    def filter_by_duration(
        self,
        items: list[T],
        min_duration: float,
        max_duration: float,
    ) -> list[T]:
        """
        Filter items by duration.

        Args:
            items: List of items to filter
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds

        Returns:
            Filtered items
        """
        result: list[T] = []

        for item in items:
            duration = self._extract_duration(item)
            if duration is not None and min_duration <= duration <= max_duration:
                result.append(item)

        return result

    def clear_filters(self) -> None:
        """Clear all active filters."""
        self._active_config = FilterConfig()

    def _extract_date(self, item: T) -> date | None:
        """Extract date from item if available."""
        if isinstance(item, Transcript):
            return item.date.date()
        elif isinstance(item, dict):
            if "timestamp" in item and isinstance(item["timestamp"], datetime):
                return item["timestamp"].date()
            if "date" in item:
                return item["date"]
        return None

    def _extract_speaker(self, item: T) -> str | None:
        """Extract speaker from item if available."""
        if isinstance(item, Segment):
            return item.speaker
        elif isinstance(item, dict):
            return item.get("speaker")
        return None

    def _extract_importance(self, item: T) -> str | None:
        """Extract importance from item if available."""
        if isinstance(item, Evidence):
            return item.importance
        elif isinstance(item, dict):
            return item.get("importance")
        return None

    def _extract_pattern_type(self, item: T) -> str | None:
        """Extract pattern type from item if available."""
        if isinstance(item, Evidence):
            return str(item.category)
        elif isinstance(item, dict):
            return item.get("category") or item.get("pattern_type")
        return None

    def _extract_category(self, item: T) -> str | None:
        """Extract category from item if available."""
        if isinstance(item, Evidence):
            return str(item.category)
        elif isinstance(item, dict):
            return item.get("category")
        return None

    def _extract_transcript_id(self, item: T) -> str | None:
        """Extract transcript ID from item if available."""
        if isinstance(item, (Segment, Evidence)):
            return item.transcript_id
        elif isinstance(item, Transcript):
            return item.id
        elif isinstance(item, dict):
            return item.get("transcript_id") or item.get("id")
        return None

    def _extract_confidence(self, item: T) -> float | None:
        """Extract confidence from item if available."""
        if isinstance(item, Segment):
            return item.confidence
        elif isinstance(item, dict):
            return item.get("confidence")
        return None

    def _extract_duration(self, item: T) -> float | None:
        """Extract duration from item if available."""
        if isinstance(item, Segment):
            return item.duration
        elif isinstance(item, Transcript):
            return item.duration_seconds
        elif isinstance(item, dict):
            return item.get("duration") or item.get("duration_seconds")
        return None


class CompositeFilter:
    """
    Composite filter for combining multiple filters with logical operators.

    Supports AND, OR, and NOT logical operations.
    """

    def __init__(
        self,
        operator: FilterLogicalOperator = FilterLogicalOperator.AND,
    ) -> None:
        """
        Initialize the composite filter.

        Args:
            operator: Logical operator for combining filters
        """
        self._operator = operator
        self._filters: list[Any] = []

    def add_filter(self, filter_config: FilterConfig) -> None:
        """
        Add a filter to this composite filter.

        Args:
            filter_config: Filter configuration to add
        """
        self._filters.append(filter_config)

    def apply(
        self,
        items: list[T],
        engine: FilterEngine,
    ) -> list[T]:
        """
        Apply all filters with the configured operator.

        Args:
            items: List of items to filter
            engine: Filter engine to use

        Returns:
            Filtered items
        """
        if not self._filters:
            return items

        if self._operator == FilterLogicalOperator.AND:
            result = items
            for filter_config in self._filters:
                result = engine.apply_filters(result, filter_config)
            return result

        elif self._operator == FilterLogicalOperator.OR:
            # Collect items that match any filter
            seen = set()
            result: list[T] = []

            for filter_config in self._filters:
                filtered = engine.apply_filters(items, filter_config)
                for item in filtered:
                    item_id = self._get_item_id(item)
                    if item_id not in seen:
                        seen.add(item_id)
                        result.append(item)

            return result

        elif self._operator == FilterLogicalOperator.NOT:
            # Exclude items that match any filter
            excluded_ids = set()

            for filter_config in self._filters:
                filtered = engine.apply_filters(items, filter_config)
                for item in filtered:
                    excluded_ids.add(self._get_item_id(item))

            return [item for item in items if self._get_item_id(item) not in excluded_ids]

        return items

    def _get_item_id(self, item: T) -> str:
        """Get unique ID for an item."""
        if isinstance(item, (Segment, Evidence, Transcript)):
            return item.id
        elif isinstance(item, dict):
            return str(item.get("id", str(id(item))))
        return str(id(item))


__all__ = [
    "FilterEngine",
    "CompositeFilter",
]
