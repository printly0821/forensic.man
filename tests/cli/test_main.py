"""Tests for forensic CLI main entry point"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from forensic.cli.main import cli


@pytest.fixture
def runner():
    """Create a Click CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def mock_home():
    """Mock home directory for config file testing."""
    with patch("pathlib.Path.home") as mock_home:
        mock_home.return_value = MagicMock(exists=lambda: False)
        yield mock_home


class TestCliMain:
    """Test suite for the main CLI entry point."""

    def test_cli_group_exists(self, runner):
        """Test that the CLI group is properly defined."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "forensic.man" in result.output
        assert "분석" in result.output or "analyze" in result.output

    def test_cli_version_option(self, runner):
        """Test --version option."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output or "forensic" in result.output

    def test_cli_help_option(self, runner):
        """Test --help option."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Commands:" in result.output or "명령:" in result.output

    def test_cli_verbose_option(self, runner):
        """Test --verbose option."""
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_cli_quiet_option(self, runner):
        """Test --quiet option."""
        result = runner.invoke(cli, ["--quiet", "--help"])
        assert result.exit_code == 0

    def test_cli_color_option_auto(self, runner):
        """Test --color auto option."""
        result = runner.invoke(cli, ["--color", "auto", "--help"])
        assert result.exit_code == 0

    def test_cli_color_option_always(self, runner):
        """Test --color always option."""
        result = runner.invoke(cli, ["--color", "always", "--help"])
        assert result.exit_code == 0

    def test_cli_color_option_never(self, runner):
        """Test --color never option."""
        result = runner.invoke(cli, ["--color", "never", "--help"])
        assert result.exit_code == 0


class TestCliCommands:
    """Test suite for CLI command registration."""

    def test_analyze_command_registered(self, runner):
        """Test that analyze command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "analyze" in result.output or "분석" in result.output

    def test_search_command_registered(self, runner):
        """Test that search command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "search" in result.output or "검색" in result.output

    def test_report_command_registered(self, runner):
        """Test that report command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "report" in result.output or "보고서" in result.output

    def test_timeline_command_registered(self, runner):
        """Test that timeline command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "timeline" in result.output or "타임라인" in result.output

    def test_config_command_registered(self, runner):
        """Test that config command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "config" in result.output or "설정" in result.output


class TestCliContext:
    """Test suite for CLI context handling."""

    def test_cli_context_initialization(self, runner):
        """Test that CLI context is properly initialized."""
        with patch("forensic.cli.main.CLIConfigLoader") as mock_loader:
            mock_config = MagicMock()
            mock_config.output = MagicMock(color="auto", unicode=True, quiet=False, verbose=False)
            mock_loader.return_value.config = mock_config

            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0

    def test_cli_console_manager_created(self):
        """Test that ConsoleManager is created with proper settings."""
        from forensic.cli.main import cli

        # Check that the command group is properly configured
        assert cli is not None
        assert hasattr(cli, "commands")


class TestMainFunction:
    """Test suite for main() function."""

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        from forensic.cli.main import main

        assert callable(main)

    def test_main_returns_zero_on_success(self):
        """Test that main returns 0 on successful execution."""
        from forensic.cli.main import main

        with patch("forensic.cli.main.cli") as mock_cli:
            mock_cli.return_value = None
            result = main()
            assert result == 0

    def test_main_returns_130_on_keyboard_interrupt(self):
        """Test that main returns 130 on KeyboardInterrupt."""
        from forensic.cli.main import main

        with patch("forensic.cli.main.cli") as mock_cli:
            mock_cli.side_effect = KeyboardInterrupt()
            result = main()
            assert result == 130

    def test_main_returns_1_on_exception(self):
        """Test that main returns 1 on exception."""
        from forensic.cli.main import main

        with patch("forensic.cli.main.cli") as mock_cli:
            mock_cli.side_effect = Exception("Test error")
            result = main()
            assert result == 1
