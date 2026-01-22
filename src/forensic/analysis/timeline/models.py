"""
Timeline data models for temporal transcript analysis.
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Timeline(BaseModel):
    """
    Timeline model for chronological transcript organization.
    """

    model_config = ConfigDict(
        defer_build=False,
        arbitrary_types_allowed=True,
    )

    id: str
    start_date: date
    end_date: date
    transcripts: list[Any] = Field(default_factory=list)
    events: list[Any] = Field(default_factory=list)
    total_duration: float = Field(default=0, ge=0)
    file_count: int = Field(default=0, ge=0)

    def add_event(self, event: "TimelineEvent") -> None:
        """Add an event to the timeline."""
        self.events.append(event)

    def get_events_by_importance(self, importance: str) -> list["TimelineEvent"]:
        """Get events filtered by importance level."""
        return [e for e in self.events if e.importance == importance]

    def get_high_importance_events(self) -> list["TimelineEvent"]:
        """Get all high importance events."""
        return self.get_events_by_importance("HIGH")

    @property
    def duration_minutes(self) -> float:
        """Total duration in minutes."""
        return self.total_duration / 60

    @property
    def duration_hours(self) -> float:
        """Total duration in hours."""
        return self.total_duration / 3600

    @property
    def day_count(self) -> int:
        """Number of unique days with recordings."""
        return (self.end_date - self.start_date).days + 1


class TimelineEvent(BaseModel):
    """
    Event marker for significant occurrences in transcripts.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    id: str
    date: date
    event_type: str
    description: str
    related_transcripts: list[str] = Field(default_factory=list)
    importance: str = Field(default="MEDIUM")
    time_value: str | None = Field(default=None)

    @property
    def time(self) -> str | None:
        """Get event time."""
        return self.time_value

    def is_high_importance(self) -> bool:
        """Check if event is high importance."""
        return self.importance == "HIGH"

    def is_medium_importance(self) -> bool:
        """Check if event is medium importance."""
        return self.importance == "MEDIUM"

    def is_low_importance(self) -> bool:
        """Check if event is low importance."""
        return self.importance == "LOW"
