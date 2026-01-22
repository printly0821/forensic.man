"""
Unit tests for speech processing modules.

Tests for transcriber, diarizer, prosody, VAD, and features modules.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import numpy as np


class TestTranscriptionConfig:
    """Tests for TranscriptionConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        from forensic.speech.transcriber import TranscriptionConfig

        assert hasattr(TranscriptionConfig, "MODEL_SIZE")
        assert hasattr(TranscriptionConfig, "LANGUAGE")
        assert TranscriptionConfig.LANGUAGE == "ko"


class TestTranscriber:
    """Tests for Transcriber class."""

    def test_init_default(self):
        """Test default initialization."""
        from forensic.speech.transcriber import Transcriber

        transcriber = Transcriber()

        assert transcriber.model_size == "large-v3"
        assert transcriber.device == "cuda"
        assert transcriber._model is None

    def test_init_custom(self):
        """Test initialization with custom parameters."""
        from forensic.speech.transcriber import Transcriber

        transcriber = Transcriber(
            model_size="base",
            device="cpu",
            compute_type="int8",
        )

        assert transcriber.model_size == "base"
        assert transcriber.device == "cpu"
        assert transcriber.compute_type == "int8"


class TestDiarizationConfig:
    """Tests for DiarizationConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        from forensic.speech.diarizer import DiarizationConfig

        assert hasattr(DiarizationConfig, "PIPELINE")
        assert hasattr(DiarizationConfig, "MIN_SPEAKERS")


class TestDiarizer:
    """Tests for Diarizer class."""

    def test_init_default(self):
        """Test default initialization."""
        from forensic.speech.diarizer import Diarizer

        diarizer = Diarizer()

        assert diarizer.pipeline_name == "pyannote/speaker-diarization-3.1"
        assert diarizer.device == "cuda"

    def test_init_custom(self):
        """Test initialization with custom parameters."""
        from forensic.speech.diarizer import Diarizer

        diarizer = Diarizer(
            pipeline="custom/pipeline",
            device="cpu",
            use_auth_token="test_token",
        )

        assert diarizer.pipeline_name == "custom/pipeline"
        assert diarizer.device == "cpu"
        assert diarizer.use_auth_token == "test_token"


class TestProsodyConfig:
    """Tests for ProsodyConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        from forensic.speech.prosody import ProsodyConfig

        assert hasattr(ProsodyConfig, "PITCH_FLOOR")
        assert hasattr(ProsodyConfig, "PITCH_CEILING")
        assert ProsodyConfig.PITCH_FLOOR == 75.0


class TestProsodyExtractor:
    """Tests for ProsodyExtractor class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.prosody import ProsodyExtractor

        extractor = ProsodyExtractor()
        assert extractor._sound_class is None

    @pytest.mark.skip(reason="Requires parselmouth")
    def test_extract_f0_stats(self):
        """Test F0 statistics extraction."""
        from forensic.speech.prosody import ProsodyExtractor

        extractor = ProsodyExtractor()

        # This test requires actual audio file and parselmouth
        # Skip in CI environments
        pass


class TestVadConfig:
    """Tests for VadConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        from forensic.speech.vad import VadConfig

        assert hasattr(VadConfig, "FRAME_DURATION_MS")
        assert hasattr(VadConfig, "AGGRESSIVENESS")


class TestVoiceActivityDetector:
    """Tests for VoiceActivityDetector class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.vad import VoiceActivityDetector

        vad = VoiceActivityDetector()
        assert vad.aggressiveness == 3

    def test_init_custom_aggressiveness(self):
        """Test initialization with custom aggressiveness."""
        from forensic.speech.vad import VoiceActivityDetector

        vad = VoiceActivityDetector(aggressiveness=2)
        assert vad.aggressiveness == 2

    def test_aggressiveness_clamping(self):
        """Test aggressiveness is clamped to valid range."""
        from forensic.speech.vad import VoiceActivityDetector

        vad_high = VoiceActivityDetector(aggressiveness=10)
        assert vad_high.aggressiveness == 3

        vad_low = VoiceActivityDetector(aggressiveness=-1)
        assert vad_low.aggressiveness == 0


class TestSpeechFrame:
    """Tests for SpeechFrame dataclass."""

    def test_create_speech_frame(self):
        """Test creating speech frame."""
        from forensic.speech.vad import SpeechFrame

        frame = SpeechFrame(
            start_time=0.0,
            end_time=0.03,
            is_speech=True,
            speech_probability=0.95,
        )

        assert frame.start_time == 0.0
        assert frame.end_time == 0.03
        assert frame.is_speech is True


class TestFeatureConfig:
    """Tests for FeatureConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        from forensic.speech.features import FeatureConfig

        assert hasattr(FeatureConfig, "SAMPLE_RATE")
        assert hasattr(FeatureConfig, "N_MFCC")
        assert hasattr(FeatureConfig, "N_LFCC")


class TestAudioFeatureExtractor:
    """Tests for AudioFeatureExtractor class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()
        assert extractor.sample_rate == 16000

    def test_init_custom_sample_rate(self):
        """Test initialization with custom sample rate."""
        from forensic.speech.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor(sample_rate=22050)
        assert extractor.sample_rate == 22050

    def test_compute_feature_statistics(self):
        """Test feature statistics computation."""
        from forensic.speech.features import AudioFeatureExtractor

        extractor = AudioFeatureExtractor()
        features = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

        stats = extractor.compute_feature_statistics(features)

        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["min"] == 1.0
        assert stats["max"] == 6.0


class TestDiarizationSegment:
    """Tests for DiarizationSegment overlap detection."""

    def test_overlapping_segments(self):
        """Test segment overlap detection."""
        from forensic.models.speech import DiarizationSegment

        seg1 = DiarizationSegment(
            id="seg1",
            start_time=0.0,
            end_time=5.0,
            speaker_id="spk1",
        )
        seg2 = DiarizationSegment(
            id="seg2",
            start_time=3.0,
            end_time=8.0,
            speaker_id="spk2",
        )

        assert seg1.overlaps(seg2)
        assert seg2.overlaps(seg1)

    def test_non_overlapping_segments(self):
        """Test non-overlapping segments."""
        from forensic.models.speech import DiarizationSegment

        seg1 = DiarizationSegment(
            id="seg1",
            start_time=0.0,
            end_time=5.0,
            speaker_id="spk1",
        )
        seg2 = DiarizationSegment(
            id="seg2",
            start_time=6.0,
            end_time=10.0,
            speaker_id="spk2",
        )

        assert not seg1.overlaps(seg2)

    def test_adjacent_segments(self):
        """Test adjacent segments (end == start)."""
        from forensic.models.speech import DiarizationSegment

        seg1 = DiarizationSegment(
            id="seg1",
            start_time=0.0,
            end_time=5.0,
            speaker_id="spk1",
        )
        seg2 = DiarizationSegment(
            id="seg2",
            start_time=5.0,
            end_time=10.0,
            speaker_id="spk2",
        )

        # Adjacent segments don't overlap
        assert not seg1.overlaps(seg2)
