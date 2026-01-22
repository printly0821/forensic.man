"""
Unit tests for speaker analysis module.

Tests SpeakerAnalyzer, SpeakerStatistics, and TurnTakingEvent functionality.
"""

from datetime import datetime
from pathlib import Path

from forensic.analysis.speaker import SpeakerAnalyzer, SpeakerStatistics, TurnTakingEvent
from forensic.models.transcript import Segment, Transcript


class TestSpeakerStatistics:
    """Tests for SpeakerStatistics model."""

    def test_create_statistics(self):
        """Test creating speaker statistics."""
        stats = SpeakerStatistics(
            speaker_id="speaker_1",
            speaker_name="Test Speaker",
            total_segments=10,
            total_duration_seconds=300,
            word_count=500,
        )
        assert stats.speaker_id == "speaker_1"
        assert stats.speaker_name == "Test Speaker"
        assert stats.total_segments == 10

    def test_add_segment(self):
        """Test adding a segment to statistics."""
        stats = SpeakerStatistics(
            speaker_id="speaker_1",
            speaker_name="Test Speaker",
        )
        stats.add_segment(duration=30.0, estimated_words=50)
        assert stats.total_segments == 1
        assert stats.total_duration_seconds == 30.0
        assert stats.word_count == 50

    def test_duration_properties(self):
        """Test duration conversion properties."""
        stats = SpeakerStatistics(
            speaker_id="speaker_1",
            speaker_name="Test Speaker",
            total_duration_seconds=300,  # 5 minutes
        )
        assert stats.get_duration_minutes() == 5.0

    def test_words_per_minute(self):
        """Test words per minute calculation."""
        stats = SpeakerStatistics(
            speaker_id="speaker_1",
            speaker_name="Test Speaker",
            total_duration_seconds=120,  # 2 minutes
            word_count=240,
        )
        assert stats.get_words_per_minute() == 120.0


class TestTurnTakingEvent:
    """Tests for TurnTakingEvent model."""

    def test_create_turn_event(self):
        """Test creating a turn-taking event."""
        event = TurnTakingEvent(
            id="turn-001",
            timestamp=datetime(2025, 6, 15, 10, 30),
            from_speaker="speaker_1",
            to_speaker="speaker_2",
            gap_seconds=1.5,
        )
        assert event.from_speaker == "speaker_1"
        assert event.to_speaker == "speaker_2"
        assert event.gap_seconds == 1.5

    def test_overlap_detection(self):
        """Test overlap detection."""
        event = TurnTakingEvent(
            id="turn-002",
            timestamp=datetime(2025, 6, 15, 10, 30),
            from_speaker="speaker_1",
            to_speaker="speaker_2",
            overlap_seconds=0.5,
        )
        assert event.is_overlap

    def test_interruption_detection(self):
        """Test interruption detection."""
        event = TurnTakingEvent(
            id="turn-003",
            timestamp=datetime(2025, 6, 15, 10, 30),
            from_speaker="speaker_1",
            to_speaker="speaker_2",
            overlap_seconds=1.0,
            interruption=True,
        )
        assert event.is_interruption

    def test_gap_display(self):
        """Test gap display property."""
        event1 = TurnTakingEvent(
            id="turn-004",
            timestamp=datetime.now(),
            from_speaker="s1",
            to_speaker="s2",
            gap_seconds=2.0,
        )
        assert "Pause" in event1.gap_display

        event2 = TurnTakingEvent(
            id="turn-005",
            timestamp=datetime.now(),
            from_speaker="s1",
            to_speaker="s2",
            overlap_seconds=0.5,
        )
        assert "Overlap" in event2.gap_display


class TestSpeakerAnalyzer:
    """Tests for SpeakerAnalyzer class."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization with default speakers."""
        analyzer = SpeakerAnalyzer()
        assert analyzer.unknown_label == "UNKNOWN"
        assert analyzer.known_speaker_count >= 2

    def test_custom_unknown_label(self):
        """Test analyzer with custom unknown label."""
        analyzer = SpeakerAnalyzer(unknown_label="UNIDENTIFIED")
        assert analyzer.unknown_label == "UNIDENTIFIED"

    def test_add_known_speaker(self):
        """Test adding a known speaker."""
        analyzer = SpeakerAnalyzer()
        analyzer.add_known_speaker("speaker_3", "Test User", ["user", "tester"])
        assert "speaker_3" in analyzer.known_speakers

    def test_normalize_alias_default_speakers(self):
        """Test alias normalization for default speakers."""
        analyzer = SpeakerAnalyzer()
        # Test 신동식 aliases
        assert analyzer.normalize_alias("동식") == "speaker_1"
        assert analyzer.normalize_alias("신씨") == "speaker_1"
        assert analyzer.normalize_alias("아버지") == "speaker_1"
        # Test 신기연 aliases
        assert analyzer.normalize_alias("기연") == "speaker_2"
        assert analyzer.normalize_alias("신기연씨") == "speaker_2"

    def test_normalize_alias_unknown(self):
        """Test alias normalization for unknown speakers."""
        analyzer = SpeakerAnalyzer()
        result = analyzer.normalize_alias("unknown_speaker")
        assert result == "UNKNOWN"

    def test_normalize_alias_speaker_id(self):
        """Test that speaker IDs pass through."""
        analyzer = SpeakerAnalyzer()
        result = analyzer.normalize_alias("speaker_5")
        assert result == "speaker_5"

    def test_get_canonical_name(self):
        """Test getting canonical speaker name."""
        analyzer = SpeakerAnalyzer()
        assert analyzer.get_canonical_name("speaker_1") == "신동식"
        assert analyzer.get_canonical_name("speaker_2") == "신기연"

    def test_identify_speaker(self):
        """Test speaker identification from segment."""
        analyzer = SpeakerAnalyzer()
        segment = Segment(
            id="seg-001",
            speaker="동식",
            start_time=0.0,
            end_time=10.0,
            content="Test content",
            confidence=1.0,
        )
        speaker_id = analyzer.identify_speaker(segment)
        assert speaker_id == "speaker_1"

    def test_compute_statistics(self):
        """Test computing statistics from transcripts."""
        analyzer = SpeakerAnalyzer()

        # Create test transcripts
        transcript1 = Transcript(
            id="transcript-001",
            file_path=Path("/data/test1.txt"),
            date=datetime(2025, 6, 15, 10, 0),
            duration_seconds=100,
            speakers=["speaker_1", "speaker_2"],
        )
        transcript1.add_segment(
            Segment(
                id="seg-001",
                speaker="동식",
                start_time=0.0,
                end_time=50.0,
                content="Test content from speaker one",
                confidence=1.0,
            )
        )
        transcript1.add_segment(
            Segment(
                id="seg-002",
                speaker="기연",
                start_time=50.0,
                end_time=100.0,
                content="Test content from speaker two",
                confidence=1.0,
            )
        )

        stats = analyzer.compute_statistics([transcript1])
        assert "speaker_1" in stats
        assert "speaker_2" in stats
        assert stats["speaker_1"].speaker_name == "신동식"

    def test_analyze_turn_taking(self):
        """Test turn-taking analysis."""
        analyzer = SpeakerAnalyzer()

        segments = [
            Segment(
                id="seg-001",
                speaker="speaker_1",
                start_time=0.0,
                end_time=10.0,
                content="First",
                confidence=1.0,
            ),
            Segment(
                id="seg-002",
                speaker="speaker_2",
                start_time=11.0,
                end_time=20.0,
                content="Second",
                confidence=1.0,
            ),
            Segment(
                id="seg-003",
                speaker="speaker_1",
                start_time=9.5,  # Overlap
                end_time=15.0,
                content="Interruption",
                confidence=1.0,
            ),
        ]

        events = analyzer.analyze_turn_taking(segments)
        # Should detect at least one turn transition
        assert len(events) >= 1

    def test_remove_speaker(self):
        """Test removing a known speaker."""
        analyzer = SpeakerAnalyzer()
        analyzer.add_known_speaker("temp", "Temporary", ["tmp"])
        assert "temp" in analyzer.known_speakers

        analyzer.remove_speaker("temp")
        assert "temp" not in analyzer.known_speakers
