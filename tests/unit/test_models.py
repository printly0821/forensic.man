"""
녹취자료 데이터 모델 단위 테스트

Segment, Speaker, Evidence, Transcript 모델의 동작을 검증합니다.
"""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from forensic.models.transcript import Evidence, Segment, Speaker, Transcript


class TestSegment:
    """Segment 모델 테스트"""

    def test_create_valid_segment(self) -> None:
        """유효한 세그먼트 생성을 검증합니다."""
        segment = Segment(
            id="seg_001",
            speaker="speaker_1",
            start_time=10.5,
            end_time=15.0,
            content="안녕하세요",
            confidence=0.95,
        )

        assert segment.id == "seg_001"
        assert segment.speaker == "speaker_1"
        assert segment.start_time == 10.5
        assert segment.end_time == 15.0
        assert segment.content == "안녕하세요"
        assert segment.confidence == 0.95

    def test_segment_duration_property(self) -> None:
        """세그먼트 지속 시간 계산을 검증합니다."""
        segment = Segment(
            id="seg_001",
            speaker="speaker_1",
            start_time=10.0,
            end_time=15.0,
            content="안녕하세요",
            confidence=0.95,
        )

        assert segment.duration == 5.0

    def test_segment_end_time_before_start_time_raises_error(self) -> None:
        """end_time이 start_time보다 작으면 ValidationError가 발생합니다."""
        with pytest.raises(ValidationError, match="end_time must be greater than start_time"):
            Segment(
                id="seg_001",
                speaker="speaker_1",
                start_time=15.0,
                end_time=10.0,
                content="안녕하세요",
                confidence=0.95,
            )

    def test_segment_negative_start_time_raises_error(self) -> None:
        """음수 start_time은 ValidationError를 발생시킵니다."""
        with pytest.raises(ValidationError):
            Segment(
                id="seg_001",
                speaker="speaker_1",
                start_time=-1.0,
                end_time=10.0,
                content="안녕하세요",
                confidence=0.95,
            )

    def test_segment_confidence_out_of_range_raises_error(self) -> None:
        """범위를 벗어난 confidence는 ValidationError를 발생시킵니다."""
        with pytest.raises(ValidationError):
            Segment(
                id="seg_001",
                speaker="speaker_1",
                start_time=0.0,
                end_time=10.0,
                content="안녕하세요",
                confidence=1.5,
            )

        with pytest.raises(ValidationError):
            Segment(
                id="seg_001",
                speaker="speaker_1",
                start_time=0.0,
                end_time=10.0,
                content="안녕하세요",
                confidence=-0.1,
            )

    def test_segment_zero_duration(self) -> None:
        """start_time과 end_time이 같은 경우를 검증합니다."""
        # end_time > 0이어야 하고, start_time보다 커야 함
        # 같은 값은 허용되지 않음 (end_time > start_time 검증)
        with pytest.raises(ValidationError, match="end_time must be greater than start_time"):
            Segment(
                id="seg_001",
                speaker="speaker_1",
                start_time=10.0,
                end_time=10.0,
                content="안녕하세요",
                confidence=0.95,
            )


class TestSpeaker:
    """Speaker 모델 테스트"""

    def test_create_valid_speaker(self) -> None:
        """유효한 화자 생성을 검증합니다."""
        speaker = Speaker(
            id="speaker_1",
            name="홍길동",
            aliases=["길동", "홍씨"],
        )

        assert speaker.id == "speaker_1"
        assert speaker.name == "홍길동"
        assert speaker.aliases == ["길동", "홍씨"]
        assert speaker.total_duration == 0
        assert speaker.segment_count == 0

    def test_speaker_with_defaults(self) -> None:
        """기본값이 있는 화자 생성을 검증합니다."""
        speaker = Speaker(id="speaker_1", name="홍길동")

        assert speaker.aliases == []
        assert speaker.total_duration == 0
        assert speaker.segment_count == 0

    def test_speaker_add_segment(self) -> None:
        """세그먼트 추가 시 통계 업데이트를 검증합니다."""
        speaker = Speaker(id="speaker_1", name="홍길동")

        speaker.add_segment(10.0)
        assert speaker.total_duration == 10.0
        assert speaker.segment_count == 1

        speaker.add_segment(15.5)
        assert speaker.total_duration == 25.5
        assert speaker.segment_count == 2

    def test_speaker_has_alias_with_name(self) -> None:
        """이름으로 별칭 확인을 검증합니다."""
        speaker = Speaker(id="speaker_1", name="홍길동", aliases=["길동"])

        assert speaker.has_alias("홍길동") is True
        assert speaker.has_alias("길동") is True
        assert speaker.has_alias("홍씨") is False

    def test_speaker_negative_total_duration_raises_error(self) -> None:
        """음수 total_duration은 ValidationError를 발생시킵니다."""
        with pytest.raises(ValidationError):
            Speaker(id="speaker_1", name="홍길동", total_duration=-1.0)

    def test_speaker_negative_segment_count_raises_error(self) -> None:
        """음수 segment_count는 ValidationError를 발생시킵니다."""
        with pytest.raises(ValidationError):
            Speaker(id="speaker_1", name="홍길동", segment_count=-1)


class TestEvidence:
    """Evidence 모델 테스트"""

    def test_create_valid_evidence(self) -> None:
        """유효한 증거 생성을 검증합니다."""
        evidence = Evidence(
            id="ev_001",
            transcript_id="transcript_001",
            segment_ids=["seg_001", "seg_002"],
            category="금융거래",
            description="5천만 원 거래",
            importance="HIGH",
            context_before="이전 대화",
            context_after="이후 대화",
        )

        assert evidence.id == "ev_001"
        assert evidence.transcript_id == "transcript_001"
        assert evidence.segment_ids == ["seg_001", "seg_002"]
        assert evidence.category == "금융거래"
        assert evidence.description == "5천만 원 거래"
        assert evidence.importance == "HIGH"
        assert evidence.context_before == "이전 대화"
        assert evidence.context_after == "이후 대화"

    def test_evidence_with_defaults(self) -> None:
        """기본값이 있는 증거 생성을 검증합니다."""
        evidence = Evidence(
            id="ev_001",
            transcript_id="transcript_001",
            category="위계위반",
            description="상사에게 명령",
        )

        assert evidence.segment_ids == []
        assert evidence.importance == "MEDIUM"
        assert evidence.context_before == ""
        assert evidence.context_after == ""

    def test_evidence_importance_checkers(self) -> None:
        """증거 중요도 확인 메서드들을 검증합니다."""
        high_evidence = Evidence(
            id="ev_001",
            transcript_id="transcript_001",
            category="test",
            description="test",
            importance="HIGH",
        )
        assert high_evidence.is_high_importance() is True
        assert high_evidence.is_medium_importance() is False
        assert high_evidence.is_low_importance() is False

        medium_evidence = Evidence(
            id="ev_002",
            transcript_id="transcript_001",
            category="test",
            description="test",
            importance="MEDIUM",
        )
        assert medium_evidence.is_high_importance() is False
        assert medium_evidence.is_medium_importance() is True
        assert medium_evidence.is_low_importance() is False

        low_evidence = Evidence(
            id="ev_003",
            transcript_id="transcript_001",
            category="test",
            description="test",
            importance="LOW",
        )
        assert low_evidence.is_high_importance() is False
        assert low_evidence.is_medium_importance() is False
        assert low_evidence.is_low_importance() is True

    def test_evidence_invalid_importance_raises_error(self) -> None:
        """유효하지 않은 importance 값은 ValidationError를 발생시킵니다."""
        with pytest.raises(ValidationError):
            Evidence(
                id="ev_001",
                transcript_id="transcript_001",
                category="test",
                description="test",
                importance="INVALID",  # type: ignore
            )


class TestTranscript:
    """Transcript 모델 테스트"""

    def test_create_valid_transcript(self) -> None:
        """유효한 녹취록 생성을 검증합니다."""
        transcript = Transcript(
            id="transcript_001",
            file_path=Path("/path/to/audio.wav"),
            date=datetime(2025, 6, 15, 10, 0),
            duration_seconds=3600.0,
            speakers=["speaker_1", "speaker_2"],
            content="전체 대화 내용",
        )

        assert transcript.id == "transcript_001"
        assert transcript.file_path == Path("/path/to/audio.wav")
        assert transcript.date == datetime(2025, 6, 15, 10, 0)
        assert transcript.duration_seconds == 3600.0
        assert transcript.speakers == ["speaker_1", "speaker_2"]
        assert transcript.content == "전체 대화 내용"
        assert transcript.segments == []
        assert transcript.metadata == {}

    def test_transcript_add_segment(self) -> None:
        """세그먼트 추가와 화자 목록 업데이트를 검증합니다."""
        transcript = Transcript(
            id="transcript_001",
            file_path=Path("/path/to/audio.wav"),
            date=datetime(2025, 6, 15),
            duration_seconds=100.0,
        )

        segment1 = Segment(
            id="seg_001",
            speaker="speaker_1",
            start_time=0.0,
            end_time=10.0,
            content="안녕하세요",
            confidence=0.95,
        )
        segment2 = Segment(
            id="seg_002",
            speaker="speaker_2",
            start_time=10.0,
            end_time=20.0,
            content="반갑습니다",
            confidence=0.90,
        )

        transcript.add_segment(segment1)
        transcript.add_segment(segment2)

        assert len(transcript.segments) == 2
        assert "speaker_1" in transcript.speakers
        assert "speaker_2" in transcript.speakers

    def test_transcript_add_duplicate_speaker_only_once(self) -> None:
        """중복 화자가 목록에 한 번만 추가되는지 검증합니다."""
        transcript = Transcript(
            id="transcript_001",
            file_path=Path("/path/to/audio.wav"),
            date=datetime(2025, 6, 15),
            duration_seconds=100.0,
        )

        segment1 = Segment(
            id="seg_001",
            speaker="speaker_1",
            start_time=0.0,
            end_time=10.0,
            content="안녕하세요",
            confidence=0.95,
        )
        segment2 = Segment(
            id="seg_002",
            speaker="speaker_1",
            start_time=10.0,
            end_time=20.0,
            content="반갑습니다",
            confidence=0.90,
        )

        transcript.add_segment(segment1)
        transcript.add_segment(segment2)

        assert transcript.speakers.count("speaker_1") == 1

    def test_transcript_get_segments_by_speaker(self) -> None:
        """화자별 세그먼트 조회를 검증합니다."""
        transcript = Transcript(
            id="transcript_001",
            file_path=Path("/path/to/audio.wav"),
            date=datetime(2025, 6, 15),
            duration_seconds=100.0,
        )

        transcript.add_segment(
            Segment(
                id="seg_001",
                speaker="speaker_1",
                start_time=0.0,
                end_time=10.0,
                content="안녕하세요",
                confidence=0.95,
            )
        )
        transcript.add_segment(
            Segment(
                id="seg_002",
                speaker="speaker_2",
                start_time=10.0,
                end_time=20.0,
                content="반갑습니다",
                confidence=0.90,
            )
        )
        transcript.add_segment(
            Segment(
                id="seg_003",
                speaker="speaker_1",
                start_time=20.0,
                end_time=30.0,
                content="또 만나요",
                confidence=0.92,
            )
        )

        speaker1_segments = transcript.get_segments_by_speaker("speaker_1")
        assert len(speaker1_segments) == 2
        assert speaker1_segments[0].id == "seg_001"
        assert speaker1_segments[1].id == "seg_003"

        speaker2_segments = transcript.get_segments_by_speaker("speaker_2")
        assert len(speaker2_segments) == 1
        assert speaker2_segments[0].id == "seg_002"

    def test_transcript_get_segments_in_range(self) -> None:
        """시간 범위 내 세그먼트 조회를 검증합니다."""
        transcript = Transcript(
            id="transcript_001",
            file_path=Path("/path/to/audio.wav"),
            date=datetime(2025, 6, 15),
            duration_seconds=100.0,
        )

        transcript.add_segment(
            Segment(
                id="seg_001",
                speaker="speaker_1",
                start_time=0.0,
                end_time=10.0,
                content="안녕하세요",
                confidence=0.95,
            )
        )
        transcript.add_segment(
            Segment(
                id="seg_002",
                speaker="speaker_2",
                start_time=10.0,
                end_time=20.0,
                content="반갑습니다",
                confidence=0.90,
            )
        )
        transcript.add_segment(
            Segment(
                id="seg_003",
                speaker="speaker_1",
                start_time=25.0,
                end_time=35.0,
                content="또 만나요",
                confidence=0.92,
            )
        )

        # 범위 내 세그먼트 (0~15초)
        in_range = transcript.get_segments_in_range(0.0, 15.0)
        assert len(in_range) == 2
        assert in_range[0].id == "seg_001"
        assert in_range[1].id == "seg_002"

        # 정확한 범위 내 세그먼트
        exact_range = transcript.get_segments_in_range(10.0, 20.0)
        assert len(exact_range) == 1
        assert exact_range[0].id == "seg_002"

    def test_transcript_properties(self) -> None:
        """녹취록 속성 메서드들을 검증합니다."""
        transcript = Transcript(
            id="transcript_001",
            file_path=Path("/path/to/audio.wav"),
            date=datetime(2025, 6, 15),
            duration_seconds=3665.0,  # 1시간 1분 5초
        )

        assert transcript.segment_count == 0
        assert transcript.speaker_count == 0
        assert transcript.get_duration_minutes() == pytest.approx(61.083, rel=0.01)
        assert transcript.get_duration_hours() == pytest.approx(1.018, rel=0.01)

    def test_transcript_negative_duration_raises_error(self) -> None:
        """음수 duration_seconds는 ValidationError를 발생시킵니다."""
        with pytest.raises(ValidationError):
            Transcript(
                id="transcript_001",
                file_path=Path("/path/to/audio.wav"),
                date=datetime(2025, 6, 15),
                duration_seconds=-1.0,
            )

    def test_transcript_zero_duration_raises_error(self) -> None:
        """0 duration_seconds는 ValidationError를 발생시킵니다."""
        with pytest.raises(ValidationError):
            Transcript(
                id="transcript_001",
                file_path=Path("/path/to/audio.wav"),
                date=datetime(2025, 6, 15),
                duration_seconds=0.0,
            )
