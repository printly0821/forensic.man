"""Tests for forensic config command"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from forensic.cli.commands.config_cmd import config


@pytest.fixture
def runner():
    """Create a Click CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def mock_context():
    """Create a mock Click context with console_manager and config_loader."""
    ctx = MagicMock()
    console_manager = MagicMock()
    config_loader = MagicMock()
    ctx.obj = {
        "console_manager": console_manager,
        "console": MagicMock(),
        "config_loader": config_loader,
        "config": MagicMock(
            analysis=MagicMock(parallel_workers=4, enable_gpu=False),
            search=MagicMock(max_results=1000),
            report=MagicMock(default_format="markdown"),
            cache=MagicMock(enabled=True),
            output=MagicMock(color="auto"),
        ),
    }
    return ctx, console_manager, config_loader


class TestConfigCommand:
    """Test suite for the config command."""

    def test_config_show(self, runner, mock_context):
        """Test config --show command."""
        ctx, console_manager, _ = mock_context

        result = runner.invoke(config, ["--show"], obj=ctx.obj, standalone_mode=False)
        assert result.exit_code == 0

    def test_config_system_info(self, runner, mock_context):
        """Test config --system-info command."""
        ctx, _, _ = mock_context

        with patch("forensic.cli.commands.config_cmd.DGXSparkDetector") as mock_detector:
            mock_dgx = MagicMock()
            mock_dgx.is_dgx_spark.return_value = False
            mock_dgx.detect.return_value = {}
            mock_detector.return_value = mock_dgx

            result = runner.invoke(config, ["--system-info"], obj=ctx.obj, standalone_mode=False)
            assert result.exit_code == 0

    def test_config_get_existing_key(self, runner, mock_context):
        """Test config --get with existing key."""
        ctx, console_manager, config_loader = mock_context
        config_loader.config.get.return_value = "test_value"

        runner.invoke(config, ["--get", "test.key"], obj=ctx.obj, standalone_mode=False)
        assert "test.key: test_value" in console_manager.info.call_args[0][0]

    def test_config_get_nonexistent_key(self, runner, mock_context):
        """Test config --get with non-existent key."""
        ctx, console_manager, config_loader = mock_context
        config_loader.config.get.return_value = None

        runner.invoke(config, ["--get", "nonexistent.key"], obj=ctx.obj, standalone_mode=False)
        assert "찾을 수 없습니다" in console_manager.warning.call_args[0][0]


class TestConfigSystemInfo:
    """Test suite for system info display function."""

    def test_show_system_info_with_dgx(self):
        """Test _show_system_info with DGX detected."""
        from forensic.cli.commands.config_cmd import _show_system_info

        console = MagicMock()
        console_manager = MagicMock()

        with patch("forensic.cli.commands.config_cmd.DGXSparkDetector") as mock_detector:
            mock_dgx = MagicMock()
            mock_dgx.is_dgx_spark.return_value = True
            mock_dgx.detect.return_value = {"gpu_count": 8}
            mock_detector.return_value = mock_dgx

            _show_system_info(console, console_manager)
            assert console.print.called

    def test_show_system_info_without_dgx(self):
        """Test _show_system_info without DGX."""
        from forensic.cli.commands.config_cmd import _show_system_info

        console = MagicMock()
        console_manager = MagicMock()

        with patch("forensic.cli.commands.config_cmd.DGXSparkDetector") as mock_detector:
            mock_dgx = MagicMock()
            mock_dgx.is_dgx_spark.return_value = False
            mock_detector.return_value = mock_dgx

            _show_system_info(console, console_manager)
            assert console.print.called


class TestConfigValueFunctions:
    """Test suite for config value functions."""

    def test_get_config_value_existing(self):
        """Test _get_config_value with existing key."""
        from forensic.cli.commands.config_cmd import _get_config_value

        config_loader = MagicMock()
        config_loader.config.get.return_value = "value123"
        console_manager = MagicMock()

        _get_config_value("test.key", config_loader, console_manager)
        assert console_manager.info.called

    def test_get_config_value_missing(self):
        """Test _get_config_value with missing key."""
        from forensic.cli.commands.config_cmd import _get_config_value

        config_loader = MagicMock()
        config_loader.config.get.return_value = None
        console_manager = MagicMock()

        _get_config_value("missing.key", config_loader, console_manager)
        assert console_manager.warning.called

    def test_show_config_displays_table(self):
        """Test _show_config displays config table."""
        from forensic.cli.commands.config_cmd import _show_config

        config = MagicMock(
            analysis=MagicMock(parallel_workers=4, enable_gpu=False),
            search=MagicMock(max_results=1000),
            report=MagicMock(default_format="markdown"),
            cache=MagicMock(enabled=True),
            output=MagicMock(color="auto"),
        )
        console = MagicMock()
        console_manager = MagicMock()

        _show_config(config, console, console_manager)
        assert console.print.called
