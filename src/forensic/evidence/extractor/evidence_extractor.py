"""
증거 추출기 모듈
"""
from typing import Literal

from forensic.evidence.extractor.categorizer import EvidenceCategorizer, get_categorizer
from forensic.evidence.extractor.id_generator import generate_evidence_id
from forensic.evidence.extractor.importance import ImportanceAssigner, get_importance_assigner
from forensic.evidence.models.evidence import Evidence, EvidenceCategory, create_evidence
from forensic.models.transcript import Segment, Transcript


class PatternMatch:
    def __init__(
        self,
        pattern_id: str,
        pattern_type: str,
        segment_ids: list[str],
        severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM",
        confidence: float = 1.0,
        description: str = "",
        target: str | None = None,
    ) -> None:
        self.pattern_id = pattern_id
        self.pattern_type = pattern_type
        self.segment_ids = segment_ids
        self.severity = severity
        self.confidence = confidence
        self.description = description
        self.target = target


class EvidenceExtractor:
    def __init__(
        self,
        categorizer: EvidenceCategorizer | None = None,
        importance_assigner: ImportanceAssigner | None = None,
    ) -> None:
        self.categorizer = categorizer or get_categorizer()
        self.importance_assigner = importance_assigner or get_importance_assigner()

    def extract_from_pattern(
        self,
        pattern: PatternMatch,
        segments: list[Segment],
        transcript: Transcript | None = None,
    ) -> Evidence:
        if not segments:
            return create_evidence(
                transcript_id=transcript.id if transcript else "",
                segment_ids=[],
                category=EvidenceCategory.OTHER,
                description=pattern.description or f"{pattern.pattern_type} 패턴 탐지",
                importance="MEDIUM",
            )

        speaker = segments[0].speaker
        content_sample = " ".join(s.content for s in segments[:2])
        occurrence_count = len(pattern.segment_ids)

        category = self.categorizer.categorize(
            pattern_type=pattern.pattern_type,
            content=content_sample,
        )

        importance = self.importance_assigner.assign_importance(
            occurrence_count=occurrence_count,
            pattern_type=pattern.pattern_type,
            severity=pattern.severity,
            confidence=pattern.confidence,
        )

        description = pattern.description or f"{pattern.pattern_type} 패턴 탐지"
        transcript_id = transcript.id if transcript else ""

        evidence = create_evidence(
            transcript_id=transcript_id,
            segment_ids=pattern.segment_ids,
            category=category,
            description=description,
            speaker=speaker,
            content_sample=content_sample,
            importance=importance,
            pattern_type=pattern.pattern_type,
            pattern_id=pattern.pattern_id,
        )

        if pattern.target:
            evidence.target = pattern.target
        evidence.confidence = pattern.confidence
        evidence.occurrence_count = occurrence_count
        if transcript and transcript.date:
            evidence.timestamp = transcript.date

        return evidence

    def extract_batch(
        self,
        patterns: list[PatternMatch],
        all_segments: list[Segment],
        transcript: Transcript | None = None,
    ) -> list[Evidence]:
        segment_map = {s.id: s for s in all_segments}
        evidence_list = []

        for pattern in patterns:
            segments = [
                segment_map[sid] for sid in pattern.segment_ids if sid in segment_map
            ]
            if segments:
                evidence = self.extract_from_pattern(pattern, segments, transcript)
                evidence_list.append(evidence)

        return evidence_list

    def assign_importance(
        self,
        evidence: Evidence,
        _occurrence_count: int,
        _pattern_type: str,
    ) -> Literal["HIGH", "MEDIUM", "LOW"]:
        return self.importance_assigner.assign_for_evidence(evidence)

    def categorize(self, evidence: Evidence) -> EvidenceCategory:
        return self.categorizer.categorize_evidence(evidence)

    def generate_id(self) -> str:
        return generate_evidence_id()


__all__ = ["PatternMatch", "EvidenceExtractor"]
