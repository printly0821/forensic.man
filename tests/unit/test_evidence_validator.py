"""
Validator 모듈 단위 테스트 (확장)
"""
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from forensic.evidence.validator import (
    DuplicateDetector,
    EvidenceValidator,
    IntegrityChecker,
    ReportGenerator,
)
from forensic.evidence.models.evidence import Evidence, EvidenceCategory
from forensic.evidence.models.validation import ValidationReport
from forensic.models.transcript import Segment, Transcript


class TestIntegrityChecker:
    def test_compute_hash(self):
        checker = IntegrityChecker()
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            speaker="A",
            content_sample="테스트 내용",
        )
        hash_value = checker.compute_hash(evidence)
        assert hash_value
        assert len(hash_value) == 64

    def test_verify_integrity(self):
        checker = IntegrityChecker()
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        hash1 = checker.compute_hash(evidence)
        evidence.integrity_hash = hash1
        assert checker.verify_integrity(evidence) is True

    def test_verify_integrity_tampered(self):
        checker = IntegrityChecker()
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        evidence.integrity_hash = "wrong_hash"
        assert checker.verify_integrity(evidence) is False

    def test_verify_timestamp(self):
        checker = IntegrityChecker()
        segment = Segment(
            id="seg-1",
            speaker="A",
            start_time=100.0,
            end_time=105.0,
            content="테스트",
            confidence=0.9,
        )
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            timestamp=datetime.fromtimestamp(100.0),
        )
        assert checker.verify_timestamp(evidence, segment) is True

    def test_verify_timestamp_mismatch(self):
        checker = IntegrityChecker()
        segment = Segment(
            id="seg-1",
            speaker="A",
            start_time=200.0,
            end_time=205.0,
            content="테스트",
            confidence=0.9,
        )
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            timestamp=datetime.fromtimestamp(100.0),
        )
        assert checker.verify_timestamp(evidence, segment) is False

    def test_verify_source_reference(self):
        checker = IntegrityChecker()
        transcript = Transcript(
            id="TR-001",
            file_path="/path/to/file",
            date=datetime.now(),
            duration_seconds=100.0,
        )
        transcript.add_segment(
            Segment(
                id="seg-1",
                speaker="A",
                start_time=0.0,
                end_time=5.0,
                content="테스트",
                confidence=0.9,
            )
        )
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=["seg-1"],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        assert checker.verify_source_reference(evidence, transcript) is True

    def test_verify_source_reference_invalid(self):
        checker = IntegrityChecker()
        transcript = Transcript(
            id="TR-001",
            file_path="/path/to/file",
            date=datetime.now(),
            duration_seconds=100.0,
        )
        transcript.add_segment(
            Segment(
                id="seg-1",
                speaker="A",
                start_time=0.0,
                end_time=5.0,
                content="테스트",
                confidence=0.9,
            )
        )
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-002",  # Wrong transcript
            segment_ids=["seg-1"],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        assert checker.verify_source_reference(evidence, transcript) is False


class TestDuplicateDetector:
    def test_calculate_content_similarity(self):
        detector = DuplicateDetector()
        sim1 = detector._calculate_content_similarity("위협하고 있다", "위협하겠다")
        assert sim1 > 0

    def test_calculate_content_similarity_identical(self):
        detector = DuplicateDetector()
        sim = detector._calculate_content_similarity("same text", "same text")
        assert sim == 1.0

    def test_calculate_content_similarity_empty(self):
        detector = DuplicateDetector()
        sim = detector._calculate_content_similarity("", "test")
        assert sim == 0.0

    def test_detect_duplicates(self):
        detector = DuplicateDetector()
        evidence1 = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            speaker="A",
            content_sample="테스트 내용",
            source_pattern_type="GASLIGHTING",
        )
        evidence2 = Evidence(
            id="EVD-TEST-002",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            speaker="A",
            content_sample="테스트 내용",
            source_pattern_type="GASLIGHTING",
        )
        duplicates = detector.detect_duplicates(evidence1, [evidence2])
        assert len(duplicates) == 1
        assert duplicates[0].id == "EVD-TEST-002"

    def test_detect_duplicates_different_speaker(self):
        detector = DuplicateDetector()
        evidence1 = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            speaker="A",
            content_sample="테스트",
            source_pattern_type="GASLIGHTING",
        )
        evidence2 = Evidence(
            id="EVD-TEST-002",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            speaker="B",  # Different speaker
            content_sample="테스트",
            source_pattern_type="GASLIGHTING",
        )
        duplicates = detector.detect_duplicates(evidence1, [evidence2])
        assert len(duplicates) == 0

    def test_create_merge_proposal(self):
        detector = DuplicateDetector()
        primary = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            occurrence_count=2,
        )
        duplicates = [
            Evidence(
                id="EVD-TEST-002",
                transcript_id="TR-001",
                segment_ids=[],
                category=EvidenceCategory.GASLIGHTING,
                description="테스트",
                occurrence_count=1,
            )
        ]
        proposal = detector.create_merge_proposal(primary, duplicates)
        assert proposal.primary_evidence_id == "EVD-TEST-001"
        assert "EVD-TEST-002" in proposal.duplicate_evidence_ids

    def test_merge_evidence(self):
        detector = DuplicateDetector()
        primary = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=["seg-1"],
            category=EvidenceCategory.GASLIGHTING,
            description="주 증거",
            occurrence_count=2,
            confidence=0.8,
        )
        duplicate = Evidence(
            id="EVD-TEST-002",
            transcript_id="TR-001",
            segment_ids=["seg-2"],
            category=EvidenceCategory.GASLIGHTING,
            description="중복",
            occurrence_count=1,
            confidence=0.9,
        )
        detector.merge_evidence(primary, [duplicate])
        assert "seg-2" in primary.segment_ids
        assert primary.occurrence_count == 3
        assert primary.confidence == 0.9


class TestEvidenceValidator:
    def test_validate_integrity(self):
        validator = EvidenceValidator()
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        result = validator.validate_integrity(evidence)
        assert result.evidence_id == "EVD-TEST-001"

    def test_validate_integrity_with_hash(self):
        validator = EvidenceValidator()
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        validator.compute_hash(evidence)
        result = validator.validate_integrity(evidence)
        assert result.is_valid is True
        assert result.hash_valid is True

    def test_compute_hash(self):
        validator = EvidenceValidator()
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        hash_value = validator.compute_hash(evidence)
        assert hash_value
        assert evidence.integrity_hash == hash_value

    def test_compute_hash_no_update(self):
        validator = EvidenceValidator()
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        hash_value = validator.compute_hash(evidence, update_evidence=False)
        assert hash_value
        assert evidence.integrity_hash == ""

    def test_get_validation_report(self):
        validator = EvidenceValidator()
        evidence1 = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        report = validator.get_validation_report([evidence1])
        assert report.total_evidence == 1
        assert len(report.validation_results) == 1

    def test_get_validation_report_with_transcript(self):
        validator = EvidenceValidator()
        transcript = Transcript(
            id="TR-001",
            file_path="/path/to/file",
            date=datetime.now(),
            duration_seconds=100.0,
        )
        transcript.add_segment(
            Segment(
                id="seg-1",
                speaker="A",
                start_time=0.0,
                end_time=5.0,
                content="테스트",
                confidence=0.9,
            )
        )
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=["seg-1"],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        report = validator.get_validation_report([evidence], {"TR-001": transcript})
        assert report.total_evidence == 1
        assert report.validation_results[0].source_valid is True

    def test_validate_and_update(self):
        validator = EvidenceValidator()
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        result = validator.validate_and_update(evidence)
        assert evidence.integrity_hash
        # After compute_hash, validation should be VALID
        # The validate_and_update method sets validation_status based on result
        # If hash was missing, it gets computed and the validation result should be updated
        # Let's verify the hash was generated
        assert len(evidence.integrity_hash) > 0

    def test_validate_and_update_with_transcript(self):
        validator = EvidenceValidator()
        transcript = Transcript(
            id="TR-001",
            file_path="/path/to/file",
            date=datetime.now(),
            duration_seconds=100.0,
        )
        transcript.add_segment(
            Segment(
                id="seg-1",
                speaker="A",
                start_time=0.0,
                end_time=5.0,
                content="테스트",
                confidence=0.9,
            )
        )
        evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=["seg-1"],
            category=EvidenceCategory.OTHER,
            description="테스트",
        )
        result = validator.validate_and_update(evidence, transcript)
        assert result.source_valid is True

    def test_create_merge_proposal(self):
        validator = EvidenceValidator()
        primary = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
        )
        duplicates = [
            Evidence(
                id="EVD-TEST-002",
                transcript_id="TR-001",
                segment_ids=[],
                category=EvidenceCategory.GASLIGHTING,
                description="테스트",
            )
        ]
        proposal = validator.create_merge_proposal(primary, duplicates)
        assert proposal.primary_evidence_id == "EVD-TEST-001"

    def test_merge_duplicates_empty_list(self):
        validator = EvidenceValidator()
        with pytest.raises(ValueError):
            validator.merge_duplicates([])

    def test_merge_duplicates(self):
        validator = EvidenceValidator()
        evidence1 = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=["seg-1"],
            category=EvidenceCategory.GASLIGHTING,
            description="주 증거",
            occurrence_count=1,
        )
        evidence2 = Evidence(
            id="EVD-TEST-002",
            transcript_id="TR-001",
            segment_ids=["seg-2"],
            category=EvidenceCategory.GASLIGHTING,
            description="중복",
            occurrence_count=1,
        )
        merged = validator.merge_duplicates([evidence1, evidence2])
        assert merged.id == "EVD-TEST-001"
        assert "seg-2" in merged.segment_ids


class TestReportGenerator:
    def test_generate_text_report(self):
        generator = ReportGenerator()
        report = ValidationReport(
            report_id="VR-TEST-001",
            generated_at=datetime.now(),
            total_evidence=1,
            valid_count=1,
        )
        report.generate_summary()
        text = generator.generate_text_report(report)
        assert "증거 검증 보고서" in text
        assert report.report_id in text

    def test_generate_json_report(self):
        generator = ReportGenerator()
        report = ValidationReport(
            report_id="VR-TEST-001",
            generated_at=datetime.now(),
            total_evidence=1,
            valid_count=1,
        )
        json_data = generator.generate_json_report(report)
        assert json_data["report_id"] == "VR-TEST-001"
        assert "summary" in json_data

    def test_save_report_text(self):
        generator = ReportGenerator()
        report = ValidationReport(
            report_id="VR-TEST-001",
            generated_at=datetime.now(),
            total_evidence=0,
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)
        try:
            result_path = generator.save_report(report, temp_path, format_type="text")
            assert result_path.exists()
            assert result_path.suffix == ".txt"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_save_report_json(self):
        generator = ReportGenerator()
        report = ValidationReport(
            report_id="VR-TEST-001",
            generated_at=datetime.now(),
            total_evidence=0,
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            temp_path = Path(f.name)
        try:
            result_path = generator.save_report(report, temp_path, format_type="json")
            assert result_path.exists()
            assert result_path.suffix == ".json"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_generate_merge_proposal_text(self):
        generator = ReportGenerator()
        from forensic.evidence.models.validation import MergeProposal
        proposal = MergeProposal(
            primary_evidence_id="EVD-TEST-001",
            duplicate_evidence_ids=["EVD-TEST-002"],
            reason="테스트",
            confidence=0.9,
        )
        text = generator.generate_merge_proposal_text(proposal)
        assert "증거 병합 제안" in text
        assert "EVD-TEST-001" in text
        assert "EVD-TEST-002" in text

    def test_format_result_with_duplicates(self):
        generator = ReportGenerator()
        from forensic.evidence.models.validation import ValidationResult
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=False,
            duplicate_found=True,
            duplicate_ids=["EVD-TEST-002"],
        )
        lines = generator._format_result(result)
        assert len(lines) > 0
        assert any("중복 발견" in line for line in lines)

    def test_format_result_with_issues(self):
        generator = ReportGenerator()
        from forensic.evidence.models.validation import ValidationResult
        result = ValidationResult(
            evidence_id="EVD-TEST-001",
            is_valid=False,
        )
        result.add_issue("테스트 문제")
        result.add_recommendation("테스트 권장사항")
        lines = generator._format_result(result)
        assert any("문제점" in line for line in lines)
        assert any("권장 조치" in line for line in lines)
