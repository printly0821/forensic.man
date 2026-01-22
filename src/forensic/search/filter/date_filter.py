"""
Date filter for search results

Provides date range filtering for transcripts and segments.
"""

from datetime import date, datetime
from typing import TypeVar

from forensic.models import Segment, Transcript
from forensic.search.models import SearchHit

T = TypeVar("T", Segment, Transcript, SearchHit, dict)


class DateFilter:
    """
    Date-based filter for search results.

    Filters items based on date ranges.
    """

    def __init__(self) -> None:
        """Initialize the date filter."""
        self._start_date: date | None = None
        self._end_date: date | None = None

    def set_range(
        self,
        start_date: date | str | None,
        end_date: date | str | None,
    ) -> None:
        """
        Set the date range for filtering.

        Args:
            start_date: Start date (inclusive) - date object or ISO string
            end_date: End date (inclusive) - date object or ISO string
        """
        self._start_date = self._parse_date(start_date) if start_date else None
        self._end_date = self._parse_date(end_date) if end_date else None

    def filter(
        self,
        items: list[T],
    ) -> list[T]:
        """
        Filter items by date range.

        Args:
            items: List of items to filter

        Returns:
            Filtered items within the date range
        """
        if self._start_date is None and self._end_date is None:
            return items

        result: list[T] = []

        for item in items:
            item_date = self._extract_date(item)

            if item_date is None:
                continue

            if self._start_date and item_date < self._start_date:
                continue

            if self._end_date and item_date > self._end_date:
                continue

            result.append(item)

        return result

    def is_in_range(
        self,
        item: T,
    ) -> bool:
        """
        Check if an item is within the configured date range.

        Args:
            item: Item to check

        Returns:
            True if item is within range
        """
        item_date = self._extract_date(item)

        if item_date is None:
            return False

        if self._start_date and item_date < self._start_date:
            return False

        return not (self._end_date and item_date > self._end_date)

    def clear(self) -> None:
        """Clear the date range filter."""
        self._start_date = None
        self._end_date = None

    def _extract_date(self, item: T) -> date | None:
        """Extract date from an item."""
        if isinstance(item, Transcript):
            return item.date.date()
        elif isinstance(item, Segment):
            # Segments don't have direct date info
            return None
        elif isinstance(item, SearchHit):
            if item.timestamp:
                return item.timestamp.date()
        elif isinstance(item, dict):
            if "timestamp" in item:
                ts = item["timestamp"]
                if isinstance(ts, datetime):
                    return ts.date()
            if "date" in item:
                d = item["date"]
                if isinstance(d, datetime):
                    return d.date()
                elif isinstance(d, date):
                    return d

        return None

    def _parse_date(self, date_input: date | str) -> date | None:
        """Parse date from various input formats."""
        if isinstance(date_input, date):
            return date_input

        if isinstance(date_input, str):
            try:
                # Try ISO format
                return date.fromisoformat(date_input)
            except ValueError:
                try:
                    # Try common formats
                    from datetime import datetime

                    dt = datetime.fromisoformat(date_input)
                    return dt.date()
                except ValueError:
                    pass

        return None


class RelativeDateFilter(DateFilter):
    """
    Date filter that supports relative date specifications.

    Supports "today", "yesterday", "last N days", etc.
    """

    def set_relative_range(
        self,
        start_offset: int | None,
        end_offset: int | None = None,
    ) -> None:
        """
        Set date range using day offsets from today.

        Args:
            start_offset: Days before today for start (negative = past)
            end_offset: Days before today for end (defaults to today)
        """
        today = date.today()

        start_date = today
        if start_offset is not None:
            from datetime import timedelta

            start_date = today + timedelta(days=start_offset)

        end_date = today
        if end_offset is not None:
            from datetime import timedelta

            end_date = today + timedelta(days=end_offset)

        self.set_range(start_date, end_date)

    def set_last_n_days(self, n: int) -> None:
        """
        Set range to the last N days from today.

        Args:
            n: Number of days
        """
        self.set_relative_range(start_offset=-n, end_offset=0)

    def set_date_range_from_strings(
        self,
        start: str | None,
        end: str | None,
    ) -> None:
        """
        Set date range from relative or absolute string specs.

        Supports:
        - "today", "yesterday", "tomorrow"
        - "last N days", "past N days"
        - ISO date strings (YYYY-MM-DD)

        Args:
            start: Start date spec
            end: End date spec
        """
        start_date = self._parse_date_spec(start) if start else None
        end_date = self._parse_date_spec(end) if end else None

        self.set_range(start_date, end_date)

    def _parse_date_spec(self, spec: str) -> date | None:
        """Parse date specification string."""
        spec_lower = spec.lower().strip()
        today = date.today()

        if spec_lower == "today":
            return today
        elif spec_lower == "yesterday":
            from datetime import timedelta

            return today - timedelta(days=1)
        elif spec_lower == "tomorrow":
            from datetime import timedelta

            return today + timedelta(days=1)
        elif spec_lower.startswith("last ") or spec_lower.startswith("past "):
            # "last 7 days" or "past 7 days"
            try:
                n = int(spec_lower.split()[1])
                from datetime import timedelta

                return today - timedelta(days=n)
            except (IndexError, ValueError):
                pass
        elif spec_lower.startswith("next "):
            # "next 7 days"
            try:
                n = int(spec_lower.split()[1])
                from datetime import timedelta

                return today + timedelta(days=n)
            except (IndexError, ValueError):
                pass

        # Try as regular date
        return self._parse_date(spec)


__all__ = [
    "DateFilter",
    "RelativeDateFilter",
]
