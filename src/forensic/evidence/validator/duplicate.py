"""
중복 탐지 모듈
"""

from forensic.evidence.models.evidence import Evidence
from forensic.evidence.models.validation import MergeProposal


class DuplicateDetector:
    def __init__(
        self,
        similarity_threshold: float = 0.9,
        time_window_hours: int = 24,
    ) -> None:
        self._similarity_threshold = similarity_threshold
        self._time_window_hours = time_window_hours

    def detect_duplicates(
        self,
        evidence: Evidence,
        existing_evidence: list[Evidence],
    ) -> list[Evidence]:
        duplicates = []
        for existing in existing_evidence:
            if existing.id == evidence.id:
                continue
            if self._are_duplicates(evidence, existing):
                duplicates.append(existing)
        return duplicates

    def _are_duplicates(self, e1: Evidence, e2: Evidence) -> bool:
        if e1.source_pattern_type != e2.source_pattern_type:
            return False
        if e1.speaker != e2.speaker:
            return False
        content_similarity = self._calculate_content_similarity(
            e1.content_sample,
            e2.content_sample,
        )
        if content_similarity < self._similarity_threshold:
            return False
        if e1.timestamp and e2.timestamp:
            time_diff_hours = abs(
                (e1.timestamp - e2.timestamp).total_seconds() / 3600
            )
            if time_diff_hours > self._time_window_hours:
                return False
        return True

    def _calculate_content_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0

        # For Korean text, use character n-grams (bigrams) for better similarity
        # This handles cases where words are similar but not identical
        def get_char_ngrams(text: str, n: int = 2) -> set[str]:
            text = text.lower().replace(" ", "")
            return {text[i:i+n] for i in range(len(text) - n + 1)} if len(text) >= n else {text}

        # Calculate word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        word_intersection = len(words1 & words2)
        word_union = len(words1 | words2)
        word_sim = word_intersection / word_union if word_union > 0 else 0.0

        # Calculate character n-gram similarity (better for Korean)
        ngrams1 = get_char_ngrams(text1, 2)
        ngrams2 = get_char_ngrams(text2, 2)
        ngram_intersection = len(ngrams1 & ngrams2)
        ngram_union = len(ngrams1 | ngrams2)
        ngram_sim = ngram_intersection / ngram_union if ngram_union > 0 else 0.0

        # Use the maximum of both similarities
        return max(word_sim, ngram_sim)

    def create_merge_proposal(
        self,
        primary: Evidence,
        duplicates: list[Evidence],
    ) -> MergeProposal:
        duplicate_ids = [d.id for d in duplicates]
        importance_levels = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        max_importance = max(
            [primary.importance] + [d.importance for d in duplicates],
            key=lambda x: importance_levels.get(x, 0),
        )
        total_occurrences = primary.occurrence_count + sum(
            d.occurrence_count for d in duplicates
        )
        avg_confidence = (
            primary.confidence + sum(d.confidence for d in duplicates)
        ) / (len(duplicates) + 1)
        reason = f"동일 패턴({primary.source_pattern_type})의 반복 탐지"
        if total_occurrences > 1:
            reason += f", 총 {total_occurrences}회 발생"
        merged_description = (
            f"{primary.description} "
            f"(총 {total_occurrences}회, 신뢰도 {avg_confidence:.2f})"
        )
        return MergeProposal(
            primary_evidence_id=primary.id,
            duplicate_evidence_ids=duplicate_ids,
            reason=reason,
            confidence=avg_confidence,
            merged_description=merged_description,
            merged_importance=max_importance,
        )

    def merge_evidence(self, primary: Evidence, duplicates: list[Evidence]) -> Evidence:
        all_segment_ids = set(primary.segment_ids)
        for dup in duplicates:
            all_segment_ids.update(dup.segment_ids)
        primary.segment_ids = sorted(all_segment_ids)
        primary.occurrence_count += sum(d.occurrence_count for d in duplicates)
        all_related = set(primary.related_evidence_ids)
        for dup in duplicates:
            all_related.update(dup.related_evidence_ids)
            all_related.discard(dup.id)
        primary.related_evidence_ids = list(all_related)
        primary.confidence = max(
            [primary.confidence] + [d.confidence for d in duplicates]
        )
        for dup in duplicates:
            primary.metadata.update(dup.metadata)
            primary.metadata["merged_from"] = primary.metadata.get("merged_from", [])
            primary.metadata["merged_from"].append(dup.id)
        return primary


__all__ = ["DuplicateDetector"]
