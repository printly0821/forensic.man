"""
Stream reader module for efficient file reading.

Provides streaming file access with automatic encoding detection
and progress tracking for large file processing.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO, Protocol

import chardet

from forensic.io.memory import DEFAULT_CHUNK_SIZE, MemoryMonitor, get_memory_monitor


class StreamReaderProtocol(Protocol):
    """Stream reader interface protocol."""

    def open(self, path: Path) -> "StreamReaderProtocol":
        """Open file and auto-detect encoding."""
        ...

    def read_chunks(self, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Iterator[bytes]:
        """Read file in chunks of specified size."""
        ...

    def get_progress(self) -> float:
        """Return current progress (0.0 ~ 1.0)."""
        ...

    def close(self) -> None:
        """Close file handle and release resources."""
        ...


class FileNotOpenError(Exception):
    """Raised when attempting to read from an unopened file."""


class EncodingDetectionError(Exception):
    """Raised when encoding detection fails."""


class StreamReader:
    """
    Stream reader for efficient file reading.

    Provides streaming access to files with automatic encoding detection,
    progress tracking, and memory-aware chunk size recommendations.

    Usage:
        with StreamReader() as reader:
            reader.open(Path("file.txt"))
            for chunk in reader.read_chunks():
                process(chunk)

    Attributes:
        path: Path to the currently open file.
        encoding: Detected file encoding.
        file_size: Total file size in bytes.
    """

    def __init__(self, memory_monitor: MemoryMonitor | None = None) -> None:
        """
        Initialize stream reader.

        Args:
            memory_monitor: Optional memory monitor for adaptive chunk sizing.
        """
        self._memory_monitor = memory_monitor or get_memory_monitor()
        self._path: Path | None = None
        self._file: BinaryIO | None = None
        self._encoding: str = "utf-8"
        self._file_size: int = 0
        self._bytes_read: int = 0

    @property
    def path(self) -> Path | None:
        """Return path to the currently open file."""
        return self._path

    @property
    def encoding(self) -> str:
        """Return detected file encoding."""
        return self._encoding

    @property
    def file_size(self) -> int:
        """Return total file size in bytes."""
        return self._file_size

    @property
    def bytes_read(self) -> int:
        """Return number of bytes read so far."""
        return self._bytes_read

    def __enter__(self) -> "StreamReader":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Context manager exit - close file handle."""
        self.close()

    def open(self, path: Path) -> "StreamReader":
        """
        Open file and auto-detect encoding.

        Detects file encoding using chardet library and opens
        the file for binary reading.

        Args:
            path: Path to the file to open.

        Returns:
            Self for method chaining.

        Raises:
            FileNotFoundError: If file does not exist.
            EncodingDetectionError: If encoding detection fails.
        """
        # Close any previously opened file
        self.close()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        self._path = path
        self._file_size = path.stat().st_size
        self._bytes_read = 0

        # Detect encoding
        self._encoding = self._detect_encoding(path)

        # Open file in binary mode for streaming
        # Using open() directly is intentional for streaming use case
        # The file handle is managed by close() and __exit__()
        self._file = open(path, "rb")  # noqa: SIM115

        return self

    def _detect_encoding(self, path: Path) -> str:
        """
        Detect file encoding using chardet.

        Reads a sample of the file to detect encoding. Falls back
        to UTF-8 if detection fails or confidence is low.

        Args:
            path: Path to the file.

        Returns:
            Detected encoding name.

        Raises:
            EncodingDetectionError: If encoding detection completely fails.
        """
        # Read sample for detection (max 64KB)
        sample_size = min(65536, path.stat().st_size)

        try:
            with open(path, "rb") as f:
                sample = f.read(sample_size)

            # Check for BOM first
            if sample.startswith(b"\xef\xbb\xbf"):
                return "utf-8-sig"
            elif sample.startswith(b"\xff\xfe"):
                return "utf-16-le"
            elif sample.startswith(b"\xfe\xff"):
                return "utf-16-be"

            # Use chardet for detection
            result = chardet.detect(sample)

            if result["encoding"] and result["confidence"] and result["confidence"] > 0.7:
                encoding = result["encoding"].lower()
                # Normalize common encodings
                if encoding in ("ascii", "iso-8859-1", "windows-1252"):
                    return encoding
                return encoding

            # Default to UTF-8
            return "utf-8"

        except Exception as e:
            raise EncodingDetectionError(f"Failed to detect encoding: {e}") from e

    def read_chunks(self, chunk_size: int | None = None) -> Iterator[bytes]:
        """
        Read file in chunks of specified size.

        Generator that yields file content in chunks. Uses adaptive
        chunk sizing based on memory state if chunk_size is not specified.

        Args:
            chunk_size: Optional chunk size in bytes. Uses recommended
                size from memory monitor if not specified.

        Yields:
            File content chunks as bytes.

        Raises:
            FileNotOpenError: If file is not open.
        """
        if self._file is None:
            raise FileNotOpenError("File not open. Call open() first.")

        # Use recommended chunk size if not specified
        if chunk_size is None:
            chunk_size = self._memory_monitor.get_recommended_chunk_size()

        while True:
            chunk = self._file.read(chunk_size)
            if not chunk:
                break

            self._bytes_read += len(chunk)
            yield chunk

    def get_progress(self) -> float:
        """
        Return current progress as a float between 0.0 and 1.0.

        Returns:
            Progress ratio (bytes_read / file_size).
        """
        if self._file_size == 0:
            return 1.0
        return min(1.0, self._bytes_read / self._file_size)

    def get_progress_percent(self) -> float:
        """
        Return current progress as a percentage.

        Returns:
            Progress percentage (0.0 ~ 100.0).
        """
        return self.get_progress() * 100.0

    def close(self) -> None:
        """
        Close file handle and release resources.

        Safe to call multiple times.
        """
        if self._file is not None:
            self._file.close()
            self._file = None

    def is_open(self) -> bool:
        """
        Check if file is currently open.

        Returns:
            True if file is open.
        """
        return self._file is not None

    def reset(self) -> None:
        """
        Reset reading position to beginning of file.

        Raises:
            FileNotOpenError: If file is not open.
        """
        if self._file is None:
            raise FileNotOpenError("File not open. Call open() first.")

        self._file.seek(0)
        self._bytes_read = 0


def read_file_streaming(
    path: Path,
    chunk_size: int | None = None,
) -> Iterator[bytes]:
    """
    Convenience function for streaming file reading.

    Opens file, yields chunks, and automatically closes file handle.

    Args:
        path: Path to the file to read.
        chunk_size: Optional chunk size in bytes.

    Yields:
        File content chunks as bytes.
    """
    with StreamReader() as reader:
        reader.open(path)
        yield from reader.read_chunks(chunk_size)
