"""
Segment merger module for handling split segments across chunk boundaries.

Provides intelligent detection and merging of segments that were
split across chunk boundaries during processing.
"""

from dataclasses import dataclass, field
from typing import Protocol

from forensic.models.transcript import Segment

# Default time tolerance for considering segments as continuous (seconds)
DEFAULT_TIME_TOLERANCE: float = 0.5

# Default minimum gap to consider segments as separate (seconds)
DEFAULT_MIN_GAP: float = 0.1


class SegmentMergerProtocol(Protocol):
    """Segment merger interface protocol."""

    def add_segment(self, segment: Segment) -> list[Segment]:
        """Add segment and return any completed merged segments."""
        ...

    def should_merge(self, seg1: Segment, seg2: Segment) -> bool:
        """Check if two segments should be merged."""
        ...

    def merge(self, seg1: Segment, seg2: Segment) -> Segment:
        """Merge two segments into one."""
        ...

    def flush(self) -> list[Segment]:
        """Flush pending segments."""
        ...


class MergeError(Exception):
    """Raised when segment merging fails."""

    pass


class InvalidSegmentError(Exception):
    """Raised when segment is invalid for merging."""

    pass


@dataclass
class MergeStats:
    """
    Statistics about merge operations.

    Attributes:
        segments_received: Total segments received.
        segments_merged: Number of merge operations performed.
        segments_output: Total segments output.
    """

    segments_received: int = 0
    segments_merged: int = 0
    segments_output: int = 0

    @property
    def merge_ratio(self) -> float:
        """Calculate merge ratio (merged / received)."""
        if self.segments_received == 0:
            return 0.0
        return self.segments_merged / self.segments_received


@dataclass
class SegmentMerger:
    """
    Merger for handling split segments across chunk boundaries.

    Detects and merges segments that were split during chunk processing,
    ensuring data integrity and continuity.

    Merging criteria:
    - Same speaker
    - Time continuity (end_time of first ~ start_time of second)
    - No significant gap between segments

    Attributes:
        time_tolerance: Maximum time gap for continuous segments.
        min_gap: Minimum gap to consider segments as separate.
    """

    time_tolerance: float = DEFAULT_TIME_TOLERANCE
    min_gap: float = DEFAULT_MIN_GAP
    _pending: Segment | None = field(default=None, repr=False)
    _stats: MergeStats = field(default_factory=MergeStats, repr=False)

    def __post_init__(self) -> None:
        """Validate initialization parameters."""
        if self.time_tolerance < 0:
            raise ValueError("time_tolerance must be non-negative")
        if self.min_gap < 0:
            raise ValueError("min_gap must be non-negative")

    @property
    def stats(self) -> MergeStats:
        """Return merge statistics."""
        return self._stats

    @property
    def has_pending(self) -> bool:
        """Check if there's a pending segment."""
        return self._pending is not None

    @property
    def pending_segment(self) -> Segment | None:
        """Return pending segment without removing it."""
        return self._pending

    def add_segment(self, segment: Segment) -> list[Segment]:
        """
        Add segment and return any completed merged segments.

        Checks if the new segment should be merged with the pending
        segment. If not mergeable, returns the pending segment and
        stores the new one as pending.

        Args:
            segment: Segment to add.

        Returns:
            List of completed segments (may be empty).
        """
        self._stats.segments_received += 1
        result: list[Segment] = []

        if self._pending is None:
            # First segment, just store as pending
            self._pending = segment
            return result

        # Check if should merge with pending
        if self.should_merge(self._pending, segment):
            # Merge segments
            self._pending = self.merge(self._pending, segment)
            self._stats.segments_merged += 1
        else:
            # Not mergeable, output pending and store new
            result.append(self._pending)
            self._stats.segments_output += 1
            self._pending = segment

        return result

    def add_segments(self, segments: list[Segment]) -> list[Segment]:
        """
        Add multiple segments and return completed segments.

        Args:
            segments: List of segments to add.

        Returns:
            List of completed segments.
        """
        result: list[Segment] = []
        for segment in segments:
            result.extend(self.add_segment(segment))
        return result

    def should_merge(self, seg1: Segment, seg2: Segment) -> bool:
        """
        Check if two segments should be merged.

        Merging criteria:
        1. Same speaker
        2. Time continuity (seg1.end_time close to seg2.start_time)
        3. No significant gap between segments

        Args:
            seg1: First segment (earlier in time).
            seg2: Second segment (later in time).

        Returns:
            True if segments should be merged.
        """
        # Must have same speaker
        if seg1.speaker != seg2.speaker:
            return False

        # Check time continuity
        time_gap = seg2.start_time - seg1.end_time

        # If gap is negative (overlap), always merge
        if time_gap < 0:
            return True

        # If gap is within tolerance, merge
        return time_gap <= self.time_tolerance

    def merge(self, seg1: Segment, seg2: Segment) -> Segment:
        """
        Merge two segments into one.

        Combines content, updates time information, and calculates
        weighted average confidence.

        Args:
            seg1: First segment (earlier).
            seg2: Second segment (later).

        Returns:
            Merged segment.

        Raises:
            MergeError: If segments cannot be merged.
        """
        if seg1.speaker != seg2.speaker:
            raise MergeError(
                f"Cannot merge segments with different speakers: {seg1.speaker} vs {seg2.speaker}"
            )

        # Combine content with space if needed
        content = self._merge_content(seg1.content, seg2.content)

        # Calculate weighted average confidence
        confidence = self._calculate_merged_confidence(seg1, seg2)

        # Create merged segment with new ID
        merged_id = f"{seg1.id}_merged"

        return Segment(
            id=merged_id,
            speaker=seg1.speaker,
            start_time=seg1.start_time,
            end_time=seg2.end_time,
            content=content,
            confidence=confidence,
        )

    def _merge_content(self, content1: str, content2: str) -> str:
        """
        Merge content from two segments.

        Handles various edge cases like trailing/leading whitespace,
        punctuation, and partial words.

        Args:
            content1: First segment content.
            content2: Second segment content.

        Returns:
            Merged content string.
        """
        # Strip both contents
        c1 = content1.rstrip()
        c2 = content2.lstrip()

        if not c1:
            return c2
        if not c2:
            return c1

        # Check if this looks like a word split (mid-word boundary)
        # A word split is indicated by:
        # - Both characters are lowercase ASCII letters (mid-word split)
        # - Both characters are Korean (Korean words don't use spaces internally)
        last_char = c1[-1]
        first_char = c2[0]

        is_word_split = self._is_word_split_boundary(last_char, first_char)

        if is_word_split:
            # Likely a split word, join without space
            return c1 + c2

        # Add space between if not already present
        if c1[-1] in " \t" or c2[0] in " \t":
            return c1 + c2

        return c1 + " " + c2

    def _is_word_split_boundary(self, last_char: str, first_char: str) -> bool:
        """
        Check if the boundary indicates a word split.

        A word split is when a word was cut in the middle during
        chunk processing. This is indicated by:
        - Both chars are lowercase ASCII letters (mid-word in English)
        - Both chars are Korean (no spaces within Korean words)

        Args:
            last_char: Last character of first content.
            first_char: First character of second content.

        Returns:
            True if this looks like a word split.
        """
        # Both lowercase ASCII letters = likely mid-word split
        if (
            last_char.islower()
            and last_char.isascii()
            and first_char.islower()
            and first_char.isascii()
        ):
            return True

        # Both Korean characters = likely mid-word split
        return self._is_korean_char(last_char) and self._is_korean_char(first_char)

    def _is_korean_char(self, char: str) -> bool:
        """
        Check if character is Korean.

        Args:
            char: Single character to check.

        Returns:
            True if Korean character.
        """
        if len(char) != 1:
            return False
        code = ord(char)
        # Korean Unicode ranges
        # Hangul Syllables: U+AC00 - U+D7A3
        # Hangul Jamo: U+1100 - U+11FF
        # Hangul Compatibility Jamo: U+3130 - U+318F
        return 0xAC00 <= code <= 0xD7A3 or 0x1100 <= code <= 0x11FF or 0x3130 <= code <= 0x318F

    def _calculate_merged_confidence(self, seg1: Segment, seg2: Segment) -> float:
        """
        Calculate weighted average confidence for merged segment.

        Weights confidence by segment duration.

        Args:
            seg1: First segment.
            seg2: Second segment.

        Returns:
            Weighted average confidence.
        """
        duration1 = seg1.duration
        duration2 = seg2.duration
        total_duration = duration1 + duration2

        if total_duration == 0:
            return (seg1.confidence + seg2.confidence) / 2

        weighted = (seg1.confidence * duration1 + seg2.confidence * duration2) / total_duration

        # Ensure confidence is in valid range
        return max(0.0, min(1.0, weighted))

    def flush(self) -> list[Segment]:
        """
        Flush pending segment and return it.

        Returns any pending segment that hasn't been output yet.

        Returns:
            List containing pending segment or empty list.
        """
        result: list[Segment] = []

        if self._pending is not None:
            result.append(self._pending)
            self._stats.segments_output += 1
            self._pending = None

        return result

    def reset(self) -> None:
        """Reset merger state completely."""
        self._pending = None
        self._stats = MergeStats()

    def process_batch(self, segments: list[Segment], is_last: bool = False) -> list[Segment]:
        """
        Process a batch of segments.

        Convenience method that adds all segments and optionally
        flushes at the end.

        Args:
            segments: List of segments to process.
            is_last: Whether this is the last batch.

        Returns:
            List of completed segments.
        """
        result = self.add_segments(segments)

        if is_last:
            result.extend(self.flush())

        return result


def detect_split_segments(segments: list[Segment]) -> list[tuple[int, int]]:
    """
    Detect potentially split segments in a list.

    Identifies pairs of adjacent segments that may have been
    split during chunk processing.

    Args:
        segments: List of segments to analyze.

    Returns:
        List of (index1, index2) tuples for potential splits.
    """
    splits: list[tuple[int, int]] = []
    merger = SegmentMerger()

    for i in range(len(segments) - 1):
        if merger.should_merge(segments[i], segments[i + 1]):
            splits.append((i, i + 1))

    return splits


def merge_all_continuous(segments: list[Segment]) -> list[Segment]:
    """
    Merge all continuous segments in a list.

    Processes the entire list and merges any adjacent segments
    that meet the merging criteria.

    Args:
        segments: List of segments to process.

    Returns:
        List of merged segments.
    """
    if not segments:
        return []

    merger = SegmentMerger()
    return merger.process_batch(segments, is_last=True)


def validate_segment_continuity(segments: list[Segment]) -> list[str]:
    """
    Validate segment time continuity.

    Checks for gaps and overlaps in segment timing.

    Args:
        segments: List of segments to validate.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: list[str] = []

    for i in range(len(segments) - 1):
        seg1 = segments[i]
        seg2 = segments[i + 1]

        gap = seg2.start_time - seg1.end_time

        if gap < -1.0:
            # Significant overlap
            errors.append(f"Segment {i} and {i + 1} have significant overlap: {-gap:.2f}s")
        elif gap > 10.0:
            # Large gap
            errors.append(f"Large gap between segment {i} and {i + 1}: {gap:.2f}s")

    return errors
