"""
Event extraction and management for timeline analysis.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from forensic.models.transcript import Transcript


class TimelineEvent:
    """
    Event marker for significant occurrences in transcripts.

    Factory class for creating timeline events from various sources.
    """

    @staticmethod
    def create(
        event_date: date,
        event_type: str,
        description: str,
        importance: str = "MEDIUM",
        event_time: datetime.time | None = None,
        related_transcripts: list[str] | None = None,
    ) -> "TimelineEvent":
        """
        Create a new timeline event.

        Args:
            event_date: Event occurrence date
            event_type: Type/category of the event
            description: Human-readable event description
            importance: Event significance level (HIGH, MEDIUM, LOW)
            event_time: Event occurrence time if available
            related_transcripts: IDs of related transcripts

        Returns:
            TimelineEvent instance
        """
        from forensic.analysis.timeline.models import TimelineEvent as EventModel

        return EventModel(
            id=str(uuid4()),
            date=event_date,
            time=event_time,
            event_type=event_type,
            description=description,
            related_transcripts=related_transcripts or [],
            importance=importance,
        )

    @staticmethod
    def from_pattern_detection(
        pattern_type: str,
        transcript_id: str,
        detection_date: date,
        count: int = 1,
    ) -> "TimelineEvent":
        """
        Create an event from pattern detection results.

        Args:
            pattern_type: Type of pattern detected (e.g., "GASLIGHTING")
            transcript_id: ID of the transcript where pattern was found
            detection_date: Date of detection
            count: Number of occurrences

        Returns:
            TimelineEvent for pattern detection
        """
        importance = "HIGH" if count >= 3 else "MEDIUM"
        description = f"{pattern_type} pattern detected ({count} occurrence{'s' if count != 1 else ''})"

        return TimelineEvent.create(
            event_date=detection_date,
            event_type="PATTERN_DETECTION",
            description=description,
            importance=importance,
            related_transcripts=[transcript_id],
        )

    @staticmethod
    def extract_from_transcript(transcript: "Transcript") -> list["TimelineEvent"]:
        """
        Extract notable events from a transcript.

        Args:
            transcript: Transcript to analyze

        Returns:
            List of timeline events extracted from the transcript
        """
        events = []

        # Create recording event
        events.append(
            TimelineEvent.create(
                event_date=transcript.date.date(),
                event_type="RECORDING",
                description=f"Recording: {transcript.file_path.name}",
                importance="LOW",
                related_transcripts=[transcript.id],
            )
        )

        # Create speaker count event if multiple speakers
        if transcript.speaker_count > 1:
            events.append(
                TimelineEvent.create(
                    event_date=transcript.date.date(),
                    event_type="MULTIPLE_SPEAKERS",
                    description=f"Conversation with {transcript.speaker_count} speakers",
                    importance="LOW",
                    related_transcripts=[transcript.id],
                )
            )

        return events
