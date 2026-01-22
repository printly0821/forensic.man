"""
Unit tests for timeline module.

Tests Timeline, TimelineBuilder, and TimelineEvent functionality.
"""

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from forensic.analysis.timeline import Timeline, TimelineBuilder, TimelineEvent
from forensic.models.transcript import Segment, Transcript


class TestTimelineEvent:
    """Tests for TimelineEvent model."""

    def test_create_event(self):
        """Test creating a basic timeline event."""
        event = TimelineEvent(
            id="evt-001",
            date=date(2025, 6, 15),
            event_type="RECORDING",
            description="Test recording event",
            importance="MEDIUM",
        )
        assert event.id == "evt-001"
        assert event.date == date(2025, 6, 15)
        assert event.event_type == "RECORDING"
        assert event.importance == "MEDIUM"

    def test_event_with_time(self):
        """Test creating an event with time."""
        event = TimelineEvent(
            id="evt-002",
            date=date(2025, 6, 15),
            time_value="14:30:00",
            event_type="PATTERN_DETECTION",
            description="Pattern detected",
            importance="HIGH",
        )
        assert event.time == "14:30:00"

    def test_event_importance_checks(self):
        """Test importance level checking methods."""
        high_event = TimelineEvent(
            id="evt-003",
            date=date(2025, 6, 15),
            event_type="TEST",
            description="High importance",
            importance="HIGH",
        )
        assert high_event.is_high_importance()
        assert not high_event.is_medium_importance()
        assert not high_event.is_low_importance()

    def test_event_with_related_transcripts(self):
        """Test event with related transcripts."""
        event = TimelineEvent(
            id="evt-004",
            date=date(2025, 6, 15),
            event_type="TEST",
            description="Test",
            related_transcripts=["transcript-1", "transcript-2"],
        )
        assert len(event.related_transcripts) == 2


class TestTimeline:
    """Tests for Timeline model."""

    def test_create_timeline(self):
        """Test creating a basic timeline."""
        timeline = Timeline(
            id="tl-001",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )
        assert timeline.id == "tl-001"
        assert timeline.start_date == date(2025, 6, 1)
        assert timeline.end_date == date(2025, 6, 30)
        assert timeline.file_count == 0

    def test_timeline_properties(self):
        """Test timeline calculated properties."""
        timeline = Timeline(
            id="tl-002",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 10),
            total_duration=3600,  # 1 hour
        )
        assert timeline.duration_minutes == 60.0
        assert timeline.duration_hours == 1.0
        assert timeline.day_count == 10

    def test_add_event(self):
        """Test adding events to timeline."""
        timeline = Timeline(
            id="tl-003",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 10),
        )
        event = TimelineEvent(
            id="evt-005",
            date=date(2025, 6, 5),
            event_type="TEST",
            description="Test event",
        )
        timeline.add_event(event)
        assert len(timeline.events) == 1

    def test_get_events_by_importance(self):
        """Test filtering events by importance."""
        timeline = Timeline(
            id="tl-004",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 10),
            events=[
                TimelineEvent(
                    id="evt-006",
                    date=date(2025, 6, 5),
                    event_type="TEST",
                    description="High event",
                    importance="HIGH",
                ),
                TimelineEvent(
                    id="evt-007",
                    date=date(2025, 6, 6),
                    event_type="TEST",
                    description="Medium event",
                    importance="MEDIUM",
                ),
            ],
        )
        high_events = timeline.get_events_by_importance("HIGH")
        assert len(high_events) == 1
        assert high_events[0].importance == "HIGH"

    def test_get_high_importance_events(self):
        """Test getting high importance events."""
        timeline = Timeline(
            id="tl-005",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 10),
            events=[
                TimelineEvent(
                    id="evt-008",
                    date=date(2025, 6, 5),
                    event_type="TEST",
                    description="High event",
                    importance="HIGH",
                ),
                TimelineEvent(
                    id="evt-009",
                    date=date(2025, 6, 6),
                    event_type="TEST",
                    description="Low event",
                    importance="LOW",
                ),
            ],
        )
        high_events = timeline.get_high_importance_events()
        assert len(high_events) == 1


class TestTimelineBuilder:
    """Tests for TimelineBuilder class."""

    @pytest.fixture
    def sample_segments(self):
        """Create sample segments for testing."""
        return [
            Segment(
                id="seg-001",
                speaker="speaker_1",
                start_time=0.0,
                end_time=10.0,
                content="First segment",
                confidence=0.95,
            ),
            Segment(
                id="seg-002",
                speaker="speaker_2",
                start_time=10.0,
                end_time=20.0,
                content="Second segment",
                confidence=0.90,
            ),
        ]

    @pytest.fixture
    def sample_transcripts(self, sample_segments):
        """Create sample transcripts for testing."""
        transcript1 = Transcript(
            id="transcript-001",
            file_path=Path("/data/2025-06-15-recording.txt"),
            date=datetime(2025, 6, 15, 10, 0),
            duration_seconds=300,
            speakers=["speaker_1", "speaker_2"],
        )
        for seg in sample_segments:
            transcript1.add_segment(seg)

        transcript2 = Transcript(
            id="transcript-002",
            file_path=Path("/data/2025-06-20-recording.txt"),
            date=datetime(2025, 6, 20, 14, 0),
            duration_seconds=600,
            speakers=["speaker_1"],
        )

        return [transcript1, transcript2]

    def test_builder_initialization(self):
        """Test builder initialization."""
        builder = TimelineBuilder("test-timeline")
        assert builder.id == "test-timeline"
        assert builder.transcript_count == 0

    def test_add_transcript(self, sample_transcripts):
        """Test adding a transcript to the builder."""
        builder = TimelineBuilder("test-timeline")
        builder.add_transcript(sample_transcripts[0])
        assert builder.transcript_count == 1

    def test_build_empty_timeline(self):
        """Test building a timeline with no transcripts."""
        builder = TimelineBuilder("empty-timeline")
        timeline = builder.build()
        assert timeline.id == "empty-timeline"
        assert timeline.file_count == 0
        assert timeline.total_duration == 0

    def test_build_timeline(self, sample_transcripts):
        """Test building a timeline with transcripts."""
        builder = TimelineBuilder("test-timeline")
        for t in sample_transcripts:
            builder.add_transcript(t)
        timeline = builder.build()
        assert timeline.file_count == 2
        assert timeline.start_date == date(2025, 6, 15)
        assert timeline.end_date == date(2025, 6, 20)
        assert len(timeline.transcripts) == 2

    def test_get_by_date(self, sample_transcripts):
        """Test querying transcripts by date."""
        builder = TimelineBuilder("test-timeline")
        for t in sample_transcripts:
            builder.add_transcript(t)

        results = builder.get_by_date(date(2025, 6, 15))
        assert len(results) == 1
        assert results[0].id == "transcript-001"

    def test_get_by_range(self, sample_transcripts):
        """Test querying transcripts by date range."""
        builder = TimelineBuilder("test-timeline")
        for t in sample_transcripts:
            builder.add_transcript(t)

        results = builder.get_by_range(date(2025, 6, 1), date(2025, 6, 18))
        assert len(results) == 1
        assert results[0].id == "transcript-001"

    def test_group_by_day(self, sample_transcripts):
        """Test grouping transcripts by day."""
        builder = TimelineBuilder("test-timeline")
        for t in sample_transcripts:
            builder.add_transcript(t)

        grouped = builder.group_by_period("day")
        assert "2025-06-15" in grouped
        assert "2025-06-20" in grouped
        assert len(grouped["2025-06-15"]) == 1

    def test_group_by_month(self, sample_transcripts):
        """Test grouping transcripts by month."""
        builder = TimelineBuilder("test-timeline")
        for t in sample_transcripts:
            builder.add_transcript(t)

        grouped = builder.group_by_period("month")
        assert "2025-06" in grouped
        assert len(grouped["2025-06"]) == 2

    def test_group_by_week(self, sample_transcripts):
        """Test grouping transcripts by week."""
        builder = TimelineBuilder("test-timeline")
        for t in sample_transcripts:
            builder.add_transcript(t)

        grouped = builder.group_by_period("week")
        # Both in same week
        assert len(grouped) >= 1
