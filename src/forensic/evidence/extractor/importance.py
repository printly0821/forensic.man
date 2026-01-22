"""
증거 중요도 할당 모듈
"""

from typing import Literal

from forensic.evidence.models.evidence import Evidence


class ImportanceAssigner:
    HIGH_THRESHOLD = 3
    MEDIUM_THRESHOLD = 1
    CRITICAL_PATTERNS = [
        "EXPLICIT_THREAT",
        "FINANCIAL_THREAT",
        "VIOLENCE_THREAT",
        "DIRECT_THREAT",
    ]
    HIGH_IMPORTANCE_PATTERNS = [
        "GASLIGHTING",
        "EMOTIONAL_MANIPULATION",
        "COERCION",
        "INTIMIDATION",
        "VERBAL_ABUSE",
    ]

    def __init__(
        self,
        high_threshold: int = 3,
        critical_patterns: list[str] | None = None,
        high_patterns: list[str] | None = None,
    ) -> None:
        self.high_threshold = high_threshold
        self.critical_patterns = critical_patterns or self.CRITICAL_PATTERNS
        self.high_patterns = high_patterns or self.HIGH_IMPORTANCE_PATTERNS

    def assign_importance(
        self,
        occurrence_count: int,
        pattern_type: str,
        severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM",
        confidence: float = 1.0,
    ) -> Literal["HIGH", "MEDIUM", "LOW"]:
        if pattern_type in self.critical_patterns or severity == "CRITICAL":
            return "HIGH"
        if confidence < 0.5:
            if occurrence_count >= self.high_threshold:
                return "MEDIUM"
            return "LOW"
        if occurrence_count >= self.high_threshold:
            return "HIGH"
        if occurrence_count >= self.MEDIUM_THRESHOLD and (
            pattern_type in self.high_patterns or severity in ("HIGH", "MEDIUM")
        ):
            return "MEDIUM"
        return "LOW"

    def assign_for_evidence(
        self,
        evidence: "Evidence",
        severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM",
    ) -> Literal["HIGH", "MEDIUM", "LOW"]:
        importance = self.assign_importance(
            occurrence_count=evidence.occurrence_count,
            pattern_type=evidence.source_pattern_type,
            severity=severity,
            confidence=evidence.confidence,
        )
        evidence.importance = importance
        return importance

    def upgrade_importance(self, evidence: "Evidence") -> bool:
        old_importance = evidence.importance
        if old_importance == "HIGH":
            return False
        if evidence.occurrence_count >= self.high_threshold:
            evidence.importance = "HIGH"
        elif evidence.importance == "LOW":
            evidence.importance = "MEDIUM"
        return old_importance != evidence.importance


_default_assigner: ImportanceAssigner | None = None


def get_importance_assigner() -> ImportanceAssigner:
    global _default_assigner
    if _default_assigner is None:
        _default_assigner = ImportanceAssigner()
    return _default_assigner


def assign_importance(
    occurrence_count: int,
    pattern_type: str,
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM",
    confidence: float = 1.0,
) -> Literal["HIGH", "MEDIUM", "LOW"]:
    return get_importance_assigner().assign_importance(
        occurrence_count, pattern_type, severity, confidence
    )


__all__ = ["ImportanceAssigner", "get_importance_assigner", "assign_importance"]
