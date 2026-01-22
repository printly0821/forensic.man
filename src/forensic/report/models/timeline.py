from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from forensic.report.models.report import Report, ReportType


class TimelineEventSummary(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: str
    description: str
    speaker: str = ""
    importance: str = "MEDIUM"
    evidence_ids: list[str] = Field(default_factory=list)
    is_key_event: bool = False
    order: int = 0

    @property
    def date(self) -> date:
        return self.timestamp.date()

class PatternOccurrenceSummary(BaseModel):
    pattern_id: str
    pattern_name: str
    pattern_type: str
    first_occurrence: date
    last_occurrence: date
    total_occurrences: int
    severity: str = "MEDIUM"
    speaker: str = ""

    @property
    def duration_days(self) -> int:
        return (self.last_occurrence - self.first_occurrence).days

    @property
    def is_high_frequency(self) -> bool:
        return self.total_occurrences >= 5

class SpeakerActivitySummary(BaseModel):
    speaker: str
    segment_count: int = 0
    total_duration: float = 0.0

    @property
    def duration_minutes(self) -> float:
        return self.total_duration / 60

class MonthlySummary(BaseModel):
    year: int
    month: int
    total_events: int = 0
    key_events: int = 0

    @property
    def month_name(self) -> str:
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        return months[self.month - 1]

class TimelineReport(Report):
    total_events: int = 0
    events: list[TimelineEventSummary] = Field(default_factory=list)
    pattern_occurrences: list[PatternOccurrenceSummary] = Field(default_factory=list)
    speaker_activities: dict[str, SpeakerActivitySummary] = Field(default_factory=dict)
    key_events: list[str] = Field(default_factory=list)
    monthly_summaries: dict[str, MonthlySummary] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        if "report_type" not in data:
            data["report_type"] = ReportType.TIMELINE
        super().__init__(**data)

    @property
    def total_speakers(self) -> int:
        return len(self.speaker_activities)

    @property
    def total_patterns(self) -> int:
        return len(self.pattern_occurrences)
