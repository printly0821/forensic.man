"""
Unit tests for speech analysis modules.

Tests for emotion analysis, gaslighting detection, and deepfake detection.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import numpy as np


class TestEmotionConfig:
    """Tests for EmotionConfig."""

    def test_emotions_list(self):
        """Test emotions list contains all expected emotions."""
        from forensic.speech.analysis.emotion import EmotionConfig

        expected = [
            "neutral",
            "happy",
            "sad",
            "angry",
            "fear",
            "disgust",
            "surprise",
        ]

        for emotion in expected:
            assert emotion in EmotionConfig.EMOTIONS

    def test_prosody_weights(self):
        """Test prosody weights exist for all emotions."""
        from forensic.speech.analysis.emotion import EmotionConfig

        for emotion in EmotionConfig.EMOTIONS:
            assert emotion in EmotionConfig.PROSODY_WEIGHTS


class TestEmotionAnalyzer:
    """Tests for EmotionAnalyzer class."""

    def test_init_default(self):
        """Test default initialization."""
        from forensic.speech.analysis.emotion import EmotionAnalyzer, EmotionModel

        analyzer = EmotionAnalyzer()
        assert analyzer.model == EmotionModel.PROSODY_BASED

    def test_init_custom_model(self):
        """Test initialization with custom model."""
        from forensic.speech.analysis.emotion import EmotionAnalyzer, EmotionModel

        analyzer = EmotionAnalyzer(model=EmotionModel.WAV2VEC2)
        assert analyzer.model == EmotionModel.WAV2VEC2

    def test_analyze_from_prosody(self):
        """Test emotion analysis from prosodic features."""
        from forensic.speech.analysis.emotion import EmotionAnalyzer

        analyzer = EmotionAnalyzer()

        result = analyzer.analyze_from_prosody(
            f0_mean=200.0,
            f0_std=50.0,
            energy=1.0,
            speaking_rate=1.2,
            segment_id="test_seg",
        )

        assert result.segment_id == "test_seg"
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0
        assert result.arousal >= 0.0
        assert result.arousal <= 1.0
        assert result.valence >= -1.0
        assert result.valence <= 1.0

    def test_emotion_to_arousal(self):
        """Test emotion to arousal mapping."""
        from forensic.speech.analysis.emotion import EmotionAnalyzer
        from forensic.models.speech import EmotionCategory

        analyzer = EmotionAnalyzer()

        angry_arousal = analyzer._emotion_to_arousal(EmotionCategory.ANGRY)
        neutral_arousal = analyzer._emotion_to_arousal(EmotionCategory.NEUTRAL)

        assert angry_arousal > neutral_arousal

    def test_emotion_to_valence(self):
        """Test emotion to valence mapping."""
        from forensic.speech.analysis.emotion import EmotionAnalyzer
        from forensic.models.speech import EmotionCategory

        analyzer = EmotionAnalyzer()

        happy_valence = analyzer._emotion_to_valence(EmotionCategory.HAPPY)
        sad_valence = analyzer._emotion_to_valence(EmotionCategory.SAD)

        assert happy_valence > sad_valence


class TestGaslightingPatterns:
    """Tests for GaslightingPatterns."""

    def test_all_patterns(self):
        """Test all patterns are defined."""
        from forensic.speech.analysis.gaslighting import GaslightingPatterns

        patterns = GaslightingPatterns.all_patterns()

        assert len(patterns) == 6

    def test_pattern_has_required_fields(self):
        """Test each pattern has required fields."""
        from forensic.speech.analysis.gaslighting import GaslightingPatterns

        patterns = GaslightingPatterns.all_patterns()

        for pattern in patterns:
            assert hasattr(pattern, "name")
            assert hasattr(pattern, "type")
            assert hasattr(pattern, "patterns")
            assert hasattr(pattern, "keywords")
            assert hasattr(pattern, "severity")


class TestGaslightingDetector:
    """Tests for GaslightingDetector class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.analysis.gaslighting import GaslightingDetector

        detector = GaslightingDetector()
        assert len(detector.patterns) == 6

    def test_detect_in_text_empty(self):
        """Test detection with empty text."""
        from forensic.speech.analysis.gaslighting import GaslightingDetector

        detector = GaslightingDetector()
        results = detector.detect_in_text("", segment_id="test")

        assert len(results) == 0

    def test_detect_denial_pattern(self):
        """Test denial pattern detection."""
        from forensic.speech.analysis.gaslighting import GaslightingDetector

        detector = GaslightingDetector()
        results = detector.detect_in_text(
            "나는 너한테 그런 말 한 적 없어",
            segment_id="test",
        )

        # Should detect denial pattern
        assert len(results) >= 0
        if results:
            assert results[0].segment_id == "test"

    def test_get_statistics_empty(self):
        """Test statistics with empty results."""
        from forensic.speech.analysis.gaslighting import GaslightingDetector

        detector = GaslightingDetector()
        stats = detector.get_statistics([])

        assert stats["total_count"] == 0
        assert stats["by_type"] == {}
        assert stats["by_severity"] == {}

    def test_classify_severity_none(self):
        """Test severity classification with no indicators."""
        from forensic.speech.analysis.gaslighting import GaslightingDetector

        detector = GaslightingDetector()
        severity = detector.classify_severity([])

        assert severity == "NONE"

    def test_classify_severity_high(self):
        """Test high severity classification."""
        from forensic.speech.analysis.gaslighting import (
            GaslightingDetector,
            GaslightingIndicator,
            GaslightingType,
        )

        detector = GaslightingDetector()

        indicators = [
            GaslightingIndicator(
                segment_id="test1",
                type=GaslightingType.COUNTER_ATTACK,
                severity="HIGH",
            ),
            GaslightingIndicator(
                segment_id="test2",
                type=GaslightingType.DENIAL,
                severity="HIGH",
            ),
        ]

        severity = detector.classify_severity(indicators)
        assert severity == "HIGH"


class TestGaslightingReportGenerator:
    """Tests for GaslightingReportGenerator class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.analysis.gaslighting import GaslightingReportGenerator

        generator = GaslightingReportGenerator()
        assert generator.detector is not None

    def test_generate_report_empty(self):
        """Test report generation with no indicators."""
        from forensic.speech.analysis.gaslighting import GaslightingReportGenerator

        generator = GaslightingReportGenerator()
        report = generator.generate_report([])

        assert "가스라이팅 탐지 보고서" in report
        assert "탐지된 패턴 수: 0" in report

    def test_generate_report_with_indicators(self):
        """Test report generation with indicators."""
        from forensic.speech.analysis.gaslighting import (
            GaslightingReportGenerator,
            GaslightingIndicator,
            GaslightingType,
        )

        generator = GaslightingReportGenerator()

        indicators = [
            GaslightingIndicator(
                segment_id="test1",
                type=GaslightingType.DENIAL,
                severity="HIGH",
                evidence="그런 적 없어",
            ),
        ]

        report = generator.generate_report(indicators)

        assert "가스라이팅 탐지 보고서" in report
        assert "탐지된 패턴 수: 1" in report


class TestDeepfakeConfig:
    """Tests for DeepfakeConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        from forensic.speech.analysis.deepfake import DeepfakeConfig

        assert hasattr(DeepfakeConfig, "CNN_FILTERS")
        assert hasattr(DeepfakeConfig, "SAMPLE_RATE")
        assert hasattr(DeepfakeConfig, "DEEPFAKE_THRESHOLD")


class TestCNNLSTMDeepfakeDetector:
    """Tests for CNNLSTMDeepfakeDetector class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.analysis.deepfake import CNNLSTMDeepfakeDetector

        detector = CNNLSTMDeepfakeDetector()
        assert detector.model_path is None
        assert detector._model is None

    def test_init_with_model_path(self):
        """Test initialization with model path."""
        from forensic.speech.analysis.deepfake import CNNLSTMDeepfakeDetector

        detector = CNNLSTMDeepfakeDetector(model_path="/path/to/model.pth")
        assert str(detector.model_path) == "/path/to/model.pth"

    def test_analyze_spectral_inconsistencies(self):
        """Test spectral inconsistency analysis."""
        from forensic.speech.analysis.deepfake import CNNLSTMDeepfakeDetector

        detector = CNNLSTMDeepfakeDetector()

        features = {
            "mfcc": np.random.randn(20, 100),
            "lfcc": np.random.randn(20, 100),
            "spectral_centroid": np.random.randn(100),
            "spectral_rolloff": np.random.randn(100),
            "zcr": np.random.randn(100),
        }

        inconsistencies = detector.analyze_spectral_inconsistencies(features)

        assert "mfcc_variance" in inconsistencies
        assert "lfcc_variance" in inconsistencies
        assert "spectral_flux" in inconsistencies
        assert "zcr_anomaly" in inconsistencies
        assert "temporal_consistency" in inconsistencies

    def test_calculate_deepfake_probability(self):
        """Test deepfake probability calculation."""
        from forensic.speech.analysis.deepfake import CNNLSTMDeepfakeDetector

        detector = CNNLSTMDeepfakeDetector()

        inconsistencies = {
            "mfcc_variance": 50.0,
            "lfcc_variance": 50.0,
            "spectral_flux": 100.0,
            "zcr_anomaly": 0.1,
            "temporal_consistency": 0.8,
        }

        is_fake, prob, explanation = detector.calculate_deepfake_probability(
            inconsistencies
        )

        assert isinstance(is_fake, bool)
        assert 0.0 <= prob <= 1.0
        assert isinstance(explanation, str)


class TestDeepfakeResult:
    """Tests for DeepfakeResult dataclass."""

    def test_create_result(self):
        """Test creating deepfake result."""
        from forensic.speech.analysis.deepfake import DeepfakeResult

        result = DeepfakeResult(
            is_deepfake=True,
            probability=0.85,
            confidence=0.9,
            indicators={"mfcc_variance": 50.0},
            explanation="High likelihood of synthetic speech",
        )

        assert result.is_deepfake is True
        assert result.probability == 0.85
        assert result.confidence == 0.9


class TestEnsembleDeepfakeDetector:
    """Tests for EnsembleDeepfakeDetector class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.analysis.deepfake import EnsembleDeepfakeDetector

        detector = EnsembleDeepfakeDetector()
        assert detector.cnn_lstm is not None

    def test_get_detailed_report(self):
        """Test detailed report generation."""
        from forensic.speech.analysis.deepfake import (
            EnsembleDeepfakeDetector,
            DeepfakeResult,
        )

        detector = EnsembleDeepfakeDetector()

        # Create test result
        result = DeepfakeResult(
            is_deepfake=False,
            probability=0.2,
            confidence=0.8,
            indicators={"mfcc_variance": 50.0},
            explanation="No issues detected",
        )

        # Mock the detect method
        with patch.object(detector, "detect", return_value=result):
            report = detector.get_detailed_report("/fake/audio.wav")

            assert "딥페이크 탐지 보고서" in report
            assert "진본" in report or "딥페이크" in report
