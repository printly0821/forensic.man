"""
대화 흐름 추출 모듈
"""
from typing import Any

from forensic.evidence.models.evidence import Evidence
from forensic.models.transcript import Segment, Transcript


class ConversationFlow:
    def __init__(
        self,
        segments: list[Segment],
        start_time: float,
        end_time: float,
    ) -> None:
        self.segments = segments
        self.start_time = start_time
        self.end_time = end_time

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def speaker_count(self) -> int:
        return len({s.speaker for s in self.segments})

    @property
    def turn_count(self) -> int:
        return len(self.segments)

    def get_speakers(self) -> list[str]:
        return list({s.speaker for s in self.segments})

    def get_text(self) -> str:
        return " ".join(s.content for s in self.segments)

    def get_speaker_turns(self, speaker_id: str) -> list[Segment]:
        return [s for s in self.segments if s.speaker == speaker_id]


class FlowExtractor:
    def __init__(self, max_gap_seconds: float = 30.0) -> None:
        self._max_gap = max_gap_seconds

    def extract_flow_around_segment(
        self,
        segment: Segment,
        all_segments: list[Segment],
        window_size: int = 10,
    ) -> ConversationFlow:
        try:
            index = all_segments.index(segment)
        except ValueError:
            index = next(
                (i for i, s in enumerate(all_segments) if s.id == segment.id),
                -1,
            )
            if index == -1:
                return ConversationFlow([], 0, 0)
        start = max(0, index - window_size // 2)
        end = min(len(all_segments), index + window_size // 2 + 1)
        flow_segments = all_segments[start:end]
        if flow_segments:
            start_time = flow_segments[0].start_time
            end_time = flow_segments[-1].end_time
        else:
            start_time = end_time = 0
        return ConversationFlow(flow_segments, start_time, end_time)

    def extract_flow_by_time(
        self,
        all_segments: list[Segment],
        start_time: float,
        end_time: float,
    ) -> ConversationFlow:
        flow_segments = [
            s
            for s in all_segments
            if s.start_time < end_time and s.end_time > start_time
        ]
        return ConversationFlow(flow_segments, start_time, end_time)

    def extract_continuous_flows(
        self,
        all_segments: list[Segment],
    ) -> list[ConversationFlow]:
        if not all_segments:
            return []
        flows = []
        current_flow_segments = [all_segments[0]]
        last_end_time = all_segments[0].end_time
        for segment in all_segments[1:]:
            gap = segment.start_time - last_end_time
            if gap <= self._max_gap:
                current_flow_segments.append(segment)
                last_end_time = segment.end_time
            else:
                if current_flow_segments:
                    flows.append(
                        ConversationFlow(
                            current_flow_segments,
                            current_flow_segments[0].start_time,
                            current_flow_segments[-1].end_time,
                        )
                    )
                current_flow_segments = [segment]
                last_end_time = segment.end_time
        if current_flow_segments:
            flows.append(
                ConversationFlow(
                    current_flow_segments,
                    current_flow_segments[0].start_time,
                    current_flow_segments[-1].end_time,
                )
            )
        return flows

    def extract_flow_for_evidence(
        self,
        evidence: Evidence,
        transcript: Transcript,
        extend_seconds: float = 60.0,
    ) -> ConversationFlow:
        if not evidence.segment_ids:
            return ConversationFlow([], 0, 0)
        related_segments = [
            s for s in transcript.segments if s.id in evidence.segment_ids
        ]
        if not related_segments:
            return ConversationFlow([], 0, 0)
        start_time = max(0, related_segments[0].start_time - extend_seconds)
        end_time = related_segments[-1].end_time + extend_seconds
        return self.extract_flow_by_time(transcript.segments, start_time, end_time)

    def analyze_flow_pattern(self, flow: ConversationFlow) -> dict[str, Any]:
        if not flow.segments:
            return {
                "dominant_speaker": None,
                "speaker_distribution": {},
                "average_turn_length": 0,
                "interruptions": 0,
            }
        speaker_counts: dict[str, int] = {}
        speaker_durations: dict[str, float] = {}
        for segment in flow.segments:
            speaker_counts[segment.speaker] = speaker_counts.get(segment.speaker, 0) + 1
            speaker_durations[segment.speaker] = (
                speaker_durations.get(segment.speaker, 0) + segment.duration
            )
        dominant_speaker = max(speaker_counts, key=speaker_counts.get, default=None)
        avg_turn_length = flow.duration / flow.turn_count if flow.turn_count > 0 else 0
        interruptions = 0
        for i in range(1, len(flow.segments)):
            if flow.segments[i].speaker == flow.segments[i - 1].speaker:
                interruptions += 1
        return {
            "dominant_speaker": dominant_speaker,
            "speaker_distribution": speaker_counts,
            "speaker_durations": speaker_durations,
            "average_turn_length": round(avg_turn_length, 2),
            "interruptions": interruptions,
            "total_duration": round(flow.duration, 2),
            "turn_count": flow.turn_count,
        }


__all__ = ["ConversationFlow", "FlowExtractor"]
