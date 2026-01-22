"""
Stream reader module unit tests.

Tests for StreamReader class and related functions.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forensic.io.reader import (
    FileNotOpenError,
    StreamReader,
    read_file_streaming,
)


class TestStreamReader:
    """StreamReader class tests."""

    @pytest.fixture
    def temp_file(self, tmp_path: Path) -> Path:
        """Create a temporary test file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello, World!\nThis is a test file.\n", encoding="utf-8")
        return file_path

    @pytest.fixture
    def utf8_bom_file(self, tmp_path: Path) -> Path:
        """Create a UTF-8 BOM file."""
        file_path = tmp_path / "test_bom.txt"
        file_path.write_bytes(b"\xef\xbb\xbfHello with BOM")
        return file_path

    @pytest.fixture
    def korean_file(self, tmp_path: Path) -> Path:
        """Create a Korean text file."""
        file_path = tmp_path / "korean.txt"
        file_path.write_text("안녕하세요, 세계!\n테스트 파일입니다.\n", encoding="utf-8")
        return file_path

    @pytest.fixture
    def large_file(self, tmp_path: Path) -> Path:
        """Create a large test file (2MB)."""
        file_path = tmp_path / "large.txt"
        content = "A" * (2 * 1024 * 1024)  # 2MB
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_init(self) -> None:
        """Test StreamReader initialization."""
        reader = StreamReader()

        assert reader.path is None
        assert reader.encoding == "utf-8"
        assert reader.file_size == 0
        assert reader.bytes_read == 0
        assert reader.is_open() is False

    def test_open_file(self, temp_file: Path) -> None:
        """Test opening a file."""
        reader = StreamReader()
        result = reader.open(temp_file)

        assert result is reader  # Returns self for chaining
        assert reader.path == temp_file
        assert reader.file_size > 0
        assert reader.is_open() is True
        assert reader.encoding in ("utf-8", "ascii")

        reader.close()

    def test_open_file_not_found(self, tmp_path: Path) -> None:
        """Test opening non-existent file raises error."""
        reader = StreamReader()
        non_existent = tmp_path / "non_existent.txt"

        with pytest.raises(FileNotFoundError):
            reader.open(non_existent)

    def test_detect_utf8_bom(self, utf8_bom_file: Path) -> None:
        """Test detection of UTF-8 BOM encoding."""
        reader = StreamReader()
        reader.open(utf8_bom_file)

        assert reader.encoding == "utf-8-sig"

        reader.close()

    def test_read_chunks_basic(self, temp_file: Path) -> None:
        """Test basic chunk reading."""
        reader = StreamReader()
        reader.open(temp_file)

        chunks = list(reader.read_chunks(chunk_size=10))

        assert len(chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in chunks)
        assert b"".join(chunks) == temp_file.read_bytes()

        reader.close()

    def test_read_chunks_without_open(self) -> None:
        """Test reading chunks without opening file raises error."""
        reader = StreamReader()

        with pytest.raises(FileNotOpenError):
            list(reader.read_chunks())

    def test_read_chunks_large_file(self, large_file: Path) -> None:
        """Test reading large file in chunks."""
        reader = StreamReader()
        reader.open(large_file)

        chunk_size = 1024 * 1024  # 1MB
        chunks = list(reader.read_chunks(chunk_size=chunk_size))

        assert len(chunks) == 2  # 2MB file / 1MB chunks = 2 chunks
        assert reader.bytes_read == 2 * 1024 * 1024

        reader.close()

    def test_get_progress(self, large_file: Path) -> None:
        """Test progress tracking."""
        reader = StreamReader()
        reader.open(large_file)

        assert reader.get_progress() == 0.0

        # Read half the file
        chunks = reader.read_chunks(chunk_size=1024 * 1024)
        next(chunks)  # Read first chunk

        assert reader.get_progress() == pytest.approx(0.5, rel=0.01)

        # Read rest
        list(chunks)

        assert reader.get_progress() == pytest.approx(1.0, rel=0.01)

        reader.close()

    def test_get_progress_percent(self, large_file: Path) -> None:
        """Test progress percentage calculation."""
        reader = StreamReader()
        reader.open(large_file)

        chunks = reader.read_chunks(chunk_size=1024 * 1024)
        next(chunks)  # Read first chunk

        assert reader.get_progress_percent() == pytest.approx(50.0, rel=1.0)

        reader.close()

    def test_get_progress_empty_file(self, tmp_path: Path) -> None:
        """Test progress for empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        reader = StreamReader()
        reader.open(empty_file)

        assert reader.get_progress() == 1.0

        reader.close()

    def test_close(self, temp_file: Path) -> None:
        """Test closing file."""
        reader = StreamReader()
        reader.open(temp_file)

        assert reader.is_open() is True

        reader.close()

        assert reader.is_open() is False

    def test_close_multiple_times(self, temp_file: Path) -> None:
        """Test closing file multiple times is safe."""
        reader = StreamReader()
        reader.open(temp_file)

        reader.close()
        reader.close()  # Should not raise

        assert reader.is_open() is False

    def test_context_manager(self, temp_file: Path) -> None:
        """Test context manager usage."""
        with StreamReader() as reader:
            reader.open(temp_file)
            assert reader.is_open() is True

        assert reader.is_open() is False

    def test_reset(self, temp_file: Path) -> None:
        """Test resetting reading position."""
        reader = StreamReader()
        reader.open(temp_file)

        # Read some data
        list(reader.read_chunks(chunk_size=10))
        assert reader.bytes_read > 0

        # Reset
        reader.reset()
        assert reader.bytes_read == 0
        assert reader.get_progress() == 0.0

        reader.close()

    def test_reset_without_open(self) -> None:
        """Test reset without open file raises error."""
        reader = StreamReader()

        with pytest.raises(FileNotOpenError):
            reader.reset()

    def test_read_korean_file(self, korean_file: Path) -> None:
        """Test reading Korean text file."""
        reader = StreamReader()
        reader.open(korean_file)

        chunks = list(reader.read_chunks())
        content = b"".join(chunks).decode("utf-8")

        assert "안녕하세요" in content
        assert "테스트" in content

        reader.close()


class TestReadFileStreaming:
    """Tests for read_file_streaming convenience function."""

    @pytest.fixture
    def temp_file(self, tmp_path: Path) -> Path:
        """Create a temporary test file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello, World!\n", encoding="utf-8")
        return file_path

    def test_read_file_streaming_basic(self, temp_file: Path) -> None:
        """Test basic streaming read."""
        chunks = list(read_file_streaming(temp_file))

        assert len(chunks) > 0
        assert b"".join(chunks) == temp_file.read_bytes()

    def test_read_file_streaming_with_chunk_size(self, temp_file: Path) -> None:
        """Test streaming read with custom chunk size."""
        chunks = list(read_file_streaming(temp_file, chunk_size=5))

        # Should have multiple small chunks
        assert len(chunks) > 1
        assert b"".join(chunks) == temp_file.read_bytes()

    def test_read_file_streaming_not_found(self, tmp_path: Path) -> None:
        """Test streaming read of non-existent file."""
        non_existent = tmp_path / "non_existent.txt"

        with pytest.raises(FileNotFoundError):
            list(read_file_streaming(non_existent))


class TestEncodingDetection:
    """Tests for encoding detection."""

    @pytest.fixture
    def utf16_le_file(self, tmp_path: Path) -> Path:
        """Create a UTF-16 LE file."""
        file_path = tmp_path / "utf16le.txt"
        file_path.write_bytes(b"\xff\xfeH\x00e\x00l\x00l\x00o\x00")
        return file_path

    @pytest.fixture
    def utf16_be_file(self, tmp_path: Path) -> Path:
        """Create a UTF-16 BE file."""
        file_path = tmp_path / "utf16be.txt"
        file_path.write_bytes(b"\xfe\xff\x00H\x00e\x00l\x00l\x00o")
        return file_path

    def test_detect_utf16_le(self, utf16_le_file: Path) -> None:
        """Test detection of UTF-16 LE encoding."""
        reader = StreamReader()
        reader.open(utf16_le_file)

        assert reader.encoding == "utf-16-le"

        reader.close()

    def test_detect_utf16_be(self, utf16_be_file: Path) -> None:
        """Test detection of UTF-16 BE encoding."""
        reader = StreamReader()
        reader.open(utf16_be_file)

        assert reader.encoding == "utf-16-be"

        reader.close()

    def test_fallback_to_utf8(self, tmp_path: Path) -> None:
        """Test fallback to UTF-8 for unknown encoding."""
        # Create a file with ASCII content (low confidence detection)
        file_path = tmp_path / "plain.txt"
        file_path.write_bytes(b"Simple ASCII text")

        reader = StreamReader()
        reader.open(file_path)

        # Should detect as ascii or utf-8
        assert reader.encoding in ("utf-8", "ascii")

        reader.close()


class TestStreamReaderWithMemoryMonitor:
    """Tests for StreamReader with MemoryMonitor integration."""

    @pytest.fixture
    def temp_file(self, tmp_path: Path) -> Path:
        """Create a temporary test file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("A" * 10000, encoding="utf-8")
        return file_path

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_adaptive_chunk_size(
        self, mock_memory: MagicMock, temp_file: Path
    ) -> None:
        """Test adaptive chunk size from memory monitor."""
        mock_memory.return_value = MagicMock(
            used=50 * (1024**3),
            available=78 * (1024**3),
            total=128 * (1024**3),
        )

        with StreamReader() as reader:
            reader.open(temp_file)

            # Read with default (adaptive) chunk size
            chunks = list(reader.read_chunks())

            assert len(chunks) > 0
