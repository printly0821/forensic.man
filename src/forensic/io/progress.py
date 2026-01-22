"""
Progress tracker module for batch file processing.

Provides progress tracking at file and batch levels with
callback management for real-time progress updates.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class ProgressTrackerProtocol(Protocol):
    """Progress tracker interface protocol."""

    def start_file(self, path: Path, total_bytes: int) -> None:
        """Start tracking a new file."""
        ...

    def update_bytes(self, bytes_processed: int) -> None:
        """Update bytes processed for current file."""
        ...

    def finish_file(self) -> None:
        """Mark current file as finished."""
        ...

    @property
    def current_file_progress(self) -> float:
        """Return current file progress (0.0 ~ 1.0)."""
        ...

    @property
    def overall_progress(self) -> float:
        """Return overall batch progress (0.0 ~ 1.0)."""
        ...


class NoActiveFileError(Exception):
    """Raised when attempting to update progress without an active file."""

    pass


class ProgressCallbackError(Exception):
    """Raised when a progress callback fails."""

    pass


# Callback type: (file_path, file_progress, overall_progress) -> None
ProgressCallback = Callable[[Path, float, float], None]

# Simple callback type: (file_path, progress) -> None
SimpleProgressCallback = Callable[[Path, float], None]


@dataclass
class FileProgress:
    """
    Progress information for a single file.

    Attributes:
        path: File path.
        total_bytes: Total file size in bytes.
        bytes_processed: Bytes processed so far.
        is_complete: Whether file processing is complete.
    """

    path: Path
    total_bytes: int
    bytes_processed: int = 0
    is_complete: bool = False

    @property
    def progress(self) -> float:
        """
        Return progress as a ratio (0.0 ~ 1.0).

        Returns:
            Progress ratio.
        """
        if self.total_bytes == 0:
            return 1.0 if self.is_complete else 0.0
        return min(1.0, self.bytes_processed / self.total_bytes)

    @property
    def progress_percent(self) -> float:
        """
        Return progress as percentage (0.0 ~ 100.0).

        Returns:
            Progress percentage.
        """
        return self.progress * 100.0


@dataclass
class BatchProgress:
    """
    Progress information for a batch of files.

    Attributes:
        total_files: Total number of files in batch.
        files_completed: Number of files completed.
        total_bytes: Total bytes across all files.
        bytes_processed: Total bytes processed across all files.
    """

    total_files: int
    files_completed: int = 0
    total_bytes: int = 0
    bytes_processed: int = 0

    @property
    def progress(self) -> float:
        """
        Return overall progress as a ratio (0.0 ~ 1.0).

        Returns:
            Progress ratio.
        """
        if self.total_files == 0:
            return 1.0
        if self.total_bytes == 0:
            # Fall back to file count-based progress
            return self.files_completed / self.total_files
        return min(1.0, self.bytes_processed / self.total_bytes)

    @property
    def progress_percent(self) -> float:
        """
        Return progress as percentage (0.0 ~ 100.0).

        Returns:
            Progress percentage.
        """
        return self.progress * 100.0

    @property
    def files_remaining(self) -> int:
        """Return number of files remaining."""
        return self.total_files - self.files_completed


@dataclass
class ProgressTracker:
    """
    Progress tracker for batch file processing.

    Tracks progress at both file and batch levels with support
    for callbacks on progress updates.

    Usage:
        tracker = ProgressTracker(total_files=10)
        tracker.set_callback(lambda p, fp, op: print(f"{p}: {fp:.1%}"))

        for file in files:
            tracker.start_file(file, file.stat().st_size)
            for chunk in read_chunks(file):
                process(chunk)
                tracker.update_bytes(len(chunk))
            tracker.finish_file()

    Attributes:
        total_files: Total number of files to process.
    """

    total_files: int
    _current_file: FileProgress | None = field(default=None, repr=False)
    _batch: BatchProgress = field(default_factory=lambda: BatchProgress(0), repr=False)
    _callbacks: list[ProgressCallback] = field(default_factory=list, repr=False)
    _file_history: list[FileProgress] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Initialize batch progress."""
        if self.total_files < 0:
            raise ValueError("total_files must be non-negative")
        self._batch = BatchProgress(total_files=self.total_files)

    def start_file(self, path: Path, total_bytes: int) -> None:
        """
        Start tracking a new file.

        Initializes progress tracking for a new file and
        triggers callbacks with initial progress (0.0).

        Args:
            path: File path.
            total_bytes: Total file size in bytes.
        """
        # Finish previous file if not already finished
        if self._current_file is not None and not self._current_file.is_complete:
            self.finish_file()

        self._current_file = FileProgress(path=path, total_bytes=total_bytes)
        self._batch.total_bytes += total_bytes

        # Trigger callbacks with initial progress
        self._notify_callbacks()

    def update_bytes(self, bytes_processed: int) -> None:
        """
        Update bytes processed for current file.

        Increments the bytes processed counter and triggers
        callbacks with updated progress.

        Args:
            bytes_processed: Number of bytes just processed.

        Raises:
            NoActiveFileError: If no file is currently being tracked.
        """
        if self._current_file is None:
            raise NoActiveFileError("No active file. Call start_file() first.")

        self._current_file.bytes_processed += bytes_processed
        self._batch.bytes_processed += bytes_processed

        # Trigger callbacks
        self._notify_callbacks()

    def update_progress(self, progress: float) -> None:
        """
        Update current file progress directly.

        Alternative to update_bytes() when exact byte counts
        are not available.

        Args:
            progress: Progress ratio (0.0 ~ 1.0).

        Raises:
            NoActiveFileError: If no file is currently being tracked.
            ValueError: If progress is out of range.
        """
        if self._current_file is None:
            raise NoActiveFileError("No active file. Call start_file() first.")
        if not 0.0 <= progress <= 1.0:
            raise ValueError("Progress must be between 0.0 and 1.0")

        # Calculate byte equivalent
        new_bytes = int(progress * self._current_file.total_bytes)
        delta = new_bytes - self._current_file.bytes_processed

        if delta > 0:
            self._current_file.bytes_processed = new_bytes
            self._batch.bytes_processed += delta
            self._notify_callbacks()

    def finish_file(self) -> None:
        """
        Mark current file as finished.

        Completes tracking for the current file and updates
        batch progress counters.

        Raises:
            NoActiveFileError: If no file is currently being tracked.
        """
        if self._current_file is None:
            raise NoActiveFileError("No active file. Call start_file() first.")

        # Ensure full progress is recorded
        remaining = self._current_file.total_bytes - self._current_file.bytes_processed
        if remaining > 0:
            self._current_file.bytes_processed = self._current_file.total_bytes
            self._batch.bytes_processed += remaining

        self._current_file.is_complete = True
        self._batch.files_completed += 1

        # Save to history
        self._file_history.append(self._current_file)

        # Trigger final callbacks for this file
        self._notify_callbacks()

        # Clear current file
        self._current_file = None

    @property
    def current_file_progress(self) -> float:
        """
        Return current file progress as a ratio.

        Returns:
            Progress ratio (0.0 ~ 1.0), or 0.0 if no active file.
        """
        if self._current_file is None:
            return 0.0
        return self._current_file.progress

    @property
    def overall_progress(self) -> float:
        """
        Return overall batch progress as a ratio.

        Returns:
            Progress ratio (0.0 ~ 1.0).
        """
        return self._batch.progress

    @property
    def current_file(self) -> Path | None:
        """Return currently tracked file path."""
        if self._current_file is None:
            return None
        return self._current_file.path

    @property
    def files_completed(self) -> int:
        """Return number of completed files."""
        return self._batch.files_completed

    @property
    def files_remaining(self) -> int:
        """Return number of remaining files."""
        return self._batch.files_remaining

    @property
    def batch_progress(self) -> BatchProgress:
        """Return batch progress information."""
        return self._batch

    def set_callback(self, callback: ProgressCallback) -> None:
        """
        Set progress callback.

        The callback is invoked on every progress update with:
        - file_path: Current file path
        - file_progress: Current file progress (0.0 ~ 1.0)
        - overall_progress: Overall batch progress (0.0 ~ 1.0)

        Args:
            callback: Callback function.
        """
        self._callbacks.append(callback)

    def set_simple_callback(self, callback: SimpleProgressCallback) -> None:
        """
        Set simple progress callback.

        Wraps a simple callback that only receives file path
        and file progress into a full callback.

        Args:
            callback: Simple callback function.
        """

        def wrapper(path: Path, file_progress: float, _overall_progress: float) -> None:
            callback(path, file_progress)

        self._callbacks.append(wrapper)

    def clear_callbacks(self) -> None:
        """Remove all progress callbacks."""
        self._callbacks.clear()

    def _notify_callbacks(self) -> None:
        """
        Notify all registered callbacks.

        Invokes each callback with current progress information.
        Callback errors are caught and logged but do not stop
        other callbacks from being invoked.
        """
        if not self._callbacks or self._current_file is None:
            return

        path = self._current_file.path
        file_progress = self._current_file.progress
        overall_progress = self._batch.progress

        for callback in self._callbacks:
            # Suppress callback errors to prevent one failing callback
            # from stopping other callbacks or the main processing
            with __import__("contextlib").suppress(Exception):
                callback(path, file_progress, overall_progress)

    def get_file_history(self) -> list[FileProgress]:
        """
        Return history of completed files.

        Returns:
            List of completed file progress objects.
        """
        return self._file_history.copy()

    def reset(self) -> None:
        """
        Reset tracker state.

        Clears all progress information and history.
        """
        self._current_file = None
        self._batch = BatchProgress(total_files=self.total_files)
        self._file_history.clear()

    def get_summary(self) -> dict[str, object]:
        """
        Get progress summary as dictionary.

        Returns:
            Dictionary with progress summary.
        """
        return {
            "total_files": self.total_files,
            "files_completed": self.files_completed,
            "files_remaining": self.files_remaining,
            "overall_progress": self.overall_progress,
            "current_file": str(self.current_file) if self.current_file else None,
            "current_file_progress": self.current_file_progress,
        }


def create_progress_tracker(
    files: list[Path],
    callback: ProgressCallback | None = None,
) -> ProgressTracker:
    """
    Create a progress tracker for a list of files.

    Convenience function that creates a tracker with the
    correct total file count and optionally sets a callback.

    Args:
        files: List of files to track.
        callback: Optional progress callback.

    Returns:
        Configured ProgressTracker instance.
    """
    tracker = ProgressTracker(total_files=len(files))
    if callback is not None:
        tracker.set_callback(callback)
    return tracker
