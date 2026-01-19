"""
녹취자료 데이터 모델

Pydantic v2 기반으로 정의된 forensic.man 프로젝트의 핵심 데이터 모델입니다.
DGX Spark 환경(ARM64, 128GB 통합 메모리)에서의 대규모 데이터 처리를 지원합니다.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator


class Segment(BaseModel):
    """
    발언 세그먼트 모델

    녹취록에서 개별 발언을 나타내는 최소 단위입니다.
    시간 기반 검색과 화자별 분석을 지원합니다.

    Attributes:
        id: 세그먼트 고유 식별자
        speaker: 화자 식별자
        start_time: 발언 시작 시간 (초 단위, 0 이상)
        end_time: 발언 종료 시간 (초 단위, start_time보다 커야 함)
        content: 발언 내용
        confidence: STT 신뢰도 (0.0 ~ 1.0)
    """

    id: str
    speaker: str
    start_time: Annotated[float, Field(ge=0, description="발언 시작 시간 (초)")]
    end_time: Annotated[float, Field(gt=0, description="발언 종료 시간 (초)")]
    content: str
    confidence: Annotated[float, Field(ge=0, le=1, description="STT 신뢰도")]

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: float, info) -> float:
        """end_time이 start_time보다 큰지 검증합니다."""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be greater than start_time")
        return v

    @property
    def duration(self) -> float:
        """세그먼트 지속 시간을 반환합니다."""
        return self.end_time - self.start_time


class Speaker(BaseModel):
    """
    화자 모델

    녹취록에 등장하는 화자 정보를 나타냅니다.
    별칭을 통한 화자 통합과 통계 정보를 제공합니다.

    Attributes:
        id: 화자 고유 식별자
        name: 화자 이름
        aliases: 화자 별칭 목록 (이름 통합 분석용)
        total_duration: 총 발언 시간 (초)
        segment_count: 총 발언 횟수
    """

    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    total_duration: Annotated[float, Field(ge=0, default=0)] = 0
    segment_count: Annotated[int, Field(ge=0, default=0)] = 0

    def add_segment(self, duration: float) -> None:
        """
        세그먼트를 추가하여 통계를 업데이트합니다.

        Args:
            duration: 추가할 세그먼트의 지속 시간 (초)
        """
        self.total_duration += duration
        self.segment_count += 1

    def has_alias(self, name: str) -> bool:
        """
        주어진 이름이 이 화자의 별칭인지 확인합니다.

        Args:
            name: 확인할 이름

        Returns:
            별칭이면 True, 아니면 False
        """
        return name in self.aliases or name == self.name


class Evidence(BaseModel):
    """
    증거 모델

    분석 결과 발견된 법적 증거를 나타냅니다.
    관련 세그먼트와 중요도를 포함합니다.

    Attributes:
        id: 증거 고유 식별자
        transcript_id: 원본 녹취록 ID
        segment_ids: 관련 세그먼트 ID 목록
        category: 증거 분류 (예: "금융거래", "위계위반")
        description: 증거 설명
        importance: 중요도 (HIGH, MEDIUM, LOW)
        context_before: 이전 맥락 내용
        context_after: 이후 맥락 내용
    """

    id: str
    transcript_id: str
    segment_ids: list[str] = Field(default_factory=list)
    category: str
    description: str
    importance: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    context_before: str = ""
    context_after: str = ""

    def is_high_importance(self) -> bool:
        """HIGH 중요도인지 확인합니다."""
        return self.importance == "HIGH"

    def is_medium_importance(self) -> bool:
        """MEDIUM 중요도인지 확인합니다."""
        return self.importance == "MEDIUM"

    def is_low_importance(self) -> bool:
        """LOW 중요도인지 확인합니다."""
        return self.importance == "LOW"


class Transcript(BaseModel):
    """
    녹취 데이터 모델

    전체 녹취록을 나타내는 최상위 모델입니다.
    세그먼트, 화자, 메타데이터를 포함합니다.

    Attributes:
        id: 녹취록 고유 식별자
        file_path: 원본 파일 경로
        date: 녹취 날짜
        duration_seconds: 녹취 전체 길이 (초)
        speakers: 화자 ID 목록
        content: 전체 텍스트 내용
        segments: 발언 세그먼트 목록
        metadata: 추가 메타데이터
    """

    id: str
    file_path: Path
    date: datetime
    duration_seconds: Annotated[float, Field(gt=0, description="녹취 전체 길이 (초)")]
    speakers: list[str] = Field(default_factory=list)
    content: str = ""
    segments: list[Segment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_segment(self, segment: Segment) -> None:
        """
        세그먼트를 추가하고 화자 목록을 업데이트합니다.

        Args:
            segment: 추가할 세그먼트
        """
        self.segments.append(segment)
        if segment.speaker not in self.speakers:
            self.speakers.append(segment.speaker)

    def get_segments_by_speaker(self, speaker_id: str) -> list[Segment]:
        """
        특정 화자의 모든 세그먼트를 반환합니다.

        Args:
            speaker_id: 화자 ID

        Returns:
            해당 화자의 세그먼트 목록
        """
        return [s for s in self.segments if s.speaker == speaker_id]

    def get_segments_in_range(
        self, start_time: float, end_time: float
    ) -> list[Segment]:
        """
        시간 범위 내의 세그먼트를 반환합니다.

        Args:
            start_time: 시작 시간 (초)
            end_time: 종료 시간 (초)

        Returns:
            시간 범위 내의 세그먼트 목록
        """
        return [
            s
            for s in self.segments
            if s.start_time < end_time and s.end_time > start_time
        ]

    @property
    def segment_count(self) -> int:
        """전체 세그먼트 수를 반환합니다."""
        return len(self.segments)

    @property
    def speaker_count(self) -> int:
        """전체 화자 수를 반환합니다."""
        return len(self.speakers)

    def get_duration_minutes(self) -> float:
        """녹취 길이를 분 단위로 반환합니다."""
        return self.duration_seconds / 60

    def get_duration_hours(self) -> float:
        """녹취 길이를 시간 단위로 반환합니다."""
        return self.duration_seconds / 3600
