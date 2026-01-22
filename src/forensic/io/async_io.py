"""
Async I/O module for concurrent file processing.

Provides asyncio-based streaming file reading and batch processing
with controlled concurrency for I/O-bound workloads.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Protocol

import chardet

from forensic.io.chunk import ChunkProcessor
from forensic.io.discovery import FileDiscovery, FileFilter, SortOrder
from forensic.io.memory import DEFAULT_CHUNK_SIZE, MemoryMonitor, get_memory_monitor
from forensic.io.merger import SegmentMerger
from forensic.models.transcript import Segment, Transcript

# Default maximum concurrent file processing
DEFAULT_MAX_CONCURRENT: int = 10


class AsyncStreamReaderProtocol(Protocol):
    """Async stream reader interface protocol."""

    async def open(self, path: Path) -> "AsyncStreamReaderProtocol":
        """Open file and auto-detect encoding."""
        ...

    async def read_chunks(
        self, chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> AsyncIterator[bytes]:
        """Read file in chunks of specified size."""
        ...

    def get_progress(self) -> float:
        """Return current progress (0.0 ~ 1.0)."""
        ...

    async def close(self) -> None:
        """Close file handle and release resources."""
        ...


class AsyncBatchProcessorProtocol(Protocol):
    """Async batch processor interface protocol."""

    async def discover_files(
        self, directory: Path, pattern: str = "*.txt"
    ) -> list[Path]:
        """Discover files matching pattern in directory."""
        ...

    async def process_all_async(
        self,
        files: list[Path],
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        on_progress: "ProgressCallback | None" = None,
    ) -> AsyncIterator[Transcript]:
        """Process all files concurrently and yield transcripts as they complete."""
        ...


class FileNotOpenError(Exception):
    """Raised when attempting to read from an unopened file."""

    pass


class EncodingDetectionError(Exception):
    """Raised when encoding detection fails."""

    pass


class AsyncFileProcessingError(Exception):
    """Raised when async file processing encounters an error."""

    def __init__(self, path: Path, cause: Exception) -> None:
        self.path = path
        self.cause = cause
        super().__init__(f"Failed to process {path}: {cause}")


@dataclass
class AsyncBatchConfig:
    """
    Configuration for async batch processing.

    Attributes:
        default_chunk_size: Default chunk size in bytes.
        skip_on_error: Whether to skip files that fail processing.
        merge_segments: Whether to merge continuous segments.
        encoding: Text encoding for processing.
        default_speaker: Default speaker ID for segments.
        max_concurrent: Maximum concurrent file processing tasks.
    """

    default_chunk_size: int = 1024 * 1024  # 1MB
    skip_on_error: bool = True
    merge_segments: bool = True
    encoding: str = "utf-8"
    default_speaker: str = "unknown"
    max_concurrent: int = DEFAULT_MAX_CONCURRENT


@dataclass
class AsyncBatchResult:
    """
    Result of async batch processing.

    Attributes:
        total_files: Total number of files processed.
        successful_files: Number of files processed successfully.
        failed_files: Number of files that failed processing.
        total_segments: Total segments extracted.
        total_duration: Total duration of all transcripts (seconds).
        errors: List of (file_path, error_message) for failed files.
    """

    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_segments: int = 0
    total_duration: float = 0.0
    errors: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Return success rate as a ratio (0.0 ~ 1.0)."""
        if self.total_files == 0:
            return 1.0
        return self.successful_files / self.total_files


class AsyncStreamReader:
    """
    Async stream reader for efficient file reading.

    Provides async streaming access to files with automatic encoding
    detection and progress tracking.

    Usage:
        async with AsyncStreamReader() as reader:
            await reader.open(Path("file.txt"))
            async for chunk in reader.read_chunks():
                process(chunk)

    Attributes:
        path: Path to the currently open file.
        encoding: Detected file encoding.
        file_size: Total file size in bytes.
    """

    def __init__(
        self, memory_monitor: MemoryMonitor | None = None
    ) -> None:
        """
        Initialize async stream reader.

        Args:
            memory_monitor: Optional memory monitor for adaptive chunk sizing.
        """
        self._memory_monitor = memory_monitor or get_memory_monitor()
        self._path: Path | None = None
        self._file: BinaryIO | None = None
        self._encoding: str = "utf-8"
        self._file_size: int = 0
        self._bytes_read: int = 0
        self._lock = asyncio.Lock()

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

    async def __aenter__(self) -> "AsyncStreamReader":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Async context manager exit - close file handle."""
        await self.close()

    async def open(self, path: Path) -> "AsyncStreamReader":
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
        await self.close()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        self._path = path
        self._file_size = path.stat().st_size
        self._bytes_read = 0

        # Detect encoding
        self._encoding = await self._detect_encoding(path)

        # Open file in binary mode for streaming
        # Using open() directly is intentional for streaming use case
        # The file handle is managed by close() and __aexit__()
        self._file = open(path, "rb")  # noqa: SIM115

        return self

    async def _detect_encoding(self, path: Path) -> str:
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
            # Run file I/O in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with open(path, "rb") as f:
                sample = await loop.run_in_executor(None, f.read, sample_size)

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

    async def read_chunks(
        self, chunk_size: int | None = None
    ) -> AsyncIterator[bytes]:
        """
        Read file in chunks of specified size.

        Async generator that yields file content in chunks. Uses adaptive
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

        loop = asyncio.get_event_loop()

        while True:
            # Run blocking read in thread pool
            chunk = await loop.run_in_executor(None, self._file.read, chunk_size)
            if not chunk:
                break

            async with self._lock:
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

    async def close(self) -> None:
        """
        Close file handle and release resources.

        Safe to call multiple times.
        """
        async with self._lock:
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

    async def reset(self) -> None:
        """
        Reset reading position to beginning of file.

        Raises:
            FileNotOpenError: If file is not open.
        """
        if self._file is None:
            raise FileNotOpenError("File not open. Call open() first.")

        self._file.seek(0)
        self._bytes_read = 0


class AsyncTranscriptBatchProcessor:
    """
    Async batch processor for transcript files.

    Processes multiple files concurrently with controlled concurrency
    and memory-aware chunk size adjustment.

    Usage:
        processor = AsyncTranscriptBatchProcessor()
        files = await processor.discover_files(Path("/data"), "*.txt")

        async for transcript in processor.process_all_async(files, max_concurrent=5):
            await save_transcript(transcript)

    Attributes:
        config: Async batch processing configuration.
    """

    def __init__(
        self,
        memory_monitor: MemoryMonitor | None = None,
        chunk_processor: ChunkProcessor | None = None,
        config: AsyncBatchConfig | None = None,
    ) -> None:
        """
        Initialize async batch processor.

        Args:
            memory_monitor: Optional memory monitor for adaptive sizing.
            chunk_processor: Optional chunk processor for text parsing.
            config: Optional batch processing configuration.
        """
        self._memory_monitor = memory_monitor or get_memory_monitor()
        self._chunk_processor = chunk_processor
        self._config = config or AsyncBatchConfig()
        self._discovery = FileDiscovery()
        self._result = AsyncBatchResult()

    @property
    def config(self) -> AsyncBatchConfig:
        """Return batch processing configuration."""
        return self._config

    @property
    def result(self) -> AsyncBatchResult:
        """Return batch processing result."""
        return self._result

    async def discover_files(
        self,
        directory: Path,
        pattern: str = "*.txt",
        recursive: bool = False,
        sort_order: SortOrder | None = SortOrder.NAME,
    ) -> list[Path]:
        """
        Discover files matching pattern in directory.

        Uses FileDiscovery to find matching files with
        optional sorting.

        Args:
            directory: Directory to search.
            pattern: Glob pattern for matching files.
            recursive: Whether to search subdirectories.
            sort_order: Optional sort order for results.

        Returns:
            List of matching file paths.
        """
        # FileDiscovery.find_by_pattern is synchronous, run in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._discovery.find_by_pattern,
            directory,
            pattern,
            recursive,
            sort_order,
        )

    async def discover_files_filtered(
        self,
        directory: Path,
        filter: FileFilter,
        sort_order: SortOrder | None = SortOrder.NAME,
    ) -> list[Path]:
        """
        Discover files with advanced filtering.

        Args:
            directory: Directory to search.
            filter: File filter criteria.
            sort_order: Optional sort order for results.

        Returns:
            List of matching file paths.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._discovery.find,
            directory,
            filter,
            sort_order,
        )

    async def process_all_async(
        self,
        files: list[Path],
        max_concurrent: int | None = None,
        skip_on_error: bool | None = None,
        on_progress: "ProgressCallback | None" = None,
    ) -> AsyncIterator[Transcript]:
        """
        Process all files concurrently and yield transcripts as they complete.

        Uses asyncio.Semaphore to control concurrency and processes
        files in parallel. Each transcript is yielded immediately upon
        completion for memory-efficient streaming.

        Args:
            files: List of files to process.
            max_concurrent: Maximum concurrent processing tasks. If None,
                uses config.max_concurrent.
            skip_on_error: Whether to skip failed files. If None,
                uses config.skip_on_error.
            on_progress: Optional async progress callback (path, progress).

        Yields:
            Transcript objects as each file completes.

        Raises:
            AsyncFileProcessingError: If a file fails and skip_on_error is False.
        """
        if max_concurrent is None:
            max_concurrent = self._config.max_concurrent

        if skip_on_error is None:
            skip_on_error = self._config.skip_on_error

        # Clamp max_concurrent based on memory state
        max_concurrent = self._get_adaptive_concurrency(max_concurrent)

        # Reset result tracking
        self._result = AsyncBatchResult(total_files=len(files))

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        # Create task queue
        tasks: list[asyncio.Task[Transcript | None]] = []

        for file_path in files:
            task = asyncio.create_task(
                self._process_single_with_semaphore(
                    file_path, semaphore, skip_on_error, on_progress
                )
            )
            tasks.append(task)

        # Yield results as tasks complete
        for task in asyncio.as_completed(tasks):
            result = await task
            if result is not None:
                yield result

    async def _process_single_with_semaphore(
        self,
        file_path: Path,
        semaphore: asyncio.Semaphore,
        skip_on_error: bool,
        on_progress: "ProgressCallback | None",
    ) -> Transcript | None:
        """
        Process single file with semaphore-controlled concurrency.

        Args:
            file_path: Path to the file.
            semaphore: Semaphore for concurrency control.
            skip_on_error: Whether to skip failed files.
            on_progress: Optional progress callback.

        Returns:
            Transcript if successful, None if failed and skipped.

        Raises:
            AsyncFileProcessingError: If processing fails and skip_on_error is False.
        """
        async with semaphore:
            try:
                transcript = await self._process_single_file(file_path, on_progress)
                self._result.successful_files += 1
                self._result.total_segments += transcript.segment_count
                self._result.total_duration += transcript.duration_seconds
                return transcript

            except Exception as e:
                self._result.failed_files += 1
                self._result.errors.append((file_path, str(e)))

                if not skip_on_error:
                    raise AsyncFileProcessingError(file_path, e) from e
                return None

    async def _process_single_file(
        self,
        file_path: Path,
        on_progress: "ProgressCallback | None",
    ) -> Transcript:
        """
        Internal method to process a single file asynchronously.

        Args:
            file_path: Path to the file.
            on_progress: Optional progress callback.

        Returns:
            Processed Transcript object.
        """
        # Create chunk processor for this file
        processor = self._get_chunk_processor()

        # Collect segments
        all_segments: list[Segment] = []

        # Process file in chunks
        async with AsyncStreamReader(self._memory_monitor) as reader:
            await reader.open(file_path)

            # Update processor encoding if detected
            processor.encoding = reader.encoding

            # Get chunk size based on memory state
            chunk_size = self._get_adaptive_chunk_size()

            # Process chunks
            async for chunk in reader.read_chunks(chunk_size):
                is_last = reader.get_progress() >= 0.99

                # Process chunk into segments
                segments = processor.process(chunk, is_last=is_last)
                all_segments.extend(segments)

                # Call progress callback if provided
                if on_progress is not None:
                    await on_progress(file_path, reader.get_progress())

                # Check memory and adjust chunk size if needed
                if self._memory_monitor.should_reduce_chunk_size():
                    chunk_size = self._memory_monitor.get_recommended_chunk_size()

            # Flush any remaining buffer
            remaining_segments = processor.flush()
            all_segments.extend(remaining_segments)

        # Merge continuous segments if configured
        if self._config.merge_segments and all_segments:
            merger = SegmentMerger()
            # Run merge in thread pool as it's CPU-bound
            loop = asyncio.get_event_loop()
            all_segments = await loop.run_in_executor(
                None,
                merger.process_batch,
                all_segments,
                True,
            )

        # Create transcript
        return self._create_transcript(file_path, all_segments)

    async def process_single(self, file_path: Path) -> Transcript:
        """
        Process a single file asynchronously.

        Args:
            file_path: Path to the file.

        Returns:
            Processed Transcript object.

        Raises:
            AsyncFileProcessingError: If processing fails.
        """
        try:
            return await self._process_single_file(file_path, None)
        except Exception as e:
            raise AsyncFileProcessingError(file_path, e) from e

    def _get_chunk_processor(self) -> ChunkProcessor:
        """
        Get or create chunk processor.

        Returns:
            ChunkProcessor instance.
        """
        if self._chunk_processor is not None:
            # Reset existing processor for new file
            self._chunk_processor.reset()
            return self._chunk_processor

        return ChunkProcessor(
            encoding=self._config.encoding,
            default_speaker=self._config.default_speaker,
        )

    def _get_adaptive_chunk_size(self) -> int:
        """
        Get adaptive chunk size based on memory state.

        Returns:
            Recommended chunk size in bytes.
        """
        recommended = self._memory_monitor.get_recommended_chunk_size()
        return min(recommended, self._config.default_chunk_size)

    def _get_adaptive_concurrency(self, requested: int) -> int:
        """
        Get adaptive concurrency based on memory state.

        Reduces concurrency when memory pressure is high to prevent OOM.

        Args:
            requested: Requested maximum concurrency.

        Returns:
            Adjusted concurrency level.
        """
        state = self._memory_monitor.get_memory_state()

        if state.level == "critical":
            return 1
        elif state.level == "warning":
            return max(1, requested // 2)

        return requested

    def _create_transcript(
        self,
        file_path: Path,
        segments: list[Segment],
    ) -> Transcript:
        """
        Create Transcript from segments.

        Args:
            file_path: Source file path.
            segments: List of segments.

        Returns:
            Transcript object.
        """
        # Calculate duration from segments
        duration = 0.0
        if segments:
            duration = max(seg.end_time for seg in segments)

        # Ensure minimum duration
        if duration == 0.0:
            duration = 0.1  # Minimum duration

        # Extract unique speakers
        speakers = list({seg.speaker for seg in segments})

        # Generate transcript ID
        transcript_id = f"transcript_{uuid.uuid4().hex[:8]}"

        # Build content from segments
        content = "\n".join(seg.content for seg in segments)

        return Transcript(
            id=transcript_id,
            file_path=file_path,
            date=datetime.now(),
            duration_seconds=duration,
            speakers=speakers,
            content=content,
            segments=segments,
            metadata={
                "source_file": str(file_path),
                "segment_count": len(segments),
                "processing_date": datetime.now().isoformat(),
                "processing_mode": "async",
            },
        )

    def get_batch_summary(self) -> dict[str, object]:
        """
        Get batch processing summary.

        Returns:
            Dictionary with batch processing statistics.
        """
        return {
            "total_files": self._result.total_files,
            "successful_files": self._result.successful_files,
            "failed_files": self._result.failed_files,
            "success_rate": self._result.success_rate,
            "total_segments": self._result.total_segments,
            "total_duration_seconds": self._result.total_duration,
            "errors": [(str(p), e) for p, e in self._result.errors],
        }


# Type alias for progress callback
ProgressCallback = "Callable[[Path, float], Awaitable[None] | None]"


async def process_directory_async(
    directory: Path,
    pattern: str = "*.txt",
    recursive: bool = False,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    on_progress: ProgressCallback | None = None,
) -> AsyncIterator[Transcript]:
    """
    Convenience function to async process all matching files in a directory.

    Args:
        directory: Directory to process.
        pattern: Glob pattern for matching files.
        recursive: Whether to search subdirectories.
        max_concurrent: Maximum concurrent file processing.
        on_progress: Optional async progress callback.

    Yields:
        Transcript objects.
    """
    processor = AsyncTranscriptBatchProcessor()
    files = await processor.discover_files(directory, pattern, recursive)
    async for transcript in processor.process_all_async(
        files, max_concurrent=max_concurrent, on_progress=on_progress
    ):
        yield transcript


async def process_files_async(
    files: list[Path],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    skip_on_error: bool = True,
    on_progress: ProgressCallback | None = None,
) -> AsyncIterator[Transcript]:
    """
    Convenience function to async process a list of files.

    Args:
        files: List of file paths.
        max_concurrent: Maximum concurrent file processing.
        skip_on_error: Whether to skip failed files.
        on_progress: Optional async progress callback.

    Yields:
        Transcript objects.
    """
    processor = AsyncTranscriptBatchProcessor()
    async for transcript in processor.process_all_async(
        files,
        max_concurrent=max_concurrent,
        skip_on_error=skip_on_error,
        on_progress=on_progress,
    ):
        yield transcript


async def read_file_streaming_async(
    path: Path,
    chunk_size: int | None = None,
) -> AsyncIterator[bytes]:
    """
    Convenience function for async streaming file reading.

    Opens file, yields chunks, and automatically closes file handle.

    Args:
        path: Path to the file to read.
        chunk_size: Optional chunk size in bytes.

    Yields:
        File content chunks as bytes.
    """
    async with AsyncStreamReader() as reader:
        await reader.open(path)
        async for chunk in reader.read_chunks(chunk_size):
            yield chunk
