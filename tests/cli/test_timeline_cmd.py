"""Tests for forensic timeline command"""

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from forensic.cli.commands.timeline_cmd import timeline


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


class TestTimelineCommand:
    """Test suite for the timeline command."""

    def test_timeline_basic(self, runner, mock_context):
        """Test basic timeline command."""
        ctx, console_manager = mock_context

        result = runner.invoke(timeline, [], obj=ctx.obj, standalone_mode=False)
        assert "타임라인 생성 중" in console_manager.info.call_args[0][0]
        assert result.exit_code == 0

    def test_timeline_with_date_range(self, runner, mock_context):
        """Test timeline command with date range."""
        ctx, _ = mock_context

        result = runner.invoke(
            timeline,
            ["--start", "2024-01-01", "--end", "2024-12-31"],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0

    def test_timeline_with_speaker_filter(self, runner, mock_context):
        """Test timeline command with speaker filter."""
        ctx, _ = mock_context

        result = runner.invoke(
            timeline, ["--speaker", "speaker1"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0

    def test_timeline_with_patterns(self, runner, mock_context):
        """Test timeline command with pattern filters."""
        ctx, _ = mock_context

        result = runner.invoke(
            timeline,
            ["--pattern", "GASLIGHTING", "--pattern", "COERCION"],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0

    def test_timeline_text_format(self, runner, mock_context):
        """Test timeline command with text output format."""
        ctx, _ = mock_context

        result = runner.invoke(timeline, ["--format", "text"], obj=ctx.obj, standalone_mode=False)
        assert result.exit_code == 0

    def test_timeline_json_format(self, runner, mock_context):
        """Test timeline command with JSON output format."""
        ctx, _ = mock_context

        result = runner.invoke(timeline, ["--format", "json"], obj=ctx.obj, standalone_mode=False)
        assert result.exit_code == 0

    def test_timeline_html_format(self, runner, mock_context):
        """Test timeline command with HTML output format."""
        ctx, _ = mock_context

        result = runner.invoke(timeline, ["--format", "html"], obj=ctx.obj, standalone_mode=False)
        assert result.exit_code == 0

    def test_timeline_day_resolution(self, runner, mock_context):
        """Test timeline command with day resolution."""
        ctx, _ = mock_context

        result = runner.invoke(
            timeline, ["--resolution", "day"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0

    def test_timeline_week_resolution(self, runner, mock_context):
        """Test timeline command with week resolution."""
        ctx, _ = mock_context

        result = runner.invoke(
            timeline, ["--resolution", "week"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0

    def test_timeline_month_resolution(self, runner, mock_context):
        """Test timeline command with month resolution."""
        ctx, _ = mock_context

        result = runner.invoke(
            timeline, ["--resolution", "month"], obj=ctx.obj, standalone_mode=False
        )
        assert result.exit_code == 0


class TestTimelineFunctions:
    """Test suite for timeline helper functions."""

    def test_generate_timeline(self):
        """Test _generate_timeline function."""
        from forensic.cli.commands.timeline_cmd import _generate_timeline

        events = _generate_timeline()
        assert isinstance(events, list)
        assert len(events) > 0
        assert "date" in events[0]
        assert "time" in events[0]
        assert "speaker" in events[0]

    def test_display_text_timeline(self):
        """Test _display_text_timeline function."""
        from forensic.cli.commands.timeline_cmd import _display_text_timeline

        console = MagicMock()
        console_manager = MagicMock()

        events = [
            {
                "date": "2025-07-15",
                "time": "14:23",
                "speaker": "Test",
                "pattern": "TEST",
                "text": "Sample text",
            }
        ]

        _display_text_timeline(events, console, console_manager)
        assert console.print.called

    def test_display_text_timeline_no_events(self):
        """Test _display_text_timeline with no events."""
        from forensic.cli.commands.timeline_cmd import _display_text_timeline

        console = MagicMock()
        console_manager = MagicMock()

        _display_text_timeline([], console, console_manager)
        assert console_manager.warning.called

    def test_display_json_timeline(self):
        """Test _display_json_timeline function."""
        from forensic.cli.commands.timeline_cmd import _display_json_timeline

        console = MagicMock()
        events = [{"test": "data"}]

        _display_json_timeline(events, console)
        assert console.print_json.called

    def test_generate_html_timeline(self):
        """Test _generate_html_timeline function."""
        from forensic.cli.commands.timeline_cmd import _generate_html_timeline

        events = [{"date": "2025-07-15"}]
        html = _generate_html_timeline(events)

        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "타임라인" in html
