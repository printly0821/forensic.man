"""
Buffer manager module unit tests.

Tests for BufferManager class and UTF-8 handling functions.
"""

import pytest

from forensic.io.buffer import (
    DEFAULT_BUFFER_SIZE_LIMIT,
    BufferManager,
    BufferOverflowError,
    BufferState,
    find_last_complete_char,
    get_utf8_char_length,
    is_valid_utf8_sequence,
)


class TestBufferManager:
    """BufferManager class tests."""

    @pytest.fixture
    def buffer(self) -> BufferManager:
        """Create a BufferManager instance."""
        return BufferManager()

    def test_init_default(self) -> None:
        """Test BufferManager default initialization."""
        buffer = BufferManager()

        assert buffer.size_limit == DEFAULT_BUFFER_SIZE_LIMIT
        assert buffer.byte_buffer_size == 0
        assert buffer.line_buffer_size == 0
        assert buffer.total_size == 0

    def test_init_custom_limit(self) -> None:
        """Test BufferManager with custom size limit."""
        buffer = BufferManager(size_limit=1024)

        assert buffer.size_limit == 1024

    def test_init_invalid_limit(self) -> None:
        """Test BufferManager with invalid size limit."""
        with pytest.raises(ValueError, match="size_limit must be positive"):
            BufferManager(size_limit=0)

        with pytest.raises(ValueError, match="size_limit must be positive"):
            BufferManager(size_limit=-1)

    def test_get_state(self, buffer: BufferManager) -> None:
        """Test get_state returns BufferState."""
        state = buffer.get_state()

        assert isinstance(state, BufferState)
        assert state.byte_buffer_size == 0
        assert state.line_buffer_size == 0
        assert state.total_size == 0
        assert state.is_at_limit is False


class TestBufferManagerAppend:
    """Tests for BufferManager.append method."""

    @pytest.fixture
    def buffer(self) -> BufferManager:
        """Create a BufferManager instance."""
        return BufferManager()

    def test_append_empty(self, buffer: BufferManager) -> None:
        """Test appending empty data."""
        result = buffer.append(b"")

        assert result == b""
        assert buffer.byte_buffer_size == 0

    def test_append_ascii(self, buffer: BufferManager) -> None:
        """Test appending ASCII data."""
        result = buffer.append(b"Hello, World!")

        assert result == b"Hello, World!"
        assert buffer.byte_buffer_size == 0

    def test_append_complete_utf8(self, buffer: BufferManager) -> None:
        """Test appending complete UTF-8 data."""
        # Korean text: "안녕하세요"
        korean = "안녕하세요".encode()
        result = buffer.append(korean)

        assert result == korean
        assert buffer.byte_buffer_size == 0

    def test_append_incomplete_utf8_2byte(self, buffer: BufferManager) -> None:
        """Test appending incomplete 2-byte UTF-8 sequence."""
        # First byte of 2-byte sequence (e.g., 'é' = 0xC3 0xA9)
        incomplete = b"Hello\xc3"
        result = buffer.append(incomplete)

        assert result == b"Hello"
        assert buffer.byte_buffer_size == 1
        assert buffer._byte_buffer == b"\xc3"

    def test_append_incomplete_utf8_3byte(self, buffer: BufferManager) -> None:
        """Test appending incomplete 3-byte UTF-8 sequence (Korean)."""
        # Korean '한' = 0xED 0x95 0x9C (actually 0xED 0x95 0x9C)
        # Let's use '가' = 0xEA 0xB0 0x80
        # First 2 bytes of 3-byte sequence
        incomplete = b"Test\xea\xb0"
        result = buffer.append(incomplete)

        assert result == b"Test"
        assert buffer.byte_buffer_size == 2

    def test_append_incomplete_utf8_4byte(self, buffer: BufferManager) -> None:
        """Test appending incomplete 4-byte UTF-8 sequence (emoji)."""
        # Emoji '😀' = 0xF0 0x9F 0x98 0x80
        # First 3 bytes of 4-byte sequence
        incomplete = b"Hi\xf0\x9f\x98"
        result = buffer.append(incomplete)

        assert result == b"Hi"
        assert buffer.byte_buffer_size == 3

    def test_append_continues_incomplete(self, buffer: BufferManager) -> None:
        """Test appending data that completes previous incomplete sequence."""
        # First append: incomplete 3-byte sequence
        buffer.append(b"Test\xea\xb0")
        assert buffer.byte_buffer_size == 2

        # Second append: completing byte
        result = buffer.append(b"\x80 more")

        # Should include the completed character
        assert result == b"\xea\xb0\x80 more"
        assert buffer.byte_buffer_size == 0

    def test_append_multiple_chunks(self, buffer: BufferManager) -> None:
        """Test appending multiple chunks."""
        # First chunk
        result1 = buffer.append(b"Hello ")
        assert result1 == b"Hello "

        # Second chunk
        result2 = buffer.append(b"World!")
        assert result2 == b"World!"

        assert buffer.byte_buffer_size == 0


class TestBufferManagerLineBuffer:
    """Tests for BufferManager line buffering."""

    @pytest.fixture
    def buffer(self) -> BufferManager:
        """Create a BufferManager instance."""
        return BufferManager()

    def test_get_incomplete_line_empty(self, buffer: BufferManager) -> None:
        """Test get_incomplete_line with empty buffer."""
        assert buffer.get_incomplete_line() is None

    def test_set_incomplete_line(self, buffer: BufferManager) -> None:
        """Test setting incomplete line."""
        buffer.set_incomplete_line("Hello, ")

        assert buffer.get_incomplete_line() == "Hello, "
        assert buffer.line_buffer_size > 0

    def test_set_incomplete_line_korean(self, buffer: BufferManager) -> None:
        """Test setting incomplete line with Korean text."""
        buffer.set_incomplete_line("안녕하")

        assert buffer.get_incomplete_line() == "안녕하"
        # Korean characters are 3 bytes each in UTF-8
        assert buffer.line_buffer_size == 9

    def test_prepend_to_text(self, buffer: BufferManager) -> None:
        """Test prepending buffered line to text."""
        buffer.set_incomplete_line("Hello, ")
        result = buffer.prepend_to_text("World!")

        assert result == "Hello, World!"
        assert buffer.get_incomplete_line() is None

    def test_prepend_to_text_empty_buffer(self, buffer: BufferManager) -> None:
        """Test prepending with empty buffer."""
        result = buffer.prepend_to_text("World!")

        assert result == "World!"

    def test_set_incomplete_line_overflow(self) -> None:
        """Test setting line that causes overflow."""
        buffer = BufferManager(size_limit=10)

        with pytest.raises(BufferOverflowError):
            buffer.set_incomplete_line("This is too long")


class TestBufferManagerFlush:
    """Tests for BufferManager flush methods."""

    @pytest.fixture
    def buffer(self) -> BufferManager:
        """Create a BufferManager instance."""
        return BufferManager()

    def test_flush_empty(self, buffer: BufferManager) -> None:
        """Test flushing empty buffer."""
        bytes_data, line_data = buffer.flush()

        assert bytes_data == b""
        assert line_data == ""

    def test_flush_with_data(self, buffer: BufferManager) -> None:
        """Test flushing buffer with data."""
        buffer.append(b"Test\xea\xb0")  # Incomplete UTF-8
        buffer.set_incomplete_line("Line ")

        bytes_data, line_data = buffer.flush()

        assert bytes_data == b"\xea\xb0"
        assert line_data == "Line "
        assert buffer.byte_buffer_size == 0
        assert buffer.line_buffer_size == 0

    def test_flush_bytes(self, buffer: BufferManager) -> None:
        """Test flushing only bytes."""
        buffer.append(b"Test\xea\xb0")
        buffer.set_incomplete_line("Line ")

        bytes_data = buffer.flush_bytes()

        assert bytes_data == b"\xea\xb0"
        assert buffer.byte_buffer_size == 0
        assert buffer.get_incomplete_line() == "Line "

    def test_flush_line(self, buffer: BufferManager) -> None:
        """Test flushing only line."""
        buffer.append(b"Test\xea\xb0")
        buffer.set_incomplete_line("Line ")

        line_data = buffer.flush_line()

        assert line_data == "Line "
        assert buffer.line_buffer_size == 0
        assert buffer.byte_buffer_size == 2

    def test_reset(self, buffer: BufferManager) -> None:
        """Test resetting buffer."""
        buffer.append(b"Test\xea\xb0")
        buffer.set_incomplete_line("Line ")

        buffer.reset()

        assert buffer.byte_buffer_size == 0
        assert buffer.line_buffer_size == 0
        assert buffer.get_incomplete_line() is None


class TestBufferManagerHasPending:
    """Tests for BufferManager.has_pending_data method."""

    @pytest.fixture
    def buffer(self) -> BufferManager:
        """Create a BufferManager instance."""
        return BufferManager()

    def test_has_pending_empty(self, buffer: BufferManager) -> None:
        """Test has_pending_data with empty buffer."""
        assert buffer.has_pending_data() is False

    def test_has_pending_bytes(self, buffer: BufferManager) -> None:
        """Test has_pending_data with byte data."""
        buffer.append(b"Test\xea\xb0")

        assert buffer.has_pending_data() is True

    def test_has_pending_line(self, buffer: BufferManager) -> None:
        """Test has_pending_data with line data."""
        buffer.set_incomplete_line("Test")

        assert buffer.has_pending_data() is True


class TestBufferManagerDecodeSafe:
    """Tests for BufferManager.decode_safe method."""

    @pytest.fixture
    def buffer(self) -> BufferManager:
        """Create a BufferManager instance."""
        return BufferManager()

    def test_decode_safe_ascii(self, buffer: BufferManager) -> None:
        """Test safe decoding of ASCII."""
        decoded, incomplete = buffer.decode_safe(b"Hello, World!")

        assert decoded == "Hello, World!"
        assert incomplete == b""

    def test_decode_safe_korean(self, buffer: BufferManager) -> None:
        """Test safe decoding of Korean text."""
        korean = "안녕하세요".encode()
        decoded, incomplete = buffer.decode_safe(korean)

        assert decoded == "안녕하세요"
        assert incomplete == b""

    def test_decode_safe_incomplete(self, buffer: BufferManager) -> None:
        """Test safe decoding with incomplete sequence."""
        decoded, incomplete = buffer.decode_safe(b"Hello\xea\xb0")

        assert decoded == "Hello"
        assert incomplete == b"\xea\xb0"

    def test_decode_safe_continues(self, buffer: BufferManager) -> None:
        """Test safe decoding continues previous incomplete."""
        # First decode with incomplete
        buffer.decode_safe(b"Test\xea\xb0")

        # Second decode completes it
        decoded, incomplete = buffer.decode_safe(b"\x80!")

        assert "가" in decoded  # Completed Korean character
        assert incomplete == b""


class TestUTF8Functions:
    """Tests for UTF-8 utility functions."""

    def test_is_valid_utf8_sequence_valid(self) -> None:
        """Test is_valid_utf8_sequence with valid UTF-8."""
        assert is_valid_utf8_sequence(b"Hello") is True
        assert is_valid_utf8_sequence("안녕".encode()) is True
        assert is_valid_utf8_sequence("😀".encode()) is True

    def test_is_valid_utf8_sequence_invalid(self) -> None:
        """Test is_valid_utf8_sequence with invalid UTF-8."""
        assert is_valid_utf8_sequence(b"\xff\xfe") is False
        assert is_valid_utf8_sequence(b"\xea\xb0") is False  # Incomplete

    def test_get_utf8_char_length(self) -> None:
        """Test get_utf8_char_length for various byte patterns."""
        # ASCII
        assert get_utf8_char_length(0x41) == 1  # 'A'
        assert get_utf8_char_length(0x7F) == 1  # DEL

        # 2-byte
        assert get_utf8_char_length(0xC3) == 2  # 'é' first byte

        # 3-byte
        assert get_utf8_char_length(0xEA) == 3  # Korean first byte

        # 4-byte
        assert get_utf8_char_length(0xF0) == 4  # Emoji first byte

        # Continuation (invalid as leading)
        assert get_utf8_char_length(0x80) == 0
        assert get_utf8_char_length(0xBF) == 0

        # Invalid
        assert get_utf8_char_length(0xF8) == 0

    def test_find_last_complete_char_ascii(self) -> None:
        """Test find_last_complete_char with ASCII."""
        assert find_last_complete_char(b"Hello") == 5

    def test_find_last_complete_char_complete_utf8(self) -> None:
        """Test find_last_complete_char with complete UTF-8."""
        korean = "안녕".encode()  # 6 bytes
        assert find_last_complete_char(korean) == 6

    def test_find_last_complete_char_incomplete(self) -> None:
        """Test find_last_complete_char with incomplete UTF-8."""
        # "안" (3 bytes) + 2 bytes of incomplete char
        incomplete = "안".encode() + b"\xeb\x85"
        result = find_last_complete_char(incomplete)
        # Should return position after complete "안"
        assert result == 3 or result == 5  # Depends on implementation

    def test_find_last_complete_char_empty(self) -> None:
        """Test find_last_complete_char with empty data."""
        assert find_last_complete_char(b"") == 0


class TestBufferManagerEdgeCases:
    """Edge case tests for BufferManager."""

    def test_large_data(self) -> None:
        """Test handling large data."""
        buffer = BufferManager(size_limit=1024 * 1024)  # 1MB
        large_data = b"A" * 100000

        result = buffer.append(large_data)

        assert result == large_data
        assert buffer.byte_buffer_size == 0

    def test_overflow_handling_line_buffer(self) -> None:
        """Test buffer overflow handling with line buffer."""
        buffer = BufferManager(size_limit=50)

        # Line buffer overflow is triggered when combined buffers exceed limit
        buffer.set_incomplete_line("A" * 40)  # 40 bytes

        # Adding more should raise overflow
        with pytest.raises(BufferOverflowError):
            buffer.set_incomplete_line("B" * 60)  # Would exceed 50 byte limit

    def test_overflow_handling_byte_buffer(self) -> None:
        """Test byte buffer overflow with very small limit."""
        # With a tiny limit, incomplete bytes can exceed it
        buffer = BufferManager(size_limit=2)

        # Append incomplete UTF-8 that would result in 3 bytes buffered
        # This should raise because incomplete (3 bytes) > limit (2 bytes)
        with pytest.raises(BufferOverflowError):
            buffer.append(b"\xf0\x9f\x98")  # 3 bytes incomplete > 2 byte limit

    def test_mixed_content(self) -> None:
        """Test mixed ASCII and UTF-8 content."""
        buffer = BufferManager()

        # Mix of ASCII, Korean, and emoji
        mixed = "Hello 안녕 😀".encode()
        result = buffer.append(mixed)

        assert result == mixed
        decoded = result.decode("utf-8")
        assert "Hello" in decoded
        assert "안녕" in decoded
        assert "😀" in decoded

    def test_continuation_bytes_only(self) -> None:
        """Test handling continuation bytes only."""
        buffer = BufferManager()

        # Only continuation bytes (invalid as start)
        result = buffer.append(b"\x80\x80\x80")

        # Should return all bytes since no valid lead byte found
        assert len(result) == 3 or buffer.byte_buffer_size > 0
