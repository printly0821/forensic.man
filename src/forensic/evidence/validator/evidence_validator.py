"""
증거 검증 모듈
"""

from forensic.evidence.models.evidence import Evidence
from forensic.evidence.models.validation import (
    MergeProposal,
    ValidationReport,
    ValidationResult,
)
from forensic.evidence.validator.duplicate import DuplicateDetector
from forensic.evidence.validator.integrity import IntegrityChecker
from forensic.models.transcript import Segment, Transcript


class EvidenceValidator:
    def __init__(
        self,
        integrity_checker: IntegrityChecker | None = None,
        duplicate_detector: DuplicateDetector | None = None,
    ) -> None:
        self.integrity = integrity_checker or IntegrityChecker()
        self.duplicate = duplicate_detector or DuplicateDetector()

    def validate_integrity(self, evidence: Evidence) -> ValidationResult:
        result = ValidationResult(evidence_id=evidence.id)
        if evidence.integrity_hash:
            hash_valid = self.integrity.verify_integrity(evidence)
            result.hash_valid = hash_valid
            if not hash_valid:
                result.add_issue("무결성 해시가 일치하지 않습니다")
                result.add_recommendation("증거를 다시 생성하거나 원본을 확인하세요")
        else:
            result.hash_valid = False
            result.add_issue("무결성 해시가 없습니다")
            result.add_recommendation("compute_hash()를 호출하여 해시를 생성하세요")
        if not result.issues:
            result.is_valid = True
        return result

    def verify_timestamp(self, evidence: Evidence, original_segment: Segment) -> bool:
        return self.integrity.verify_timestamp(evidence, original_segment)

    def verify_source_reference(self, evidence: Evidence, transcript: Transcript) -> bool:
        return self.integrity.verify_source_reference(evidence, transcript)

    def compute_hash(self, evidence: Evidence, update_evidence: bool = True) -> str:
        hash_value = self.integrity.compute_hash(evidence)
        if update_evidence:
            evidence.integrity_hash = hash_value
        return hash_value

    def detect_duplicates(
        self,
        evidence: Evidence,
        existing_evidence: list[Evidence],
    ) -> list[Evidence]:
        return self.duplicate.detect_duplicates(evidence, existing_evidence)

    def merge_duplicates(self, evidence_list: list[Evidence]) -> Evidence:
        if not evidence_list:
            raise ValueError("evidence_list must not be empty")
        primary = evidence_list[0]
        duplicates = evidence_list[1:]
        return self.duplicate.merge_evidence(primary, duplicates)

    def get_validation_report(
        self,
        evidence_list: list[Evidence],
        transcripts: dict[str, Transcript] | None = None,
    ) -> ValidationReport:
        from forensic.evidence.extractor.id_generator import generate_evidence_id

        report = ValidationReport(
            report_id=f"VR-{generate_evidence_id()[4:]}",
        )

        transcripts = transcripts or {}

        for evidence in evidence_list:
            result = self.validate_integrity(evidence)

            if evidence.transcript_id in transcripts:
                transcript = transcripts[evidence.transcript_id]
                source_valid = self.verify_source_reference(evidence, transcript)
                result.source_valid = source_valid
                if not source_valid:
                    result.add_issue("원본 참조가 유효하지 않습니다")
            else:
                result.source_valid = False
                result.add_issue("원본 녹취록을 찾을 수 없습니다")

            duplicates = self.detect_duplicates(evidence, evidence_list)
            if duplicates:
                result.duplicate_found = True
                result.duplicate_ids = [d.id for d in duplicates]
                result.add_issue(f"{len(duplicates)}개의 중복 증거 발견")
                result.add_recommendation("중복 증거를 병합하는 것을 고려하세요")

            report.add_result(result)

        report.generate_summary()
        report.calculate_integrity_score()

        return report

    def validate_and_update(
        self,
        evidence: Evidence,
        transcript: Transcript | None = None,
        check_duplicates: bool = True,
        existing_evidence: list[Evidence] | None = None,
    ) -> ValidationResult:
        result = self.validate_integrity(evidence)

        if not evidence.integrity_hash:
            self.compute_hash(evidence)
            result.add_recommendation("무결성 해시가 생성되었습니다")

        if transcript:
            source_valid = self.verify_source_reference(evidence, transcript)
            result.source_valid = source_valid
            if not source_valid:
                result.add_issue("원본 참조가 유효하지 않습니다")

        if check_duplicates and existing_evidence:
            duplicates = self.detect_duplicates(evidence, existing_evidence)
            if duplicates:
                result.duplicate_found = True
                result.duplicate_ids = [d.id for d in duplicates]

        if result.is_valid and not result.duplicate_found:
            evidence.validation_status = "VALID"
        elif result.duplicate_found:
            evidence.validation_status = "PENDING"
        else:
            evidence.validation_status = "INVALID"

        return result

    def create_merge_proposal(
        self,
        primary: Evidence,
        duplicates: list[Evidence],
    ) -> MergeProposal:
        return self.duplicate.create_merge_proposal(primary, duplicates)


__all__ = ["EvidenceValidator"]
