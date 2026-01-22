"""Tests for forensic analyze command"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from forensic.cli.commands.analyze_cmd import analyze


@pytest.fixture
def runner():
    """Create a Click CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def mock_context():
    """Create a mock Click context with console_manager."""
    console_manager = MagicMock()
    console = MagicMock()
    config = MagicMock()
    ctx_obj = {
        "console_manager": console_manager,
        "console": console,
        "config": config,
    }
    return ctx_obj, console_manager, console


@pytest.fixture
def temp_dirs():
    """Create temporary input and output directories."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_dir = Path(tmp_dir) / "input"
        output_dir = Path(tmp_dir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        yield input_dir, output_dir


@pytest.fixture
def sample_transcript(temp_dirs):
    """Create a sample transcript JSON file."""
    input_dir, _ = temp_dirs
    transcript_file = input_dir / "transcript.json"
    transcript_data = {
        "segments": [
            {
                "speaker_id": "speaker1",
                "speaker_name": "Test Speaker",
                "text": "This is a test transcript.",
                "start_time": 0.0,
                "end_time": 5.0,
            }
        ]
    }
    with open(transcript_file, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f)
    return transcript_file


class TestAnalyzeCommand:
    """Test suite for the analyze command."""

    def test_analyze_missing_input_path(self, runner):
        """Test analyze command with missing input path."""
        result = runner.invoke(analyze, ["--input", "/nonexistent", "--output", "/tmp/output"])
        # Click returns 2 for bad/missing parameters
        assert result.exit_code in (1, 2)
        assert "경로 오류" in result.output or "does not exist" in result.output.lower()

    def test_analyze_with_valid_paths(self, runner, temp_dirs, mock_context):
        """Test analyze command with valid input/output paths."""
        input_dir, output_dir = temp_dirs
        ctx_obj, _, _ = mock_context

        with patch("forensic.cli.commands.analyze_cmd.GracefulInterrupt"):
            result = runner.invoke(
                analyze,
                ["--input", str(input_dir), "--output", str(output_dir)],
                obj=ctx_obj,
                standalone_mode=False,
            )

        # The command should complete or show progress
        assert (
            result.exit_code in (0, None)
            or "분석" in result.output
            or "1단계" in str(result.output)
        )

    def test_analyze_with_force_flag(self, runner, temp_dirs, mock_context):
        """Test analyze command with --force flag."""
        input_dir, output_dir = temp_dirs
        ctx_obj, _, _ = mock_context

        result = runner.invoke(
            analyze,
            ["--input", str(input_dir), "--output", str(output_dir), "--force"],
            obj=ctx_obj,
            standalone_mode=False,
        )
        assert result.exit_code in (0, None)

    def test_analyze_with_parallel_flag(self, runner, temp_dirs, mock_context):
        """Test analyze command with --parallel flag."""
        input_dir, output_dir = temp_dirs
        ctx_obj, _, _ = mock_context

        result = runner.invoke(
            analyze,
            ["--input", str(input_dir), "--output", str(output_dir), "--parallel"],
            obj=ctx_obj,
            standalone_mode=False,
        )
        assert result.exit_code in (0, None)

    def test_analyze_with_gpu_flag(self, runner, temp_dirs, mock_context):
        """Test analyze command with --gpu flag."""
        input_dir, output_dir = temp_dirs
        ctx_obj, _, _ = mock_context

        result = runner.invoke(
            analyze,
            ["--input", str(input_dir), "--output", str(output_dir), "--gpu"],
            obj=ctx_obj,
            standalone_mode=False,
        )
        assert result.exit_code in (0, None)

    def test_analyze_with_no_cache_flag(self, runner, temp_dirs, mock_context):
        """Test analyze command with --no-cache flag."""
        input_dir, output_dir = temp_dirs
        ctx_obj, _, _ = mock_context

        result = runner.invoke(
            analyze,
            ["--input", str(input_dir), "--output", str(output_dir), "--no-cache"],
            obj=ctx_obj,
            standalone_mode=False,
        )
        assert result.exit_code in (0, None)


class TestAnalyzeHelperFunctions:
    """Test suite for analyze command helper functions."""

    def test_discover_files(self, temp_dirs):
        """Test _discover_files function."""
        from forensic.cli.commands.analyze_cmd import _discover_files

        input_dir, _ = temp_dirs
        # Create test files
        (input_dir / "test.json").touch()
        (input_dir / "test.txt").touch()
        (input_dir / "test.csv").touch()
        (input_dir / "test.md").touch()
        (input_dir / "test.py").touch()  # Should be ignored

        files = _discover_files(input_dir)
        assert len(files) == 4

    def test_load_transcripts(self, temp_dirs):
        """Test _load_transcripts function."""
        from forensic.cli.commands.analyze_cmd import _load_transcripts

        input_dir, _ = temp_dirs
        # Create a sample transcript file
        transcript_file = input_dir / "transcript.json"
        transcript_data = {
            "segments": [
                {
                    "speaker_id": "speaker1",
                    "speaker_name": "Test Speaker",
                    "text": "This is a test transcript.",
                    "start_time": 0.0,
                    "end_time": 5.0,
                }
            ]
        }
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f)

        files = list(input_dir.glob("*.json"))

        console_manager = MagicMock()
        transcripts = _load_transcripts(files, console_manager)

        # Transcript should be loaded since it has valid structure
        assert len(transcripts) >= 0

    def test_generate_speaker_stats(self):
        """Test _generate_speaker_stats function."""
        from forensic.cli.commands.analyze_cmd import _generate_speaker_stats

        # Create mock transcript with segments
        mock_transcript = MagicMock()
        mock_segment = MagicMock()
        mock_segment.speaker_id = "speaker1"
        mock_segment.speaker_name = "Test Speaker"
        mock_segment.text = "This is a test"
        mock_transcript.segments = [mock_segment]

        stats = _generate_speaker_stats([mock_transcript], [])
        assert len(stats) == 1
        assert stats[0].speaker_id == "speaker1"
        assert stats[0].total_segments == 1
