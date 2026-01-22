"""
Unit tests for pattern detection module.

Tests PatternDetector, GaslightingPattern, ThreatPattern, and related models.
"""

from datetime import datetime
from pathlib import Path

import pytest

from forensic.analysis.pattern import (
    EmotionalManipulation,
    GaslightingPattern,
    KeywordDictionary,
    PatternDetector,
    ThreatPattern,
)
from forensic.models.transcript import Segment, Transcript


class TestKeywordDictionary:
    """Tests for KeywordDictionary class."""

    def test_gaslighting_keywords_structure(self):
        """Test gaslighting keywords are properly defined."""
        keywords = KeywordDictionary.all_gaslighting_keywords()
        assert "DENIAL" in keywords
        assert "TRIVIALIZING" in keywords
        assert "COUNTERING" in keywords
        assert len(keywords["DENIAL"]) > 0

    def test_emotional_manipulation_keywords(self):
        """Test emotional manipulation keywords."""
        keywords = KeywordDictionary.all_manipulation_keywords()
        assert "GUILT_TRIPPING" in keywords
        assert "SHAMING" in keywords
        assert "FEAR_INDUCING" in keywords

    def test_threat_keywords(self):
        """Test threat keywords."""
        keywords = KeywordDictionary.all_threat_keywords()
        assert "EXPLICIT_THREAT" in keywords
        assert "FINANCIAL_THREAT" in keywords
        assert "SOCIAL_THREAT" in keywords


class TestGaslightingPattern:
    """Tests for GaslightingPattern model."""

    def test_create_gaslighting_pattern(self):
        """Test creating a gaslighting pattern."""
        pattern = GaslightingPattern(
            pattern_type="DENIAL",
            segment_ids=["seg-001"],
            speaker="speaker_1",
            content_sample="그런 적 없어",
            confidence=0.8,
        )
        assert pattern.pattern_type == "DENIAL"
        assert pattern.confidence == 0.8

    def test_importance_calculation(self):
        """Test importance level based on occurrence count."""
        pattern = GaslightingPattern(
            pattern_type="TRIVIALIZING",
            segment_ids=["seg-001"],
            speaker="speaker_1",
            content_sample="별거 아니야",
            occurrence_count=3,
        )
        assert pattern.get_importance() == "HIGH"

    def test_confidence_check(self):
        """Test high confidence check."""
        pattern = GaslightingPattern(
            pattern_type="COUNTERING",
            segment_ids=["seg-001"],
            speaker="speaker_1",
            content_sample="네가 잘못 기억해",
            confidence=0.8,
        )
        assert pattern.is_high_confidence()


class TestThreatPattern:
    """Tests for ThreatPattern model."""

    def test_create_threat_pattern(self):
        """Test creating a threat pattern."""
        threat = ThreatPattern(
            threat_type="EXPLICIT_THREAT",
            segment_ids=["seg-001"],
            speaker="speaker_1",
            content_sample="가만 안 둬",
            severity="HIGH",
        )
        assert threat.threat_type == "EXPLICIT_THREAT"
        assert threat.severity == "HIGH"

    def test_critical_severity_check(self):
        """Test critical severity check."""
        threat = ThreatPattern(
            threat_type="EXPLICIT_THREAT",
            segment_ids=["seg-001"],
            speaker="speaker_1",
            content_sample="죽여버릴",
            severity="CRITICAL",
        )
        assert threat.is_critical()

    def test_high_severity_check(self):
        """Test high severity check."""
        threat = ThreatPattern(
            threat_type="FINANCIAL_THREAT",
            segment_ids=["seg-001"],
            speaker="speaker_1",
            content_sample="돈 안 줄 거야",
            severity="HIGH",
        )
        assert threat.is_high_severity()


class TestEmotionalManipulation:
    """Tests for EmotionalManipulation model."""

    def test_create_emotional_manipulation(self):
        """Test creating an emotional manipulation pattern."""
        pattern = EmotionalManipulation(
            manipulation_type="GUILT_TRIPPING",
            segment_ids=["seg-001"],
            speaker="speaker_1",
            content_sample="다 네 때문이야",
            intensity="HIGH",
        )
        assert pattern.manipulation_type == "GUILT_TRIPPING"
        assert pattern.intensity == "HIGH"

    def test_high_intensity_check(self):
        """Test high intensity check."""
        pattern = EmotionalManipulation(
            manipulation_type="SHAMING",
            segment_ids=["seg-001"],
            speaker="speaker_1",
            content_sample="창피하지도 않아",
            intensity="HIGH",
        )
        assert pattern.is_high_intensity()


class TestPatternDetector:
    """Tests for PatternDetector class."""

    @pytest.fixture
    def sample_segments(self):
        """Create sample segments with manipulation patterns."""
        return [
            Segment(
                id="seg-001",
                speaker="speaker_1",
                start_time=0.0,
                end_time=10.0,
                content="그런 적 없어, 상상하는 거야",
                confidence=1.0,
            ),
            Segment(
                id="seg-002",
                speaker="speaker_1",
                start_time=10.0,
                end_time=20.0,
                content="별거 아니야, 예민해",
                confidence=1.0,
            ),
            Segment(
                id="seg-003",
                speaker="speaker_1",
                start_time=20.0,
                end_time=30.0,
                content="네가 잘못 기억해",
                confidence=1.0,
            ),
            Segment(
                id="seg-004",
                speaker="speaker_1",
                start_time=30.0,
                end_time=40.0,
                content="가만 안 둬",
                confidence=1.0,
            ),
            Segment(
                id="seg-005",
                speaker="speaker_1",
                start_time=40.0,
                end_time=50.0,
                content="다 네 때문이야",
                confidence=1.0,
            ),
        ]

    def test_detector_initialization(self):
        """Test detector initialization."""
        detector = PatternDetector()
        assert detector._confidence_threshold == 0.7
        assert detector._repetition_threshold == 3

    def test_detector_custom_thresholds(self):
        """Test detector with custom thresholds."""
        detector = PatternDetector(
            confidence_threshold=0.8,
            repetition_threshold=5,
            intensity_threshold="HIGH",
            severity_threshold="HIGH",
        )
        assert detector._confidence_threshold == 0.8
        assert detector._repetition_threshold == 5

    def test_detect_gaslighting(self, sample_segments):
        """Test gaslighting detection."""
        detector = PatternDetector(confidence_threshold=0.5)
        patterns = detector.detect_gaslighting(sample_segments)

        # Should detect at least one gaslighting pattern
        assert len(patterns) >= 1

        # Check pattern types
        pattern_types = {p.pattern_type for p in patterns}
        assert len(pattern_types) > 0

    def test_detect_threats(self, sample_segments):
        """Test threat detection."""
        detector = PatternDetector(severity_threshold="LOW")
        threats = detector.detect_threats(sample_segments)

        # Should detect the threat
        assert len(threats) >= 1
        assert threats[0].speaker == "speaker_1"

    def test_detect_emotional_manipulation(self, sample_segments):
        """Test emotional manipulation detection."""
        detector = PatternDetector(intensity_threshold="LOW")
        patterns = detector.detect_emotional_manipulation(sample_segments)

        # Should detect emotional manipulation
        assert len(patterns) >= 1

    def test_add_custom_pattern(self):
        """Test adding custom patterns."""
        detector = PatternDetector()
        detector.add_custom_pattern(
            name="CUSTOM_PATTERN",
            keywords=["커스텀", "패턴"],
            pattern_type="gaslighting",
        )
        assert "CUSTOM_PATTERN" in detector._custom_patterns.get("gaslighting", {})

    def test_detect_all(self, sample_segments):
        """Test detecting all patterns."""
        transcript = Transcript(
            id="transcript-001",
            file_path=Path("/data/test.txt"),
            date=datetime(2025, 6, 15, 10, 0),
            duration_seconds=100,
            speakers=["speaker_1"],
        )
        for seg in sample_segments:
            transcript.add_segment(seg)

        detector = PatternDetector(
            confidence_threshold=0.5,
            severity_threshold="LOW",
            intensity_threshold="LOW",
        )
        evidence = detector.detect_all(transcript)

        # Should produce some evidence
        assert len(evidence) >= 1

    def test_normalize_text(self):
        """Test text normalization for comparison."""
        detector = PatternDetector()
        text1 = "Hello    World  !!!"
        text2 = "hello world"
        assert detector._normalize_text(text1) == detector._normalize_text(text2)

    def test_repeated_statements_detection(self):
        """Test detection of repeated statements."""
        detector = PatternDetector(repetition_threshold=2)

        segments = [
            Segment(
                id=f"seg-{i}",
                speaker="speaker_1",
                start_time=float(i * 10),
                end_time=float(i * 10 + 5),
                content="반복되는 말입니다",
                confidence=1.0,
            )
            for i in range(3)
        ]

        repeated = detector.detect_repeated_statements(segments, threshold=2)
        assert len(repeated) >= 1
