"""
File discovery module unit tests.

Tests for FileDiscovery, FileFilter, and related functions.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from forensic.io.discovery import (
    DirectoryNotFoundError,
    FileDiscovery,
    FileFilter,
    InvalidFilterError,
    SortOrder,
    discover_files,
)


class TestFileFilter:
    """FileFilter class tests."""

    def test_default_filter(self) -> None:
        """Test default filter values."""
        filter = FileFilter()

        assert filter.pattern == "*.txt"
        assert filter.recursive is False
        assert filter.min_size is None
        assert filter.max_size is None
        assert filter.after_date is None
        assert filter.before_date is None
        assert filter.extensions == []

    def test_custom_filter(self) -> None:
        """Test custom filter values."""
        now = datetime.now()
        filter = FileFilter(
            pattern="*.json",
            recursive=True,
            min_size=100,
            max_size=10000,
            after_date=now - timedelta(days=7),
            before_date=now,
            extensions=[".json", ".txt"],
        )

        assert filter.pattern == "*.json"
        assert filter.recursive is True
        assert filter.min_size == 100
        assert filter.max_size == 10000
        assert filter.extensions == [".json", ".txt"]

    def test_invalid_min_size(self) -> None:
        """Test negative min_size raises error."""
        with pytest.raises(InvalidFilterError):
            FileFilter(min_size=-1)

    def test_invalid_max_size(self) -> None:
        """Test negative max_size raises error."""
        with pytest.raises(InvalidFilterError):
            FileFilter(max_size=-1)

    def test_min_greater_than_max_size(self) -> None:
        """Test min_size greater than max_size raises error."""
        with pytest.raises(InvalidFilterError):
            FileFilter(min_size=1000, max_size=100)

    def test_invalid_date_range(self) -> None:
        """Test after_date after before_date raises error."""
        now = datetime.now()
        with pytest.raises(InvalidFilterError):
            FileFilter(
                after_date=now,
                before_date=now - timedelta(days=1),
            )

    def test_matches_size_no_limits(self) -> None:
        """Test size matching without limits."""
        filter = FileFilter()

        assert filter.matches_size(0) is True
        assert filter.matches_size(1000) is True
        assert filter.matches_size(1000000) is True

    def test_matches_size_with_min(self) -> None:
        """Test size matching with minimum."""
        filter = FileFilter(min_size=100)

        assert filter.matches_size(50) is False
        assert filter.matches_size(100) is True
        assert filter.matches_size(200) is True

    def test_matches_size_with_max(self) -> None:
        """Test size matching with maximum."""
        filter = FileFilter(max_size=1000)

        assert filter.matches_size(500) is True
        assert filter.matches_size(1000) is True
        assert filter.matches_size(1001) is False

    def test_matches_size_with_range(self) -> None:
        """Test size matching with min and max."""
        filter = FileFilter(min_size=100, max_size=1000)

        assert filter.matches_size(50) is False
        assert filter.matches_size(100) is True
        assert filter.matches_size(500) is True
        assert filter.matches_size(1000) is True
        assert filter.matches_size(1001) is False

    def test_matches_date_no_limits(self) -> None:
        """Test date matching without limits."""
        filter = FileFilter()
        now = datetime.now()

        assert filter.matches_date(now) is True
        assert filter.matches_date(now - timedelta(days=365)) is True

    def test_matches_date_with_after(self) -> None:
        """Test date matching with after_date."""
        now = datetime.now()
        filter = FileFilter(after_date=now - timedelta(days=7))

        assert filter.matches_date(now) is True
        assert filter.matches_date(now - timedelta(days=5)) is True
        assert filter.matches_date(now - timedelta(days=10)) is False

    def test_matches_date_with_before(self) -> None:
        """Test date matching with before_date."""
        now = datetime.now()
        filter = FileFilter(before_date=now)

        assert filter.matches_date(now - timedelta(days=1)) is True
        assert filter.matches_date(now + timedelta(days=1)) is False

    def test_matches_extension_no_filter(self) -> None:
        """Test extension matching without filter."""
        filter = FileFilter()

        assert filter.matches_extension(Path("file.txt")) is True
        assert filter.matches_extension(Path("file.json")) is True
        assert filter.matches_extension(Path("file")) is True

    def test_matches_extension_with_filter(self) -> None:
        """Test extension matching with filter."""
        filter = FileFilter(extensions=[".txt", ".json"])

        assert filter.matches_extension(Path("file.txt")) is True
        assert filter.matches_extension(Path("file.json")) is True
        assert filter.matches_extension(Path("file.xml")) is False

    def test_matches_extension_case_insensitive(self) -> None:
        """Test extension matching is case insensitive."""
        filter = FileFilter(extensions=[".TXT"])

        assert filter.matches_extension(Path("file.txt")) is True
        assert filter.matches_extension(Path("file.TXT")) is True


class TestFileDiscovery:
    """FileDiscovery class tests."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with test files."""
        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2" * 100)
        (tmp_path / "file3.json").write_text('{"key": "value"}')

        # Create subdirectory with files
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file4.txt").write_text("subcontent")
        (subdir / "file5.txt").write_text("subcontent2")

        return tmp_path

    @pytest.fixture
    def discovery(self) -> FileDiscovery:
        """Create a FileDiscovery instance."""
        return FileDiscovery()

    def test_init(self) -> None:
        """Test FileDiscovery initialization."""
        discovery = FileDiscovery()
        assert discovery is not None

    def test_init_follow_symlinks(self) -> None:
        """Test FileDiscovery with follow_symlinks option."""
        discovery = FileDiscovery(follow_symlinks=True)
        assert discovery is not None

    def test_find_by_pattern_basic(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test basic pattern matching."""
        files = discovery.find_by_pattern(temp_dir, "*.txt")

        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    def test_find_by_pattern_recursive(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test recursive pattern matching."""
        files = discovery.find_by_pattern(temp_dir, "*.txt", recursive=True)

        assert len(files) == 4  # 2 in root + 2 in subdir
        assert all(f.suffix == ".txt" for f in files)

    def test_find_by_pattern_nonexistent_dir(self, discovery: FileDiscovery) -> None:
        """Test finding in non-existent directory raises error."""
        with pytest.raises(DirectoryNotFoundError):
            discovery.find_by_pattern(Path("/nonexistent"), "*.txt")

    def test_find_by_pattern_file_not_dir(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test finding in file path raises error."""
        file_path = temp_dir / "file1.txt"
        with pytest.raises(DirectoryNotFoundError):
            discovery.find_by_pattern(file_path, "*.txt")

    def test_find_with_filter(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test finding with FileFilter."""
        filter = FileFilter(pattern="*.txt", min_size=100)
        files = discovery.find(temp_dir, filter)

        # Only file2.txt should match (larger than 100 bytes)
        assert len(files) == 1
        assert files[0].name == "file2.txt"

    def test_find_with_extension_filter(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test finding with extension filter."""
        filter = FileFilter(pattern="*", extensions=[".json"])
        files = discovery.find(temp_dir, filter)

        assert len(files) == 1
        assert files[0].suffix == ".json"

    def test_find_sorted_by_name(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test finding with name sorting."""
        files = discovery.find_by_pattern(temp_dir, "*.txt", sort_order=SortOrder.NAME)

        assert len(files) == 2
        assert files[0].name == "file1.txt"
        assert files[1].name == "file2.txt"

    def test_find_sorted_by_name_desc(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test finding with descending name sorting."""
        files = discovery.find_by_pattern(temp_dir, "*.txt", sort_order=SortOrder.NAME_DESC)

        assert len(files) == 2
        assert files[0].name == "file2.txt"
        assert files[1].name == "file1.txt"

    def test_find_sorted_by_size(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test finding with size sorting."""
        files = discovery.find_by_pattern(temp_dir, "*.txt", sort_order=SortOrder.SIZE)

        assert len(files) == 2
        # file1.txt is smaller
        assert files[0].name == "file1.txt"
        assert files[1].name == "file2.txt"

    def test_find_transcript_files(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test finding transcript files."""
        files = discovery.find_transcript_files(temp_dir, recursive=False)

        # Should find .txt and .json files
        extensions = {f.suffix for f in files}
        assert ".txt" in extensions
        assert ".json" in extensions

    def test_get_total_size(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test calculating total file size."""
        files = list(temp_dir.glob("*.txt"))
        total = discovery.get_total_size(files)

        expected = sum(f.stat().st_size for f in files)
        assert total == expected

    def test_count_by_extension(self, discovery: FileDiscovery, temp_dir: Path) -> None:
        """Test counting files by extension."""
        files = list(temp_dir.glob("*.*"))
        counts = discovery.count_by_extension(files)

        assert counts[".txt"] == 2
        assert counts[".json"] == 1


class TestDiscoverFilesFunction:
    """Tests for discover_files convenience function."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with test files."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        return tmp_path

    def test_discover_files_basic(self, temp_dir: Path) -> None:
        """Test basic file discovery."""
        files = discover_files(temp_dir, "*.txt")

        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    def test_discover_files_no_matches(self, temp_dir: Path) -> None:
        """Test discovery with no matches."""
        files = discover_files(temp_dir, "*.json")

        assert len(files) == 0


class TestSortOrder:
    """SortOrder enum tests."""

    def test_sort_order_values(self) -> None:
        """Test SortOrder enum values."""
        assert SortOrder.NAME.value == "name"
        assert SortOrder.SIZE.value == "size"
        assert SortOrder.DATE.value == "date"
        assert SortOrder.NAME_DESC.value == "name_desc"
        assert SortOrder.SIZE_DESC.value == "size_desc"
        assert SortOrder.DATE_DESC.value == "date_desc"
