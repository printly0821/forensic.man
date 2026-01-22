"""
맥락 보존 모듈
"""
from typing import Any

from forensic.evidence.models.evidence import Evidence
from forensic.models.transcript import Segment, Transcript


class ContextPreserver:
    def __init__(
        self,
        before_count: int = 3,
        after_count: int = 3,
        default_before_count: int | None = None,
        default_after_count: int | None = None,
        max_context_length: int = 1000,
    ) -> None:
        # Support both parameter naming conventions
        if default_before_count is not None:
            self._before_count = default_before_count
        else:
            self._before_count = before_count
        if default_after_count is not None:
            self._after_count = default_after_count
        else:
            self._after_count = after_count
        self._max_context_length = max_context_length

    def extract_context(
        self,
        segment: Segment,
        all_segments: list[Segment],
        before_count: int = 0,
        after_count: int = 0,
    ) -> tuple[str, str]:
        if before_count == 0:
            before_count = self._before_count
        if after_count == 0:
            after_count = self._after_count

        try:
            index = all_segments.index(segment)
        except ValueError:
            index = next(
                (i for i, s in enumerate(all_segments) if s.id == segment.id),
                -1,
            )
            if index == -1:
                return "", ""

        before_start = max(0, index - before_count)
        before_segments = all_segments[before_start:index]
        context_before = self._format_context(before_segments)

        after_end = min(len(all_segments), index + after_count + 1)
        after_segments = all_segments[index + 1:after_end]
        context_after = self._format_context(after_segments)

        return context_before, context_after

    def _format_context(self, segments: list[Segment]) -> str:
        if not segments:
            return ""
        lines = []
        total_length = 0
        for segment in segments:
            line = f"[{segment.speaker}]: {segment.content}"
            if total_length + len(line) > self._max_context_length:
                break
            lines.append(line)
            total_length += len(line) + 1
        return "\n".join(lines)

    def get_conversation_flow(
        self,
        evidence: Evidence,
        all_segments: list[Segment],
        window_size: int = 10,
    ) -> list[Segment]:
        if not evidence.segment_ids:
            return []
        first_segment_id = evidence.segment_ids[0]
        first_segment = next(
            (s for s in all_segments if s.id == first_segment_id),
            None,
        )
        if not first_segment:
            return []
        try:
            index = all_segments.index(first_segment)
        except ValueError:
            return []
        start = max(0, index - window_size // 2)
        end = min(len(all_segments), index + window_size // 2 + 1)
        return all_segments[start:end]

    def apply_to_evidence(
        self,
        evidence: Evidence,
        all_segments: list[Segment],
        before_count: int = 0,
        after_count: int = 0,
    ) -> Evidence:
        if not evidence.segment_ids:
            return evidence
        first_segment = next(
            (s for s in all_segments if s.id == evidence.segment_ids[0]),
            None,
        )
        if first_segment:
            context_before, context_after = self.extract_context(
                first_segment,
                all_segments,
                before_count,
                after_count,
            )
            evidence.context_before = context_before
            evidence.context_after = context_after
        return evidence

    def set_context_range(self, before_count: int, after_count: int) -> None:
        if before_count >= 0:
            self._before_count = before_count
        if after_count >= 0:
            self._after_count = after_count

    def get_context_range(self) -> tuple[int, int]:
        return self._before_count, self._after_count

    def get_position_in_transcript(
        self,
        segment: Segment,
        transcript: Transcript,
    ) -> dict[str, Any]:
        try:
            index = transcript.segments.index(segment)
        except ValueError:
            index = next(
                (i for i, s in enumerate(transcript.segments) if s.id == segment.id),
                -1,
            )
        if index == -1:
            return {
                "index": -1,
                "total": len(transcript.segments),
                "percentage": 0.0,
                "time_position": segment.start_time,
                "duration": segment.duration,
            }
        total = len(transcript.segments)
        percentage = (index + 1) / total * 100 if total > 0 else 0
        return {
            "index": index,
            "total": total,
            "percentage": round(percentage, 2),
            "time_position": segment.start_time,
            "duration": segment.duration,
            "speaker": segment.speaker,
        }


__all__ = ["ContextPreserver"]
