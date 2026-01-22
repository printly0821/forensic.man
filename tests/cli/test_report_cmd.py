"""Tests for forensic report command"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from forensic.cli.commands.report_cmd import report


@pytest.fixture
def runner():
    """Create a Click CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_context():
    """Create a mock Click context with console_manager."""
    ctx = MagicMock()
    console_manager = MagicMock()
    ctx.obj = {
        "console_manager": console_manager,
        "console": MagicMock(),
        "config": MagicMock(),
    }
    return ctx, console_manager


class TestReportCommand:
    """Test suite for the report command."""

    def test_report_legal_type(self, runner, temp_dir, mock_context):
        """Test report command with legal type."""
        ctx, console_manager = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "legal", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code in (0, None)
        # Verify info was called with generation message
        if console_manager.info.called:
            call_args = str(console_manager.info.call_args)
            assert "legal" in call_args.lower() or "보고서" in call_args

    def test_report_timeline_type(self, runner, temp_dir, mock_context):
        """Test report command with timeline type."""
        ctx, _ = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "timeline", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0

    def test_report_summary_type(self, runner, temp_dir, mock_context):
        """Test report command with summary type."""
        ctx, _ = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "summary", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0

    def test_report_evidence_type(self, runner, temp_dir, mock_context):
        """Test report command with evidence type."""
        ctx, _ = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "evidence", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0

    def test_report_statistical_type(self, runner, temp_dir, mock_context):
        """Test report command with statistical type."""
        ctx, _ = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "statistical", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0

    def test_report_markdown_format(self, runner, temp_dir, mock_context):
        """Test report command with markdown format."""
        ctx, _ = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "legal", "--format", "markdown", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0
        assert (output_path / "report.markdown").exists()

    def test_report_json_format(self, runner, temp_dir, mock_context):
        """Test report command with JSON format."""
        ctx, _ = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "legal", "--format", "json", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0
        assert (output_path / "report.json").exists()

    def test_report_html_format(self, runner, temp_dir, mock_context):
        """Test report command with HTML format."""
        ctx, _ = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "legal", "--format", "html", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0
        assert (output_path / "report.html").exists()

    def test_report_pdf_format(self, runner, temp_dir, mock_context):
        """Test report command with PDF format."""
        ctx, _ = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "legal", "--format", "pdf", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0

    def test_report_with_min_importance(self, runner, temp_dir, mock_context):
        """Test report command with min-importance filter."""
        ctx, _ = mock_context
        output_path = temp_dir / "report_output"

        result = runner.invoke(
            report,
            ["--type", "legal", "--min-importance", "HIGH", "--output", str(output_path)],
            obj=ctx.obj,
            standalone_mode=False,
        )
        assert result.exit_code == 0


class TestReportGeneration:
    """Test suite for report generation functions."""

    def test_generate_report_creates_file(self, temp_dir):
        """Test _generate_report creates output file."""
        from forensic.cli.commands.report_cmd import _generate_report

        console_manager = MagicMock()
        output_path = temp_dir / "output"
        output_path.mkdir(parents=True, exist_ok=True)

        _generate_report("legal", output_path, "markdown", console_manager)

        assert (output_path / "report.markdown").exists()
        assert console_manager.success.called

    def test_generate_report_content(self, temp_dir):
        """Test _generate_report creates expected content."""
        from forensic.cli.commands.report_cmd import _generate_report

        console_manager = MagicMock()
        output_path = temp_dir / "output"
        output_path.mkdir(parents=True, exist_ok=True)

        _generate_report("summary", output_path, "markdown", console_manager)

        report_file = output_path / "report.markdown"
        with open(report_file, encoding="utf-8") as f:
            content = f.read()
        assert "Summary 보고서" in content
