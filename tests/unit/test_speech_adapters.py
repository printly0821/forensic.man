"""
Unit tests for speech adapter modules.

Tests for Whisper streaming adapter.
All tests use mocking to avoid requiring actual model loading.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from forensic.speech.adapters import (
    AdapterState,
    WhisperStreamingAdapter,
    WhisperStreamingConfig,
)
from forensic.speech.e2e import StreamChunk


class TestWhisperStreamingConfig:
    """Tests for WhisperStreamingConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        config = WhisperStreamingConfig()

        assert config.MODEL_SIZE == "large-v3"
        assert config.DEVICE == "cuda"
        assert config.COMPUTE_TYPE == "float16"
        assert config.CHUNK_DURATION_SEC == 5.0
        assert config.LANGUAGE == "ko"

    def test_config_custom(self):
        """Test custom configuration."""
        config = WhisperStreamingConfig(
            MODEL_SIZE="base",
            DEVICE="cpu",
            CHUNK_DURATION_SEC=10.0,
        )

        assert config.MODEL_SIZE == "base"
        assert config.DEVICE == "cpu"
        assert config.CHUNK_DURATION_SEC == 10.0

    def test_sample_rate(self):
        """Test sample rate property."""
        config = WhisperStreamingConfig()
        assert config.sample_rate == 16000


class TestWhisperStreamingAdapter:
    """Tests for WhisperStreamingAdapter class."""

    def test_init_default(self):
        """Test default initialization."""
        adapter = WhisperStreamingAdapter()

        assert adapter.config.MODEL_SIZE == "large-v3"
        assert adapter.get_state() == AdapterState.IDLE

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = WhisperStreamingConfig(MODEL_SIZE="base")
        adapter = WhisperStreamingAdapter(config=config)

        assert adapter.config.MODEL_SIZE == "base"

    def test_init_with_callback(self):
        """Test initialization with progress callback."""
        callback = Mock()
        adapter = WhisperStreamingAdapter(progress_callback=callback)

        assert adapter.progress_callback is callback

    @pytest.mark.skip(reason="Requires faster-whisper installation")
    def test_initialize_success(self):
        """Test successful initialization."""
        # Skipped in CI environments without faster-whisper
        pass

    @pytest.mark.skip(reason="Requires faster-whisper installation")
    def test_initialize_failure(self):
        """Test initialization failure."""
        adapter = WhisperStreamingAdapter()

        with pytest.raises(ImportError):
            adapter.initialize()

        assert adapter.get_state() == AdapterState.ERROR

    def test_create_stream_chunk(self):
        """Test creating a stream chunk."""
        adapter = WhisperStreamingAdapter()
        audio = np.random.randn(80000).astype(np.float32)  # 5 seconds at 16kHz

        chunk = adapter.create_stream_chunk(audio, "test_001")

        assert chunk.chunk_id == "test_001"
        assert chunk.sample_rate == 24000  # Resampled to 24kHz
        assert chunk.is_final is False

    def test_create_stream_chunk_final(self):
        """Test creating a final stream chunk."""
        adapter = WhisperStreamingAdapter()
        audio = np.random.randn(80000).astype(np.float32)

        chunk = adapter.create_stream_chunk(audio, "final_001", is_final=True)

        assert chunk.is_final is True

    def test_create_chunk_validates_to_stream_chunk(self):
        """Test created chunk is valid StreamChunk."""
        adapter = WhisperStreamingAdapter()
        audio = np.random.randn(80000).astype(np.float32)

        chunk = adapter.create_stream_chunk(audio, "test")

        assert isinstance(chunk, StreamChunk)
        assert chunk.frame_count > 0

    def test_resample_to_24khz_fallback(self):
        """Test resampling fallback without librosa."""
        adapter = WhisperStreamingAdapter()
        audio_16k = np.random.randn(16000).astype(np.float32)

        # Use fallback resampling (librosa not available in test)
        result = adapter._resample_to_24khz(audio_16k)

        assert len(result) == 24000

    @patch("soundfile.read")
    def test_load_audio_mono(self, mock_read):
        """Test loading mono audio."""
        mock_read.return_value = (np.random.randn(16000).astype(np.float32), 16000)

        adapter = WhisperStreamingAdapter()
        audio, sr = adapter._load_audio(Path("test.wav"))

        assert sr == 16000
        assert len(audio) == 16000

    @patch("soundfile.read")
    def test_load_audio_stereo_to_mono(self, mock_read):
        """Test loading stereo audio converts to mono."""
        stereo_audio = np.random.randn(16000, 2).astype(np.float32)
        mock_read.return_value = (stereo_audio, 16000)

        adapter = WhisperStreamingAdapter()
        audio, sr = adapter._load_audio(Path("test.wav"))

        assert sr == 16000
        assert audio.ndim == 1  # Converted to mono

    @patch("soundfile.read", side_effect=FileNotFoundError("test.wav not found"))
    def test_load_audio_file_not_found(self, mock_read):
        """Test loading non-existent file."""
        adapter = WhisperStreamingAdapter()

        with pytest.raises(FileNotFoundError):
            adapter._load_audio(Path("nonexistent.wav"))

    def test_chunk_audio(self):
        """Test audio chunking."""
        adapter = WhisperStreamingAdapter()

        # 10 seconds of audio at 16kHz
        audio = np.random.randn(160000).astype(np.float32)

        chunks = list(adapter._chunk_audio(audio, 16000))

        assert len(chunks) > 0
        for chunk_audio, chunk_id, is_final in chunks:
            assert isinstance(chunk_audio, np.ndarray)
            assert isinstance(chunk_id, str)
            assert isinstance(is_final, bool)

    def test_chunk_audio_last_chunk_final(self):
        """Test last chunk is marked as final."""
        adapter = WhisperStreamingAdapter()

        # Short audio (less than 2 chunks)
        audio = np.random.randn(50000).astype(np.float32)

        chunks = list(adapter._chunk_audio(audio, 16000))

        assert len(chunks) > 0
        assert chunks[-1][2] is True  # Last chunk is_final

    def test_is_ready_before_initialize(self):
        """Test is_ready before initialization."""
        adapter = WhisperStreamingAdapter()

        assert adapter.is_ready() is False

    def test_reset(self):
        """Test resetting adapter state."""
        adapter = WhisperStreamingAdapter()
        adapter._state = AdapterState.COMPLETED

        adapter.reset()

        assert adapter.get_state() == AdapterState.IDLE


class TestWhisperStreamingAdapterIntegration:
    """Integration tests for Whisper streaming adapter."""

    @pytest.mark.skip(reason="Requires faster-whisper installation")
    def test_transcribe_chunks(self):
        """Test transcribing stream chunks."""
        # Skipped in CI environments without faster-whisper
        pass
