"""
Unit tests for filter module
"""

from datetime import date, datetime

from forensic.models import Evidence, Segment, Transcript
from forensic.search.filter import (
    AbusePatternFilter,
    CompositeFilter,
    DateFilter,
    FilterEngine,
    GaslightingFilter,
    HighImportanceFilter,
    ImportanceFilter,
    MediumHighImportanceFilter,
    PatternFilter,
    RelativeDateFilter,
    SpeakerAliasFilter,
    SpeakerFilter,
    ThreatFilter,
)
from forensic.search.models import FilterConfig, FilterLogicalOperator


class TestFilterEngine:
    """Tests for FilterEngine class."""

    def setup_method(self):
        """Set up test data."""
        self.segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="test",
                confidence=0.9,
            ),
            Segment(
                id="seg2",
                speaker="신기연",
                start_time=1.0,
                end_time=2.0,
                content="test",
                confidence=0.95,
            ),
        ]
        self.engine = FilterEngine()

    def test_no_filters(self):
        """Test filtering with no filters applied."""
        config = FilterConfig()
        result = self.engine.apply_filters(self.segments, config)

        assert len(result) == 2

    def test_filter_by_speakers(self):
        """Test filtering by speakers."""
        config = FilterConfig(speakers=["신동식"])
        result = self.engine.apply_filters(self.segments, config)

        assert len(result) == 1
        assert result[0].speaker == "신동식"

    def test_filter_by_confidence(self):
        """Test filtering by confidence range."""
        config = FilterConfig(confidence_min=0.92)
        result = self.engine.apply_filters(self.segments, config)

        assert len(result) == 1
        assert result[0].confidence == 0.95

    def test_filter_by_duration(self):
        """Test filtering by duration."""
        config = FilterConfig(duration_max=0.5)
        result = self.engine.apply_filters(self.segments, config)

        # First segment has duration 1.0, second has 1.0
        assert len(result) == 0

    def test_multiple_filters(self):
        """Test multiple filters combined."""
        config = FilterConfig(
            speakers=["신동식", "신기연"],
            confidence_min=0.8,
        )
        result = self.engine.apply_filters(self.segments, config)

        assert len(result) == 2


class TestDateFilter:
    """Tests for DateFilter class."""

    def setup_method(self):
        """Set up test data."""
        self.transcripts = [
            Transcript(
                id="trans1",
                file_path="/path/file1.txt",
                date=datetime(2025, 1, 15, 12, 0),
                duration_seconds=100,
                content="test",
                segments=[],
            ),
            Transcript(
                id="trans2",
                file_path="/path/file2.txt",
                date=datetime(2025, 2, 20, 12, 0),
                duration_seconds=100,
                content="test",
                segments=[],
            ),
        ]
        self.filter = DateFilter()

    def test_filter_by_date_range(self):
        """Test filtering by date range."""
        self.filter.set_range(
            date(2025, 1, 1),
            date(2025, 1, 31),
        )

        result = self.filter.filter(self.transcripts)

        assert len(result) == 1
        assert result[0].id == "trans1"

    def test_date_filter_with_segments(self):
        """Test that segments are not affected (no date)."""
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="test",
                confidence=0.9,
            ),
        ]

        self.filter.set_range(
            date(2025, 1, 1),
            date(2025, 1, 31),
        )

        result = self.filter.filter(segments)

        # Segments don't have dates, so they're excluded
        assert len(result) == 0

    def test_clear_filters(self):
        """Test clearing date filter."""
        self.filter.set_range(date(2025, 1, 1), date(2025, 1, 31))
        self.filter.clear()

        assert self.filter._start_date is None
        assert self.filter._end_date is None


class TestRelativeDateFilter:
    """Tests for RelativeDateFilter class."""

    def test_last_n_days(self):
        """Test filtering for last N days."""
        filter = RelativeDateFilter()
        filter.set_last_n_days(7)

        # Should have start_date = 7 days ago, end_date = today
        assert filter._start_date is not None
        assert filter._end_date is not None

    def test_relative_spec(self):
        """Test relative date specifications."""
        filter = RelativeDateFilter()

        # "today" should work
        filter.set_date_range_from_strings("today", "today")

        assert filter._start_date is not None
        assert filter._end_date is not None


class TestSpeakerFilter:
    """Tests for SpeakerFilter class."""

    def setup_method(self):
        """Set up test data."""
        self.segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="test",
                confidence=0.9,
            ),
            Segment(
                id="seg2",
                speaker="신기연",
                start_time=1.0,
                end_time=2.0,
                content="test",
                confidence=0.95,
            ),
        ]
        self.filter = SpeakerFilter()

    def test_include_speakers(self):
        """Test including specific speakers."""
        self.filter.include_speakers(["신동식"])
        result = self.filter.filter(self.segments)

        assert len(result) == 1
        assert result[0].speaker == "신동식"

    def test_exclude_speakers(self):
        """Test excluding specific speakers."""
        self.filter.exclude_speakers(["신동식"])
        result = self.filter.filter(self.segments)

        assert len(result) == 1
        assert result[0].speaker == "신기연"

    def test_matches_method(self):
        """Test matches method."""
        self.filter.include_speakers(["신동식"])

        assert self.filter.matches(self.segments[0]) is True
        assert self.filter.matches(self.segments[1]) is False


class TestSpeakerAliasFilter:
    """Tests for SpeakerAliasFilter class."""

    def test_add_alias(self):
        """Test adding speaker aliases."""
        filter = SpeakerAliasFilter()

        filter.add_alias("John Doe", "john")
        filter.add_aliases("Jane Doe", ["jane", "ms doe"])

        assert filter.matches({"speaker": "john"}) is True
        assert filter.matches({"speaker": "jane"}) is True

    def test_resolve_speaker(self):
        """Test speaker name resolution."""
        filter = SpeakerAliasFilter()
        filter.add_alias("신동식", "신")

        resolved = filter.resolve_speaker("신")

        assert resolved == "신동식"


class TestImportanceFilter:
    """Tests for ImportanceFilter class."""

    def setup_method(self):
        """Set up test data."""

        self.evidence = [
            Evidence(
                id="ev1",
                transcript_id="trans1",
                segment_ids=["seg1"],
                category="GASLIGHTING",
                description="Gaslighting evidence",
                importance="HIGH",
            ),
            Evidence(
                id="ev2",
                transcript_id="trans1",
                segment_ids=["seg2"],
                category="THREAT",
                description="Threat evidence",
                importance="LOW",
            ),
        ]

    def test_filter_by_importance_levels(self):
        """Test filtering by importance levels."""
        filter = ImportanceFilter()
        filter.set_levels(["HIGH"])

        result = filter.filter(self.evidence)

        assert len(result) == 1
        assert result[0].importance == "HIGH"

    def test_min_importance(self):
        """Test minimum importance filter."""
        filter = ImportanceFilter()
        filter.set_min_importance("MEDIUM")

        result = filter.filter(self.evidence)

        assert len(result) == 1
        assert result[0].importance == "HIGH"

    def test_high_importance_filter(self):
        """Test HighImportanceFilter shortcut."""
        filter = HighImportanceFilter()

        result = filter.filter(self.evidence)

        assert len(result) == 1
        assert result[0].importance == "HIGH"

    def test_medium_high_importance_filter(self):
        """Test MediumHighImportanceFilter shortcut."""
        filter = MediumHighImportanceFilter()

        result = filter.filter(self.evidence)

        assert len(result) == 1
        assert result[0].importance == "HIGH"


class TestPatternFilter:
    """Tests for PatternFilter class."""

    def setup_method(self):
        """Set up test data."""
        self.evidence = [
            Evidence(
                id="ev1",
                transcript_id="trans1",
                segment_ids=["seg1"],
                category="GASLIGHTING",
                description="Gaslighting evidence",
                importance="HIGH",
            ),
            Evidence(
                id="ev2",
                transcript_id="trans1",
                segment_ids=["seg2"],
                category="THREAT",
                description="Threat evidence",
                importance="LOW",
            ),
            Evidence(
                id="ev3",
                transcript_id="trans1",
                segment_ids=["seg3"],
                category="EMOTIONAL_MANIPULATION",
                description="Emotional manipulation",
                importance="MEDIUM",
            ),
        ]

    def test_filter_by_pattern_type(self):
        """Test filtering by pattern type."""
        filter = PatternFilter()
        filter.add_pattern("GASLIGHTING")

        result = filter.filter(self.evidence)

        assert len(result) == 1
        assert str(result[0].category) == "GASLIGHTING"

    def test_exclude_pattern(self):
        """Test excluding pattern types."""
        filter = PatternFilter()
        filter.exclude_pattern("THREAT")

        result = filter.filter(self.evidence)

        assert len(result) == 2
        assert all(e.category != "THREAT" for e in result)

    def test_gaslighting_filter(self):
        """Test GaslightingFilter shortcut."""
        filter = GaslightingFilter()

        result = filter.filter(self.evidence)

        assert len(result) == 1
        assert str(result[0].category) == "GASLIGHTING"

    def test_threat_filter(self):
        """Test ThreatFilter shortcut."""
        filter = ThreatFilter()

        result = filter.filter(self.evidence)

        assert len(result) == 1
        assert result[0].category == "THREAT"

    def test_abuse_pattern_filter(self):
        """Test AbusePatternFilter combined filter."""
        filter = AbusePatternFilter()

        result = filter.filter(self.evidence)

        # Should match GASLIGHTING, THREAT, EMOTIONAL_MANIPULATION
        assert len(result) == 3


class TestCompositeFilter:
    """Tests for CompositeFilter class."""

    def setup_method(self):
        """Set up test data."""
        self.segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="가스라이팅",
                confidence=0.9,
            ),
            Segment(
                id="seg2",
                speaker="신기연",
                start_time=1.0,
                end_time=2.0,
                content="위협",
                confidence=0.95,
            ),
        ]
        self.engine = FilterEngine()

    def test_and_logic(self):
        """Test AND composite filter."""
        composite = CompositeFilter(FilterLogicalOperator.AND)

        # Create filters that together match nothing
        config1 = FilterConfig(speakers=["신동식"])
        config2 = FilterConfig(speakers=["신기연"])

        composite.add_filter(config1)
        composite.add_filter(config2)

        result = composite.apply(self.segments, self.engine)

        # No segment has both speakers
        assert len(result) == 0

    def test_or_logic(self):
        """Test OR composite filter."""
        composite = CompositeFilter(FilterLogicalOperator.OR)

        config1 = FilterConfig(speakers=["신동식"])
        config2 = FilterConfig(speakers=["신기연"])

        composite.add_filter(config1)
        composite.add_filter(config2)

        result = composite.apply(self.segments, self.engine)

        # Should match both segments
        assert len(result) == 2

    def test_not_logic(self):
        """Test NOT composite filter."""
        composite = CompositeFilter(FilterLogicalOperator.NOT)

        config = FilterConfig(speakers=["신동식"])
        composite.add_filter(config)

        result = composite.apply(self.segments, self.engine)

        # Should exclude 신동식, leaving 신기연
        assert len(result) == 1
        assert result[0].speaker == "신기연"
