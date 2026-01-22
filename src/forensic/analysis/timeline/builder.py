"""
Timeline builder for chronological transcript organization.
"""

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from forensic.analysis.timeline.models import Timeline, TimelineEvent
    from forensic.models.transcript import Transcript


class TimelineBuilder:
    """
    Builder for creating chronologically ordered timelines.

    Provides methods for adding transcripts, querying by date range,
    grouping by period, and extracting events.

    Usage:
        builder = TimelineBuilder("case-001")
        builder.add_transcript(transcript1)
        builder.add_transcript(transcript2)
        timeline = builder.build()
    """

    def __init__(self, timeline_id: str) -> None:
        """
        Initialize the timeline builder.

        Args:
            timeline_id: Unique identifier for this timeline
        """
        self.id: str = timeline_id
        self._transcripts: list[Transcript] = []
        self._events: list[TimelineEvent] = []

    def add_transcript(self, transcript: "Transcript") -> None:
        """
        Add a transcript to the timeline.

        Args:
            transcript: Transcript to add
        """
        self._transcripts.append(transcript)

        # Extract events from transcript
        from forensic.analysis.timeline.events import TimelineEvent as EventExtractor

        for event in EventExtractor.extract_from_transcript(transcript):
            self._events.append(event)

    def add_event(self, event: "TimelineEvent") -> None:
        """
        Add a custom event to the timeline.

        Args:
            event: Event to add
        """
        self._events.append(event)

    def build(self) -> "Timeline":
        """
        Build the timeline with all added transcripts and events.

        Returns:
            Constructed Timeline instance
        """
        from forensic.analysis.timeline.models import Timeline

        # Sort transcripts by date
        sorted_transcripts = sorted(
            self._transcripts, key=lambda t: t.date
        )

        # Calculate date range
        if sorted_transcripts:
            start_date = sorted_transcripts[0].date.date()
            end_date = sorted_transcripts[-1].date.date()
            total_duration = sum(t.duration_seconds for t in sorted_transcripts)
        else:
            start_date = date.today()
            end_date = date.today()
            total_duration = 0.0

        # Sort events by date
        sorted_events = sorted(
            self._events, key=lambda e: (e.date, e.time or datetime.min.time())
        )

        timeline = Timeline(
            id=self.id,
            start_date=start_date,
            end_date=end_date,
            transcripts=sorted_transcripts,
            total_duration=total_duration,
            file_count=len(sorted_transcripts),
            events=sorted_events,
        )

        return timeline

    def get_by_date(self, query_date: date) -> list["Transcript"]:
        """
        Get transcripts for a specific date.

        Args:
            query_date: Date to query

        Returns:
            List of transcripts for the specified date
        """
        return [
            t for t in self._transcripts
            if t.date.date() == query_date
        ]

    def get_by_range(
        self,
        start: date,
        end: date,
    ) -> list["Transcript"]:
        """
        Get transcripts within a date range (inclusive).

        Args:
            start: Start date
            end: End date

        Returns:
            List of transcripts within the range
        """
        return [
            t for t in self._transcripts
            if start <= t.date.date() <= end
        ]

    def group_by_period(
        self,
        period: Literal["day", "week", "month"] = "day",
    ) -> dict[str, list["Transcript"]]:
        """
        Group transcripts by time period.

        Args:
            period: Grouping period ("day", "week", or "month")

        Returns:
            Dictionary mapping period keys to transcript lists
        """


        if period == "day":
            return self._group_by_day()
        elif period == "week":
            return self._group_by_week()
        elif period == "month":
            return self._group_by_month()
        else:
            raise ValueError(f"Invalid period: {period}")

    def _group_by_day(self) -> dict[str, list["Transcript"]]:
        """Group transcripts by day."""
        groups: dict[str, list[Transcript]] = {}

        for transcript in self._transcripts:
            key = transcript.date.date().isoformat()
            if key not in groups:
                groups[key] = []
            groups[key].append(transcript)

        return groups

    def _group_by_week(self) -> dict[str, list["Transcript"]]:
        """Group transcripts by week."""
        groups: dict[str, list[Transcript]] = {}

        for transcript in self._transcripts:
            dt = transcript.date
            # Get Monday of the week
            monday = dt - timedelta(days=dt.weekday())
            key = f"{monday.year}-W{monday.isocalendar()[1]:02d}"
            if key not in groups:
                groups[key] = []
            groups[key].append(transcript)

        return groups

    def _group_by_month(self) -> dict[str, list["Transcript"]]:
        """Group transcripts by month."""
        groups: dict[str, list[Transcript]] = {}

        for transcript in self._transcripts:
            dt = transcript.date
            key = dt.strftime("%Y-%m")
            if key not in groups:
                groups[key] = []
            groups[key].append(transcript)

        return groups

    def extract_events(self) -> list["TimelineEvent"]:
        """
        Extract all events from the timeline.

        Returns:
            List of all timeline events, sorted by date
        """
        return sorted(
            self._events,
            key=lambda e: (e.date, e.time or datetime.min.time())
        )

    @property
    def transcript_count(self) -> int:
        """Get the number of transcripts added."""
        return len(self._transcripts)

    @property
    def event_count(self) -> int:
        """Get the number of events added."""
        return len(self._events)
