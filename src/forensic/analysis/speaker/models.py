"""
Speaker analysis data models.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class SpeakerStatistics(BaseModel):
    """
    Statistical summary for a speaker.

    Comprehensive statistics about a speaker's participation across
    all analyzed transcripts.

    Attributes:
        speaker_id: Unique speaker identifier
        speaker_name: Display name for the speaker
        aliases: List of known aliases for this speaker
        total_segments: Total number of speech segments
        total_duration_seconds: Total speaking time in seconds
        average_segment_length: Average duration of speech segments
        word_count: Estimated total word count
        speaking_ratio: Proportion of total speaking time (0.0-1.0)
        first_appearance: Timestamp of first appearance
        last_appearance: Timestamp of most recent appearance
    """

    speaker_id: str
    speaker_name: str
    aliases: list[str] = Field(default_factory=list, description="Known speaker aliases")
    total_segments: int = Field(default=0, ge=0, description="Total speech segments")
    total_duration_seconds: float = Field(default=0, ge=0, description="Total speaking time (seconds)")
    average_segment_length: float = Field(default=0, ge=0, description="Avg segment duration (seconds)")
    word_count: int = Field(default=0, ge=0, description="Estimated total words spoken")
    speaking_ratio: float = Field(default=0, ge=0, le=1, description="Proportion of speaking time")
    first_appearance: datetime = Field(default_factory=datetime.now, description="First appearance timestamp")
    last_appearance: datetime = Field(default_factory=datetime.now, description="Last appearance timestamp")

    def get_duration_minutes(self) -> float:
        """Total speaking duration in minutes."""
        return self.total_duration_seconds / 60

    def get_words_per_minute(self) -> float:
        """Calculate words per minute speaking rate."""
        if self.total_duration_seconds > 0:
            return (self.word_count / self.total_duration_seconds) * 60
        return 0.0

    def add_segment(self, duration: float, estimated_words: int = 0) -> None:
        """
        Add a segment to update statistics.

        Args:
            duration: Duration of the segment in seconds
            estimated_words: Estimated word count for the segment
        """
        self.total_segments += 1
        self.total_duration_seconds += duration
        self.word_count += estimated_words
        if self.total_segments > 0:
            self.average_segment_length = self.total_duration_seconds / self.total_segments


class TurnTakingEvent(BaseModel):
    """
    Speaker turn-taking transition event.

    Records when one speaker stops speaking and another begins,
    including timing and interruption detection.

    Attributes:
        id: Unique event identifier
        timestamp: When the turn transition occurred
        from_speaker: Speaker who was speaking before
        to_speaker: Speaker who speaks next
        gap_seconds: Silence between turns (negative if overlap)
        overlap_seconds: Duration of overlapping speech
        interruption: Whether this appears to be an interruption
    """

    id: str
    timestamp: datetime
    from_speaker: str
    to_speaker: str
    gap_seconds: float = Field(default=0, description="Silence between turns (negative=overlap)")
    overlap_seconds: float = Field(default=0, ge=0, description="Duration of overlap")
    interruption: bool = Field(default=False, description="Interruption detected")

    @property
    def is_overlap(self) -> bool:
        """Check if this turn involved overlapping speech."""
        return self.overlap_seconds > 0

    @property
    def is_interruption(self) -> bool:
        """Check if this was an interruption."""
        return self.interruption

    @property
    def gap_display(self) -> str:
        """Human-readable gap description."""
        if self.overlap_seconds > 0:
            return f"Overlap: {self.overlap_seconds:.2f}s"
        elif self.gap_seconds < 0:
            return f"Interruption: {abs(self.gap_seconds):.2f}s"
        elif self.gap_seconds > 0:
            return f"Pause: {self.gap_seconds:.2f}s"
        else:
            return "Immediate"
