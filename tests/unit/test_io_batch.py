"""
Batch processor module unit tests.

Tests for TranscriptBatchProcessor, BatchConfig, BatchResult, and related functions.
"""

from pathlib import Path

import pytest

from forensic.io.batch import (
    BatchConfig,
    BatchResult,
    FileProcessingError,
    TranscriptBatchProcessor,
    process_directory,
    process_files,
)
from forensic.io.discovery import FileFilter, SortOrder
from forensic.io.memory import MemoryMonitor


class TestBatchConfig:
    """BatchConfig class tests."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = BatchConfig()

        assert config.default_chunk_size == 1024 * 1024  # 1MB
        assert config.skip_on_error is True
        assert config.merge_segments is True
        assert config.encoding == "utf-8"
        assert config.default_speaker == "unknown"

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = BatchConfig(
            default_chunk_size=512 * 1024,
            skip_on_error=False,
            merge_segments=False,
            encoding="euc-kr",
            default_speaker="speaker1",
        )

        assert config.default_chunk_size == 512 * 1024
        assert config.skip_on_error is False
        assert config.merge_segments is False
        assert config.encoding == "euc-kr"
        assert config.default_speaker == "speaker1"


class TestBatchResult:
    """BatchResult class tests."""

    def test_default_result(self) -> None:
        """Test default result values."""
        result = BatchResult()

        assert result.total_files == 0
        assert result.successful_files == 0
        assert result.failed_files == 0
        assert result.total_segments == 0
        assert result.total_duration == 0.0
        assert result.errors == []

    def test_success_rate_all_success(self) -> None:
        """Test success rate with all files successful."""
        result = BatchResult(total_files=10, successful_files=10, failed_files=0)

        assert result.success_rate == 1.0

    def test_success_rate_partial(self) -> None:
        """Test success rate with partial success."""
        result = BatchResult(total_files=10, successful_files=7, failed_files=3)

        assert result.success_rate == 0.7

    def test_success_rate_all_failed(self) -> None:
        """Test success rate with all files failed."""
        result = BatchResult(total_files=10, successful_files=0, failed_files=10)

        assert result.success_rate == 0.0

    def test_success_rate_empty(self) -> None:
        """Test success rate with no files."""
        result = BatchResult(total_files=0)

        assert result.success_rate == 1.0

    def test_with_errors(self) -> None:
        """Test result with error list."""
        errors = [(Path("/test1.txt"), "Error 1"), (Path("/test2.txt"), "Error 2")]
        result = BatchResult(
            total_files=5,
            successful_files=3,
            failed_files=2,
            errors=errors,
        )

        assert len(result.errors) == 2
        assert result.errors[0][0] == Path("/test1.txt")


class TestFileProcessingError:
    """FileProcessingError class tests."""

    def test_error_creation(self) -> None:
        """Test error creation with path and cause."""
        path = Path("/test/file.txt")
        cause = ValueError("Invalid content")
        error = FileProcessingError(path, cause)

        assert error.path == path
        assert error.cause == cause
        assert "file.txt" in str(error)
        assert "Invalid content" in str(error)


class TestTranscriptBatchProcessor:
    """TranscriptBatchProcessor class tests."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with test files."""
        # Create test transcript files with timestamp format
        (tmp_path / "file1.txt").write_text(
            "[00:00:00.000 --> 00:00:05.000] Hello world\n"
            "[00:00:05.000 --> 00:00:10.000] This is a test\n"
        )
        (tmp_path / "file2.txt").write_text(
            "[00:00:00.000 --> 00:00:03.000] Second file\n"
            "[00:00:03.000 --> 00:00:06.000] More content\n"
        )
        (tmp_path / "file3.json").write_text('{"key": "value"}')

        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file4.txt").write_text("[00:00:00.000 --> 00:00:02.000] Subdirectory file\n")

        return tmp_path

    @pytest.fixture
    def processor(self) -> TranscriptBatchProcessor:
        """Create a batch processor instance."""
        return TranscriptBatchProcessor()

    def test_init_default(self) -> None:
        """Test default initialization."""
        processor = TranscriptBatchProcessor()

        assert processor.config is not None
        assert processor.config.default_chunk_size == 1024 * 1024

    def test_init_with_config(self) -> None:
        """Test initialization with custom config."""
        config = BatchConfig(default_chunk_size=512 * 1024)
        processor = TranscriptBatchProcessor(config=config)

        assert processor.config.default_chunk_size == 512 * 1024

    def test_init_with_memory_monitor(self) -> None:
        """Test initialization with memory monitor."""
        monitor = MemoryMonitor()
        processor = TranscriptBatchProcessor(memory_monitor=monitor)

        assert processor is not None

    def test_discover_files(self, processor: TranscriptBatchProcessor, temp_dir: Path) -> None:
        """Test file discovery."""
        files = processor.discover_files(temp_dir, "*.txt")

        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    def test_discover_files_recursive(
        self, processor: TranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test recursive file discovery."""
        files = processor.discover_files(temp_dir, "*.txt", recursive=True)

        assert len(files) == 3  # 2 in root + 1 in subdir

    def test_discover_files_sorted(
        self, processor: TranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test file discovery with sorting."""
        files = processor.discover_files(temp_dir, "*.txt", sort_order=SortOrder.NAME_DESC)

        assert len(files) == 2
        assert files[0].name == "file2.txt"
        assert files[1].name == "file1.txt"

    def test_discover_files_filtered(
        self, processor: TranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test file discovery with filter."""
        file_filter = FileFilter(pattern="*.txt", min_size=50)
        files = processor.discover_files_filtered(temp_dir, file_filter)

        # Both files should be larger than 50 bytes
        assert len(files) == 2

    def test_process_single(self, processor: TranscriptBatchProcessor, temp_dir: Path) -> None:
        """Test processing a single file."""
        file_path = temp_dir / "file1.txt"
        transcript = processor.process_single(file_path)

        assert transcript is not None
        assert transcript.file_path == file_path
        assert transcript.segment_count >= 0

    def test_process_single_nonexistent_raises_error(
        self, processor: TranscriptBatchProcessor
    ) -> None:
        """Test processing non-existent file raises error."""
        with pytest.raises(FileProcessingError):
            processor.process_single(Path("/nonexistent/file.txt"))

    def test_process_all_basic(self, processor: TranscriptBatchProcessor, temp_dir: Path) -> None:
        """Test processing all files."""
        files = [temp_dir / "file1.txt", temp_dir / "file2.txt"]
        transcripts = list(processor.process_all(files))

        assert len(transcripts) == 2
        assert processor.result.successful_files == 2
        assert processor.result.failed_files == 0

    def test_process_all_with_progress(
        self, processor: TranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test processing with progress callback."""
        files = [temp_dir / "file1.txt"]
        progress_calls: list[tuple[Path, float]] = []

        def on_progress(path: Path, progress: float) -> None:
            progress_calls.append((path, progress))

        list(processor.process_all(files, on_progress=on_progress))

        assert len(progress_calls) >= 1

    def test_process_all_skip_on_error(
        self, processor: TranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test processing continues on error with skip_on_error=True."""
        files = [
            temp_dir / "file1.txt",
            Path("/nonexistent.txt"),  # This will fail
            temp_dir / "file2.txt",
        ]

        transcripts = list(processor.process_all(files, skip_on_error=True))

        assert len(transcripts) == 2  # Only successful files
        assert processor.result.successful_files == 2
        assert processor.result.failed_files == 1

    def test_process_all_raise_on_error(
        self, processor: TranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test processing raises error with skip_on_error=False."""
        files = [Path("/nonexistent.txt"), temp_dir / "file1.txt"]

        with pytest.raises(FileProcessingError):
            list(processor.process_all(files, skip_on_error=False))

    def test_process_all_empty_list(self, processor: TranscriptBatchProcessor) -> None:
        """Test processing empty file list."""
        transcripts = list(processor.process_all([]))

        assert len(transcripts) == 0
        assert processor.result.total_files == 0

    def test_get_batch_summary(self, processor: TranscriptBatchProcessor, temp_dir: Path) -> None:
        """Test getting batch summary."""
        files = [temp_dir / "file1.txt", temp_dir / "file2.txt"]
        list(processor.process_all(files))

        summary = processor.get_batch_summary()

        assert summary["total_files"] == 2
        assert summary["successful_files"] == 2
        assert summary["failed_files"] == 0
        assert summary["success_rate"] == 1.0
        assert "total_segments" in summary
        assert "total_duration_seconds" in summary

    def test_result_property(self, processor: TranscriptBatchProcessor, temp_dir: Path) -> None:
        """Test result property."""
        files = [temp_dir / "file1.txt"]
        list(processor.process_all(files))

        result = processor.result

        assert result.total_files == 1
        assert result.successful_files == 1

    def test_config_property(self, processor: TranscriptBatchProcessor) -> None:
        """Test config property."""
        config = processor.config

        assert config is not None
        assert isinstance(config, BatchConfig)


class TestProcessDirectoryFunction:
    """Tests for process_directory convenience function."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with test files."""
        (tmp_path / "file1.txt").write_text("[00:00:00.000 --> 00:00:05.000] Hello\n")
        (tmp_path / "file2.txt").write_text("[00:00:00.000 --> 00:00:03.000] World\n")
        return tmp_path

    def test_process_directory_basic(self, temp_dir: Path) -> None:
        """Test basic directory processing."""
        transcripts = list(process_directory(temp_dir, "*.txt"))

        assert len(transcripts) == 2

    def test_process_directory_with_progress(self, temp_dir: Path) -> None:
        """Test directory processing with progress callback."""
        calls: list[float] = []

        def on_progress(_path: Path, progress: float) -> None:
            calls.append(progress)

        list(process_directory(temp_dir, "*.txt", on_progress=on_progress))

        assert len(calls) >= 1

    def test_process_directory_no_matches(self, temp_dir: Path) -> None:
        """Test directory processing with no matching files."""
        transcripts = list(process_directory(temp_dir, "*.json"))

        assert len(transcripts) == 0


class TestProcessFilesFunction:
    """Tests for process_files convenience function."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with test files."""
        (tmp_path / "file1.txt").write_text("[00:00:00.000 --> 00:00:05.000] Hello\n")
        (tmp_path / "file2.txt").write_text("[00:00:00.000 --> 00:00:03.000] World\n")
        return tmp_path

    def test_process_files_basic(self, temp_dir: Path) -> None:
        """Test basic file processing."""
        files = [temp_dir / "file1.txt", temp_dir / "file2.txt"]
        transcripts = list(process_files(files))

        assert len(transcripts) == 2

    def test_process_files_with_progress(self, temp_dir: Path) -> None:
        """Test file processing with progress callback."""
        files = [temp_dir / "file1.txt"]
        calls: list[float] = []

        def on_progress(_path: Path, progress: float) -> None:
            calls.append(progress)

        list(process_files(files, on_progress=on_progress))

        assert len(calls) >= 1

    def test_process_files_skip_on_error(self, temp_dir: Path) -> None:
        """Test file processing with skip_on_error."""
        files = [
            temp_dir / "file1.txt",
            Path("/nonexistent.txt"),
        ]

        transcripts = list(process_files(files, skip_on_error=True))

        assert len(transcripts) == 1

    def test_process_files_raise_on_error(self) -> None:
        """Test file processing raises error."""
        files = [Path("/nonexistent.txt")]

        with pytest.raises(FileProcessingError):
            list(process_files(files, skip_on_error=False))

    def test_process_files_empty_list(self) -> None:
        """Test processing empty file list."""
        transcripts = list(process_files([]))

        assert len(transcripts) == 0
