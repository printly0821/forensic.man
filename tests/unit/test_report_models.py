"""
Unit tests for report models.
"""

import pytest
from datetime import date, datetime

from forensic.report.models.config import (
    LegalReportConfig,
    ReportConfig,
    SummaryReportConfig,
    TimelineReportConfig,
)
from forensic.report.models.legal import (
    Appendix,
    CaseInfo,
    CustodyRecord,
    EvidenceChainSummary,
    EvidenceSummary,
    LegalReport,
)
from forensic.report.models.report import Report, ReportMetadata, ReportSection, ReportType
from forensic.report.models.summary import (
    AnalysisOverview,
    AnalysisStatistics,
    KeyFinding,
    PatternStatistics,
    Recommendation,
    SpeakerComparison,
    SummaryReport,
)
from forensic.report.models.timeline import (
    MonthlySummary,
    PatternOccurrenceSummary,
    SpeakerActivitySummary,
    TimelineEventSummary,
    TimelineReport,
)


class TestReportModels:
    """Test basic report models."""

    def test_report_metadata(self):
        """Test ReportMetadata model."""
        metadata = ReportMetadata(
            created_by="test_user",
            version="2.0.0",
        )
        assert metadata.created_by == "test_user"
        assert metadata.version == "2.0.0"
        assert isinstance(metadata.created_at, datetime)

    def test_report_type_enum(self):
        """Test ReportType enum."""
        assert ReportType.LEGAL.value == "LEGAL"
        assert ReportType.TIMELINE.value == "TIMELINE"
        assert ReportType.SUMMARY.value == "SUMMARY"

    def test_base_report(self):
        """Test base Report model."""
        report = Report(
            id="RPT-20250101-0001",
            report_type=ReportType.LEGAL,
            title="Test Report",
        )
        assert report.id == "RPT-20250101-0001"
        assert report.report_type == ReportType.LEGAL
        assert report.title == "Test Report"


class TestConfigModels:
    """Test configuration models."""

    def test_report_config_defaults(self):
        """Test ReportConfig default values."""
        config = ReportConfig()
        assert config.output_format == "MARKDOWN"
        assert config.language == "ko"
        assert config.include_toc is True

    def test_report_config_should_include_evidence(self):
        """Test evidence filtering by importance."""
        config = ReportConfig(min_importance="HIGH")
        assert config.should_include_evidence("HIGH") is True
        assert config.should_include_evidence("MEDIUM") is False


class TestLegalReportModels:
    """Test legal report models."""

    def test_case_info(self):
        """Test CaseInfo model."""
        case_info = CaseInfo(
            case_number="2025-123",
            court_name="Seoul District Court",
            case_type="CRIMINAL",
        )
        assert case_info.case_number == "2025-123"
        assert case_info.case_type == "CRIMINAL"

    def test_evidence_summary(self):
        """Test EvidenceSummary model."""
        evidence = EvidenceSummary(
            evidence_id="EVID-001",
            category="THREAT",
            importance="HIGH",
            timestamp=datetime.now(),
            speaker="Speaker A",
            content_sample="Threatening statement",
            context_summary="Context of threat",
            source_reference="transcript-001",
        )
        assert evidence.evidence_id == "EVID-001"
        assert evidence.is_high_importance is True

    def test_legal_report(self):
        """Test LegalReport model."""
        report = LegalReport(
            id="RPT-20250101-0001",
            title="Legal Evidence Report",
        )
        assert report.report_type == ReportType.LEGAL
        assert report.total_evidence == 0


class TestTimelineReportModels:
    """Test timeline report models."""

    def test_timeline_event_summary(self):
        """Test TimelineEventSummary model."""
        event = TimelineEventSummary(
            event_id="EVENT-001",
            timestamp=datetime.now(),
            event_type="THREAT",
            description="Threatening statement",
            speaker="Speaker A",
            is_key_event=True,
        )
        assert event.event_id == "EVENT-001"
        assert event.is_key_event is True

    def test_pattern_occurrence_summary(self):
        """Test PatternOccurrenceSummary model."""
        pattern = PatternOccurrenceSummary(
            pattern_id="PATTERN-001",
            pattern_name="Gaslighting",
            pattern_type="EMOTIONAL_MANIPULATION",
            first_occurrence=date(2025, 1, 1),
            last_occurrence=date(2025, 1, 31),
            total_occurrences=10,
        )
        assert pattern.duration_days == 30
        assert pattern.is_high_frequency is True


class TestSummaryReportModels:
    """Test summary report models."""

    def test_analysis_overview(self):
        """Test AnalysisOverview model."""
        overview = AnalysisOverview(
            total_files=100,
            total_duration=3600.0,
            date_range=(date(2025, 1, 1), date(2025, 1, 31)),
            total_speakers=2,
            total_segments=500,
            analysis_date=date(2025, 1, 31),
        )
        assert overview.total_files == 100
        assert overview.duration_hours == 60.0

    def test_key_finding(self):
        """Test KeyFinding model."""
        finding = KeyFinding(
            finding_id="FIND-001",
            title="Critical Finding",
            description="Critical issue detected",
            severity="CRITICAL",
            occurrence_count=5,
        )
        assert finding.finding_id == "FIND-001"
        assert finding.is_critical is True

    def test_analysis_statistics(self):
        """Test AnalysisStatistics model."""
        stats = AnalysisStatistics(
            total_files=100,
            total_duration_minutes=3600.0,
            total_segments=500,
            total_evidence=50,
            evidence_by_importance={"HIGH": 10, "MEDIUM": 30, "LOW": 10},
        )
        assert stats.total_files == 100
        assert stats.high_importance_ratio == 0.2

    def test_speaker_comparison(self):
        """Test SpeakerComparison model."""
        comparison = SpeakerComparison(
            speakers=["Speaker A", "Speaker B"],
            segment_counts={"Speaker A": 300, "Speaker B": 200},
            evidence_involvement={"Speaker A": 20, "Speaker B": 15},
        )
        assert comparison.dominant_speaker == "Speaker A"

    def test_recommendation(self):
        """Test Recommendation model."""
        rec = Recommendation(
            recommendation_id="REC-001",
            priority="URGENT",
            title="Immediate Action Required",
            description="Take action now",
            rationale="Critical risk detected",
        )
        assert rec.recommendation_id == "REC-001"
        assert rec.is_urgent is True
