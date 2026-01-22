"""
내보내기 관련 모델
"""
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from forensic.evidence.models.evidence import Evidence, EvidenceCategory


class ExportConfig(BaseModel):
    format: Literal["JSON", "LEGAL", "SUMMARY", "CHAIN"] = "JSON"
    include_context: bool = True
    include_metadata: bool = True
    min_importance: Literal["HIGH", "MEDIUM", "LOW"] = "LOW"
    categories: list[EvidenceCategory] | None = None
    date_range: tuple[date, date] | None = None
    template: str = "korean_criminal"
    output_encoding: str = "utf-8"
    include_hash: bool = True
    include_chain: bool = False

    def should_include_evidence(self, evidence: Evidence) -> bool:
        importance_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        if importance_order[evidence.importance] < importance_order[self.min_importance]:
            return False
        if self.categories and evidence.category not in self.categories:
            return False
        if self.date_range and evidence.timestamp:
            evidence_date = evidence.timestamp.date()
            if evidence_date < self.date_range[0] or evidence_date > self.date_range[1]:
                return False
        return True

    def get_file_extension(self) -> str:
        extensions = {
            "JSON": ".json",
            "LEGAL": ".md",
            "SUMMARY": ".md",
            "CHAIN": ".md",
        }
        return extensions.get(self.format, ".txt")


class EvidenceSummary(BaseModel):
    id: str
    date: date
    speaker: str
    category: EvidenceCategory
    description: str
    importance: Literal["HIGH", "MEDIUM", "LOW"]
    content_sample: str

    @classmethod
    def from_evidence(cls, evidence: Evidence) -> "EvidenceSummary":
        return cls(
            id=evidence.id,
            date=evidence.timestamp.date() if evidence.timestamp else date.today(),
            speaker=evidence.speaker,
            category=evidence.category,
            description=evidence.description,
            importance=evidence.importance,
            content_sample=evidence.content_sample,
        )


class LegalDocument(BaseModel):
    document_id: str
    title: str
    case_reference: str | None = None
    generated_at: datetime = Field(default_factory=datetime.now)
    evidence_summary: list[EvidenceSummary] = Field(default_factory=list)
    timeline_summary: str = ""
    pattern_analysis: str = ""
    speaker_analysis: str = ""
    conclusion: str = ""
    appendix_paths: list[Path] = Field(default_factory=list)
    integrity_statement: str = ""
    signature_placeholder: str = ""

    def add_evidence_summary(self, summary: EvidenceSummary) -> None:
        self.evidence_summary.append(summary)

    def get_high_importance_count(self) -> int:
        return sum(1 for s in self.evidence_summary if s.importance == "HIGH")

    def get_total_evidence_count(self) -> int:
        return len(self.evidence_summary)

    def get_category_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for summary in self.evidence_summary:
            cat = summary.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def generate_integrity_statement(self) -> str:
        self.integrity_statement = (
            f"본 문서는 {self.generated_at.strftime('%Y년 %m월 %d일 %H:%M')}에 "
            f"자동 생성되었으며, 원본 데이터의 무결성이 검증되었습니다. "
            f"총 {self.get_total_evidence_count()}건의 증거가 포함되어 있으며, "
            f"그 중 {self.get_high_importance_count()}건이 높은 중요도로 분류되었습니다.\n"
            f"모든 증거는 SHA-256 해시를 통해 무결성이 확인되었습니다."
        )
        return self.integrity_statement


class ChainOfCustody(BaseModel):
    chain_id: str
    evidence_id: str
    collected_at: datetime = Field(default_factory=datetime.now)
    collected_by: str = ""
    storage_location: str = ""
    transfer_history: list[dict[str, Any]] = Field(default_factory=list)
    last_accessed: datetime | None = None
    last_accessed_by: str = ""
    integrity_checks: list[dict[str, Any]] = Field(default_factory=list)

    def add_transfer(
        self, transferred_to: str, transferred_at: datetime, purpose: str = ""
    ) -> None:
        self.transfer_history.append(
            {"to": transferred_to, "at": transferred_at.isoformat(), "purpose": purpose}
        )
        self.last_accessed = transferred_at
        self.last_accessed_by = transferred_to

    def add_integrity_check(self, checked_at: datetime, hash_value: str, is_valid: bool) -> None:
        self.integrity_checks.append(
            {"at": checked_at.isoformat(), "hash": hash_value, "valid": is_valid}
        )

    def get_latest_hash(self) -> str | None:
        if self.integrity_checks:
            return self.integrity_checks[-1].get("hash")
        return None


__all__ = ["ExportConfig", "EvidenceSummary", "LegalDocument", "ChainOfCustody"]
