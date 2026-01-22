"""
Chunk processor module for parsing text segments from byte chunks.

Handles decoding and parsing of file chunks into structured
Segment objects with support for chunk boundary handling.
"""

import re
import uuid
from typing import Protocol

from forensic.models.transcript import Segment


class ChunkProcessorProtocol(Protocol):
    """Chunk processor interface protocol."""

    def process(self, chunk: bytes, is_last: bool = False) -> list[Segment]:
        """Process chunk and return segments."""
        ...

    def get_pending(self) -> str | None:
        """Return pending incomplete text."""
        ...

    def flush(self) -> list[Segment]:
        """Flush remaining buffer and return segments."""
        ...


class DecodingError(Exception):
    """Raised when chunk decoding fails."""

    pass


class ChunkProcessor:
    """
    Processor for converting byte chunks to Segment objects.

    Handles text decoding, segment boundary detection, and buffering
    of incomplete segments across chunk boundaries.

    The processor maintains a buffer for incomplete text that spans
    chunk boundaries, ensuring no data is lost during processing.

    Attributes:
        encoding: Text encoding for decoding bytes.
        speaker: Default speaker ID for parsed segments.
    """

    # Pattern to match segment-like text blocks
    # Matches lines that look like speaker turns or timestamped entries
    SEGMENT_PATTERN = re.compile(
        r"(?P<speaker>[^\n:]+?):\s*(?P<content>.+?)(?=\n[^\n:]+:|\n\n|\Z)",
        re.DOTALL,
    )

    # Pattern for timestamp format [HH:MM:SS] or [MM:SS] or (HH:MM:SS)
    TIMESTAMP_PATTERN = re.compile(
        r"[\[\(]?(?:(?P<hours>\d{1,2}):)?(?P<minutes>\d{1,2}):(?P<seconds>\d{2})[\]\)]?",
    )

    def __init__(
        self,
        encoding: str = "utf-8",
        default_speaker: str = "unknown",
        default_confidence: float = 1.0,
    ) -> None:
        """
        Initialize chunk processor.

        Args:
            encoding: Text encoding for decoding bytes.
            default_speaker: Default speaker ID for segments without speaker.
            default_confidence: Default confidence score for segments.
        """
        self._encoding = encoding
        self._default_speaker = default_speaker
        self._default_confidence = default_confidence
        self._buffer: str = ""
        self._current_time: float = 0.0
        self._segment_counter: int = 0

    @property
    def encoding(self) -> str:
        """Return text encoding."""
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        """Set text encoding."""
        self._encoding = value

    def process(self, chunk: bytes, is_last: bool = False) -> list[Segment]:
        """
        Process byte chunk and return list of segments.

        Decodes the chunk, combines with buffered text, and parses
        complete segments. Incomplete text is buffered for the next chunk.

        Args:
            chunk: Byte chunk to process.
            is_last: Whether this is the last chunk in the file.

        Returns:
            List of parsed Segment objects.

        Raises:
            DecodingError: If chunk cannot be decoded.
        """
        # Decode chunk
        text = self._decode_chunk(chunk)

        # Combine with buffer
        combined = self._buffer + text

        # Parse segments
        segments, remaining = self._parse_segments(combined, is_last)

        # Update buffer
        self._buffer = remaining if not is_last else ""

        return segments

    def _decode_chunk(self, chunk: bytes) -> str:
        """
        Decode byte chunk to string.

        Args:
            chunk: Byte chunk to decode.

        Returns:
            Decoded string.

        Raises:
            DecodingError: If decoding fails.
        """
        try:
            return chunk.decode(self._encoding, errors="replace")
        except Exception as e:
            raise DecodingError(f"Failed to decode chunk: {e}") from e

    def _parse_segments(
        self, text: str, include_incomplete: bool = False
    ) -> tuple[list[Segment], str]:
        """
        Parse text into segments.

        Identifies complete segments and returns them along with
        any remaining incomplete text.

        Args:
            text: Text to parse.
            include_incomplete: Whether to include incomplete segments.

        Returns:
            Tuple of (segments list, remaining text).
        """
        segments: list[Segment] = []

        # Try pattern-based parsing
        matches = list(self.SEGMENT_PATTERN.finditer(text))

        if matches:
            last_end = 0

            for match in matches:
                speaker = match.group("speaker").strip()
                content = match.group("content").strip()

                if content:
                    segment = self._create_segment(speaker, content)
                    segments.append(segment)

                last_end = match.end()

            # Remaining text after last match
            remaining = text[last_end:].strip()

        else:
            # Fall back to line-based parsing
            segments, remaining = self._parse_lines(text, include_incomplete)

        return segments, remaining

    def _parse_lines(
        self, text: str, include_incomplete: bool = False
    ) -> tuple[list[Segment], str]:
        """
        Parse text line by line.

        Simple line-based parsing for text without clear speaker patterns.

        Args:
            text: Text to parse.
            include_incomplete: Whether to include incomplete segments.

        Returns:
            Tuple of (segments list, remaining text).
        """
        segments: list[Segment] = []
        lines = text.split("\n")

        # Check if last line might be incomplete
        complete_lines = lines[:-1] if lines and not include_incomplete else lines
        remaining = lines[-1] if lines and not include_incomplete else ""

        # Group consecutive non-empty lines as segments
        current_content: list[str] = []

        for line in complete_lines:
            line = line.strip()
            if line:
                current_content.append(line)
            elif current_content:
                # Empty line marks end of segment
                content = " ".join(current_content)
                segment = self._create_segment(self._default_speaker, content)
                segments.append(segment)
                current_content = []

        # Handle remaining content
        if current_content and include_incomplete:
            content = " ".join(current_content)
            segment = self._create_segment(self._default_speaker, content)
            segments.append(segment)
        elif current_content:
            # Add to remaining
            remaining = " ".join(current_content) + (" " + remaining if remaining else "")

        return segments, remaining.strip()

    def _create_segment(self, speaker: str, content: str) -> Segment:
        """
        Create a Segment object with auto-generated metadata.

        Args:
            speaker: Speaker identifier.
            content: Segment content.

        Returns:
            Segment object.
        """
        # Estimate duration based on content length (rough approximation)
        # Average speech rate: ~150 words per minute, ~5 chars per word
        char_count = len(content)
        estimated_duration = max(0.5, char_count / 750.0 * 60.0)  # seconds

        start_time = self._current_time
        end_time = start_time + estimated_duration
        self._current_time = end_time

        self._segment_counter += 1

        return Segment(
            id=f"seg_{uuid.uuid4().hex[:8]}",
            speaker=speaker if speaker else self._default_speaker,
            start_time=start_time,
            end_time=end_time,
            content=content,
            confidence=self._default_confidence,
        )

    def get_pending(self) -> str | None:
        """
        Return pending incomplete text in buffer.

        Returns:
            Buffered text or None if buffer is empty.
        """
        return self._buffer if self._buffer else None

    def flush(self) -> list[Segment]:
        """
        Flush buffer and return any remaining segments.

        Processes any remaining buffered text and returns
        the resulting segments.

        Returns:
            List of segments from remaining buffer.
        """
        if not self._buffer:
            return []

        # Process remaining buffer as last chunk
        segments, _ = self._parse_segments(self._buffer, include_incomplete=True)
        self._buffer = ""

        return segments

    def reset(self) -> None:
        """
        Reset processor state.

        Clears buffer and resets time tracking.
        """
        self._buffer = ""
        self._current_time = 0.0
        self._segment_counter = 0


class TimestampedChunkProcessor(ChunkProcessor):
    """
    Chunk processor with timestamp extraction support.

    Extends ChunkProcessor to extract and use timestamps from
    formatted transcript text.
    """

    # Pattern for timestamped entries: [00:00:00] Speaker: Content
    TIMESTAMPED_ENTRY_PATTERN = re.compile(
        r"[\[\(]?(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[\]\)]?\s*"
        r"(?:([^\n:]+?):\s*)?(.+?)(?=[\[\(]?\d{1,2}:|\n\n|\Z)",
        re.DOTALL,
    )

    def _parse_segments(
        self, text: str, include_incomplete: bool = False
    ) -> tuple[list[Segment], str]:
        """
        Parse text with timestamp extraction.

        Overrides parent to extract timestamps from formatted text.

        Args:
            text: Text to parse.
            include_incomplete: Whether to include incomplete segments.

        Returns:
            Tuple of (segments list, remaining text).
        """
        segments: list[Segment] = []
        matches = list(self.TIMESTAMPED_ENTRY_PATTERN.finditer(text))

        if matches:
            last_end = 0

            for i, match in enumerate(matches):
                hours = int(match.group(1)) if match.group(1) else 0
                minutes = int(match.group(2))
                seconds = int(match.group(3))
                speaker = match.group(4)
                content = match.group(5)

                if content:
                    content = content.strip()
                    start_time = hours * 3600 + minutes * 60 + seconds

                    # Calculate end time from next entry or estimate
                    if i + 1 < len(matches):
                        next_match = matches[i + 1]
                        nh = int(next_match.group(1)) if next_match.group(1) else 0
                        nm = int(next_match.group(2))
                        ns = int(next_match.group(3))
                        end_time = nh * 3600 + nm * 60 + ns
                    else:
                        # Estimate duration for last segment
                        char_count = len(content)
                        end_time = start_time + max(0.5, char_count / 750.0 * 60.0)

                    self._segment_counter += 1

                    segment = Segment(
                        id=f"seg_{uuid.uuid4().hex[:8]}",
                        speaker=speaker.strip() if speaker else self._default_speaker,
                        start_time=start_time,
                        end_time=end_time,
                        content=content,
                        confidence=self._default_confidence,
                    )
                    segments.append(segment)

                last_end = match.end()

            remaining = text[last_end:].strip()
            return segments, remaining

        # Fall back to parent implementation
        return super()._parse_segments(text, include_incomplete)
