"""
Async I/O module unit tests.

Tests for AsyncStreamReader, AsyncTranscriptBatchProcessor,
and related async functions.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from forensic.io.async_io import (
    DEFAULT_MAX_CONCURRENT,
    AsyncBatchConfig,
    AsyncBatchResult,
    AsyncFileProcessingError,
    AsyncStreamReader,
    AsyncTranscriptBatchProcessor,
    FileNotOpenError,
    process_directory_async,
    process_files_async,
    read_file_streaming_async,
)
from forensic.io.memory import MemoryMonitor

# Type alias for async progress callback
AsyncProgressCallback = Callable[[Path, float], Awaitable[None] | None]


class TestAsyncBatchConfig:
    """AsyncBatchConfig class tests."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = AsyncBatchConfig()

        assert config.default_chunk_size == 1024 * 1024  # 1MB
        assert config.skip_on_error is True
        assert config.merge_segments is True
        assert config.encoding == "utf-8"
        assert config.default_speaker == "unknown"
        assert config.max_concurrent == DEFAULT_MAX_CONCURRENT

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = AsyncBatchConfig(
            default_chunk_size=512 * 1024,
            skip_on_error=False,
            merge_segments=False,
            encoding="euc-kr",
            default_speaker="speaker1",
            max_concurrent=5,
        )

        assert config.default_chunk_size == 512 * 1024
        assert config.skip_on_error is False
        assert config.merge_segments is False
        assert config.encoding == "euc-kr"
        assert config.default_speaker == "speaker1"
        assert config.max_concurrent == 5


class TestAsyncBatchResult:
    """AsyncBatchResult class tests."""

    def test_default_result(self) -> None:
        """Test default result values."""
        result = AsyncBatchResult()

        assert result.total_files == 0
        assert result.successful_files == 0
        assert result.failed_files == 0
        assert result.total_segments == 0
        assert result.total_duration == 0.0
        assert result.errors == []

    def test_success_rate_all_success(self) -> None:
        """Test success rate with all files successful."""
        result = AsyncBatchResult(total_files=10, successful_files=10, failed_files=0)

        assert result.success_rate == 1.0

    def test_success_rate_partial(self) -> None:
        """Test success rate with partial success."""
        result = AsyncBatchResult(total_files=10, successful_files=7, failed_files=3)

        assert result.success_rate == 0.7

    def test_success_rate_all_failed(self) -> None:
        """Test success rate with all files failed."""
        result = AsyncBatchResult(total_files=10, successful_files=0, failed_files=10)

        assert result.success_rate == 0.0

    def test_success_rate_empty(self) -> None:
        """Test success rate with no files."""
        result = AsyncBatchResult(total_files=0)

        assert result.success_rate == 1.0

    def test_with_errors(self) -> None:
        """Test result with error list."""
        errors = [(Path("/test1.txt"), "Error 1"), (Path("/test2.txt"), "Error 2")]
        result = AsyncBatchResult(
            total_files=5,
            successful_files=3,
            failed_files=2,
            errors=errors,
        )

        assert len(result.errors) == 2
        assert result.errors[0][0] == Path("/test1.txt")


class TestAsyncFileProcessingError:
    """AsyncFileProcessingError class tests."""

    def test_error_creation(self) -> None:
        """Test error creation with path and cause."""
        path = Path("/test/file.txt")
        cause = ValueError("Invalid content")
        error = AsyncFileProcessingError(path, cause)

        assert error.path == path
        assert error.cause == cause
        assert "file.txt" in str(error)
        assert "Invalid content" in str(error)


class TestAsyncStreamReader:
    """AsyncStreamReader class tests."""

    @pytest.fixture
    def temp_file(self, tmp_path: Path) -> Path:
        """Create a temporary test file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello world! " * 1000)  # ~12KB
        return file_path

    @pytest.fixture
    def reader(self) -> AsyncStreamReader:
        """Create an async stream reader instance."""
        return AsyncStreamReader()

    @pytest.mark.asyncio
    async def test_init_default(self) -> None:
        """Test default initialization."""
        reader = AsyncStreamReader()

        assert reader.path is None
        assert reader.file_size == 0
        assert reader.bytes_read == 0
        assert reader.is_open() is False

    @pytest.mark.asyncio
    async def test_init_with_memory_monitor(self) -> None:
        """Test initialization with memory monitor."""
        monitor = MemoryMonitor()
        reader = AsyncStreamReader(memory_monitor=monitor)

        assert reader is not None

    @pytest.mark.asyncio
    async def test_open_file(self, reader: AsyncStreamReader, temp_file: Path) -> None:
        """Test opening a file."""
        await reader.open(temp_file)

        assert reader.path == temp_file
        assert reader.file_size > 0
        assert reader.is_open() is True

    @pytest.mark.asyncio
    async def test_open_nonexistent_raises_error(self, reader: AsyncStreamReader) -> None:
        """Test opening non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await reader.open(Path("/nonexistent/file.txt"))

    @pytest.mark.asyncio
    async def test_read_chunks_default_size(
        self, reader: AsyncStreamReader, temp_file: Path
    ) -> None:
        """Test reading chunks with default size."""
        await reader.open(temp_file)

        chunks = []
        async for chunk in reader.read_chunks():
            chunks.append(chunk)

        assert len(chunks) > 0
        assert reader.bytes_read == temp_file.stat().st_size

    @pytest.mark.asyncio
    async def test_read_chunks_custom_size(
        self, reader: AsyncStreamReader, temp_file: Path
    ) -> None:
        """Test reading chunks with custom size."""
        await reader.open(temp_file)

        chunks = []
        async for chunk in reader.read_chunks(chunk_size=1024):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Most chunks should be at or near the specified size
        assert all(len(c) <= 1024 for c in chunks)

    @pytest.mark.asyncio
    async def test_read_chunks_without_open_raises_error(
        self, reader: AsyncStreamReader
    ) -> None:
        """Test reading chunks without opening raises FileNotOpenError."""
        with pytest.raises(FileNotOpenError):
            async for _ in reader.read_chunks():
                pass

    @pytest.mark.asyncio
    async def test_get_progress(self, reader: AsyncStreamReader, temp_file: Path) -> None:
        """Test progress tracking."""
        await reader.open(temp_file)

        assert reader.get_progress() == 0.0

        async for _ in reader.read_chunks(chunk_size=1024):
            # Progress should increase
            assert 0.0 <= reader.get_progress() <= 1.0
            break

        # After full read, progress should be complete
        async for _ in reader.read_chunks(chunk_size=1024):
            pass

        assert reader.get_progress() == 1.0

    @pytest.mark.asyncio
    async def test_get_progress_percent(
        self, reader: AsyncStreamReader, temp_file: Path
    ) -> None:
        """Test progress percentage tracking."""
        await reader.open(temp_file)

        # After full read
        async for _ in reader.read_chunks():
            pass

        assert reader.get_progress_percent() == 100.0

    @pytest.mark.asyncio
    async def test_close(self, reader: AsyncStreamReader, temp_file: Path) -> None:
        """Test closing file."""
        await reader.open(temp_file)
        assert reader.is_open() is True

        await reader.close()
        assert reader.is_open() is False

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_file: Path) -> None:
        """Test async context manager usage."""
        async with AsyncStreamReader() as reader:
            await reader.open(temp_file)
            assert reader.is_open() is True

        # File should be closed after exiting context
        assert reader.is_open() is False

    @pytest.mark.asyncio
    async def test_reset(self, reader: AsyncStreamReader, temp_file: Path) -> None:
        """Test resetting reading position."""
        await reader.open(temp_file)

        # Read some data
        async for chunk in reader.read_chunks(chunk_size=1024):
            first_chunk = chunk
            break

        assert reader.bytes_read > 0

        # Reset
        await reader.reset()
        assert reader.bytes_read == 0

        # Read again and verify same data
        async for chunk in reader.read_chunks(chunk_size=1024):
            assert chunk == first_chunk
            break

    @pytest.mark.asyncio
    async def test_reset_without_open_raises_error(
        self, reader: AsyncStreamReader
    ) -> None:
        """Test reset without opening raises FileNotOpenError."""
        with pytest.raises(FileNotOpenError):
            await reader.reset()

    @pytest.mark.asyncio
    async def test_encoding_detection_utf8(self, tmp_path: Path) -> None:
        """Test encoding detection for UTF-8 file."""
        file_path = tmp_path / "utf8.txt"
        file_path.write_text("Hello world", encoding="utf-8")

        reader = AsyncStreamReader()
        await reader.open(file_path)

        assert reader.encoding in ("utf-8", "ascii")

    @pytest.mark.asyncio
    async def test_encoding_detection_utf8_bom(self, tmp_path: Path) -> None:
        """Test encoding detection for UTF-8 with BOM."""
        file_path = tmp_path / "utf8_bom.txt"
        file_path.write_bytes(b"\xef\xbb\xbfHello world")

        reader = AsyncStreamReader()
        await reader.open(file_path)

        assert reader.encoding == "utf-8-sig"


class TestAsyncTranscriptBatchProcessor:
    """AsyncTranscriptBatchProcessor class tests."""

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
        (subdir / "file4.txt").write_text(
            "[00:00:00.000 --> 00:00:02.000] Subdirectory file\n"
        )

        return tmp_path

    @pytest.fixture
    def processor(self) -> AsyncTranscriptBatchProcessor:
        """Create an async batch processor instance."""
        return AsyncTranscriptBatchProcessor()

    @pytest.mark.asyncio
    async def test_init_default(self) -> None:
        """Test default initialization."""
        processor = AsyncTranscriptBatchProcessor()

        assert processor.config is not None
        assert processor.config.default_chunk_size == 1024 * 1024
        assert processor.config.max_concurrent == DEFAULT_MAX_CONCURRENT

    @pytest.mark.asyncio
    async def test_init_with_config(self) -> None:
        """Test initialization with custom config."""
        config = AsyncBatchConfig(
            default_chunk_size=512 * 1024, max_concurrent=5
        )
        processor = AsyncTranscriptBatchProcessor(config=config)

        assert processor.config.default_chunk_size == 512 * 1024
        assert processor.config.max_concurrent == 5

    @pytest.mark.asyncio
    async def test_init_with_memory_monitor(self) -> None:
        """Test initialization with memory monitor."""
        monitor = MemoryMonitor()
        processor = AsyncTranscriptBatchProcessor(memory_monitor=monitor)

        assert processor is not None

    @pytest.mark.asyncio
    async def test_discover_files(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test async file discovery."""
        files = await processor.discover_files(temp_dir, "*.txt")

        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    @pytest.mark.asyncio
    async def test_discover_files_recursive(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test recursive file discovery."""
        files = await processor.discover_files(temp_dir, "*.txt", recursive=True)

        assert len(files) == 3  # 2 in root + 1 in subdir

    @pytest.mark.asyncio
    async def test_process_single(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test processing a single file."""
        file_path = temp_dir / "file1.txt"
        transcript = await processor.process_single(file_path)

        assert transcript is not None
        assert transcript.file_path == file_path
        assert transcript.segment_count >= 0

    @pytest.mark.asyncio
    async def test_process_single_nonexistent_raises_error(
        self, processor: AsyncTranscriptBatchProcessor
    ) -> None:
        """Test processing non-existent file raises error."""
        with pytest.raises(AsyncFileProcessingError):
            await processor.process_single(Path("/nonexistent/file.txt"))

    @pytest.mark.asyncio
    async def test_process_all_async_basic(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test processing all files asynchronously."""
        files = [temp_dir / "file1.txt", temp_dir / "file2.txt"]

        transcripts = []
        async for transcript in processor.process_all_async(files):
            transcripts.append(transcript)

        assert len(transcripts) == 2
        assert processor.result.successful_files == 2
        assert processor.result.failed_files == 0

    @pytest.mark.asyncio
    async def test_process_all_async_with_concurrency_limit(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test processing with concurrency limit."""
        files = [temp_dir / "file1.txt", temp_dir / "file2.txt"]

        transcripts = []
        async for transcript in processor.process_all_async(files, max_concurrent=1):
            transcripts.append(transcript)

        assert len(transcripts) == 2

    @pytest.mark.asyncio
    async def test_process_all_async_with_progress(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test processing with async progress callback."""
        files = [temp_dir / "file1.txt"]
        progress_calls: list[tuple[Path, float]] = []

        async def on_progress(path: Path, progress: float) -> None:
            progress_calls.append((path, progress))

        async for _ in processor.process_all_async(files, on_progress=on_progress):
            pass

        assert len(progress_calls) >= 1

    @pytest.mark.asyncio
    async def test_process_all_async_skip_on_error(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test processing continues on error with skip_on_error=True."""
        files = [
            temp_dir / "file1.txt",
            Path("/nonexistent.txt"),  # This will fail
            temp_dir / "file2.txt",
        ]

        transcripts = []
        async for transcript in processor.process_all_async(
            files, skip_on_error=True
        ):
            transcripts.append(transcript)

        assert len(transcripts) == 2  # Only successful files
        assert processor.result.successful_files == 2
        assert processor.result.failed_files == 1

    @pytest.mark.asyncio
    async def test_process_all_async_raise_on_error(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test processing raises error with skip_on_error=False."""
        files = [Path("/nonexistent.txt"), temp_dir / "file1.txt"]

        with pytest.raises(AsyncFileProcessingError):
            async for _ in processor.process_all_async(files, skip_on_error=False):
                pass

    @pytest.mark.asyncio
    async def test_process_all_async_empty_list(
        self, processor: AsyncTranscriptBatchProcessor
    ) -> None:
        """Test processing empty file list."""
        transcripts = []
        async for transcript in processor.process_all_async([]):
            transcripts.append(transcript)

        assert len(transcripts) == 0
        assert processor.result.total_files == 0

    @pytest.mark.asyncio
    async def test_get_adaptive_concurrency(self, processor: AsyncTranscriptBatchProcessor) -> None:
        """Test adaptive concurrency based on memory state."""
        # Normal state should return requested concurrency
        concurrency = processor._get_adaptive_concurrency(10)
        assert concurrency == 10

    @pytest.mark.asyncio
    async def test_get_batch_summary(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test getting batch summary."""
        files = [temp_dir / "file1.txt", temp_dir / "file2.txt"]
        async for _ in processor.process_all_async(files):
            pass

        summary = processor.get_batch_summary()

        assert summary["total_files"] == 2
        assert summary["successful_files"] == 2
        assert summary["failed_files"] == 0
        assert summary["success_rate"] == 1.0
        assert "total_segments" in summary
        assert "total_duration_seconds" in summary

    @pytest.mark.asyncio
    async def test_result_property(
        self, processor: AsyncTranscriptBatchProcessor, temp_dir: Path
    ) -> None:
        """Test result property."""
        files = [temp_dir / "file1.txt"]
        async for _ in processor.process_all_async(files):
            pass

        result = processor.result

        assert result.total_files == 1
        assert result.successful_files == 1

    @pytest.mark.asyncio
    async def test_config_property(self, processor: AsyncTranscriptBatchProcessor) -> None:
        """Test config property."""
        config = processor.config

        assert config is not None
        assert isinstance(config, AsyncBatchConfig)


class TestProcessDirectoryAsyncFunction:
    """Tests for process_directory_async convenience function."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with test files."""
        (tmp_path / "file1.txt").write_text(
            "[00:00:00.000 --> 00:00:05.000] Hello\n"
        )
        (tmp_path / "file2.txt").write_text(
            "[00:00:00.000 --> 00:00:03.000] World\n"
        )
        return tmp_path

    @pytest.mark.asyncio
    async def test_process_directory_async_basic(self, temp_dir: Path) -> None:
        """Test basic async directory processing."""
        transcripts = []
        async for transcript in process_directory_async(temp_dir, "*.txt"):
            transcripts.append(transcript)

        assert len(transcripts) == 2

    @pytest.mark.asyncio
    async def test_process_directory_async_with_concurrency(
        self, temp_dir: Path
    ) -> None:
        """Test directory processing with concurrency limit."""
        transcripts = []
        async for transcript in process_directory_async(
            temp_dir, "*.txt", max_concurrent=1
        ):
            transcripts.append(transcript)

        assert len(transcripts) == 2

    @pytest.mark.asyncio
    async def test_process_directory_async_with_progress(
        self, temp_dir: Path
    ) -> None:
        """Test directory processing with async progress callback."""
        calls: list[float] = []

        async def on_progress(_path: Path, progress: float) -> None:
            calls.append(progress)

        async for _ in process_directory_async(
            temp_dir, "*.txt", on_progress=on_progress
        ):
            pass

        assert len(calls) >= 1

    @pytest.mark.asyncio
    async def test_process_directory_async_no_matches(self, temp_dir: Path) -> None:
        """Test directory processing with no matching files."""
        transcripts = []
        async for transcript in process_directory_async(temp_dir, "*.json"):
            transcripts.append(transcript)

        assert len(transcripts) == 0


class TestProcessFilesAsyncFunction:
    """Tests for process_files_async convenience function."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with test files."""
        (tmp_path / "file1.txt").write_text(
            "[00:00:00.000 --> 00:00:05.000] Hello\n"
        )
        (tmp_path / "file2.txt").write_text(
            "[00:00:00.000 --> 00:00:03.000] World\n"
        )
        return tmp_path

    @pytest.mark.asyncio
    async def test_process_files_async_basic(self, temp_dir: Path) -> None:
        """Test basic async file processing."""
        files = [temp_dir / "file1.txt", temp_dir / "file2.txt"]

        transcripts = []
        async for transcript in process_files_async(files):
            transcripts.append(transcript)

        assert len(transcripts) == 2

    @pytest.mark.asyncio
    async def test_process_files_async_with_progress(self, temp_dir: Path) -> None:
        """Test file processing with async progress callback."""
        files = [temp_dir / "file1.txt"]
        calls: list[float] = []

        async def on_progress(_path: Path, progress: float) -> None:
            calls.append(progress)

        async for _ in process_files_async(files, on_progress=on_progress):
            pass

        assert len(calls) >= 1

    @pytest.mark.asyncio
    async def test_process_files_async_skip_on_error(self, temp_dir: Path) -> None:
        """Test file processing with skip_on_error."""
        files = [
            temp_dir / "file1.txt",
            Path("/nonexistent.txt"),
        ]

        transcripts = []
        async for transcript in process_files_async(files, skip_on_error=True):
            transcripts.append(transcript)

        assert len(transcripts) == 1

    @pytest.mark.asyncio
    async def test_process_files_async_raise_on_error(self) -> None:
        """Test file processing raises error."""
        files = [Path("/nonexistent.txt")]

        with pytest.raises(AsyncFileProcessingError):
            async for _ in process_files_async(files, skip_on_error=False):
                pass

    @pytest.mark.asyncio
    async def test_process_files_async_empty_list(self) -> None:
        """Test processing empty file list."""
        transcripts = []
        async for transcript in process_files_async([]):
            transcripts.append(transcript)

        assert len(transcripts) == 0


class TestReadFileStreamingAsyncFunction:
    """Tests for read_file_streaming_async convenience function."""

    @pytest.fixture
    def temp_file(self, tmp_path: Path) -> Path:
        """Create a temporary test file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello world! " * 1000)
        return file_path

    @pytest.mark.asyncio
    async def test_read_file_streaming_async_basic(
        self, temp_file: Path
    ) -> None:
        """Test basic async streaming file reading."""
        chunks = []
        async for chunk in read_file_streaming_async(temp_file):
            chunks.append(chunk)

        assert len(chunks) > 0
        total_bytes = sum(len(c) for c in chunks)
        assert total_bytes == temp_file.stat().st_size

    @pytest.mark.asyncio
    async def test_read_file_streaming_async_with_chunk_size(
        self, temp_file: Path
    ) -> None:
        """Test streaming with custom chunk size."""
        chunks = []
        async for chunk in read_file_streaming_async(temp_file, chunk_size=1024):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert all(len(c) <= 1024 for c in chunks)


class TestConcurrencyControl:
    """Tests for concurrency control mechanisms."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create multiple test files."""
        for i in range(5):
            (tmp_path / f"file{i}.txt").write_text(
                f"[00:00:00.000 --> 00:00:0{i}.000] Content {i}\n"
            )
        return tmp_path

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, temp_dir: Path) -> None:
        """Test that semaphore properly limits concurrent tasks."""
        import asyncio

        files = sorted(temp_dir.glob("*.txt"))
        max_concurrent = 2

        active_count = 0
        max_active = 0
        lock = asyncio.Lock()

        async def counting_processor(file_list: list[Path]) -> list:
            """Processor that tracks concurrent execution."""
            nonlocal active_count, max_active

            results = []
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_with_counting(path: Path):
                nonlocal active_count, max_active

                async with semaphore:
                    async with lock:
                        active_count += 1
                        if active_count > max_active:
                            max_active = active_count

                    # Simulate some work
                    await asyncio.sleep(0.01)

                    async with lock:
                        active_count -= 1

                    return {"id": f"t_{path.name}"}

            tasks = [asyncio.create_task(process_with_counting(f)) for f in file_list]
            for task in asyncio.as_completed(tasks):
                result = await task
                if result:
                    results.append(result)

            return results

        transcripts = await counting_processor(files)

        assert len(transcripts) == 5
        assert max_active <= max_concurrent
