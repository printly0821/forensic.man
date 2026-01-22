"""
검증 관련 모델
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    evidence_id: str
    is_valid: bool = True
    timestamp_valid: bool = True
    source_valid: bool = True
    hash_valid: bool = True
    duplicate_found: bool = False
    duplicate_ids: list[str] = Field(default_factory=list)
    validation_time: datetime = Field(default_factory=datetime.now)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    def add_issue(self, issue: str) -> None:
        self.issues.append(issue)
        if self.is_valid:
            self.is_valid = False

    def add_recommendation(self, recommendation: str) -> None:
        self.recommendations.append(recommendation)

    def has_duplicates(self) -> bool:
        return self.duplicate_found and len(self.duplicate_ids) > 0

    def get_severity(self) -> str:
        if not self.is_valid:
            if self.hash_valid and self.source_valid:
                return "LOW"
            if self.timestamp_valid or self.source_valid:
                return "MEDIUM"
            return "HIGH"
        return "NONE"


class ValidationReport(BaseModel):
    report_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    total_evidence: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    validation_results: list[ValidationResult] = Field(default_factory=list)
    summary: str = ""
    integrity_score: float = Field(ge=0, le=1, default=1.0)

    def add_result(self, result: ValidationResult) -> None:
        self.validation_results.append(result)
        self.total_evidence += 1
        if result.is_valid:
            self.valid_count += 1
        else:
            self.invalid_count += 1
        if result.has_duplicates():
            self.duplicate_count += len(result.duplicate_ids)

    def calculate_integrity_score(self) -> float:
        if self.total_evidence == 0:
            return 1.0
        valid_score = self.valid_count / self.total_evidence
        duplicate_penalty = min(self.duplicate_count / self.total_evidence, 0.5)
        self.integrity_score = max(0.0, valid_score - duplicate_penalty)
        return self.integrity_score

    def generate_summary(self) -> str:
        if self.total_evidence == 0:
            self.summary = "검증할 증거가 없습니다."
            return self.summary
        score_percent = self.calculate_integrity_score() * 100
        self.summary = (
            f"총 {self.total_evidence}개 증거 중 "
            f"{self.valid_count}개 유효, "
            f"{self.invalid_count}개 무효, "
            f"{self.duplicate_count}개 중복 발견. "
            f"무결성 점수: {score_percent:.1f}%"
        )
        return self.summary

    def get_invalid_evidence_ids(self) -> list[str]:
        return [r.evidence_id for r in self.validation_results if not r.is_valid]

    def get_duplicate_groups(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for result in self.validation_results:
            if result.has_duplicates():
                groups[result.evidence_id] = result.duplicate_ids
        return groups


class MergeProposal(BaseModel):
    primary_evidence_id: str
    duplicate_evidence_ids: list[str] = Field(default_factory=list)
    reason: str = ""
    confidence: float = Field(ge=0, le=1, default=1.0)
    merged_description: str = ""
    merged_importance: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"

    def add_duplicate(self, evidence_id: str) -> None:
        if evidence_id not in self.duplicate_evidence_ids:
            self.duplicate_evidence_ids.append(evidence_id)

    def get_total_count(self) -> int:
        return 1 + len(self.duplicate_evidence_ids)


__all__ = ["ValidationResult", "ValidationReport", "MergeProposal"]
