"""
Evidence 확장 모델
"""
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceCategory(str, Enum):
    GASLIGHTING = "GASLIGHTING"
    EMOTIONAL_MANIPULATION = "EMOTIONAL_MANIPULATION"
    THREAT = "THREAT"
    REPEATED_ABUSE = "REPEATED_ABUSE"
    DENIAL = "DENIAL"
    ISOLATION = "ISOLATION"
    FINANCIAL_ABUSE = "FINANCIAL_ABUSE"
    OTHER = "OTHER"


class ExtendedEvidence(BaseModel):
    id: str
    transcript_id: str
    segment_ids: list[str] = Field(default_factory=list)
    category: EvidenceCategory
    description: str
    importance: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    context_before: str = ""
    context_after: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    source_pattern_type: str = ""
    source_pattern_id: str = ""
    speaker: str = ""
    target: str | None = None
    timestamp: datetime | None = None
    content_sample: str = ""
    occurrence_count: int = 1
    confidence: float = Field(default=1.0)
    integrity_hash: str = ""
    related_evidence_ids: list[str] = Field(default_factory=list)
    validation_status: Literal["VALID", "INVALID", "PENDING"] = "PENDING"
    export_status: Literal["NOT_EXPORTED", "EXPORTED", "MODIFIED"] = "NOT_EXPORTED"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_high_importance(self) -> bool:
        return self.importance == "HIGH"

    def is_medium_importance(self) -> bool:
        return self.importance == "MEDIUM"

    def is_low_importance(self) -> bool:
        return self.importance == "LOW"

    def is_validated(self) -> bool:
        return self.validation_status == "VALID"

    def is_exported(self) -> bool:
        return self.export_status == "EXPORTED"

    def add_related_evidence(self, evidence_id: str) -> None:
        if evidence_id not in self.related_evidence_ids:
            self.related_evidence_ids.append(evidence_id)


Evidence = ExtendedEvidence


def create_evidence(
    transcript_id: str,
    segment_ids: list[str],
    category: EvidenceCategory,
    description: str,
    speaker: str = "",
    content_sample: str = "",
    importance: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM",
    pattern_type: str = "",
    pattern_id: str = "",
) -> Evidence:
    from forensic.evidence.extractor.id_generator import generate_evidence_id
    evidence_id = generate_evidence_id()
    return Evidence(
        id=evidence_id,
        transcript_id=transcript_id,
        segment_ids=segment_ids,
        category=category,
        description=description,
        speaker=speaker,
        content_sample=content_sample,
        importance=importance,
        source_pattern_type=pattern_type,
        source_pattern_id=pattern_id,
        timestamp=datetime.now(),
    )


__all__ = ["EvidenceCategory", "ExtendedEvidence", "Evidence", "create_evidence"]
