"""
Models 모듈 단위 테스트 (확장)
"""
import pytest
from datetime import datetime, date

from forensic.evidence.models.evidence import Evidence, EvidenceCategory, create_evidence
from forensic.evidence.models.validation import (
    ValidationResult,
    ValidationReport,
    MergeProposal,
)
from forensic.evidence.models.chain import (
    EvidenceChain,
    ChainBuilder,
)
from forensic.evidence.models.export import (
    ExportConfig,
    LegalDocument,
    EvidenceSummary,
    ChainOfCustody,
)


class TestEvidenceCategory:
    def test_category_values(self):
        assert EvidenceCategory.GASLIGHTING == "GASLIGHTING"
        assert EvidenceCategory.THREAT == "THREAT"
        assert EvidenceCategory.EMOTIONAL_MANIPULATION == "EMOTIONAL_MANIPULATION"
        assert EvidenceCategory.REPEATED_ABUSE == "REPEATED_ABUSE"
        assert EvidenceCategory.DENIAL == "DENIAL"
        assert EvidenceCategory.ISOLATION == "ISOLATION"
        assert EvidenceCategory.FINANCIAL_ABUSE == "FINANCIAL_ABUSE"
        assert EvidenceCategory.OTHER == "OTHER"


class TestEvidence:
    def test_create_evidence_factory(self):
        evidence = create_evidence(
            transcript_id="TR-001",
            segment_ids=["seg-1"],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            speaker="A",
            content_sample="테스트 내용",
        )
        assert evidence.transcript_id == "TR-001"
        assert evidence.category == EvidenceCategory.GASLIGHTING
        assert evidence.description == "테스트"

    def test_add_related_evidence(self):
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        evidence.add_related_evidence("EVD-TEST-002")
        assert "EVD-TEST-002" in evidence.related_evidence_ids

    def test_add_related_evidence_duplicate(self):
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        evidence.add_related_evidence("EVD-TEST-002")
        evidence.add_related_evidence("EVD-TEST-002")
        assert evidence.related_evidence_ids.count("EVD-TEST-002") == 1

    def test_is_high_importance(self):
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            importance="HIGH",
        )
        assert evidence.is_high_importance() is True
        assert evidence.is_medium_importance() is False
        assert evidence.is_low_importance() is False

    def test_is_medium_importance(self):
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            importance="MEDIUM",
        )
        assert evidence.is_medium_importance() is True

    def test_is_low_importance(self):
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            importance="LOW",
        )
        assert evidence.is_low_importance() is True

    def test_is_validated(self):
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            validation_status="VALID",
        )
        assert evidence.is_validated() is True

    def test_is_exported(self):
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            export_status="EXPORTED",
        )
        assert evidence.is_exported() is True


class TestValidationResult:
    def test_validation_result_creation(self):
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=True,
        )
        assert result.evidence_id == "EVD-TEST-001"
        assert result.is_valid is True

    def test_add_issue(self):
        result = ValidationResult(evidence_id="EVD-TEST-001")
        result.add_issue("테스트 문제")
        assert result.is_valid is False
        assert "테스트 문제" in result.issues

    def test_add_recommendation(self):
        result = ValidationResult(evidence_id="EVD-TEST-001")
        result.add_recommendation("테스트 권장사항")
        assert "테스트 권장사항" in result.recommendations

    def test_has_duplicates(self):
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            duplicate_found=True,
            duplicate_ids=["EVD-TEST-002"],
        )
        assert result.has_duplicates() is True

    def test_get_severity_none(self):
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=True,
        )
        assert result.get_severity() == "NONE"

    def test_get_severity_low(self):
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=False,
            hash_valid=True,
            source_valid=True,
        )
        assert result.get_severity() == "LOW"

    def test_get_severity_medium(self):
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=False,
            hash_valid=False,
            source_valid=True,
        )
        assert result.get_severity() == "MEDIUM"

    def test_get_severity_high(self):
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=False,
            hash_valid=False,
            source_valid=False,
            timestamp_valid=False,  # Also need to set this to False
        )
        assert result.get_severity() == "HIGH"


class TestValidationReport:
    def test_validation_report_creation(self):
        report = ValidationReport(
            report_id="VR-TEST-001",
        )
        assert report.report_id == "VR-TEST-001"
        assert report.total_evidence == 0

    def test_add_result(self):
        report = ValidationReport(report_id="VR-TEST-001")
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=True,
        )
        report.add_result(result)
        assert report.total_evidence == 1
        assert report.valid_count == 1

    def test_add_result_invalid(self):
        report = ValidationReport(report_id="VR-TEST-001")
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=False,
        )
        report.add_result(result)
        assert report.invalid_count == 1

    def test_add_result_with_duplicates(self):
        report = ValidationReport(report_id="VR-TEST-001")
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=True,
            duplicate_found=True,
            duplicate_ids=["EVD-TEST-002", "EVD-TEST-003"],
        )
        report.add_result(result)
        assert report.duplicate_count == 2

    def test_calculate_integrity_score(self):
        report = ValidationReport(report_id="VR-TEST-001")
        result1 = ValidationResult(evidence_id="EVD-TEST-001", is_valid=True)
        result2 = ValidationResult(evidence_id="EVD-TEST-002", is_valid=True)
        report.add_result(result1)
        report.add_result(result2)
        score = report.calculate_integrity_score()
        assert score == 1.0

    def test_calculate_integrity_score_with_duplicates(self):
        report = ValidationReport(report_id="VR-TEST-001")
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=True,
            duplicate_found=True,
            duplicate_ids=["EVD-TEST-002"],
        )
        report.add_result(result)
        score = report.calculate_integrity_score()
        assert score < 1.0

    def test_generate_summary(self):
        report = ValidationReport(report_id="VR-TEST-001")
        result = ValidationResult(evidence_id="EVD-TEST-001", is_valid=True)
        report.add_result(result)
        summary = report.generate_summary()
        assert "총 1개 증거" in summary
        assert "1개 유효" in summary

    def test_generate_summary_empty(self):
        report = ValidationReport(report_id="VR-TEST-001")
        summary = report.generate_summary()
        assert "검증할 증거가 없습니다" in summary

    def test_get_invalid_evidence_ids(self):
        report = ValidationReport(report_id="VR-TEST-001")
        result1 = ValidationResult(evidence_id="EVD-TEST-001", is_valid=True)
        result2 = ValidationResult(evidence_id="EVD-TEST-002", is_valid=False)
        report.add_result(result1)
        report.add_result(result2)
        invalid_ids = report.get_invalid_evidence_ids()
        assert "EVD-TEST-002" in invalid_ids
        assert "EVD-TEST-001" not in invalid_ids

    def test_get_duplicate_groups(self):
        report = ValidationReport(report_id="VR-TEST-001")
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=True,
            duplicate_found=True,
            duplicate_ids=["EVD-TEST-002"],
        )
        report.add_result(result)
        groups = report.get_duplicate_groups()
        assert "EVD-TEST-001" in groups
        assert groups["EVD-TEST-001"] == ["EVD-TEST-002"]


class TestEvidenceChain:
    def test_chain_creation(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=["EVD-001", "EVD-002"],
            chain_type="TEMPORAL",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        assert chain.chain_id == "CHN-202501-001"
        assert len(chain.evidence_ids) == 2
        assert chain.chain_type == "TEMPORAL"

    def test_add_evidence(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=[],
            chain_type="PATTERN",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        chain.add_evidence("EVD-001")
        assert "EVD-001" in chain.evidence_ids

    def test_remove_evidence(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=["EVD-001", "EVD-002"],
            chain_type="PATTERN",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        chain.remove_evidence("EVD-001")
        assert "EVD-001" not in chain.evidence_ids
        assert "EVD-002" in chain.evidence_ids

    def test_get_duration_days(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=[],
            chain_type="TEMPORAL",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        duration = chain.get_duration_days()
        assert duration == 30

    def test_is_temporal_chain(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=[],
            chain_type="TEMPORAL",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        assert chain.is_temporal_chain() is True

    def test_is_pattern_chain(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=[],
            chain_type="PATTERN",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        assert chain.is_pattern_chain() is True

    def test_is_speaker_chain(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=[],
            chain_type="SPEAKER",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        assert chain.is_speaker_chain() is True

    def test_is_critical(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=[],
            chain_type="TEMPORAL",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            severity="CRITICAL",
        )
        assert chain.is_critical() is True

    def test_is_high_severity(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=[],
            chain_type="TEMPORAL",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            severity="HIGH",
        )
        assert chain.is_high_severity() is True

    def test_get_evidence_count(self):
        chain = EvidenceChain(
            chain_id="CHN-202501-001",
            evidence_ids=["EVD-001", "EVD-002", "EVD-003"],
            chain_type="TEMPORAL",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        assert chain.get_evidence_count() == 3

    def test_chain_builder_create_temporal_chain(self):
        evidence1 = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            speaker="A",
            source_pattern_type="GASLIGHTING",
            timestamp=datetime.now(),
            importance="HIGH",
        )
        evidence2 = Evidence(
            id="EVD-002",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            speaker="A",
            source_pattern_type="GASLIGHTING",
            timestamp=datetime.now(),
            importance="HIGH",
        )
        chain = ChainBuilder.create_temporal_chain([evidence1, evidence2], "CHN-001")
        assert chain.chain_type == "TEMPORAL"
        assert len(chain.evidence_ids) == 2

    def test_chain_builder_empty_list_raises(self):
        with pytest.raises(ValueError):
            ChainBuilder.create_temporal_chain([], "CHN-001")


class TestChainOfCustody:
    def test_chain_of_custody_creation(self):
        chain = ChainOfCustody(
            chain_id="COC-001",
            evidence_id="EVD-001",
            collected_by="SYSTEM",
        )
        assert chain.chain_id == "COC-001"
        assert chain.evidence_id == "EVD-001"

    def test_add_transfer(self):
        chain = ChainOfCustody(
            chain_id="COC-001",
            evidence_id="EVD-001",
            collected_by="SYSTEM",
        )
        chain.add_transfer(
            transferred_to="USER_A",
            transferred_at=datetime.now(),
            purpose="검사 할당",
        )
        assert len(chain.transfer_history) == 1
        assert chain.transfer_history[0]["to"] == "USER_A"

    def test_add_integrity_check(self):
        chain = ChainOfCustody(
            chain_id="COC-001",
            evidence_id="EVD-001",
        )
        chain.add_integrity_check(
            checked_at=datetime.now(),
            hash_value="abc123",
            is_valid=True,
        )
        assert len(chain.integrity_checks) == 1
        assert chain.get_latest_hash() == "abc123"

    def test_get_latest_hash_none(self):
        chain = ChainOfCustody(
            chain_id="COC-001",
            evidence_id="EVD-001",
        )
        assert chain.get_latest_hash() is None


class TestExportConfig:
    def test_should_include_by_importance(self):
        config = ExportConfig(min_importance="HIGH")
        evidence = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            importance="HIGH",
        )
        assert config.should_include_evidence(evidence) is True
        evidence2 = Evidence(
            id="EVD-002",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            importance="MEDIUM",
        )
        assert config.should_include_evidence(evidence2) is False

    def test_should_include_by_category(self):
        config = ExportConfig(
            categories=[EvidenceCategory.GASLIGHTING, EvidenceCategory.THREAT]
        )
        evidence1 = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
        )
        evidence2 = Evidence(
            id="EVD-002",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        assert config.should_include_evidence(evidence1) is True
        assert config.should_include_evidence(evidence2) is False

    def test_get_file_extension(self):
        assert ExportConfig(format="JSON").get_file_extension() == ".json"
        assert ExportConfig(format="LEGAL").get_file_extension() == ".md"
        assert ExportConfig(format="CHAIN").get_file_extension() == ".md"
        assert ExportConfig(format="SUMMARY").get_file_extension() == ".md"


class TestMergeProposal:
    def test_merge_proposal_creation(self):
        proposal = MergeProposal(
            primary_evidence_id="EVD-001",
            duplicate_evidence_ids=["EVD-002", "EVD-003"],
            reason="중복 탐지",
            confidence=0.9,
            merged_importance="HIGH",
        )
        assert proposal.primary_evidence_id == "EVD-001"
        assert len(proposal.duplicate_evidence_ids) == 2

    def test_add_duplicate(self):
        proposal = MergeProposal(
            primary_evidence_id="EVD-001",
        )
        proposal.add_duplicate("EVD-002")
        assert "EVD-002" in proposal.duplicate_evidence_ids

    def test_add_duplicate_no_duplicate(self):
        proposal = MergeProposal(
            primary_evidence_id="EVD-001",
            duplicate_evidence_ids=["EVD-002"],
        )
        proposal.add_duplicate("EVD-002")
        assert proposal.duplicate_evidence_ids.count("EVD-002") == 1

    def test_get_total_count(self):
        proposal = MergeProposal(
            primary_evidence_id="EVD-001",
            duplicate_evidence_ids=["EVD-002", "EVD-003"],
        )
        assert proposal.get_total_count() == 3


class TestEvidenceSummary:
    def test_from_evidence(self):
        evidence = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            speaker="A",
            timestamp=datetime.now(),
            importance="HIGH",
            content_sample="테스트 내용",
        )
        summary = EvidenceSummary.from_evidence(evidence)
        assert summary.id == "EVD-001"
        assert summary.category == EvidenceCategory.GASLIGHTING


class TestLegalDocument:
    def test_legal_document_creation(self):
        doc = LegalDocument(
            document_id="DOC-001",
            title="테스트 문서",
        )
        assert doc.document_id == "DOC-001"
        assert doc.title == "테스트 문서"

    def test_add_evidence_summary(self):
        doc = LegalDocument(
            document_id="DOC-001",
            title="테스트 문서",
        )
        evidence = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            timestamp=datetime.now(),
            importance="HIGH",
            content_sample="테스트",
        )
        summary = EvidenceSummary.from_evidence(evidence)
        doc.add_evidence_summary(summary)
        assert len(doc.evidence_summary) == 1

    def test_get_high_importance_count(self):
        doc = LegalDocument(
            document_id="DOC-001",
            title="테스트 문서",
        )
        evidence1 = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            timestamp=datetime.now(),
            importance="HIGH",
            content_sample="테스트",
        )
        evidence2 = Evidence(
            id="EVD-002",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            timestamp=datetime.now(),
            importance="MEDIUM",
            content_sample="테스트",
        )
        doc.add_evidence_summary(EvidenceSummary.from_evidence(evidence1))
        doc.add_evidence_summary(EvidenceSummary.from_evidence(evidence2))
        assert doc.get_high_importance_count() == 1

    def test_get_total_evidence_count(self):
        doc = LegalDocument(
            document_id="DOC-001",
            title="테스트 문서",
        )
        assert doc.get_total_evidence_count() == 0
        evidence = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            timestamp=datetime.now(),
            content_sample="테스트",
        )
        doc.add_evidence_summary(EvidenceSummary.from_evidence(evidence))
        assert doc.get_total_evidence_count() == 1

    def test_get_category_counts(self):
        doc = LegalDocument(
            document_id="DOC-001",
            title="테스트 문서",
        )
        evidence1 = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            timestamp=datetime.now(),
            content_sample="테스트",
        )
        evidence2 = Evidence(
            id="EVD-002",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            timestamp=datetime.now(),
            content_sample="테스트",
        )
        doc.add_evidence_summary(EvidenceSummary.from_evidence(evidence1))
        doc.add_evidence_summary(EvidenceSummary.from_evidence(evidence2))
        counts = doc.get_category_counts()
        assert counts.get("GASLIGHTING") == 2

    def test_generate_integrity_statement(self):
        doc = LegalDocument(
            document_id="DOC-001",
            title="테스트 문서",
        )
        evidence = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            timestamp=datetime.now(),
            importance="HIGH",
            content_sample="테스트",
        )
        doc.add_evidence_summary(EvidenceSummary.from_evidence(evidence))
        statement = doc.generate_integrity_statement()
        assert "무결성이 검증" in statement
        assert "1건" in statement
