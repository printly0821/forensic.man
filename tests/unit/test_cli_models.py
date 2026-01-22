"""Tests for CLI models"""
import pytest
from pathlib import Path

from forensic.cli.models.config import (
    AnalysisConfig,
    ForensicCLIConfig,
    ReportConfig,
)
from forensic.cli.models.context import CLIContext
from forensic.cli.models.progress import ProgressState
from forensic.cli.models.result import AnalyzeResult, ProcessingError, SpeakerStats


class TestCLIContext:
    """Tests for CLIContext model"""

    def test_default_values(self) -> None:
        """Test default context values"""
        ctx = CLIContext()
        assert ctx.verbose is False
        assert ctx.quiet is False

    def test_should_show_progress(self) -> None:
        """Test progress display logic"""
        ctx = CLIContext(quiet=False)
        assert ctx.should_show_progress() is True

        ctx = CLIContext(quiet=True)
        assert ctx.should_show_progress() is False

    def test_should_show_verbose(self) -> None:
        """Test verbose message logic"""
        ctx = CLIContext(verbose=True, quiet=False)
        assert ctx.should_show_verbose() is True

        ctx = CLIContext(verbose=True, quiet=True)
        assert ctx.should_show_verbose() is False


class TestForensicCLIConfig:
    """Tests for ForensicCLIConfig model"""

    def test_default_config(self) -> None:
        """Test default configuration values"""
        config = ForensicCLIConfig()

        assert config.analysis.parallel_workers == 4
        assert config.search.max_results == 1000
        assert config.report.default_format == "markdown"
        assert config.cache.enabled is True
        assert config.output.color == "auto"

    def test_config_get_method(self) -> None:
        """Test getting nested config values"""
        config = ForensicCLIConfig()

        assert config.get("analysis.parallel_workers") == 4
        assert config.get("search.max_results") == 1000
        assert config.get("invalid.key") is None
        assert config.get("invalid.key", "default") == "default"

    def test_analysis_config_validation(self) -> None:
        """Test AnalysisConfig validation"""
        # Valid config
        config = AnalysisConfig(
            chunk_size_mb=10, parallel_workers=8, enable_gpu=True, timeout_per_file=600
        )
        assert config.chunk_size_mb == 10

        # Invalid chunk_size_mb (too large)
        with pytest.raises(ValueError):
            AnalysisConfig(chunk_size_mb=101)

    def test_report_format_validation(self) -> None:
        """Test ReportConfig format validation"""
        # Valid formats
        for fmt in ["markdown", "html", "json", "pdf"]:
            config = ReportConfig(default_format=fmt)
            assert config.default_format == fmt

        # Invalid format
        with pytest.raises(ValueError):
            ReportConfig(default_format="invalid")


class TestAnalyzeResult:
    """Tests for AnalyzeResult model"""

    def test_default_values(self) -> None:
        """Test default result values"""
        result = AnalyzeResult()
        assert result.total_files == 0
        assert result.total_segments == 0
        assert result.total_evidence == 0

    def test_add_speaker_stats(self) -> None:
        """Test adding speaker statistics"""
        result = AnalyzeResult()
        stats = SpeakerStats(
            speaker_id="speaker1", speaker_name="Test Speaker", total_segments=10
        )

        result.add_speaker_stats(stats)

        assert "speaker1" in result.speaker_stats
        assert result.speaker_stats["speaker1"].total_segments == 10

    def test_add_error(self) -> None:
        """Test adding processing errors"""
        result = AnalyzeResult()
        error = ProcessingError(
            file_path="/test/file.txt", error_type="TestError", error_message="Test error message"
        )

        result.add_error(error)

        assert len(result.errors) == 1
        assert result.errors[0].file_path == "/test/file.txt"

    def test_increment_pattern_count(self) -> None:
        """Test incrementing pattern counts"""
        result = AnalyzeResult()

        result.increment_pattern_count("GASLIGHTING")
        result.increment_pattern_count("GASLIGHTING")
        result.increment_pattern_count("THREAT")

        assert result.patterns_found["GASLIGHTING"] == 2
        assert result.patterns_found["THREAT"] == 1

    def test_success_rate(self) -> None:
        """Test success rate calculation"""
        result = AnalyzeResult(total_files=10)

        # No errors
        assert result.success_rate == 100.0

        # Add unrecovered error
        error = ProcessingError(
            file_path="/test/file.txt", error_type="TestError", error_message="Test", recovered=False
        )
        result.add_error(error)

        assert result.success_rate == 90.0


class TestProgressState:
    """Tests for ProgressState model"""

    def test_create_new(self) -> None:
        """Test creating new progress state"""
        state = ProgressState.create_new("test-job", 100, Path("/tmp"))

        assert state.job_id == "test-job"
        assert state.total_files == 100
        assert state.processed_files == 0

    def test_progress_percentage(self) -> None:
        """Test progress percentage calculation"""
        state = ProgressState(job_id="test", total_files=100)

        assert state.progress_percentage == 0.0

        state.processed_files = 50
        assert state.progress_percentage == 50.0

    def test_is_complete(self) -> None:
        """Test completion status"""
        state = ProgressState(job_id="test", total_files=100)

        assert state.is_complete is False

        state.processed_files = 100
        assert state.is_complete is True
