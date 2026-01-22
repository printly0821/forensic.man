"""
Progress tracker module unit tests.

Tests for ProgressTracker, FileProgress, BatchProgress, and related functions.
"""

from pathlib import Path

import pytest

from forensic.io.progress import (
    BatchProgress,
    FileProgress,
    NoActiveFileError,
    ProgressTracker,
    create_progress_tracker,
)


class TestFileProgress:
    """FileProgress class tests."""

    def test_create_file_progress(self) -> None:
        """Test creating FileProgress."""
        fp = FileProgress(path=Path("test.txt"), total_bytes=1000)

        assert fp.path == Path("test.txt")
        assert fp.total_bytes == 1000
        assert fp.bytes_processed == 0
        assert fp.is_complete is False

    def test_progress_ratio(self) -> None:
        """Test progress ratio calculation."""
        fp = FileProgress(path=Path("test.txt"), total_bytes=1000, bytes_processed=500)

        assert fp.progress == 0.5

    def test_progress_percent(self) -> None:
        """Test progress percentage calculation."""
        fp = FileProgress(path=Path("test.txt"), total_bytes=1000, bytes_processed=250)

        assert fp.progress_percent == 25.0

    def test_progress_zero_total(self) -> None:
        """Test progress with zero total bytes."""
        fp = FileProgress(path=Path("test.txt"), total_bytes=0)

        assert fp.progress == 0.0

        fp.is_complete = True
        assert fp.progress == 1.0

    def test_progress_overflow(self) -> None:
        """Test progress caps at 1.0."""
        fp = FileProgress(path=Path("test.txt"), total_bytes=100, bytes_processed=200)

        assert fp.progress == 1.0


class TestBatchProgress:
    """BatchProgress class tests."""

    def test_create_batch_progress(self) -> None:
        """Test creating BatchProgress."""
        bp = BatchProgress(total_files=10)

        assert bp.total_files == 10
        assert bp.files_completed == 0
        assert bp.total_bytes == 0
        assert bp.bytes_processed == 0

    def test_progress_by_bytes(self) -> None:
        """Test progress calculation by bytes."""
        bp = BatchProgress(
            total_files=2,
            files_completed=1,
            total_bytes=1000,
            bytes_processed=500,
        )

        assert bp.progress == 0.5

    def test_progress_by_file_count(self) -> None:
        """Test progress fallback to file count."""
        bp = BatchProgress(
            total_files=4,
            files_completed=2,
            total_bytes=0,  # No byte tracking
            bytes_processed=0,
        )

        assert bp.progress == 0.5

    def test_progress_empty_batch(self) -> None:
        """Test progress with empty batch."""
        bp = BatchProgress(total_files=0)

        assert bp.progress == 1.0

    def test_files_remaining(self) -> None:
        """Test files remaining calculation."""
        bp = BatchProgress(total_files=10, files_completed=3)

        assert bp.files_remaining == 7


class TestProgressTracker:
    """ProgressTracker class tests."""

    def test_init(self) -> None:
        """Test ProgressTracker initialization."""
        tracker = ProgressTracker(total_files=5)

        assert tracker.total_files == 5
        assert tracker.files_completed == 0
        assert tracker.overall_progress == 0.0

    def test_init_negative_files_raises_error(self) -> None:
        """Test negative total_files raises error."""
        with pytest.raises(ValueError):
            ProgressTracker(total_files=-1)

    def test_start_file(self, tmp_path: Path) -> None:
        """Test starting file tracking."""
        tracker = ProgressTracker(total_files=1)
        test_file = tmp_path / "test.txt"

        tracker.start_file(test_file, 1000)

        assert tracker.current_file == test_file
        assert tracker.current_file_progress == 0.0

    def test_update_bytes(self, tmp_path: Path) -> None:
        """Test updating bytes processed."""
        tracker = ProgressTracker(total_files=1)
        test_file = tmp_path / "test.txt"

        tracker.start_file(test_file, 1000)
        tracker.update_bytes(500)

        assert tracker.current_file_progress == 0.5

    def test_update_bytes_without_file_raises_error(self) -> None:
        """Test updating without active file raises error."""
        tracker = ProgressTracker(total_files=1)

        with pytest.raises(NoActiveFileError):
            tracker.update_bytes(100)

    def test_update_progress(self, tmp_path: Path) -> None:
        """Test updating progress directly."""
        tracker = ProgressTracker(total_files=1)
        test_file = tmp_path / "test.txt"

        tracker.start_file(test_file, 1000)
        tracker.update_progress(0.75)

        assert tracker.current_file_progress == 0.75

    def test_update_progress_out_of_range_raises_error(self, tmp_path: Path) -> None:
        """Test invalid progress value raises error."""
        tracker = ProgressTracker(total_files=1)
        test_file = tmp_path / "test.txt"

        tracker.start_file(test_file, 1000)

        with pytest.raises(ValueError):
            tracker.update_progress(1.5)

        with pytest.raises(ValueError):
            tracker.update_progress(-0.1)

    def test_finish_file(self, tmp_path: Path) -> None:
        """Test finishing file tracking."""
        tracker = ProgressTracker(total_files=2)
        test_file = tmp_path / "test.txt"

        tracker.start_file(test_file, 1000)
        tracker.update_bytes(500)
        tracker.finish_file()

        assert tracker.files_completed == 1
        assert tracker.current_file is None

    def test_finish_file_without_active_raises_error(self) -> None:
        """Test finishing without active file raises error."""
        tracker = ProgressTracker(total_files=1)

        with pytest.raises(NoActiveFileError):
            tracker.finish_file()

    def test_overall_progress(self, tmp_path: Path) -> None:
        """Test overall progress calculation."""
        tracker = ProgressTracker(total_files=2)

        # Process first file (1000 bytes)
        file1 = tmp_path / "file1.txt"
        tracker.start_file(file1, 1000)
        tracker.update_bytes(1000)
        tracker.finish_file()

        # Start second file (1000 bytes)
        file2 = tmp_path / "file2.txt"
        tracker.start_file(file2, 1000)
        tracker.update_bytes(500)

        # 1500 of 2000 bytes processed = 75%
        assert tracker.overall_progress == pytest.approx(0.75, rel=0.01)

    def test_callback(self, tmp_path: Path) -> None:
        """Test progress callback invocation."""
        tracker = ProgressTracker(total_files=1)
        callback_calls: list[tuple[Path, float, float]] = []

        def callback(path: Path, file_progress: float, overall_progress: float) -> None:
            callback_calls.append((path, file_progress, overall_progress))

        tracker.set_callback(callback)

        test_file = tmp_path / "test.txt"
        tracker.start_file(test_file, 1000)
        tracker.update_bytes(500)

        assert len(callback_calls) >= 2  # At least start and update
        last_call = callback_calls[-1]
        assert last_call[0] == test_file
        assert last_call[1] == pytest.approx(0.5, rel=0.01)

    def test_simple_callback(self, tmp_path: Path) -> None:
        """Test simple progress callback."""
        tracker = ProgressTracker(total_files=1)
        callback_calls: list[tuple[Path, float]] = []

        def simple_callback(path: Path, progress: float) -> None:
            callback_calls.append((path, progress))

        tracker.set_simple_callback(simple_callback)

        test_file = tmp_path / "test.txt"
        tracker.start_file(test_file, 1000)
        tracker.update_bytes(500)

        assert len(callback_calls) >= 2
        last_call = callback_calls[-1]
        assert last_call[0] == test_file
        assert last_call[1] == pytest.approx(0.5, rel=0.01)

    def test_clear_callbacks(self, tmp_path: Path) -> None:
        """Test clearing callbacks."""
        tracker = ProgressTracker(total_files=1)
        callback_calls: list[float] = []

        def callback(_path: Path, fp: float, _op: float) -> None:
            callback_calls.append(fp)

        tracker.set_callback(callback)
        tracker.clear_callbacks()

        test_file = tmp_path / "test.txt"
        tracker.start_file(test_file, 1000)
        tracker.update_bytes(500)

        assert len(callback_calls) == 0

    def test_callback_error_handling(self, tmp_path: Path) -> None:
        """Test callback errors are suppressed."""
        tracker = ProgressTracker(total_files=1)

        def failing_callback(_path: Path, _fp: float, _op: float) -> None:
            raise RuntimeError("Callback error")

        tracker.set_callback(failing_callback)

        test_file = tmp_path / "test.txt"
        # Should not raise
        tracker.start_file(test_file, 1000)
        tracker.update_bytes(500)

    def test_file_history(self, tmp_path: Path) -> None:
        """Test file history tracking."""
        tracker = ProgressTracker(total_files=2)

        file1 = tmp_path / "file1.txt"
        tracker.start_file(file1, 1000)
        tracker.finish_file()

        file2 = tmp_path / "file2.txt"
        tracker.start_file(file2, 500)
        tracker.finish_file()

        history = tracker.get_file_history()
        assert len(history) == 2
        assert history[0].path == file1
        assert history[1].path == file2

    def test_reset(self, tmp_path: Path) -> None:
        """Test resetting tracker."""
        tracker = ProgressTracker(total_files=2)

        file1 = tmp_path / "file1.txt"
        tracker.start_file(file1, 1000)
        tracker.finish_file()

        tracker.reset()

        assert tracker.files_completed == 0
        assert tracker.overall_progress == 0.0
        assert len(tracker.get_file_history()) == 0

    def test_get_summary(self, tmp_path: Path) -> None:
        """Test getting progress summary."""
        tracker = ProgressTracker(total_files=2)

        file1 = tmp_path / "file1.txt"
        tracker.start_file(file1, 1000)

        summary = tracker.get_summary()

        assert summary["total_files"] == 2
        assert summary["files_completed"] == 0
        assert summary["files_remaining"] == 2
        assert summary["current_file"] == str(file1)

    def test_auto_finish_on_new_file(self, tmp_path: Path) -> None:
        """Test automatic finish when starting new file."""
        tracker = ProgressTracker(total_files=2)

        file1 = tmp_path / "file1.txt"
        tracker.start_file(file1, 1000)

        # Start new file without finishing first
        file2 = tmp_path / "file2.txt"
        tracker.start_file(file2, 500)

        # First file should be auto-finished
        assert tracker.files_completed == 1
        assert tracker.current_file == file2


class TestCreateProgressTracker:
    """Tests for create_progress_tracker function."""

    def test_create_basic(self, tmp_path: Path) -> None:
        """Test basic tracker creation."""
        files = [tmp_path / "a.txt", tmp_path / "b.txt"]
        tracker = create_progress_tracker(files)

        assert tracker.total_files == 2

    def test_create_with_callback(self, tmp_path: Path) -> None:
        """Test tracker creation with callback."""
        files = [tmp_path / "a.txt"]
        calls: list[float] = []

        def callback(_path: Path, fp: float, _op: float) -> None:
            calls.append(fp)

        tracker = create_progress_tracker(files, callback)

        (tmp_path / "a.txt").write_text("test")
        tracker.start_file(files[0], 4)
        tracker.update_bytes(2)

        assert len(calls) >= 1

    def test_create_empty_list(self) -> None:
        """Test tracker creation with empty file list."""
        tracker = create_progress_tracker([])

        assert tracker.total_files == 0
        assert tracker.overall_progress == 1.0
