"""
Segment merger module unit tests.

Tests for SegmentMerger class and segment merging functions.
"""

import pytest

from forensic.io.merger import (
    DEFAULT_MIN_GAP,
    DEFAULT_TIME_TOLERANCE,
    MergeError,
    MergeStats,
    SegmentMerger,
    detect_split_segments,
    merge_all_continuous,
    validate_segment_continuity,
)
from forensic.models.transcript import Segment


def create_segment(
    id: str = "seg_001",
    speaker: str = "speaker_a",
    start_time: float = 0.0,
    end_time: float = 1.0,
    content: str = "Test content",
    confidence: float = 0.9,
) -> Segment:
    """Helper to create test segments."""
    return Segment(
        id=id,
        speaker=speaker,
        start_time=start_time,
        end_time=end_time,
        content=content,
        confidence=confidence,
    )


class TestSegmentMerger:
    """SegmentMerger class tests."""

    @pytest.fixture
    def merger(self) -> SegmentMerger:
        """Create a SegmentMerger instance."""
        return SegmentMerger()

    def test_init_default(self) -> None:
        """Test SegmentMerger default initialization."""
        merger = SegmentMerger()

        assert merger.time_tolerance == DEFAULT_TIME_TOLERANCE
        assert merger.min_gap == DEFAULT_MIN_GAP
        assert merger.has_pending is False
        assert merger.pending_segment is None

    def test_init_custom(self) -> None:
        """Test SegmentMerger with custom parameters."""
        merger = SegmentMerger(time_tolerance=1.0, min_gap=0.5)

        assert merger.time_tolerance == 1.0
        assert merger.min_gap == 0.5

    def test_init_invalid_tolerance(self) -> None:
        """Test SegmentMerger with invalid time tolerance."""
        with pytest.raises(ValueError, match="time_tolerance must be non-negative"):
            SegmentMerger(time_tolerance=-1.0)

    def test_init_invalid_min_gap(self) -> None:
        """Test SegmentMerger with invalid min gap."""
        with pytest.raises(ValueError, match="min_gap must be non-negative"):
            SegmentMerger(min_gap=-1.0)

    def test_stats(self, merger: SegmentMerger) -> None:
        """Test stats property."""
        stats = merger.stats

        assert isinstance(stats, MergeStats)
        assert stats.segments_received == 0
        assert stats.segments_merged == 0
        assert stats.segments_output == 0


class TestSegmentMergerAddSegment:
    """Tests for SegmentMerger.add_segment method."""

    @pytest.fixture
    def merger(self) -> SegmentMerger:
        """Create a SegmentMerger instance."""
        return SegmentMerger()

    def test_add_first_segment(self, merger: SegmentMerger) -> None:
        """Test adding first segment stores as pending."""
        seg = create_segment()
        result = merger.add_segment(seg)

        assert result == []
        assert merger.has_pending is True
        assert merger.pending_segment == seg
        assert merger.stats.segments_received == 1

    def test_add_non_mergeable_segments(self, merger: SegmentMerger) -> None:
        """Test adding segments that should not merge."""
        seg1 = create_segment(id="seg_001", start_time=0.0, end_time=1.0)
        seg2 = create_segment(id="seg_002", speaker="speaker_b", start_time=5.0, end_time=6.0)

        merger.add_segment(seg1)
        result = merger.add_segment(seg2)

        assert len(result) == 1
        assert result[0] == seg1
        assert merger.pending_segment == seg2

    def test_add_mergeable_segments(self, merger: SegmentMerger) -> None:
        """Test adding segments that should merge."""
        seg1 = create_segment(id="seg_001", start_time=0.0, end_time=1.0, content="Hello")
        seg2 = create_segment(id="seg_002", start_time=1.0, end_time=2.0, content="World")

        merger.add_segment(seg1)
        result = merger.add_segment(seg2)

        # No output yet, segments are merged into pending
        assert result == []
        assert merger.has_pending is True
        assert merger.stats.segments_merged == 1

    def test_add_segments_batch(self, merger: SegmentMerger) -> None:
        """Test adding multiple segments at once."""
        segments = [
            create_segment(id=f"seg_{i}", start_time=float(i * 10), end_time=float(i * 10 + 1))
            for i in range(3)
        ]

        result = merger.add_segments(segments)

        # First two should be output, third pending
        assert len(result) == 2
        assert merger.has_pending is True


class TestSegmentMergerShouldMerge:
    """Tests for SegmentMerger.should_merge method."""

    @pytest.fixture
    def merger(self) -> SegmentMerger:
        """Create a SegmentMerger instance."""
        return SegmentMerger()

    def test_should_merge_same_speaker_continuous(self, merger: SegmentMerger) -> None:
        """Test should_merge with same speaker and continuous time."""
        seg1 = create_segment(start_time=0.0, end_time=1.0)
        seg2 = create_segment(start_time=1.0, end_time=2.0)

        assert merger.should_merge(seg1, seg2) is True

    def test_should_merge_same_speaker_small_gap(self, merger: SegmentMerger) -> None:
        """Test should_merge with same speaker and small gap."""
        seg1 = create_segment(start_time=0.0, end_time=1.0)
        seg2 = create_segment(start_time=1.3, end_time=2.0)  # 0.3s gap < 0.5s tolerance

        assert merger.should_merge(seg1, seg2) is True

    def test_should_not_merge_different_speakers(self, merger: SegmentMerger) -> None:
        """Test should_merge with different speakers."""
        seg1 = create_segment(speaker="speaker_a", start_time=0.0, end_time=1.0)
        seg2 = create_segment(speaker="speaker_b", start_time=1.0, end_time=2.0)

        assert merger.should_merge(seg1, seg2) is False

    def test_should_not_merge_large_gap(self, merger: SegmentMerger) -> None:
        """Test should_merge with large time gap."""
        seg1 = create_segment(start_time=0.0, end_time=1.0)
        seg2 = create_segment(start_time=5.0, end_time=6.0)  # 4s gap > 0.5s tolerance

        assert merger.should_merge(seg1, seg2) is False

    def test_should_merge_overlap(self, merger: SegmentMerger) -> None:
        """Test should_merge with overlapping times."""
        seg1 = create_segment(start_time=0.0, end_time=2.0)
        seg2 = create_segment(start_time=1.5, end_time=3.0)  # Overlap

        assert merger.should_merge(seg1, seg2) is True


class TestSegmentMergerMerge:
    """Tests for SegmentMerger.merge method."""

    @pytest.fixture
    def merger(self) -> SegmentMerger:
        """Create a SegmentMerger instance."""
        return SegmentMerger()

    def test_merge_basic(self, merger: SegmentMerger) -> None:
        """Test basic segment merging."""
        seg1 = create_segment(
            id="seg_001", start_time=0.0, end_time=1.0, content="Hello", confidence=0.9
        )
        seg2 = create_segment(
            id="seg_002", start_time=1.0, end_time=2.0, content="World", confidence=0.8
        )

        merged = merger.merge(seg1, seg2)

        assert merged.speaker == "speaker_a"
        assert merged.start_time == 0.0
        assert merged.end_time == 2.0
        assert "Hello" in merged.content
        assert "World" in merged.content
        assert merged.id == "seg_001_merged"

    def test_merge_content_with_space(self, merger: SegmentMerger) -> None:
        """Test merging adds space between content."""
        seg1 = create_segment(content="Hello")
        seg2 = create_segment(start_time=1.0, end_time=2.0, content="World")

        merged = merger.merge(seg1, seg2)

        assert merged.content == "Hello World"

    def test_merge_content_no_space_partial_word(self, merger: SegmentMerger) -> None:
        """Test merging partial words without space."""
        seg1 = create_segment(content="Hel")
        seg2 = create_segment(start_time=1.0, end_time=2.0, content="lo")

        merged = merger.merge(seg1, seg2)

        assert merged.content == "Hello"

    def test_merge_korean_partial_word(self, merger: SegmentMerger) -> None:
        """Test merging Korean partial words."""
        seg1 = create_segment(content="안녕하")
        seg2 = create_segment(start_time=1.0, end_time=2.0, content="세요")

        merged = merger.merge(seg1, seg2)

        assert merged.content == "안녕하세요"

    def test_merge_confidence_weighted(self, merger: SegmentMerger) -> None:
        """Test merged confidence is weighted average."""
        # seg1: 1 second duration, 0.9 confidence
        # seg2: 3 seconds duration, 0.7 confidence
        # Expected: (0.9*1 + 0.7*3) / 4 = 3.0 / 4 = 0.75
        seg1 = create_segment(start_time=0.0, end_time=1.0, confidence=0.9)
        seg2 = create_segment(start_time=1.0, end_time=4.0, confidence=0.7)

        merged = merger.merge(seg1, seg2)

        assert abs(merged.confidence - 0.75) < 0.01

    def test_merge_different_speakers_raises(self, merger: SegmentMerger) -> None:
        """Test merging different speakers raises error."""
        seg1 = create_segment(speaker="speaker_a")
        seg2 = create_segment(speaker="speaker_b", start_time=1.0, end_time=2.0)

        with pytest.raises(MergeError, match="different speakers"):
            merger.merge(seg1, seg2)


class TestSegmentMergerFlush:
    """Tests for SegmentMerger.flush method."""

    @pytest.fixture
    def merger(self) -> SegmentMerger:
        """Create a SegmentMerger instance."""
        return SegmentMerger()

    def test_flush_empty(self, merger: SegmentMerger) -> None:
        """Test flushing with no pending segment."""
        result = merger.flush()

        assert result == []

    def test_flush_with_pending(self, merger: SegmentMerger) -> None:
        """Test flushing with pending segment."""
        seg = create_segment()
        merger.add_segment(seg)

        result = merger.flush()

        assert len(result) == 1
        assert result[0] == seg
        assert merger.has_pending is False

    def test_flush_clears_pending(self, merger: SegmentMerger) -> None:
        """Test flush clears pending segment."""
        merger.add_segment(create_segment())
        merger.flush()

        assert merger.pending_segment is None


class TestSegmentMergerReset:
    """Tests for SegmentMerger.reset method."""

    @pytest.fixture
    def merger(self) -> SegmentMerger:
        """Create a SegmentMerger instance."""
        return SegmentMerger()

    def test_reset(self, merger: SegmentMerger) -> None:
        """Test reset clears all state."""
        merger.add_segment(create_segment())
        merger.reset()

        assert merger.has_pending is False
        assert merger.stats.segments_received == 0
        assert merger.stats.segments_merged == 0


class TestSegmentMergerProcessBatch:
    """Tests for SegmentMerger.process_batch method."""

    @pytest.fixture
    def merger(self) -> SegmentMerger:
        """Create a SegmentMerger instance."""
        return SegmentMerger()

    def test_process_batch_not_last(self, merger: SegmentMerger) -> None:
        """Test process_batch without flush."""
        segments = [
            create_segment(id="seg_001", start_time=0.0, end_time=1.0),
            create_segment(id="seg_002", start_time=10.0, end_time=11.0),
            create_segment(id="seg_003", start_time=20.0, end_time=21.0),
        ]

        result = merger.process_batch(segments, is_last=False)

        # Two output, one pending
        assert len(result) == 2
        assert merger.has_pending is True

    def test_process_batch_last(self, merger: SegmentMerger) -> None:
        """Test process_batch with flush."""
        segments = [
            create_segment(id="seg_001", start_time=0.0, end_time=1.0),
            create_segment(id="seg_002", start_time=10.0, end_time=11.0),
            create_segment(id="seg_003", start_time=20.0, end_time=21.0),
        ]

        result = merger.process_batch(segments, is_last=True)

        # All three output
        assert len(result) == 3
        assert merger.has_pending is False

    def test_process_batch_with_merges(self, merger: SegmentMerger) -> None:
        """Test process_batch with mergeable segments."""
        segments = [
            create_segment(id="seg_001", start_time=0.0, end_time=1.0, content="Hello"),
            create_segment(id="seg_002", start_time=1.0, end_time=2.0, content="World"),
            create_segment(id="seg_003", start_time=10.0, end_time=11.0, content="Test"),
        ]

        result = merger.process_batch(segments, is_last=True)

        # First two merged, third separate
        assert len(result) == 2
        assert "Hello" in result[0].content
        assert "World" in result[0].content


class TestMergeStats:
    """Tests for MergeStats dataclass."""

    def test_merge_ratio_no_received(self) -> None:
        """Test merge ratio with no segments received."""
        stats = MergeStats()

        assert stats.merge_ratio == 0.0

    def test_merge_ratio(self) -> None:
        """Test merge ratio calculation."""
        stats = MergeStats(segments_received=10, segments_merged=3, segments_output=7)

        assert stats.merge_ratio == 0.3


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_detect_split_segments_empty(self) -> None:
        """Test detect_split_segments with empty list."""
        result = detect_split_segments([])

        assert result == []

    def test_detect_split_segments_single(self) -> None:
        """Test detect_split_segments with single segment."""
        segments = [create_segment()]
        result = detect_split_segments(segments)

        assert result == []

    def test_detect_split_segments_found(self) -> None:
        """Test detect_split_segments finds splits."""
        segments = [
            create_segment(id="seg_001", start_time=0.0, end_time=1.0),
            create_segment(id="seg_002", start_time=1.0, end_time=2.0),  # Split
            create_segment(id="seg_003", start_time=10.0, end_time=11.0),  # Not split
        ]

        result = detect_split_segments(segments)

        assert (0, 1) in result
        assert (1, 2) not in result

    def test_merge_all_continuous_empty(self) -> None:
        """Test merge_all_continuous with empty list."""
        result = merge_all_continuous([])

        assert result == []

    def test_merge_all_continuous(self) -> None:
        """Test merge_all_continuous merges correctly."""
        segments = [
            create_segment(id="seg_001", start_time=0.0, end_time=1.0, content="A"),
            create_segment(id="seg_002", start_time=1.0, end_time=2.0, content="B"),
            create_segment(id="seg_003", start_time=10.0, end_time=11.0, content="C"),
            create_segment(id="seg_004", start_time=11.0, end_time=12.0, content="D"),
        ]

        result = merge_all_continuous(segments)

        # Should merge (A,B) and (C,D)
        assert len(result) == 2

    def test_validate_segment_continuity_valid(self) -> None:
        """Test validate_segment_continuity with valid segments."""
        segments = [
            create_segment(id="seg_001", start_time=0.0, end_time=1.0),
            create_segment(id="seg_002", start_time=1.0, end_time=2.0),
            create_segment(id="seg_003", start_time=2.5, end_time=3.5),
        ]

        errors = validate_segment_continuity(segments)

        assert errors == []

    def test_validate_segment_continuity_overlap(self) -> None:
        """Test validate_segment_continuity detects overlap."""
        segments = [
            create_segment(id="seg_001", start_time=0.0, end_time=5.0),
            create_segment(id="seg_002", start_time=2.0, end_time=6.0),  # Overlap
        ]

        errors = validate_segment_continuity(segments)

        assert len(errors) == 1
        assert "overlap" in errors[0].lower()

    def test_validate_segment_continuity_large_gap(self) -> None:
        """Test validate_segment_continuity detects large gap."""
        segments = [
            create_segment(id="seg_001", start_time=0.0, end_time=1.0),
            create_segment(id="seg_002", start_time=20.0, end_time=21.0),  # 19s gap
        ]

        errors = validate_segment_continuity(segments)

        assert len(errors) == 1
        assert "gap" in errors[0].lower()


class TestSegmentMergerEdgeCases:
    """Edge case tests for SegmentMerger."""

    def test_merge_empty_content(self) -> None:
        """Test merging segments with empty content."""
        merger = SegmentMerger()
        seg1 = create_segment(content="")
        seg2 = create_segment(start_time=1.0, end_time=2.0, content="Hello")

        merged = merger.merge(seg1, seg2)

        assert merged.content == "Hello"

    def test_merge_whitespace_content(self) -> None:
        """Test merging segments with whitespace content."""
        merger = SegmentMerger()
        seg1 = create_segment(content="Hello ")
        seg2 = create_segment(start_time=1.0, end_time=2.0, content=" World")

        merged = merger.merge(seg1, seg2)

        # Should handle whitespace gracefully
        assert "Hello" in merged.content
        assert "World" in merged.content

    def test_merge_punctuation_ending(self) -> None:
        """Test merging when first segment ends with punctuation."""
        merger = SegmentMerger()
        seg1 = create_segment(content="Hello!")
        seg2 = create_segment(start_time=1.0, end_time=2.0, content="World")

        merged = merger.merge(seg1, seg2)

        # Should add space after punctuation
        assert merged.content == "Hello! World"

    def test_zero_duration_segments(self) -> None:
        """Test merging segments with near-zero duration."""
        merger = SegmentMerger()
        seg1 = create_segment(start_time=0.0, end_time=0.001, confidence=0.9)
        seg2 = create_segment(start_time=0.001, end_time=0.002, confidence=0.7)

        merged = merger.merge(seg1, seg2)

        # Should handle near-zero duration gracefully
        assert 0.0 <= merged.confidence <= 1.0

    def test_very_long_content(self) -> None:
        """Test merging segments with very long content."""
        merger = SegmentMerger()
        long_content = "A" * 10000
        seg1 = create_segment(content=long_content)
        seg2 = create_segment(start_time=1.0, end_time=2.0, content=long_content)

        merged = merger.merge(seg1, seg2)

        # With space between (uppercase A is not treated as word split)
        assert len(merged.content) >= 20000

    def test_many_segments_batch(self) -> None:
        """Test processing many segments."""
        merger = SegmentMerger()
        segments = [
            create_segment(
                id=f"seg_{i:04d}",
                start_time=float(i * 10),
                end_time=float(i * 10 + 1),
            )
            for i in range(100)
        ]

        result = merger.process_batch(segments, is_last=True)

        assert len(result) == 100
        assert merger.stats.segments_received == 100
