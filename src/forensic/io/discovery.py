"""
File discovery module for batch file processing.

Provides glob pattern-based file discovery with filtering,
sorting, and recursive directory traversal options.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Protocol


class SortOrder(Enum):
    """File sorting order enumeration."""

    NAME = "name"
    SIZE = "size"
    DATE = "date"
    NAME_DESC = "name_desc"
    SIZE_DESC = "size_desc"
    DATE_DESC = "date_desc"


class FileDiscoveryProtocol(Protocol):
    """File discovery interface protocol."""

    def find(self, directory: Path, filter: "FileFilter") -> list[Path]:
        """Find files matching filter criteria."""
        ...

    def find_by_pattern(self, directory: Path, pattern: str, recursive: bool = False) -> list[Path]:
        """Find files matching glob pattern."""
        ...


class DirectoryNotFoundError(Exception):
    """Raised when the specified directory does not exist."""

    pass


class InvalidFilterError(Exception):
    """Raised when filter criteria are invalid."""

    pass


@dataclass
class FileFilter:
    """
    File filter criteria for discovery.

    Attributes:
        pattern: Glob pattern for file matching (e.g., "*.txt").
        recursive: Whether to search subdirectories.
        min_size: Minimum file size in bytes (inclusive).
        max_size: Maximum file size in bytes (inclusive).
        after_date: Only files modified after this date.
        before_date: Only files modified before this date.
        extensions: List of allowed file extensions (e.g., [".txt", ".json"]).
    """

    pattern: str = "*.txt"
    recursive: bool = False
    min_size: int | None = None
    max_size: int | None = None
    after_date: datetime | None = None
    before_date: datetime | None = None
    extensions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate filter criteria."""
        if self.min_size is not None and self.min_size < 0:
            raise InvalidFilterError("min_size must be non-negative")
        if self.max_size is not None and self.max_size < 0:
            raise InvalidFilterError("max_size must be non-negative")
        if (
            self.min_size is not None
            and self.max_size is not None
            and self.min_size > self.max_size
        ):
            raise InvalidFilterError("min_size cannot be greater than max_size")
        if (
            self.after_date is not None
            and self.before_date is not None
            and self.after_date > self.before_date
        ):
            raise InvalidFilterError("after_date cannot be after before_date")

    def matches_size(self, size: int) -> bool:
        """
        Check if file size matches filter criteria.

        Args:
            size: File size in bytes.

        Returns:
            True if size matches criteria.
        """
        if self.min_size is not None and size < self.min_size:
            return False
        return not (self.max_size is not None and size > self.max_size)

    def matches_date(self, mtime: datetime) -> bool:
        """
        Check if modification date matches filter criteria.

        Args:
            mtime: File modification time.

        Returns:
            True if date matches criteria.
        """
        if self.after_date is not None and mtime < self.after_date:
            return False
        return not (self.before_date is not None and mtime > self.before_date)

    def matches_extension(self, path: Path) -> bool:
        """
        Check if file extension matches filter criteria.

        Args:
            path: File path.

        Returns:
            True if extension matches criteria.
        """
        if not self.extensions:
            return True
        return path.suffix.lower() in [ext.lower() for ext in self.extensions]


@dataclass
class FileInfo:
    """
    File information for sorting and filtering.

    Attributes:
        path: File path.
        size: File size in bytes.
        mtime: File modification time.
    """

    path: Path
    size: int
    mtime: datetime


class FileDiscovery:
    """
    File discovery with glob patterns and filtering.

    Provides methods for discovering files based on patterns,
    size, date, and other criteria with sorting options.

    Usage:
        discovery = FileDiscovery()
        files = discovery.find(
            Path("/data"),
            FileFilter(pattern="*.txt", min_size=1024)
        )
    """

    def __init__(self, follow_symlinks: bool = False) -> None:
        """
        Initialize file discovery.

        Args:
            follow_symlinks: Whether to follow symbolic links.
        """
        self._follow_symlinks = follow_symlinks

    def find(
        self,
        directory: Path,
        filter: FileFilter,
        sort_order: SortOrder | None = None,
    ) -> list[Path]:
        """
        Find files matching filter criteria.

        Discovers files using glob pattern and applies all
        filter criteria including size and date restrictions.

        Args:
            directory: Directory to search in.
            filter: Filter criteria to apply.
            sort_order: Optional sort order for results.

        Returns:
            List of matching file paths.

        Raises:
            DirectoryNotFoundError: If directory does not exist.
        """
        if not directory.exists():
            raise DirectoryNotFoundError(f"Directory not found: {directory}")
        if not directory.is_dir():
            raise DirectoryNotFoundError(f"Path is not a directory: {directory}")

        # Get files matching pattern
        pattern = f"**/{filter.pattern}" if filter.recursive else filter.pattern

        matching_files: list[FileInfo] = []

        for path in directory.glob(pattern):
            if not path.is_file():
                continue

            # Skip symlinks if not following them
            if path.is_symlink() and not self._follow_symlinks:
                continue

            try:
                stat = path.stat(follow_symlinks=self._follow_symlinks)
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime)

                # Apply filters
                if not filter.matches_size(size):
                    continue
                if not filter.matches_date(mtime):
                    continue
                if not filter.matches_extension(path):
                    continue

                matching_files.append(FileInfo(path=path, size=size, mtime=mtime))

            except OSError:
                # Skip files that can't be accessed
                continue

        # Sort results
        sorted_files = self._sort_files(matching_files, sort_order)

        return [f.path for f in sorted_files]

    def find_by_pattern(
        self,
        directory: Path,
        pattern: str,
        recursive: bool = False,
        sort_order: SortOrder | None = None,
    ) -> list[Path]:
        """
        Find files matching glob pattern.

        Simple convenience method for pattern-only discovery
        without additional filtering.

        Args:
            directory: Directory to search in.
            pattern: Glob pattern (e.g., "*.txt").
            recursive: Whether to search subdirectories.
            sort_order: Optional sort order for results.

        Returns:
            List of matching file paths.

        Raises:
            DirectoryNotFoundError: If directory does not exist.
        """
        filter = FileFilter(pattern=pattern, recursive=recursive)
        return self.find(directory, filter, sort_order)

    def find_transcript_files(
        self,
        directory: Path,
        recursive: bool = True,
        sort_order: SortOrder = SortOrder.NAME,
    ) -> list[Path]:
        """
        Find transcript files (common text formats).

        Convenience method for finding transcript files
        with common extensions (.txt, .srt, .vtt, .json).

        Args:
            directory: Directory to search in.
            recursive: Whether to search subdirectories.
            sort_order: Sort order for results.

        Returns:
            List of matching file paths.

        Raises:
            DirectoryNotFoundError: If directory does not exist.
        """
        filter = FileFilter(
            pattern="*",
            recursive=recursive,
            extensions=[".txt", ".srt", ".vtt", ".json"],
        )
        return self.find(directory, filter, sort_order)

    def _sort_files(
        self,
        files: list[FileInfo],
        sort_order: SortOrder | None,
    ) -> list[FileInfo]:
        """
        Sort files by specified order.

        Args:
            files: List of file info objects.
            sort_order: Sort order to apply.

        Returns:
            Sorted list of file info objects.
        """
        if sort_order is None:
            return files

        match sort_order:
            case SortOrder.NAME:
                return sorted(files, key=lambda f: f.path.name.lower())
            case SortOrder.NAME_DESC:
                return sorted(files, key=lambda f: f.path.name.lower(), reverse=True)
            case SortOrder.SIZE:
                return sorted(files, key=lambda f: f.size)
            case SortOrder.SIZE_DESC:
                return sorted(files, key=lambda f: f.size, reverse=True)
            case SortOrder.DATE:
                return sorted(files, key=lambda f: f.mtime)
            case SortOrder.DATE_DESC:
                return sorted(files, key=lambda f: f.mtime, reverse=True)
            case _:
                return files

    def get_total_size(self, files: list[Path]) -> int:
        """
        Calculate total size of files.

        Args:
            files: List of file paths.

        Returns:
            Total size in bytes.
        """
        total = 0
        for path in files:
            try:
                total += path.stat().st_size
            except OSError:
                continue
        return total

    def count_by_extension(self, files: list[Path]) -> dict[str, int]:
        """
        Count files by extension.

        Args:
            files: List of file paths.

        Returns:
            Dictionary of extension counts.
        """
        counts: dict[str, int] = {}
        for path in files:
            ext = path.suffix.lower() if path.suffix else "(no extension)"
            counts[ext] = counts.get(ext, 0) + 1
        return counts


def discover_files(
    directory: Path,
    pattern: str = "*.txt",
    recursive: bool = False,
) -> list[Path]:
    """
    Convenience function for file discovery.

    Args:
        directory: Directory to search in.
        pattern: Glob pattern.
        recursive: Whether to search subdirectories.

    Returns:
        List of matching file paths.
    """
    discovery = FileDiscovery()
    return discovery.find_by_pattern(directory, pattern, recursive)
