"""Tests for forensic search command"""

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from forensic.cli.commands.search_cmd import search


@pytest.fixture
def runner():
    """Create a Click CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def mock_context():
    """Create a mock Click context with console_manager."""
    ctx = MagicMock()
    console_manager = MagicMock()
    ctx.obj = {"console_manager": console_manager, "console": MagicMock()}
    return ctx, console_manager


class TestSearchCommand:
    """Test suite for the search command."""

    def test_search_with_query(self, runner, mock_context):
        """Test search command with a basic query."""
        ctx, console_manager = mock_context

        result = runner.invoke(search, ["test query"], obj=ctx.obj, standalone_mode=False)
        assert "검색 중" in console_manager.info.call_args[0][0] or result.exit_code == 0

    def test_search_with_speaker_filter(self, runner, mock_context):
        """Test search command with speaker filter."""
        ctx, _ = mock_context

        result = runner.invoke(
            search, ["test query", "--speaker", "speaker1"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0

    def test_search_with_date_range(self, runner, mock_context):
        """Test search command with valid date range."""
        ctx, _ = mock_context

        result = runner.invoke(
            search,
            ["test query", "--date", "2024-01-01:2024-12-31"],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0

    def test_search_with_invalid_date_range(self, runner, mock_context):
        """Test search command with invalid date range."""
        ctx, console_manager = mock_context

        result = runner.invoke(
            search, ["test query", "--date", "invalid"], obj=ctx.obj, standalone_mode=False
        )
        assert "날짜 오류" in console_manager.error.call_args[0][0]

    def test_search_with_importance_filter(self, runner, mock_context):
        """Test search command with importance filter."""
        ctx, _ = mock_context

        result = runner.invoke(
            search,
            ["test query", "--importance", "HIGH", "--importance", "MEDIUM"],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0

    def test_search_with_regex_flag(self, runner, mock_context):
        """Test search command with regex flag."""
        ctx, _ = mock_context

        result = runner.invoke(
            search, ["test.*query", "--regex"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0

    def test_search_with_case_sensitive_flag(self, runner, mock_context):
        """Test search command with case-sensitive flag."""
        ctx, _ = mock_context

        result = runner.invoke(
            search, ["Test Query", "--case-sensitive"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0

    def test_search_with_limit(self, runner, mock_context):
        """Test search command with custom limit."""
        ctx, _ = mock_context

        result = runner.invoke(
            search, ["test query", "--limit", "50"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0

    def test_search_table_format(self, runner, mock_context):
        """Test search command with table output format."""
        ctx, _ = mock_context

        result = runner.invoke(
            search, ["test query", "--format", "table"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0

    def test_search_json_format(self, runner, mock_context):
        """Test search command with JSON output format."""
        ctx, _ = mock_context

        result = runner.invoke(
            search, ["test query", "--format", "json"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0

    def test_search_csv_format(self, runner, mock_context):
        """Test search command with CSV output format."""
        ctx, _ = mock_context

        result = runner.invoke(
            search, ["test query", "--format", "csv"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0


class TestSearchHelperFunctions:
    """Test suite for search command helper functions."""

    def test_display_table_with_results(self):
        """Test _display_table function with results."""
        from forensic.cli.commands.search_cmd import _display_table

        console = MagicMock()
        console_manager = MagicMock()

        results = [
            {"speaker": "speaker1", "date": "2024-01-01", "text": "Test result", "score": 0.9}
        ]

        _display_table(results, console, console_manager)
        assert console.print.called

    def test_display_table_without_results(self):
        """Test _display_table function without results."""
        from forensic.cli.commands.search_cmd import _display_table

        console = MagicMock()
        console_manager = MagicMock()

        _display_table([], console, console_manager)
        assert console_manager.warning.called

    def test_display_json(self):
        """Test _display_json function."""
        from forensic.cli.commands.search_cmd import _display_json

        console = MagicMock()
        results = [{"test": "data"}]

        _display_json(results, console)
        assert console.print_json.called

    def test_display_csv(self):
        """Test _display_csv function."""
        from forensic.cli.commands.search_cmd import _display_csv

        console = MagicMock()
        results = [{"speaker": "speaker1", "text": "test"}]

        _display_csv(results, console)
        assert console.print.called
