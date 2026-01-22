"""
Unit tests for speech data models.

Tests for all Pydantic models in forensic.models.speech.
"""

import pytest
from datetime import datetime

from forensic.models.speech import (
    SpeechSegment,
    DiarizationSegment,
    ProsodyFeatures,
    EmotionAnalysis,
    EmotionCategory,
    GaslightingIndicator,
    GaslightingType,
    AuthenticityScore,
    AuthenticityExplanation,
    TemporalDegradationReport,
    IntegrityChain,
    AnalysisResults,
)


class TestSpeechSegment:
    """Tests for SpeechSegment model."""

    def test_create_valid_segment(self):
        """Test creating a valid speech segment."""
        segment = SpeechSegment(
            id="seg_001",
            start_time=0.0,
            end_time=5.0,
            text="Hello world",
            confidence=0.95,
        )

        assert segment.id == "seg_001"
        assert segment.start_time == 0.0
        assert segment.end_time == 5.0
        assert segment.text == "Hello world"
        assert segment.confidence == 0.95

    def test_segment_duration(self):
        """Test segment duration calculation."""
        segment = SpeechSegment(
            id="seg_001",
            start_time=10.0,
            end_time=25.0,
            text="Test",
        )

        assert segment.duration == 15.0

    def test_invalid_end_time_raises_error(self):
        """Test that end_time < start_time raises error."""
        with pytest.raises(ValueError, match="end_time must be greater than start_time"):
            SpeechSegment(
                id="seg_001",
                start_time=10.0,
                end_time=5.0,
                text="Test",
            )

    def test_negative_start_time_raises_error(self):
        """Test that negative start_time raises error."""
        with pytest.raises(ValueError):
            SpeechSegment(
                id="seg_001",
                start_time=-1.0,
                end_time=5.0,
                text="Test",
            )

    def test_confidence_out_of_range_raises_error(self):
        """Test that confidence > 1.0 raises error."""
        with pytest.raises(ValueError):
            SpeechSegment(
                id="seg_001",
                start_time=0.0,
                end_time=5.0,
                text="Test",
                confidence=1.5,
            )


class TestDiarizationSegment:
    """Tests for DiarizationSegment model."""

    def test_create_valid_segment(self):
        """Test creating a valid diarization segment."""
        segment = DiarizationSegment(
            id="dia_001",
            start_time=0.0,
            end_time=5.0,
            speaker_id="speaker_1",
            confidence=0.9,
        )

        assert segment.speaker_id == "speaker_1"
        assert segment.duration == 5.0

    def test_segment_overlaps_true(self):
        """Test overlap detection with overlapping segments."""
        seg1 = DiarizationSegment(
            id="dia_001",
            start_time=0.0,
            end_time=5.0,
            speaker_id="spk_1",
        )
        seg2 = DiarizationSegment(
            id="dia_002",
            start_time=3.0,
            end_time=8.0,
            speaker_id="spk_2",
        )

        assert seg1.overlaps(seg2)
        assert seg2.overlaps(seg1)

    def test_segment_overlaps_false(self):
        """Test overlap detection with non-overlapping segments."""
        seg1 = DiarizationSegment(
            id="dia_001",
            start_time=0.0,
            end_time=5.0,
            speaker_id="spk_1",
        )
        seg2 = DiarizationSegment(
            id="dia_002",
            start_time=6.0,
            end_time=10.0,
            speaker_id="spk_2",
        )

        assert not seg1.overlaps(seg2)


class TestProsodyFeatures:
    """Tests for ProsodyFeatures model."""

    def test_create_valid_features(self):
        """Test creating valid prosody features."""
        features = ProsodyFeatures(
            segment_id="seg_001",
            f0_mean=150.0,
            f0_std=20.0,
            f0_min=100.0,
            f0_max=200.0,
            f0_range=100.0,
            jitter=0.5,
            shimmer=0.3,
            hnr=10.0,
        )

        assert features.segment_id == "seg_001"
        assert features.f0_mean == 150.0

    def test_f0_cv_calculation(self):
        """Test F0 coefficient of variation calculation."""
        features = ProsodyFeatures(
            segment_id="seg_001",
            f0_mean=200.0,
            f0_std=40.0,
            f0_min=100.0,
            f0_max=300.0,
            f0_range=200.0,
            jitter=0.5,
            shimmer=0.3,
            hnr=10.0,
        )

        # CV = (std / mean) * 100
        expected_cv = (40.0 / 200.0) * 100
        assert features.f0_cv == expected_cv

    def test_f0_cv_zero_mean(self):
        """Test F0 CV with zero mean."""
        features = ProsodyFeatures(
            segment_id="seg_001",
            f0_mean=0.0,
            f0_std=0.0,
            f0_min=0.0,
            f0_max=0.0,
            f0_range=0.0,
            jitter=0.0,
            shimmer=0.0,
            hnr=0.0,
        )

        assert features.f0_cv == 0.0


class TestEmotionAnalysis:
    """Tests for EmotionAnalysis model."""

    def test_create_valid_emotion(self):
        """Test creating valid emotion analysis."""
        emotion = EmotionAnalysis(
            segment_id="seg_001",
            primary_emotion=EmotionCategory.HAPPY,
            emotion_scores={"happy": 0.8, "sad": 0.1, "angry": 0.1},
            confidence=0.85,
            arousal=0.7,
            valence=0.6,
        )

        assert emotion.primary_emotion == EmotionCategory.HAPPY
        assert emotion.confidence == 0.85

    def test_get_emotion_score(self):
        """Test getting score for specific emotion."""
        emotion = EmotionAnalysis(
            segment_id="seg_001",
            primary_emotion=EmotionCategory.HAPPY,
            emotion_scores={"happy": 0.8, "sad": 0.1, "angry": 0.1},
        )

        assert emotion.get_emotion_score(EmotionCategory.HAPPY) == 0.8
        assert emotion.get_emotion_score(EmotionCategory.SAD) == 0.1

    def test_is_high_arousal(self):
        """Test high arousal detection."""
        high_arousal = EmotionAnalysis(
            segment_id="seg_001",
            primary_emotion=EmotionCategory.ANGRY,
            arousal=0.8,
        )

        low_arousal = EmotionAnalysis(
            segment_id="seg_002",
            primary_emotion=EmotionCategory.NEUTRAL,
            arousal=0.4,
        )

        assert high_arousal.is_high_arousal()
        assert not low_arousal.is_high_arousal()

    def test_is_negative_valence(self):
        """Test negative valence detection."""
        negative = EmotionAnalysis(
            segment_id="seg_001",
            primary_emotion=EmotionCategory.SAD,
            valence=-0.6,
        )

        positive = EmotionAnalysis(
            segment_id="seg_002",
            primary_emotion=EmotionCategory.HAPPY,
            valence=0.5,
        )

        assert negative.is_negative_valence()
        assert not positive.is_negative_valence()


class TestGaslightingIndicator:
    """Tests for GaslightingIndicator model."""

    def test_create_valid_indicator(self):
        """Test creating valid gaslighting indicator."""
        indicator = GaslightingIndicator(
            segment_id="seg_001",
            type=GaslightingType.DENIAL,
            severity="HIGH",
            confidence=0.9,
            evidence="그런 적 없어",
        )

        assert indicator.type == GaslightingType.DENIAL
        assert indicator.severity == "HIGH"

    def test_is_high_severity(self):
        """Test high severity detection."""
        high = GaslightingIndicator(
            segment_id="seg_001",
            type=GaslightingType.COUNTER_ATTACK,
            severity="HIGH",
        )

        medium = GaslightingIndicator(
            segment_id="seg_002",
            type=GaslightingType.TRIVIALIZING,
            severity="MEDIUM",
        )

        assert high.is_high_severity()
        assert not medium.is_high_severity()

    def test_is_confident(self):
        """Test high confidence detection."""
        confident = GaslightingIndicator(
            segment_id="seg_001",
            type=GaslightingType.DENIAL,
            confidence=0.85,
        )

        not_confident = GaslightingIndicator(
            segment_id="seg_002",
            type=GaslightingType.BLOCKING,
            confidence=0.5,
        )

        assert confident.is_confident()
        assert not not_confident.is_confident()


class TestAuthenticityScore:
    """Tests for AuthenticityScore model."""

    def test_create_valid_score(self):
        """Test creating valid authenticity score."""
        score = AuthenticityScore(
            audio_id="audio_001",
            score=75.0,
            explanation="Natural speech characteristics detected",
            deepfake_probability=0.25,
            confidence=0.9,
            indicators=["consistent prosody", "natural spectral features"],
        )

        assert score.score == 75.0
        assert len(score.indicators) == 2

    def test_is_likely_authentic(self):
        """Test authenticity detection."""
        authentic = AuthenticityScore(
            audio_id="audio_001",
            score=85.0,
            explanation="Authentic",
            deepfake_probability=0.15,
        )

        fake = AuthenticityScore(
            audio_id="audio_002",
            score=45.0,
            explanation="Potential deepfake",
            deepfake_probability=0.55,
        )

        assert authentic.is_likely_authentic()
        assert not fake.is_likely_authentic()

    def test_is_likely_deepfake(self):
        """Test deepfake detection."""
        deepfake = AuthenticityScore(
            audio_id="audio_001",
            score=30.0,
            explanation="Highly likely deepfake",
            deepfake_probability=0.8,
        )

        authentic = AuthenticityScore(
            audio_id="audio_002",
            score=90.0,
            explanation="Authentic",
            deepfake_probability=0.1,
        )

        assert deepfake.is_likely_deepfake()
        assert not authentic.is_likely_deepfake()


class TestAnalysisResults:
    """Tests for AnalysisResults model."""

    def test_create_empty_results(self):
        """Test creating empty analysis results."""
        results = AnalysisResults(audio_id="audio_001")

        assert results.audio_id == "audio_001"
        assert results.get_segment_count() == 0
        assert results.get_speaker_count() == 0
        assert results.get_gaslighting_count() == 0

    def test_with_segments(self):
        """Test results with speech segments."""
        segment = SpeechSegment(
            id="seg_001",
            start_time=0.0,
            end_time=5.0,
            text="Hello",
        )

        results = AnalysisResults(
            audio_id="audio_001",
            segments=[segment],
        )

        assert results.get_segment_count() == 1

    def test_with_diarization(self):
        """Test results with diarization."""
        dia_seg = DiarizationSegment(
            id="dia_001",
            start_time=0.0,
            end_time=5.0,
            speaker_id="spk_1",
        )

        results = AnalysisResults(
            audio_id="audio_001",
            diarization=[dia_seg],
        )

        assert results.get_speaker_count() == 1

    def test_with_gaslighting(self):
        """Test results with gaslighting indicators."""
        indicator = GaslightingIndicator(
            segment_id="seg_001",
            type=GaslightingType.DENIAL,
        )

        results = AnalysisResults(
            audio_id="audio_001",
            gaslighting=[indicator],
        )

        assert results.get_gaslighting_count() == 1

    def test_has_deepfake_risk(self):
        """Test deepfake risk detection."""
        fake_score = AuthenticityScore(
            audio_id="audio_001",
            score=30.0,
            explanation="Fake",
            deepfake_probability=0.8,
        )

        results_risk = AnalysisResults(
            audio_id="audio_001",
            authenticity=fake_score,
        )

        assert results_risk.has_deepfake_risk()

    def test_has_deepfake_risk_none(self):
        """Test deepfake risk when no authenticity score."""
        results = AnalysisResults(audio_id="audio_001")

        assert not results.has_deepfake_risk()


class TestIntegrityChain:
    """Tests for IntegrityChain model."""

    def test_create_valid_chain(self):
        """Test creating valid integrity chain."""
        chain = IntegrityChain(
            audio_id="audio_001",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            checksum="abc123",
        )

        assert chain.audio_id == "audio_001"

    def test_verify_integrity_true(self):
        """Test integrity verification (match)."""
        chain = IntegrityChain(
            audio_id="audio_001",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            checksum="abc123",
        )

        assert chain.verify_integrity("abc123")

    def test_verify_integrity_false(self):
        """Test integrity verification (mismatch)."""
        chain = IntegrityChain(
            audio_id="audio_001",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            checksum="abc123",
        )

        assert not chain.verify_integrity("wrong")


class TestTemporalDegradationReport:
    """Tests for TemporalDegradationReport model."""

    def test_no_degradation(self):
        """Test report with no degradation."""
        report = TemporalDegradationReport(
            audio_id="audio_001",
            degradation_detected=False,
            severity="NONE",
        )

        assert not report.degradation_detected
        assert report.severity == "NONE"

    def test_with_degradation(self):
        """Test report with degradation detected."""
        report = TemporalDegradationReport(
            audio_id="audio_001",
            degradation_detected=True,
            degradation_type="compression_artifact",
            affected_segments=["seg_001", "seg_002"],
            severity="HIGH",
        )

        assert report.degradation_detected
        assert len(report.affected_segments) == 2
