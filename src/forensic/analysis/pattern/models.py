"""
Pattern detection data models.
"""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class GaslightingPattern(BaseModel):
    """
    Gaslighting manipulation pattern detection result.

    Gaslighting is a form of psychological manipulation where the abuser
    makes the victim question their own perception of reality.

    Attributes:
        id: Unique pattern identifier
        pattern_type: Specific type of gaslighting detected
        segment_ids: IDs of related transcript segments
        speaker: Speaker who exhibited the pattern
        target: Target of the gaslighting (if identifiable)
        content_sample: Representative quote from the pattern
        confidence: Detection confidence score (0.0-1.0)
        context_before: Text context before the pattern
        context_after: Text context after the pattern
        occurrence_count: Number of times this pattern occurred
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    pattern_type: Literal[
        "DENIAL",  # 부정 ("그런 적 없어")
        "TRIVIALIZING",  # 축소 ("별거 아니야")
        "DIVERTING",  # 화제 전환
        "COUNTERING",  # 기억 왜곡 ("네가 잘못 기억해")
        "BLOCKING",  # 차단/회피
        "FORGETTING",  # 망각 주장
        "WITHHOLDING",  # 정보 차단
    ] = Field(description="Type of gaslighting pattern")
    segment_ids: list[str] = Field(default_factory=list, description="Related segment IDs")
    speaker: str = Field(description="Speaker who exhibited the pattern")
    target: str = Field(default="", description="Target of the gaslighting")
    content_sample: str = Field(description="Representative quote")
    confidence: float = Field(default=0.5, ge=0, le=1, description="Detection confidence")
    context_before: str = Field(default="", description="Context before the pattern")
    context_after: str = Field(default="", description="Context after the pattern")
    occurrence_count: int = Field(default=1, ge=1, description="Number of occurrences")

    def is_high_confidence(self) -> bool:
        """Check if detection has high confidence."""
        return self.confidence >= 0.7

    def get_importance(self) -> str:
        """Get importance level based on occurrence count."""
        if self.occurrence_count >= 3:
            return "HIGH"
        elif self.occurrence_count >= 2:
            return "MEDIUM"
        return "LOW"


class ThreatPattern(BaseModel):
    """
    Threat and coercion pattern detection result.

    Detects explicit and implicit threats used for control.

    Attributes:
        id: Unique pattern identifier
        threat_type: Category of threat
        segment_ids: IDs of related transcript segments
        speaker: Speaker who made the threat
        content_sample: Representative quote from the threat
        severity: Threat severity level
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    threat_type: Literal[
        "EXPLICIT_THREAT",  # 명시적 위협
        "IMPLICIT_THREAT",  # 암시적 위협
        "FINANCIAL_THREAT",  # 경제적 압박
        "SOCIAL_THREAT",  # 사회적 위협 (관계 단절 등)
        "LEGAL_THREAT",  # 법적 위협
    ] = Field(description="Category of threat")
    segment_ids: list[str] = Field(default_factory=list, description="Related segment IDs")
    speaker: str = Field(description="Speaker who made the threat")
    content_sample: str = Field(description="Representative quote")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        default="MEDIUM", description="Threat severity"
    )

    def is_critical(self) -> bool:
        """Check if threat is critical severity."""
        return self.severity == "CRITICAL"

    def is_high_severity(self) -> bool:
        """Check if threat is high or critical severity."""
        return self.severity in ("CRITICAL", "HIGH")


class StatementOccurrence(BaseModel):
    """
    Single occurrence of a repeated statement.

    Attributes:
        segment_id: ID of the segment containing the statement
        timestamp: When the statement was made
        speaker: Who made the statement
        content: The actual content of this occurrence
    """

    segment_id: str
    timestamp: datetime
    speaker: str
    content: str


class RepeatedStatement(BaseModel):
    """
    Pattern of repeated statements across time.

    Tracks statements that are made multiple times, which can
    indicate controlling behavior or obsession.

    Attributes:
        id: Unique pattern identifier
        pattern: Normalized form of the repeated pattern
        occurrences: List of when this statement occurred
        speaker: Speaker who made the statements
        total_count: Total number of repetitions
        first_occurrence: When the statement first appeared
        last_occurrence: When the statement most recently appeared
        time_span_days: Duration over which repetitions occurred
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    pattern: str = Field(description="Normalized repeated pattern")
    occurrences: list[StatementOccurrence] = Field(
        default_factory=list, description="List of occurrences"
    )
    speaker: str = Field(description="Speaker who made the statements")
    total_count: int = Field(default=1, ge=1, description="Total repetitions")
    first_occurrence: datetime = Field(description="First occurrence timestamp")
    last_occurrence: datetime = Field(description="Most recent occurrence")
    time_span_days: int = Field(default=0, ge=0, description="Time span in days")

    def add_occurrence(self, occurrence: StatementOccurrence) -> None:
        """Add a new occurrence to this pattern."""
        self.occurrences.append(occurrence)
        self.total_count = len(self.occurrences)

        timestamps = [occ.timestamp for occ in self.occurrences]
        self.first_occurrence = min(timestamps)
        self.last_occurrence = max(timestamps)

        delta = self.last_occurrence - self.first_occurrence
        self.time_span_days = delta.days

    @property
    def average_frequency_days(self) -> float:
        """Calculate average days between occurrences."""
        if self.total_count <= 1 or self.time_span_days == 0:
            return 0.0
        return self.time_span_days / (self.total_count - 1)


class EmotionalManipulation(BaseModel):
    """
    Emotional manipulation pattern detection result.

    Detects various forms of emotional coercion and control tactics.

    Attributes:
        id: Unique pattern identifier
        manipulation_type: Category of emotional manipulation
        segment_ids: IDs of related transcript segments
        speaker: Speaker who used the manipulation
        content_sample: Representative quote from the manipulation
        intensity: Intensity level of the manipulation
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    manipulation_type: Literal[
        "GUILT_TRIPPING",  # 죄책감 유발
        "SHAMING",  # 수치심 유발
        "FEAR_INDUCING",  # 공포 유발
        "LOVE_BOMBING",  # 과도한 애정 표현
        "SILENT_TREATMENT",  # 침묵/무시
        "VICTIMHOOD",  # 피해자 역할
    ] = Field(description="Type of emotional manipulation")
    segment_ids: list[str] = Field(default_factory=list, description="Related segment IDs")
    speaker: str = Field(description="Speaker who used manipulation")
    content_sample: str = Field(description="Representative quote")
    intensity: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        default="MEDIUM", description="Manipulation intensity"
    )

    def is_high_intensity(self) -> bool:
        """Check if manipulation is high intensity."""
        return self.intensity == "HIGH"
