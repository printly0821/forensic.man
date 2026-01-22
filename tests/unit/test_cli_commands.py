"""
Tests for CLI commands
"""

from click.testing import CliRunner

from forensic.cli.main import cli


class TestCLIMain:
    """Tests for the main CLI group"""

    def test_cli_group_exists(self) -> None:
        """Test that the CLI group can be invoked"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_cli_version_option(self) -> None:
        """Test the --version option"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_cli_has_all_commands(self) -> None:
        """Test that all subcommands are registered"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert "analyze" in result.output
        assert "search" in result.output
        assert "report" in result.output
        assert "timeline" in result.output
        assert "config" in result.output


class TestAnalyzeCommand:
    """Tests for the analyze command"""

    def test_analyze_requires_input(self) -> None:
        """Test that analyze requires input option"""
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--output", "/tmp/output"])
        assert result.exit_code != 0

    def test_analyze_help(self) -> None:
        """Test analyze help text"""
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0


class TestSearchCommand:
    """Tests for the search command"""

    def test_search_requires_query(self) -> None:
        """Test that search requires query argument"""
        runner = CliRunner()
        result = runner.invoke(cli, ["search"])
        assert result.exit_code != 0

    def test_search_help(self) -> None:
        """Test search help text"""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0

    def test_search_accepts_query(self) -> None:
        """Test that search accepts a query"""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test"])
        assert result.exit_code == 0


class TestReportCommand:
    """Tests for the report command"""

    def test_report_requires_type(self) -> None:
        """Test that report requires type option"""
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "--output", "/tmp/report.md"])
        assert result.exit_code != 0

    def test_report_help(self) -> None:
        """Test report help text"""
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "--help"])
        assert result.exit_code == 0


class TestTimelineCommand:
    """Tests for the timeline command"""

    def test_timeline_help(self) -> None:
        """Test timeline help text"""
        runner = CliRunner()
        result = runner.invoke(cli, ["timeline", "--help"])
        assert result.exit_code == 0


class TestConfigCommand:
    """Tests for the config command"""

    def test_config_help(self) -> None:
        """Test config help text"""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0

    def test_config_show(self) -> None:
        """Test config --show displays configuration"""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--show"])
        assert result.exit_code == 0

    def test_config_system_info(self) -> None:
        """Test config --system-info displays system information"""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--system-info"])
        assert result.exit_code == 0
