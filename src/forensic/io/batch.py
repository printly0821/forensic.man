"""
Batch processor module for processing multiple transcript files.

Provides sequential batch processing with memory-aware chunk size
adjustment, progress tracking, and result streaming.
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

from forensic.io.chunk import ChunkProcessor
from forensic.io.discovery import FileDiscovery, FileFilter, SortOrder
from forensic.io.memory import MemoryMonitor, get_memory_monitor
from forensic.io.merger import SegmentMerger
from forensic.io.progress import ProgressTracker, SimpleProgressCallback
from forensic.io.reader import StreamReader
from forensic.models.transcript import Segment, Transcript


class BatchProcessorProtocol(Protocol):
    """Batch processor interface protocol."""

    def discover_files(self, directory: Path, pattern: str = "*.txt") -> list[Path]:
        """Discover files matching pattern in directory."""
        ...

    def process_all(
        self,
        files: list[Path],
        on_progress: SimpleProgressCallback | None = None,
    ) -> Iterator[Transcript]:
        """Process all files and yield transcripts as they complete."""
        ...


class BatchProcessingError(Exception):
    """Raised when batch processing encounters an error."""

    pass


class FileProcessingError(Exception):
    """Raised when processing a single file fails."""

    def __init__(self, path: Path, cause: Exception) -> None:
        self.path = path
        self.cause = cause
        super().__init__(f"Failed to process {path}: {cause}")


@dataclass
class BatchResult:
    """
    Result of batch processing.

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


@dataclass
class BatchConfig:
    """
    Configuration for batch processing.

    Attributes:
        default_chunk_size: Default chunk size in bytes.
        skip_on_error: Whether to skip files that fail processing.
        merge_segments: Whether to merge continuous segments.
        encoding: Text encoding for processing.
        default_speaker: Default speaker ID for segments.
    """

    default_chunk_size: int = 1024 * 1024  # 1MB
    skip_on_error: bool = True
    merge_segments: bool = True
    encoding: str = "utf-8"
    default_speaker: str = "unknown"


class TranscriptBatchProcessor:
    """
    Batch processor for transcript files.

    Processes multiple files sequentially with memory-aware
    chunk size adjustment and result streaming.

    Usage:
        processor = TranscriptBatchProcessor()
        files = processor.discover_files(Path("/data"), "*.txt")

        for transcript in processor.process_all(files, on_progress=print_progress):
            save_transcript(transcript)

    Attributes:
        config: Batch processing configuration.
    """

    def __init__(
        self,
        memory_monitor: MemoryMonitor | None = None,
        chunk_processor: ChunkProcessor | None = None,
        config: BatchConfig | None = None,
    ) -> None:
        """
        Initialize batch processor.

        Args:
            memory_monitor: Optional memory monitor for adaptive sizing.
            chunk_processor: Optional chunk processor for text parsing.
            config: Optional batch processing configuration.
        """
        self._memory_monitor = memory_monitor or get_memory_monitor()
        self._chunk_processor = chunk_processor
        self._config = config or BatchConfig()
        self._discovery = FileDiscovery()
        self._result = BatchResult()

    @property
    def config(self) -> BatchConfig:
        """Return batch processing configuration."""
        return self._config

    @property
    def result(self) -> BatchResult:
        """Return batch processing result."""
        return self._result

    def discover_files(
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
        return self._discovery.find_by_pattern(directory, pattern, recursive, sort_order)

    def discover_files_filtered(
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
        return self._discovery.find(directory, filter, sort_order)

    def process_all(
        self,
        files: list[Path],
        on_progress: SimpleProgressCallback | None = None,
        skip_on_error: bool | None = None,
    ) -> Iterator[Transcript]:
        """
        Process all files and yield transcripts as they complete.

        Processes files sequentially with memory-aware chunk sizing.
        Each transcript is yielded immediately upon completion for
        memory-efficient streaming.

        Args:
            files: List of files to process.
            on_progress: Optional progress callback (path, progress).
            skip_on_error: Whether to skip failed files. If None,
                uses config.skip_on_error.

        Yields:
            Transcript objects as each file completes.

        Raises:
            FileProcessingError: If a file fails and skip_on_error is False.
        """
        if skip_on_error is None:
            skip_on_error = self._config.skip_on_error

        # Reset result tracking
        self._result = BatchResult(total_files=len(files))

        # Create progress tracker
        tracker = ProgressTracker(total_files=len(files))
        if on_progress is not None:
            tracker.set_simple_callback(on_progress)

        # Process each file
        for file_path in files:
            try:
                transcript = self._process_single_file(file_path, tracker)
                self._result.successful_files += 1
                self._result.total_segments += transcript.segment_count
                self._result.total_duration += transcript.duration_seconds
                yield transcript

            except Exception as e:
                self._result.failed_files += 1
                self._result.errors.append((file_path, str(e)))

                if not skip_on_error:
                    raise FileProcessingError(file_path, e) from e

    def process_single(self, file_path: Path) -> Transcript:
        """
        Process a single file.

        Args:
            file_path: Path to the file.

        Returns:
            Processed Transcript object.

        Raises:
            FileProcessingError: If processing fails.
        """
        try:
            tracker = ProgressTracker(total_files=1)
            return self._process_single_file(file_path, tracker)
        except Exception as e:
            raise FileProcessingError(file_path, e) from e

    def _process_single_file(
        self,
        file_path: Path,
        tracker: ProgressTracker,
    ) -> Transcript:
        """
        Internal method to process a single file.

        Args:
            file_path: Path to the file.
            tracker: Progress tracker instance.

        Returns:
            Processed Transcript object.
        """
        # Get file size and start tracking
        file_size = file_path.stat().st_size
        tracker.start_file(file_path, file_size)

        # Create chunk processor for this file
        processor = self._get_chunk_processor()

        # Collect segments
        all_segments: list[Segment] = []

        # Process file in chunks
        with StreamReader(self._memory_monitor) as reader:
            reader.open(file_path)

            # Update processor encoding if detected
            processor.encoding = reader.encoding

            # Get chunk size based on memory state
            chunk_size = self._get_adaptive_chunk_size()

            # Process chunks
            chunks = reader.read_chunks(chunk_size)

            for chunk in chunks:
                is_last = reader.get_progress() >= 0.99

                # Process chunk into segments
                segments = processor.process(chunk, is_last=is_last)
                all_segments.extend(segments)

                # Update progress
                tracker.update_bytes(len(chunk))

                # Check memory and adjust chunk size if needed
                if self._memory_monitor.should_reduce_chunk_size():
                    chunk_size = self._memory_monitor.get_recommended_chunk_size()

            # Flush any remaining buffer
            remaining_segments = processor.flush()
            all_segments.extend(remaining_segments)

        # Merge continuous segments if configured
        if self._config.merge_segments and all_segments:
            merger = SegmentMerger()
            all_segments = merger.process_batch(all_segments, is_last=True)

        # Finish tracking
        tracker.finish_file()

        # Create transcript
        return self._create_transcript(file_path, all_segments)

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


def process_directory(
    directory: Path,
    pattern: str = "*.txt",
    recursive: bool = False,
    on_progress: SimpleProgressCallback | None = None,
) -> Iterator[Transcript]:
    """
    Convenience function to process all matching files in a directory.

    Args:
        directory: Directory to process.
        pattern: Glob pattern for matching files.
        recursive: Whether to search subdirectories.
        on_progress: Optional progress callback.

    Yields:
        Transcript objects.
    """
    processor = TranscriptBatchProcessor()
    files = processor.discover_files(directory, pattern, recursive)
    yield from processor.process_all(files, on_progress)


def process_files(
    files: list[Path],
    on_progress: SimpleProgressCallback | None = None,
    skip_on_error: bool = True,
) -> Iterator[Transcript]:
    """
    Convenience function to process a list of files.

    Args:
        files: List of file paths.
        on_progress: Optional progress callback.
        skip_on_error: Whether to skip failed files.

    Yields:
        Transcript objects.
    """
    processor = TranscriptBatchProcessor()
    yield from processor.process_all(files, on_progress, skip_on_error)
