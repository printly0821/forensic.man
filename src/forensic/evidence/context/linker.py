"""
관련 세그먼트 연결 모듈
"""
import re
from typing import Any

from forensic.evidence.models.evidence import Evidence
from forensic.models.transcript import Segment


class SegmentLinker:
    def __init__(
        self,
        similarity_threshold: float = 0.7,
        max_links: int = 10,
    ) -> None:
        self._similarity_threshold = similarity_threshold
        self._max_links = max_links

    def link_related_segments(
        self,
        evidence: Evidence,
        all_segments: list[Segment],
        similarity_threshold: float = 0.0,
    ) -> list[str]:
        if similarity_threshold == 0:
            similarity_threshold = self._similarity_threshold
        if not evidence.segment_ids:
            return []
        existing_ids = set(evidence.segment_ids)
        candidates = [s for s in all_segments if s.id not in existing_ids]
        base_text = evidence.content_sample.lower()
        if not base_text:
            return []
        scored_segments = []
        for segment in candidates:
            similarity = self._calculate_similarity(base_text, segment.content.lower())
            if similarity >= similarity_threshold:
                scored_segments.append((segment.id, similarity))
        scored_segments.sort(key=lambda x: x[1], reverse=True)
        linked_ids = [sid for sid, _ in scored_segments[: self._max_links]]
        return linked_ids

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def _tokenize(self, text: str) -> list[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text)
        return [w for w in cleaned.split() if len(w) > 1]

    def link_by_speaker(
        self,
        evidence: Evidence,
        all_segments: list[Segment],
        time_window_seconds: float = 300.0,
    ) -> list[str]:
        if not evidence.speaker:
            return []
        base_time = None
        if evidence.timestamp:
            base_time = evidence.timestamp.timestamp()
        elif evidence.segment_ids:
            first_seg = next(
                (s for s in all_segments if s.id == evidence.segment_ids[0]),
                None,
            )
            if first_seg:
                base_time = first_seg.start_time
        if base_time is None:
            return [
                s.id
                for s in all_segments
                if s.speaker == evidence.speaker and s.id not in evidence.segment_ids
            ]
        linked = []
        for segment in all_segments:
            if (
                segment.speaker == evidence.speaker
                and segment.id not in evidence.segment_ids
                and abs(segment.start_time - base_time) <= time_window_seconds
            ):
                linked.append(segment.id)
        return linked

    def build_link_graph(
        self,
        evidence_list: list[Evidence],
        all_segments: list[Segment],
    ) -> dict[str, dict[str, Any]]:
        graph: dict[str, dict[str, Any]] = {}
        for evidence in evidence_list:
            graph[evidence.id] = {
                "evidence": evidence,
                "linked_segments": [],
                "linked_evidence": [],
                "speaker_links": [],
            }
            linked_segment_ids = self.link_related_segments(evidence, all_segments)
            graph[evidence.id]["linked_segments"] = linked_segment_ids
            speaker_links = self.link_by_speaker(evidence, all_segments)
            graph[evidence.id]["speaker_links"] = speaker_links
        for ev1 in evidence_list:
            for ev2 in evidence_list:
                if ev1.id >= ev2.id:
                    continue
                if ev1.speaker and ev1.speaker == ev2.speaker:
                    graph[ev1.id]["linked_evidence"].append(ev2.id)
                    graph[ev2.id]["linked_evidence"].append(ev1.id)
                if (
                    ev1.source_pattern_type
                    and ev1.source_pattern_type == ev2.source_pattern_type
                ):
                    if ev2.id not in graph[ev1.id]["linked_evidence"]:
                        graph[ev1.id]["linked_evidence"].append(ev2.id)
                    if ev1.id not in graph[ev2.id]["linked_evidence"]:
                        graph[ev2.id]["linked_evidence"].append(ev1.id)
        return graph


__all__ = ["SegmentLinker"]
