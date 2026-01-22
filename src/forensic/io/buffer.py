"""
Buffer manager module for handling chunk boundaries.

Provides intelligent buffering for incomplete lines and UTF-8
multibyte character handling across chunk boundaries.
"""

from dataclasses import dataclass, field
from typing import Protocol

# Default buffer size limit (64KB)
DEFAULT_BUFFER_SIZE_LIMIT: int = 64 * 1024

# UTF-8 byte patterns for detecting incomplete multibyte sequences
# Leading bytes: 110xxxxx (2-byte), 1110xxxx (3-byte), 11110xxx (4-byte)
UTF8_CONTINUATION_MASK: int = 0xC0
UTF8_CONTINUATION_VALUE: int = 0x80
UTF8_2BYTE_LEAD: int = 0xC0
UTF8_3BYTE_LEAD: int = 0xE0
UTF8_4BYTE_LEAD: int = 0xF0


class BufferManagerProtocol(Protocol):
    """Buffer manager interface protocol."""

    def append(self, data: bytes) -> bytes:
        """Append data to buffer and return complete bytes."""
        ...

    def get_incomplete_line(self) -> str | None:
        """Return incomplete line from buffer."""
        ...

    def set_incomplete_line(self, line: str) -> None:
        """Set incomplete line in buffer."""
        ...

    def flush(self) -> tuple[bytes, str]:
        """Flush buffer and return remaining data."""
        ...

    def reset(self) -> None:
        """Reset buffer state."""
        ...


class BufferOverflowError(Exception):
    """Raised when buffer exceeds size limit."""

    pass


class InvalidUTF8Error(Exception):
    """Raised when invalid UTF-8 sequence is detected."""

    pass


@dataclass
class BufferState:
    """
    Current buffer state information.

    Attributes:
        byte_buffer_size: Current byte buffer size.
        line_buffer_size: Current line buffer size.
        total_size: Total buffer size.
        is_at_limit: Whether buffer is at size limit.
    """

    byte_buffer_size: int
    line_buffer_size: int
    total_size: int
    is_at_limit: bool


@dataclass
class BufferManager:
    """
    Buffer manager for handling chunk boundaries.

    Manages incomplete data across chunk boundaries with support for:
    - UTF-8 multibyte character handling (Korean 3-byte, emoji 4-byte)
    - Incomplete line buffering
    - Memory-efficient buffer management with size limits

    Attributes:
        size_limit: Maximum buffer size in bytes.
    """

    size_limit: int = DEFAULT_BUFFER_SIZE_LIMIT
    _byte_buffer: bytes = field(default=b"", repr=False)
    _line_buffer: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        """Validate initialization parameters."""
        if self.size_limit <= 0:
            raise ValueError("size_limit must be positive")

    @property
    def byte_buffer_size(self) -> int:
        """Return current byte buffer size."""
        return len(self._byte_buffer)

    @property
    def line_buffer_size(self) -> int:
        """Return current line buffer size in bytes."""
        return len(self._line_buffer.encode("utf-8"))

    @property
    def total_size(self) -> int:
        """Return total buffer size in bytes."""
        return self.byte_buffer_size + self.line_buffer_size

    def get_state(self) -> BufferState:
        """
        Return current buffer state.

        Returns:
            BufferState with current buffer information.
        """
        return BufferState(
            byte_buffer_size=self.byte_buffer_size,
            line_buffer_size=self.line_buffer_size,
            total_size=self.total_size,
            is_at_limit=self.total_size >= self.size_limit,
        )

    def append(self, data: bytes) -> bytes:
        """
        Append data to buffer and return complete bytes.

        Handles UTF-8 multibyte character boundaries by detecting
        incomplete sequences at chunk boundaries.

        Args:
            data: Byte data to append.

        Returns:
            Complete bytes safe for UTF-8 decoding.

        Raises:
            BufferOverflowError: If buffer exceeds size limit.
        """
        if not data:
            return self._byte_buffer

        # Combine existing buffer with new data
        combined = self._byte_buffer + data

        # Check buffer limit
        if len(combined) > self.size_limit:
            # Try to process what we can
            complete, incomplete = self._split_at_utf8_boundary(combined)
            if len(incomplete) > self.size_limit:
                raise BufferOverflowError(
                    f"Buffer overflow: {len(incomplete)} bytes exceeds limit {self.size_limit}"
                )
            self._byte_buffer = incomplete
            return complete

        # Find UTF-8 boundary
        complete, incomplete = self._split_at_utf8_boundary(combined)
        self._byte_buffer = incomplete

        return complete

    def _split_at_utf8_boundary(self, data: bytes) -> tuple[bytes, bytes]:
        """
        Split data at UTF-8 character boundary.

        Finds the last complete UTF-8 character and splits there,
        leaving incomplete sequences in the buffer.

        Args:
            data: Byte data to split.

        Returns:
            Tuple of (complete_bytes, incomplete_bytes).
        """
        if not data:
            return b"", b""

        # Find the last byte that could be a UTF-8 leading byte
        # Check up to 4 bytes from the end (max UTF-8 sequence length)
        for i in range(min(4, len(data)), 0, -1):
            idx = len(data) - i
            byte = data[idx]

            # Check if this is a leading byte
            if byte >= UTF8_4BYTE_LEAD:
                # 4-byte sequence (11110xxx)
                expected_length = 4
            elif byte >= UTF8_3BYTE_LEAD:
                # 3-byte sequence (1110xxxx)
                expected_length = 3
            elif byte >= UTF8_2BYTE_LEAD:
                # 2-byte sequence (110xxxxx)
                expected_length = 2
            elif (byte & UTF8_CONTINUATION_MASK) == UTF8_CONTINUATION_VALUE:
                # Continuation byte (10xxxxxx) - keep looking
                continue
            else:
                # ASCII byte (0xxxxxxx) - complete
                continue

            # Check if we have enough bytes for the sequence
            remaining_bytes = len(data) - idx
            if remaining_bytes < expected_length:
                # Incomplete sequence - split here
                return data[:idx], data[idx:]

        # All bytes are complete
        return data, b""

    def get_incomplete_line(self) -> str | None:
        """
        Return incomplete line from buffer.

        Returns:
            Incomplete line string or None if buffer is empty.
        """
        return self._line_buffer if self._line_buffer else None

    def set_incomplete_line(self, line: str) -> None:
        """
        Set incomplete line in buffer.

        Args:
            line: Incomplete line to buffer.

        Raises:
            BufferOverflowError: If total buffer exceeds size limit.
        """
        line_bytes = len(line.encode("utf-8"))
        if self.byte_buffer_size + line_bytes > self.size_limit:
            raise BufferOverflowError(
                f"Buffer overflow: adding {line_bytes} bytes would exceed limit {self.size_limit}"
            )
        self._line_buffer = line

    def prepend_to_text(self, text: str) -> str:
        """
        Prepend buffered incomplete line to text.

        Combines the buffered incomplete line with new text
        and clears the line buffer.

        Args:
            text: Text to prepend to.

        Returns:
            Combined text with buffered line prepended.
        """
        if self._line_buffer:
            combined = self._line_buffer + text
            self._line_buffer = ""
            return combined
        return text

    def flush(self) -> tuple[bytes, str]:
        """
        Flush buffer and return remaining data.

        Returns all buffered data and resets the buffer state.

        Returns:
            Tuple of (byte_buffer, line_buffer).
        """
        byte_data = self._byte_buffer
        line_data = self._line_buffer
        self._byte_buffer = b""
        self._line_buffer = ""
        return byte_data, line_data

    def flush_bytes(self) -> bytes:
        """
        Flush only byte buffer and return remaining bytes.

        Returns:
            Remaining bytes from buffer.
        """
        byte_data = self._byte_buffer
        self._byte_buffer = b""
        return byte_data

    def flush_line(self) -> str:
        """
        Flush only line buffer and return remaining line.

        Returns:
            Remaining line from buffer.
        """
        line_data = self._line_buffer
        self._line_buffer = ""
        return line_data

    def reset(self) -> None:
        """Reset buffer state completely."""
        self._byte_buffer = b""
        self._line_buffer = ""

    def has_pending_data(self) -> bool:
        """
        Check if buffer has any pending data.

        Returns:
            True if buffer has pending bytes or lines.
        """
        return bool(self._byte_buffer) or bool(self._line_buffer)

    def decode_safe(self, data: bytes, encoding: str = "utf-8") -> tuple[str, bytes]:
        """
        Safely decode bytes handling incomplete sequences.

        Attempts to decode bytes and returns any incomplete
        sequence that couldn't be decoded.

        Args:
            data: Bytes to decode.
            encoding: Text encoding to use.

        Returns:
            Tuple of (decoded_string, incomplete_bytes).
        """
        # Combine with existing byte buffer
        combined = self._byte_buffer + data

        # Find safe boundary
        complete, incomplete = self._split_at_utf8_boundary(combined)

        # Update buffer with incomplete bytes
        self._byte_buffer = incomplete

        # Decode complete bytes
        try:
            decoded = complete.decode(encoding)
            return decoded, incomplete
        except UnicodeDecodeError:
            # Fall back to replacement mode
            decoded = complete.decode(encoding, errors="replace")
            return decoded, incomplete


def is_valid_utf8_sequence(data: bytes) -> bool:
    """
    Check if byte sequence is valid UTF-8.

    Args:
        data: Byte sequence to validate.

    Returns:
        True if valid UTF-8, False otherwise.
    """
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def get_utf8_char_length(leading_byte: int) -> int:
    """
    Get expected length of UTF-8 character from leading byte.

    Args:
        leading_byte: First byte of UTF-8 sequence.

    Returns:
        Expected character length in bytes (1-4).
    """
    if leading_byte < 0x80:
        return 1  # ASCII
    elif leading_byte < 0xC0:
        return 0  # Continuation byte (invalid as leading)
    elif leading_byte < 0xE0:
        return 2  # 2-byte sequence
    elif leading_byte < 0xF0:
        return 3  # 3-byte sequence (Korean, etc.)
    elif leading_byte < 0xF8:
        return 4  # 4-byte sequence (emoji, etc.)
    else:
        return 0  # Invalid


def find_last_complete_char(data: bytes) -> int:
    """
    Find index of last complete UTF-8 character in data.

    Args:
        data: Byte data to analyze.

    Returns:
        Index after last complete character.
    """
    if not data:
        return 0

    # Check from the end for incomplete sequences
    for i in range(min(4, len(data)), 0, -1):
        idx = len(data) - i
        byte = data[idx]
        expected_length = get_utf8_char_length(byte)

        if expected_length == 0:
            # Continuation byte, keep looking
            continue

        remaining = len(data) - idx
        if remaining >= expected_length:
            # Complete character, check if there's more after
            return len(data)
        else:
            # Incomplete character, return position before it
            return idx

    return len(data)
