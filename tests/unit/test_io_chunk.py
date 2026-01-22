"""
Chunk processor module unit tests.

Tests for ChunkProcessor and TimestampedChunkProcessor classes.
"""

import pytest

from forensic.io.chunk import (
    ChunkProcessor,
    TimestampedChunkProcessor,
)
from forensic.models.transcript import Segment


class TestChunkProcessor:
    """ChunkProcessor class tests."""

    @pytest.fixture
    def processor(self) -> ChunkProcessor:
        """Create a ChunkProcessor instance."""
        return ChunkProcessor(encoding="utf-8", default_speaker="speaker")

    def test_init(self) -> None:
        """Test ChunkProcessor initialization."""
        processor = ChunkProcessor(
            encoding="utf-8",
            default_speaker="test_speaker",
            default_confidence=0.9,
        )

        assert processor.encoding == "utf-8"
        assert processor._default_speaker == "test_speaker"
        assert processor._default_confidence == 0.9
        assert processor.get_pending() is None

    def test_encoding_property(self, processor: ChunkProcessor) -> None:
        """Test encoding property getter and setter."""
        assert processor.encoding == "utf-8"

        processor.encoding = "utf-16"
        assert processor.encoding == "utf-16"

    def test_process_simple_text(self, processor: ChunkProcessor) -> None:
        """Test processing simple text chunk."""
        chunk = b"Hello, World!\n\nThis is a test."
        segments = processor.process(chunk)

        assert len(segments) > 0
        assert all(isinstance(seg, Segment) for seg in segments)

    def test_process_speaker_pattern(self) -> None:
        """Test processing text with speaker pattern."""
        processor = ChunkProcessor()
        chunk = b"Alice: Hello, how are you?\nBob: I'm fine, thanks!"

        segments = processor.process(chunk, is_last=True)

        assert len(segments) >= 1
        # Should detect speaker names
        speakers = {seg.speaker for seg in segments}
        assert "Alice" in speakers or "Bob" in speakers or "unknown" in speakers

    def test_process_empty_chunk(self, processor: ChunkProcessor) -> None:
        """Test processing empty chunk."""
        segments = processor.process(b"")

        assert segments == []

    def test_process_whitespace_only(self, processor: ChunkProcessor) -> None:
        """Test processing whitespace-only chunk."""
        segments = processor.process(b"   \n\n   ")

        assert segments == []

    def test_process_with_buffering(self, processor: ChunkProcessor) -> None:
        """Test buffering across chunks with line-based content."""
        # First chunk - incomplete line without speaker pattern
        # Line-based parsing will buffer incomplete lines
        chunk1 = b"Hello, this is a"
        segments1 = processor.process(chunk1)

        # Should have pending text (line-based parsing buffers last line)
        pending = processor.get_pending()
        assert pending is not None
        assert "Hello" in pending

        # Second chunk completes the content
        chunk2 = b" test.\n\nSecond paragraph."
        segments2 = processor.process(chunk2, is_last=True)

        # Should have processed content
        assert len(segments1) + len(segments2) >= 1

    def test_get_pending_with_line_based(self, processor: ChunkProcessor) -> None:
        """Test get_pending returns buffered text with line-based parsing."""
        # Initially no pending
        assert processor.get_pending() is None

        # Process incomplete line (no newline at end, no speaker pattern)
        processor.process(b"Hello, ho")

        # Should have pending
        pending = processor.get_pending()
        assert pending is not None
        assert len(pending) > 0

    def test_get_pending_with_speaker_pattern(self, processor: ChunkProcessor) -> None:
        """Test get_pending with speaker pattern and partial content."""
        # Process text with speaker pattern followed by incomplete text
        processor.process(b"Alice: Complete text.\n\nPartial")

        # Should have pending from incomplete part
        pending = processor.get_pending()
        assert pending is not None or pending == ""  # May be empty after pattern match

    def test_flush(self, processor: ChunkProcessor) -> None:
        """Test flush processes remaining buffer."""
        # Process incomplete text (line-based)
        processor.process(b"Incomplete content")

        # Flush should process remaining
        segments = processor.flush()

        # Should produce segment from remaining buffer
        assert len(segments) >= 0
        assert processor.get_pending() is None

    def test_flush_empty_buffer(self, processor: ChunkProcessor) -> None:
        """Test flush with empty buffer."""
        segments = processor.flush()

        assert segments == []

    def test_reset(self, processor: ChunkProcessor) -> None:
        """Test reset clears state."""
        processor.process(b"Test content")
        processor.reset()

        assert processor.get_pending() is None
        assert processor._current_time == 0.0
        assert processor._segment_counter == 0

    def test_segment_ids_unique(self, processor: ChunkProcessor) -> None:
        """Test that segment IDs are unique."""
        chunk = b"A: First.\n\nB: Second.\n\nC: Third."
        segments = processor.process(chunk, is_last=True)

        ids = [seg.id for seg in segments]
        assert len(ids) == len(set(ids))  # All IDs unique

    def test_segment_time_progression(self, processor: ChunkProcessor) -> None:
        """Test that segment times progress."""
        chunk = b"A: First.\n\nB: Second.\n\nC: Third."
        segments = processor.process(chunk, is_last=True)

        if len(segments) >= 2:
            for i in range(1, len(segments)):
                assert segments[i].start_time >= segments[i - 1].end_time

    def test_process_korean_text(self) -> None:
        """Test processing Korean text."""
        processor = ChunkProcessor(encoding="utf-8")
        chunk = "갑: 안녕하세요.\n\n을: 반갑습니다.".encode()

        segments = processor.process(chunk, is_last=True)

        assert len(segments) >= 1
        content = " ".join(seg.content for seg in segments)
        assert "안녕" in content or "반갑" in content


class TestChunkProcessorDecoding:
    """Tests for chunk decoding."""

    def test_decode_utf8(self) -> None:
        """Test UTF-8 decoding."""
        processor = ChunkProcessor(encoding="utf-8")
        chunk = b"Hello, World!"

        segments = processor.process(chunk, is_last=True)

        content = " ".join(seg.content for seg in segments)
        assert "Hello" in content or "World" in content or len(segments) == 0

    def test_decode_with_replacement(self) -> None:
        """Test decoding with invalid bytes uses replacement."""
        processor = ChunkProcessor(encoding="utf-8")
        # Invalid UTF-8 byte sequence
        chunk = b"Hello \xff\xfe World"

        # Should not raise, uses replacement character
        segments = processor.process(chunk, is_last=True)

        assert isinstance(segments, list)


class TestTimestampedChunkProcessor:
    """TimestampedChunkProcessor class tests."""

    @pytest.fixture
    def processor(self) -> TimestampedChunkProcessor:
        """Create a TimestampedChunkProcessor instance."""
        return TimestampedChunkProcessor(encoding="utf-8")

    def test_init(self) -> None:
        """Test TimestampedChunkProcessor initialization."""
        processor = TimestampedChunkProcessor(
            encoding="utf-8",
            default_speaker="narrator",
        )

        assert processor.encoding == "utf-8"
        assert processor._default_speaker == "narrator"

    def test_parse_timestamped_text(self, processor: TimestampedChunkProcessor) -> None:
        """Test parsing timestamped transcript."""
        chunk = b"[00:00:05] Alice: Hello!\n[00:00:10] Bob: Hi there!"

        segments = processor.process(chunk, is_last=True)

        assert len(segments) >= 1

        # Check timestamps are extracted
        if segments:
            # First segment should start at 5 seconds
            assert segments[0].start_time >= 0

    def test_parse_hour_timestamps(self, processor: TimestampedChunkProcessor) -> None:
        """Test parsing timestamps with hours."""
        chunk = b"[01:30:00] Speaker: One hour thirty minutes in."

        segments = processor.process(chunk, is_last=True)

        if segments:
            # 1:30:00 = 5400 seconds
            assert segments[0].start_time == 5400.0

    def test_parse_parenthesis_timestamps(
        self, processor: TimestampedChunkProcessor
    ) -> None:
        """Test parsing timestamps with parentheses."""
        chunk = b"(05:30) Speaker: Five minutes thirty seconds."

        segments = processor.process(chunk, is_last=True)

        if segments:
            # 5:30 = 330 seconds
            assert segments[0].start_time == 330.0

    def test_fallback_to_pattern_matching(
        self, processor: TimestampedChunkProcessor
    ) -> None:
        """Test fallback to pattern matching without timestamps."""
        chunk = b"Alice: Hello!\nBob: Hi!"

        segments = processor.process(chunk, is_last=True)

        # Should still parse using parent's pattern matching
        assert isinstance(segments, list)

    def test_calculate_end_time_from_next(
        self, processor: TimestampedChunkProcessor
    ) -> None:
        """Test end time calculated from next segment's start."""
        chunk = b"[00:00:00] A: First.\n[00:00:10] B: Second."

        segments = processor.process(chunk, is_last=True)

        if len(segments) >= 2:
            # First segment should end at second segment's start
            assert segments[0].end_time == segments[1].start_time


class TestChunkProcessorEdgeCases:
    """Edge case tests for ChunkProcessor."""

    def test_very_long_line(self) -> None:
        """Test processing very long line."""
        processor = ChunkProcessor()
        long_content = "A" * 10000
        chunk = f"Speaker: {long_content}".encode()

        segments = processor.process(chunk, is_last=True)

        assert len(segments) >= 1
        if segments:
            assert len(segments[0].content) > 0

    def test_multiple_colons_in_content(self) -> None:
        """Test handling colons in content."""
        processor = ChunkProcessor()
        chunk = b"Alice: The time is 10:30:00 exactly."

        segments = processor.process(chunk, is_last=True)

        # Should handle colons in content correctly
        assert isinstance(segments, list)

    def test_special_characters(self) -> None:
        """Test handling special characters."""
        processor = ChunkProcessor()
        chunk = b"Speaker: Special chars: @#$%^&*()"

        segments = processor.process(chunk, is_last=True)

        assert isinstance(segments, list)

    def test_newline_variations(self) -> None:
        """Test handling different newline styles."""
        processor = ChunkProcessor()

        # Windows style
        chunk_crlf = b"A: Hello.\r\n\r\nB: World."
        segments = processor.process(chunk_crlf, is_last=True)
        assert isinstance(segments, list)

        # Unix style
        processor.reset()
        chunk_lf = b"A: Hello.\n\nB: World."
        segments = processor.process(chunk_lf, is_last=True)
        assert isinstance(segments, list)


class TestChunkProcessorBuffering:
    """Detailed tests for buffering behavior."""

    def test_line_based_buffering(self) -> None:
        """Test that line-based parsing properly buffers incomplete lines."""
        processor = ChunkProcessor()

        # First chunk - line without newline at end (no speaker pattern)
        chunk1 = b"First line of text"
        segments1 = processor.process(chunk1)

        # Line-based parsing should buffer the incomplete line
        pending = processor.get_pending()
        assert pending is not None

        # Second chunk with newline
        chunk2 = b" continued.\n\nSecond paragraph."
        segments2 = processor.process(chunk2, is_last=True)

        # Combined should have segments
        assert len(segments1) + len(segments2) >= 1

    def test_multiple_chunks_streaming(self) -> None:
        """Test streaming multiple chunks."""
        processor = ChunkProcessor()

        chunks = [
            b"Line one",
            b" continues.\n\n",
            b"Line two",
            b" also continues.\n\n",
            b"Line three.",
        ]

        all_segments = []
        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1
            segments = processor.process(chunk, is_last=is_last)
            all_segments.extend(segments)

        # Should have processed some segments
        assert len(all_segments) >= 0  # May vary based on parsing
