"""
Unit tests for speech XAI and report modules.

Tests for GradCAM, SHAP explainer, and legal report generator.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import numpy as np


class TestGradCAMConfig:
    """Tests for GradCAMConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        from forensic.speech.xai.gradcam import GradCAMConfig

        assert hasattr(GradCAMConfig, "TARGET_LAYER")
        assert hasattr(GradCAMConfig, "SMOOTH_GRAD")
        assert hasattr(GradCAMConfig, "THRESHOLD_PERCENTILE")


class TestTemporalContribution:
    """Tests for TemporalContribution dataclass."""

    def test_create_contribution(self):
        """Test creating temporal contribution."""
        from forensic.speech.xai.gradcam import TemporalContribution

        contrib = TemporalContribution(
            start_time=0.0,
            end_time=1.0,
            contribution=0.85,
            importance="HIGH",
        )

        assert contrib.start_time == 0.0
        assert contrib.end_time == 1.0
        assert contrib.contribution == 0.85
        assert contrib.importance == "HIGH"


class TestSpeechGradCAM:
    """Tests for SpeechGradCAM class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.xai.gradcam import SpeechGradCAM

        gradcam = SpeechGradCAM()
        assert gradcam.model is None
        assert gradcam.target_layer == "features.8"

    def test_init_with_model(self):
        """Test initialization with model."""
        from forensic.speech.xai.gradcam import SpeechGradCAM

        mock_model = MagicMock()
        gradcam = SpeechGradCAM(model=mock_model, target_layer="custom_layer")

        assert gradcam.model == mock_model
        assert gradcam.target_layer == "custom_layer"

    def test_compute_temporal_importance_missing_file(self):
        """Test temporal importance with missing file."""
        from forensic.speech.xai.gradcam import SpeechGradCAM

        gradcam = SpeechGradCAM()

        with pytest.raises(FileNotFoundError):
            gradcam.compute_temporal_importance("/nonexistent/file.wav")

    def test_explain_prediction(self):
        """Test prediction explanation."""
        from forensic.speech.xai.gradcam import SpeechGradCAM

        gradcam = SpeechGradCAM()

        contributions = [
            Mock(start_time=0.0, end_time=1.0, contribution=0.8, importance="HIGH"),
            Mock(start_time=1.0, end_time=2.0, contribution=0.3, importance="MEDIUM"),
        ]

        explanation = gradcam.explain_prediction(
            "/fake/file.wav",
            "deepfake",
            contributions,
        )

        assert "예측: deepfake" in explanation
        assert "시간대별 기여도 분석" in explanation


class TestGradCAMAnalyzer:
    """Tests for GradCAMAnalyzer class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.xai.gradcam import GradCAMAnalyzer

        analyzer = GradCAMAnalyzer()
        assert analyzer.gradcam is not None

    def test_analyze_audio_missing_file(self):
        """Test analyze with missing file."""
        from forensic.speech.xai.gradcam import GradCAMAnalyzer

        analyzer = GradCAMAnalyzer()

        with pytest.raises(FileNotFoundError):
            analyzer.analyze_audio("/nonexistent/file.wav")

    def test_get_important_segments(self):
        """Test getting important segments."""
        from forensic.speech.xai.gradcam import (
            GradCAMAnalyzer,
            TemporalContribution,
        )

        analyzer = GradCAMAnalyzer()

        contributions = [
            TemporalContribution(0.0, 1.0, 0.9, "HIGH"),
            TemporalContribution(1.0, 2.0, 0.5, "MEDIUM"),
            TemporalContribution(2.0, 3.0, 0.3, "LOW"),
        ]

        top_2 = analyzer.get_important_segments(contributions, top_k=2)

        assert len(top_2) == 2
        assert top_2[0].contribution >= top_2[1].contribution

    def test_generate_report(self):
        """Test report generation."""
        from forensic.speech.xai.gradcam import (
            GradCAMAnalyzer,
            TemporalContribution,
        )

        analyzer = GradCAMAnalyzer()

        result = {
            "audio_file": "/fake/audio.wav",
            "contributions": [
                TemporalContribution(0.0, 1.0, 0.9, "HIGH"),
                TemporalContribution(1.0, 2.0, 0.4, "MEDIUM"),
                TemporalContribution(2.0, 3.0, 0.2, "LOW"),
            ],
            "important_regions": [
                {"start": 0.0, "end": 1.0, "score": 0.9},
            ],
            "heatmap": [0.9, 0.4, 0.2],
        }

        report = analyzer.generate_report(result)

        assert "GradCAM 분석 보고서" in report
        assert "높음 (HIGH): 1구간" in report


class TestSHAPConfig:
    """Tests for SHAPConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        from forensic.speech.xai.shap_explainer import SHAPConfig

        assert hasattr(SHAPConfig, "BACKGROUND_SAMPLES")
        assert hasattr(SHAPConfig, "MAX_FEATURES_DISPLAY")


class TestFeatureType:
    """Tests for FeatureType enum."""

    def test_all_types(self):
        """Test all feature types are defined."""
        from forensic.speech.xai.shap_explainer import FeatureType

        assert FeatureType.MFCC
        assert FeatureType.LFCC
        assert FeatureType.SPECTRAL_CENTROID
        assert FeatureType.SPECTRAL_ROLLOFF
        assert FeatureType.ZCR


class TestFeatureImportance:
    """Tests for FeatureImportance dataclass."""

    def test_create_importance(self):
        """Test creating feature importance."""
        from forensic.speech.xai.shap_explainer import (
            FeatureImportance,
            FeatureType,
        )

        importance = FeatureImportance(
            feature_name="mfcc_0",
            feature_type=FeatureType.MFCC,
            importance=0.85,
            shap_value=0.5,
            direction="positive",
        )

        assert importance.feature_name == "mfcc_0"
        assert importance.feature_type == FeatureType.MFCC
        assert importance.importance == 0.85


class TestSpeechSHAPExplainer:
    """Tests for SpeechSHAPExplainer class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.xai.shap_explainer import SpeechSHAPExplainer

        explainer = SpeechSHAPExplainer()
        assert explainer.model is None
        assert explainer.masker is None

    def test_init_with_model(self):
        """Test initialization with model."""
        from forensic.speech.xai.shap_explainer import SpeechSHAPExplainer

        mock_model = MagicMock()
        explainer = SpeechSHAPExplainer(model=mock_model)

        assert explainer.model == mock_model

    def test_infer_feature_type(self):
        """Test feature type inference."""
        from forensic.speech.xai.shap_explainer import SpeechSHAPExplainer

        explainer = SpeechSHAPExplainer()

        assert explainer._infer_feature_type("mfcc_0").value == "mfcc"
        assert explainer._infer_feature_type("lfcc_5").value == "lfcc"
        assert explainer._infer_feature_type("spectral_centroid").value == "spectral_centroid"
        assert explainer._infer_feature_type("unknown").value == "mfcc"  # default

    def test_get_feature_importance(self):
        """Test getting feature importance."""
        from forensic.speech.xai.shap_explainer import SpeechSHAPExplainer

        explainer = SpeechSHAPExplainer()

        shap_values = np.array([
            [0.5, -0.3, 0.2],
            [0.4, 0.1, -0.1],
        ])
        feature_names = ["mfcc_0", "lfcc_0", "energy"]

        importance = explainer.get_feature_importance(shap_values, feature_names)

        assert len(importance) == 3
        assert importance[0].feature_name == "mfcc_0"


class TestFeatureImportanceAnalyzer:
    """Tests for FeatureImportanceAnalyzer class."""

    def test_init(self):
        """Test initialization."""
        from forensic.speech.xai.shap_explainer import FeatureImportanceAnalyzer

        analyzer = FeatureImportanceAnalyzer()
        assert analyzer.shap_explainer is not None

    def test_analyze_audio_missing_file(self):
        """Test analyze with missing file."""
        from forensic.speech.xai.shap_explainer import FeatureImportanceAnalyzer

        analyzer = FeatureImportanceAnalyzer()

        with pytest.raises(FileNotFoundError):
            analyzer.analyze_audio("/nonexistent/file.wav")

    def test_get_top_features(self):
        """Test getting top features."""
        from forensic.speech.xai.shap_explainer import (
            FeatureImportanceAnalyzer,
            FeatureImportance,
            FeatureType,
        )

        analyzer = FeatureImportanceAnalyzer()

        explanation = {
            "feature_importance": [
                FeatureImportance("mfcc_0", FeatureType.MFCC, 0.9, 0.5, "positive"),
                FeatureImportance("lfcc_0", FeatureType.LFCC, 0.5, 0.2, "positive"),
                FeatureImportance("energy", FeatureType.ENERGY, 0.3, 0.1, "negative"),
            ],
        }

        top_2 = analyzer.get_top_features(explanation, top_k=2)

        assert len(top_2) == 2
        assert top_2[0].importance >= top_2[1].importance

    def test_generate_report(self):
        """Test report generation."""
        from forensic.speech.xai.shap_explainer import (
            FeatureImportanceAnalyzer,
            FeatureImportance,
            FeatureType,
        )

        analyzer = FeatureImportanceAnalyzer()

        explanation = {
            "audio_file": "/fake/audio.wav",
            "feature_importance": [
                FeatureImportance("mfcc_0", FeatureType.MFCC, 0.9, 0.5, "positive"),
                FeatureImportance("lfcc_0", FeatureType.LFCC, 0.5, 0.2, "positive"),
            ],
        }

        report = analyzer.generate_report(explanation)

        assert "특징 중요도 분석 보고서" in report
        assert "주요 특징" in report


class TestReportStandard:
    """Tests for ReportStandard enum."""

    def test_all_standards(self):
        """Test all report standards are defined."""
        from forensic.speech.report.legal import ReportStandard

        assert ReportStandard.DAUBERT
        assert ReportStandard.FRYE
        assert ReportStandard.ISO_17025


class TestEvidenceType:
    """Tests for EvidenceType enum."""

    def test_all_types(self):
        """Test all evidence types are defined."""
        from forensic.speech.report.legal import EvidenceType

        assert EvidenceType.AUDIO_AUTHENTICITY
        assert EvidenceType.SPEAKER_IDENTIFICATION
        assert EvidenceType.EMOTIONAL_STATE
        assert EvidenceType.MANIPULATION_DETECTION
        assert EvidenceType.DEEPFAKE_DETECTION


class TestChainOfCustody:
    """Tests for ChainOfCustody dataclass."""

    def test_create_custody(self):
        """Test creating chain of custody."""
        from forensic.speech.report.legal import ChainOfCustody

        custody = ChainOfCustody(
            evidence_id="ev_001",
            collected_at=datetime.now(),
            collected_by="Officer Smith",
            current_custodian="Dr. Analyst",
            custody_transfers=[],
            integrity_checksums=[],
        )

        assert custody.evidence_id == "ev_001"
        assert custody.collected_by == "Officer Smith"


class TestMethodologySection:
    """Tests for MethodologySection dataclass."""

    def test_create_methodology(self):
        """Test creating methodology section."""
        from forensic.speech.report.legal import MethodologySection

        method = MethodologySection(
            name="Speech Transcription",
            description="Using faster-whisper",
            parameters={"model": "large-v3"},
            validation_reference="IEEE ICASSP 2023",
            error_rate=0.05,
            peer_reviewed=True,
        )

        assert method.name == "Speech Transcription"
        assert method.peer_reviewed is True


class TestLegalReportGenerator:
    """Tests for LegalReportGenerator class."""

    def test_init_default(self):
        """Test default initialization."""
        from forensic.speech.report.legal import (
            LegalReportGenerator,
            ReportStandard,
        )

        generator = LegalReportGenerator()

        assert generator.standard == ReportStandard.DAUBERT
        assert "Analyst" in generator.expert_name

    def test_init_custom(self):
        """Test initialization with custom parameters."""
        from forensic.speech.report.legal import (
            LegalReportGenerator,
            ReportStandard,
        )

        generator = LegalReportGenerator(
            standard=ReportStandard.FRYE,
            expert_name="Dr. Expert",
            organization="Forensic Lab Inc.",
        )

        assert generator.standard == ReportStandard.FRYE
        assert generator.expert_name == "Dr. Expert"
        assert generator.organization == "Forensic Lab Inc."

    def test_create_chain_of_custody(self):
        """Test chain of custody creation."""
        from forensic.speech.report.legal import LegalReportGenerator

        generator = LegalReportGenerator()

        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            custody = generator.create_chain_of_custody(
                tmp_path,
                "Officer Smith",
                "CASE-001",
            )

            assert "CASE-001" in custody.evidence_id
            assert custody.collected_by == "Officer Smith"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_calculate_checksum(self):
        """Test checksum calculation."""
        from forensic.speech.report.legal import LegalReportGenerator

        generator = LegalReportGenerator()

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            checksum = generator.calculate_checksum(tmp_path)

            assert isinstance(checksum, str)
            assert len(checksum) == 64  # SHA-256 hex length
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_generate_report(self):
        """Test report generation."""
        from forensic.speech.report.legal import LegalReportGenerator
        from forensic.models.speech import AnalysisResults

        generator = LegalReportGenerator()

        results = AnalysisResults(audio_id="audio_001")

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(b"RIFF" + b"\x00" * 36 + b"WAVE")
            audio_path = tmp.name

        try:
            report = generator.generate_report(
                results,
                audio_path,
                "CASE-001",
            )

            assert "법의학 음성 분석 보고서" in report
            assert "CASE-001" in report
        finally:
            Path(audio_path).unlink(missing_ok=True)

    def test_header_section(self):
        """Test header section generation."""
        from forensic.speech.report.legal import LegalReportGenerator

        generator = LegalReportGenerator(expert_name="Dr. Test")

        header = generator._header_section("CASE-001", Path("/fake/audio.wav"))

        assert "CASE-001" in header
        assert "Dr. Test" in header
        assert "audio.wav" in header

    def test_executive_summary(self):
        """Test executive summary generation."""
        from forensic.speech.report.legal import LegalReportGenerator
        from forensic.models.speech import (
            AnalysisResults,
            SpeechSegment,
            DiarizationSegment,
            GaslightingIndicator,
            GaslightingType,
            AuthenticityScore,
        )

        generator = LegalReportGenerator()

        results = AnalysisResults(
            audio_id="audio_001",
            segments=[
                SpeechSegment(
                    id="seg_001",
                    start_time=0.0,
                    end_time=5.0,
                    text="Hello",
                )
            ],
            diarization=[
                DiarizationSegment(
                    id="dia_001",
                    start_time=0.0,
                    end_time=5.0,
                    speaker_id="spk_1",
                )
            ],
            gaslighting=[
                GaslightingIndicator(
                    segment_id="seg_001",
                    type=GaslightingType.DENIAL,
                )
            ],
            authenticity=AuthenticityScore(
                audio_id="audio_001",
                score=85.0,
                explanation="Authentic",
                deepfake_probability=0.15,
            ),
        )

        summary = generator._executive_summary(results)

        assert "화자 수: 1명" in summary
        assert "가스라이팅 패턴: 1건" in summary

    def test_generate_report_with_output(self):
        """Test report generation with file output."""
        from forensic.speech.report.legal import LegalReportGenerator
        from forensic.models.speech import AnalysisResults

        generator = LegalReportGenerator()

        results = AnalysisResults(audio_id="audio_001")

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_tmp:
            audio_tmp.write(b"RIFF" + b"\x00" * 36 + b"WAVE")
            audio_path = audio_tmp.name

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as report_tmp:
            report_path = report_tmp.name

        try:
            generator.generate_report(
                results,
                audio_path,
                "CASE-001",
                output_path=report_path,
            )

            assert Path(report_path).exists()

            content = Path(report_path).read_text()
            assert "법의학 음성 분석 보고서" in content
        finally:
            Path(audio_path).unlink(missing_ok=True)
            Path(report_path).unlink(missing_ok=True)

    @pytest.mark.skip(reason="Requires python-docx")
    def test_generate_word_document(self):
        """Test Word document generation."""
        from forensic.speech.report.legal import LegalReportGenerator
        from forensic.models.speech import AnalysisResults

        generator = LegalReportGenerator()

        results = AnalysisResults(audio_id="audio_001")

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_tmp:
            audio_tmp.write(b"RIFF" + b"\x00" * 36 + b"WAVE")
            audio_path = audio_tmp.name

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as doc_tmp:
            doc_path = doc_tmp.name

        try:
            generator.generate_word_document(
                results,
                audio_path,
                "CASE-001",
                doc_path,
            )

            assert Path(doc_path).exists()
        finally:
            Path(audio_path).unlink(missing_ok=True)
            Path(doc_path).unlink(missing_ok=True)
