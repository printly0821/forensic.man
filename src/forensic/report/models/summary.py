from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from forensic.report.models.report import Report, ReportType


class AnalysisOverview(BaseModel):
    total_files: int
    total_duration: float
    date_range: tuple[date, date]
    total_speakers: int
    total_segments: int

    @property
    def duration_hours(self) -> float:
        return self.total_duration / 60

class KeyFinding(BaseModel):
    finding_id: str
    title: str
    description: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    supporting_evidence: list[str] = Field(default_factory=list)
    first_occurrence: date | None = None
    occurrence_count: int = 1

    @property
    def is_critical(self) -> bool:
        return self.severity == "CRITICAL"

    @property
    def is_high_severity(self) -> bool:
        return self.severity in ("CRITICAL", "HIGH")

class AnalysisStatistics(BaseModel):
    total_files: int
    total_duration_minutes: float
    total_segments: int
    total_evidence: int
    evidence_by_importance: dict[str, int] = Field(default_factory=dict)

    @property
    def high_importance_ratio(self) -> float:
        total = sum(self.evidence_by_importance.values())
        if total == 0:
            return 0.0
        return self.evidence_by_importance.get("HIGH", 0) / total

class PatternStatistics(BaseModel):
    total_patterns: int
    high_frequency_patterns: list[str] = Field(default_factory=list)
    most_common_pattern: str = ""

class SpeakerComparison(BaseModel):
    speakers: list[str]
    segment_counts: dict[str, int] = Field(default_factory=dict)
    evidence_involvement: dict[str, int] = Field(default_factory=dict)

    @property
    def dominant_speaker(self) -> str | None:
        if not self.segment_counts:
            return None
        return max(self.segment_counts, key=self.segment_counts.get)

class Recommendation(BaseModel):
    recommendation_id: str
    priority: Literal["URGENT", "HIGH", "MEDIUM", "LOW"]
    title: str
    description: str
    rationale: str

    @property
    def is_urgent(self) -> bool:
        return self.priority == "URGENT"

class SummaryReport(Report):
    analysis_overview: AnalysisOverview | None = None
    key_findings: list[KeyFinding] = Field(default_factory=list)
    statistics: AnalysisStatistics | None = None
    pattern_summary: PatternStatistics | None = None
    speaker_comparison: SpeakerComparison | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    conclusion: str = ""

    def __init__(self, **data: Any) -> None:
        if "report_type" not in data:
            data["report_type"] = ReportType.SUMMARY
        super().__init__(**data)

    @property
    def total_findings(self) -> int:
        return len(self.key_findings)

    @property
    def critical_finding_count(self) -> int:
        return sum(1 for f in self.key_findings if f.is_critical)
