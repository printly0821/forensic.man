"""
증거 체인 모델
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class EvidenceChain(BaseModel):
    chain_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    chain_type: Literal["TEMPORAL", "PATTERN", "SPEAKER", "TOPIC"] = "PATTERN"
    start_date: date
    end_date: date
    speaker: str = ""
    pattern_type: str = ""
    description: str = ""
    total_occurrences: int = 1
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, object] = Field(default_factory=dict)

    def add_evidence(self, evidence_id: str) -> None:
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)
            self.total_occurrences += 1

    def remove_evidence(self, evidence_id: str) -> bool:
        if evidence_id in self.evidence_ids:
            self.evidence_ids.remove(evidence_id)
            self.total_occurrences = max(1, self.total_occurrences - 1)
            return True
        return False

    def get_duration_days(self) -> int:
        return (self.end_date - self.start_date).days

    def is_critical(self) -> bool:
        return self.severity == "CRITICAL"

    def is_high_severity(self) -> bool:
        return self.severity == "HIGH"

    def is_temporal_chain(self) -> bool:
        return self.chain_type == "TEMPORAL"

    def is_pattern_chain(self) -> bool:
        return self.chain_type == "PATTERN"

    def is_speaker_chain(self) -> bool:
        return self.chain_type == "SPEAKER"

    def get_evidence_count(self) -> int:
        return len(self.evidence_ids)


class ChainBuilder:
    @staticmethod
    def create_temporal_chain(evidence_list, chain_id: str) -> EvidenceChain:
        if not evidence_list:
            raise ValueError("evidence_list must not be empty")
        dates = [e.timestamp.date() for e in evidence_list if e.timestamp]
        if not dates:
            from datetime import date as dt_date
            start = end = dt_date.today()
        else:
            start = min(dates)
            end = max(dates)
        speaker = evidence_list[0].speaker if evidence_list[0].speaker else ""
        pattern_type = (
            evidence_list[0].source_pattern_type
            if evidence_list[0].source_pattern_type
            else ""
        )
        severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for e in evidence_list:
            severity_counts[e.importance] += 1
        if severity_counts["HIGH"] >= 3:
            severity = "CRITICAL"
        elif severity_counts["HIGH"] >= 1:
            severity = "HIGH"
        elif severity_counts["MEDIUM"] >= 2:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        return EvidenceChain(
            chain_id=chain_id,
            evidence_ids=[e.id for e in evidence_list],
            chain_type="TEMPORAL",
            start_date=start,
            end_date=end,
            speaker=speaker,
            pattern_type=pattern_type,
            description=f"시간 기반 증거 체인 ({start} ~ {end})",
            total_occurrences=len(evidence_list),
            severity=severity,
        )

    @staticmethod
    def create_pattern_chain(evidence_list, pattern_type: str, chain_id: str) -> EvidenceChain:
        if not evidence_list:
            raise ValueError("evidence_list must not be empty")
        dates = [e.timestamp.date() for e in evidence_list if e.timestamp]
        if not dates:
            from datetime import date as dt_date
            start = end = dt_date.today()
        else:
            start = min(dates)
            end = max(dates)
        speaker = evidence_list[0].speaker if evidence_list[0].speaker else ""
        total_occurrences = sum(e.occurrence_count for e in evidence_list)
        high_count = sum(1 for e in evidence_list if e.importance == "HIGH")
        if high_count >= len(evidence_list) / 2:
            severity = "CRITICAL"
        elif high_count >= 1:
            severity = "HIGH"
        else:
            severity = "MEDIUM"
        return EvidenceChain(
            chain_id=chain_id,
            evidence_ids=[e.id for e in evidence_list],
            chain_type="PATTERN",
            start_date=start,
            end_date=end,
            speaker=speaker,
            pattern_type=pattern_type,
            description=f"{pattern_type} 패턴 기반 증거 체인",
            total_occurrences=total_occurrences,
            severity=severity,
        )


__all__ = ["EvidenceChain", "ChainBuilder"]
