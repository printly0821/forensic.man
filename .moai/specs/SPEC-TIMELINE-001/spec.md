---
id: SPEC-TIMELINE-001
version: "1.0.0"
status: "draft"
created: "2026-01-18"
updated: "2026-01-18"
author: "지니"
priority: "HIGH"
dependencies:
  - SPEC-CORE-001
  - SPEC-IO-001
---

# SPEC-TIMELINE-001: 시계열 분석 및 화자 분리 시스템

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-01-18 | 지니 | 초기 작성 - 시계열 분석, 화자 분리, 패턴 인식 모듈 |

---

## 1. 개요

### 1.1 목적

183개 녹취 파일의 시계열 분석, 화자 분리, 가스라이팅 패턴 인식을 수행하는 핵심 분석 모듈을 구현합니다. NVIDIA DGX Spark의 대용량 메모리와 GPU 가속을 활용하여 효율적인 분석을 지원합니다.

### 1.2 범위

- 시계열 분석: 전체 파일의 시간순 정렬, 그룹화, 이벤트 마커 추출
- 화자 분리: 신동식, 신기연 두 화자 식별 및 통계 분석
- 패턴 인식: 가스라이팅, 반복 발언, 감정적 조작, 위협/압박 표현 탐지

### 1.3 의존성

- **SPEC-CORE-001**: Transcript, Segment, Speaker, Evidence 모델
- **SPEC-IO-001**: StreamReader, ChunkProcessor, BatchProcessor

### 1.4 대상 시스템

| 항목 | 사양 |
|------|------|
| 플랫폼 | NVIDIA DGX Spark |
| CPU | 20코어 ARM (Cortex-X925 + A725) |
| GPU | Blackwell 6,144 CUDA cores |
| 메모리 | 128GB 통합 LPDDR5x |
| 분석 대상 | 183개 파일, 30분+ 분량, 2025.06~12 |

---

## 2. 요구사항 (EARS 형식)

### 2.1 유비쿼터스 요구사항 (Ubiquitous)

**[REQ-U-001]** 시스템은 항상 모든 녹취 파일을 시간순으로 정렬하여 관리해야 한다.

**[REQ-U-002]** 모든 발언 세그먼트는 화자 정보를 포함해야 한다.

**[REQ-U-003]** 패턴 탐지 결과는 원본 세그먼트에 대한 참조를 유지해야 한다.

**[REQ-U-004]** 화자 별칭(동식, 기연, 신씨 등)은 정규화된 이름으로 매핑되어야 한다.

### 2.2 이벤트 기반 요구사항 (Event-Driven)

**[REQ-E-001]** 녹취 파일이 로드될 때, 파일명 또는 메타데이터에서 날짜를 추출해야 한다.

**[REQ-E-002]** 새로운 세그먼트가 생성될 때, 화자 식별을 수행해야 한다.

**[REQ-E-003]** 패턴이 탐지될 때, Evidence 모델로 변환하고 중요도를 할당해야 한다.

**[REQ-E-004]** 화자 전환이 발생할 때, 전환 패턴을 기록해야 한다.

**[REQ-E-005]** 배치 분석이 완료될 때, 통계 요약을 생성해야 한다.

### 2.3 상태 기반 요구사항 (State-Driven)

**[REQ-S-001]** GPU가 사용 가능한 상태일 때, 패턴 인식에 CUDA 가속을 적용해야 한다.

**[REQ-S-002]** 동일 날짜에 여러 파일이 존재하는 상태일 때, 시간 순서로 병합하여 표시해야 한다.

**[REQ-S-003]** 화자가 미식별된 상태일 때, "UNKNOWN" 레이블을 할당해야 한다.

### 2.4 원치 않는 동작 요구사항 (Unwanted Behavior)

**[REQ-W-001]** 시스템은 원본 녹취 데이터를 수정하지 않아야 한다.

**[REQ-W-002]** 시스템은 화자 식별 없이 증거를 생성하지 않아야 한다.

**[REQ-W-003]** 시스템은 맥락 없이 패턴 탐지 결과를 보고하지 않아야 한다.

### 2.5 선택적 요구사항 (Optional Feature)

**[REQ-O-001]** 사용자가 특정 기간을 지정하면, 해당 기간의 녹취만 분석해야 한다.

**[REQ-O-002]** 사용자가 특정 화자를 지정하면, 해당 화자의 발언만 추출해야 한다.

**[REQ-O-003]** 사용자가 시각화를 요청하면, 시계열 그래프를 생성해야 한다.

**[REQ-O-004]** 사용자가 커스텀 패턴을 정의하면, 해당 패턴도 탐지해야 한다.

### 2.6 복합 요구사항 (Complex)

**[REQ-C-001]** DGX Spark 환경이고 GPU가 사용 가능할 때, 패턴 인식 배치 크기를 100으로 설정하고 CUDA 가속을 활성화해야 한다.

**[REQ-C-002]** 분석 대상이 50개 파일 이상이고 메모리가 64GB 이상 가용할 때, 병렬 분석 모드를 활성화해야 한다.

**[REQ-C-003]** 가스라이팅 패턴이 탐지되고 반복 횟수가 3회 이상일 때, 중요도를 HIGH로 자동 상향해야 한다.

---

## 3. 인터페이스 정의

### 3.1 TimelineBuilder

```python
class TimelineBuilder(Protocol):
    """시계열 구축 인터페이스"""

    def add_transcript(self, transcript: Transcript) -> None:
        """녹취 데이터를 타임라인에 추가한다."""
        ...

    def build(self) -> Timeline:
        """정렬된 타임라인을 생성한다."""
        ...

    def get_by_date(self, date: datetime.date) -> list[Transcript]:
        """특정 날짜의 녹취 목록을 반환한다."""
        ...

    def get_by_range(
        self,
        start: datetime.date,
        end: datetime.date
    ) -> list[Transcript]:
        """날짜 범위 내 녹취 목록을 반환한다."""
        ...

    def group_by_period(
        self,
        period: Literal["day", "week", "month"]
    ) -> dict[str, list[Transcript]]:
        """기간별로 그룹화된 녹취 목록을 반환한다."""
        ...

    def extract_events(self) -> list[TimelineEvent]:
        """주요 이벤트 마커를 추출한다."""
        ...
```

### 3.2 SpeakerAnalyzer

```python
class SpeakerAnalyzer(Protocol):
    """화자 분리 및 통계 인터페이스"""

    def identify_speaker(self, segment: Segment) -> str:
        """세그먼트에서 화자를 식별한다."""
        ...

    def normalize_alias(self, name: str) -> str:
        """화자 별칭을 정규화된 이름으로 변환한다."""
        ...

    def get_statistics(self, speaker_id: str) -> SpeakerStatistics:
        """특정 화자의 통계를 반환한다."""
        ...

    def get_all_statistics(self) -> dict[str, SpeakerStatistics]:
        """모든 화자의 통계를 반환한다."""
        ...

    def analyze_turn_taking(
        self,
        segments: list[Segment]
    ) -> list[TurnTakingEvent]:
        """화자 전환 패턴을 분석한다."""
        ...

    def get_speaking_ratio(self) -> dict[str, float]:
        """화자별 발언 비율을 반환한다."""
        ...
```

### 3.3 PatternDetector

```python
class PatternDetector(Protocol):
    """패턴 인식 인터페이스"""

    def detect_gaslighting(
        self,
        segments: list[Segment]
    ) -> list[GaslightingPattern]:
        """가스라이팅 패턴을 탐지한다."""
        ...

    def detect_repeated_statements(
        self,
        segments: list[Segment],
        threshold: int = 3
    ) -> list[RepeatedStatement]:
        """반복 발언을 추적한다."""
        ...

    def detect_emotional_manipulation(
        self,
        segments: list[Segment]
    ) -> list[EmotionalManipulation]:
        """감정적 조작 표현을 탐지한다."""
        ...

    def detect_threats(
        self,
        segments: list[Segment]
    ) -> list[ThreatPattern]:
        """위협/압박 표현을 탐지한다."""
        ...

    def add_custom_pattern(
        self,
        name: str,
        keywords: list[str],
        context_rules: Optional[dict] = None
    ) -> None:
        """사용자 정의 패턴을 추가한다."""
        ...

    def detect_all(
        self,
        segments: list[Segment]
    ) -> list[Evidence]:
        """모든 패턴을 탐지하고 Evidence로 변환한다."""
        ...
```

---

## 4. 데이터 모델

### 4.1 Timeline (시계열 데이터)

```python
class Timeline(BaseModel):
    """시계열 데이터 모델"""
    id: str                           # 타임라인 ID
    start_date: datetime.date         # 시작 날짜
    end_date: datetime.date           # 종료 날짜
    transcripts: list[Transcript]     # 정렬된 녹취 목록
    total_duration: float             # 총 녹취 시간 (초)
    file_count: int                   # 파일 개수
    events: list[TimelineEvent]       # 주요 이벤트
```

### 4.2 TimelineEvent (이벤트 마커)

```python
class TimelineEvent(BaseModel):
    """타임라인 이벤트 마커"""
    id: str                           # 이벤트 ID
    date: datetime.date               # 발생 날짜
    time: Optional[datetime.time]     # 발생 시간 (가능한 경우)
    event_type: str                   # 이벤트 유형
    description: str                  # 설명
    related_transcripts: list[str]    # 관련 녹취 ID 목록
    importance: Literal["HIGH", "MEDIUM", "LOW"]
```

### 4.3 SpeakerStatistics (화자 통계)

```python
class SpeakerStatistics(BaseModel):
    """화자 통계 모델"""
    speaker_id: str                   # 화자 ID
    speaker_name: str                 # 화자 이름
    aliases: list[str]                # 별칭 목록
    total_segments: int               # 총 발언 세그먼트 수
    total_duration_seconds: float     # 총 발언 시간 (초)
    average_segment_length: float     # 평균 발언 길이 (초)
    word_count: int                   # 총 단어 수
    speaking_ratio: float             # 발언 비율 (0.0 ~ 1.0)
    first_appearance: datetime        # 첫 발언 시점
    last_appearance: datetime         # 마지막 발언 시점
```

### 4.4 TurnTakingEvent (화자 전환)

```python
class TurnTakingEvent(BaseModel):
    """화자 전환 이벤트"""
    id: str                           # 이벤트 ID
    timestamp: datetime               # 전환 시점
    from_speaker: str                 # 이전 화자
    to_speaker: str                   # 다음 화자
    gap_seconds: float                # 전환 간격 (초)
    overlap_seconds: float            # 중복 발언 시간 (초)
    interruption: bool                # 끼어들기 여부
```

### 4.5 GaslightingPattern (가스라이팅 패턴)

```python
class GaslightingPattern(BaseModel):
    """가스라이팅 패턴 모델"""
    id: str                           # 패턴 ID
    pattern_type: Literal[
        "DENIAL",           # 부정 ("그런 적 없어")
        "TRIVIALIZING",     # 축소 ("별거 아니야")
        "DIVERTING",        # 화제 전환
        "COUNTERING",       # 기억 왜곡 ("네가 잘못 기억해")
        "BLOCKING",         # 차단/회피
        "FORGETTING",       # 망각 주장
        "WITHHOLDING"       # 정보 차단
    ]
    segment_ids: list[str]            # 관련 세그먼트 ID
    speaker: str                      # 발화자
    target: str                       # 대상자
    content_sample: str               # 대표 발언 샘플
    confidence: float                 # 탐지 신뢰도 (0.0 ~ 1.0)
    context_before: str               # 전후 맥락 (이전)
    context_after: str                # 전후 맥락 (이후)
    occurrence_count: int             # 발생 횟수
```

### 4.6 RepeatedStatement (반복 발언)

```python
class RepeatedStatement(BaseModel):
    """반복 발언 모델"""
    id: str                           # ID
    pattern: str                      # 반복 패턴 (정규화된 형태)
    occurrences: list[StatementOccurrence]  # 발생 목록
    speaker: str                      # 발화자
    total_count: int                  # 총 반복 횟수
    first_occurrence: datetime        # 첫 발생 시점
    last_occurrence: datetime         # 마지막 발생 시점
    time_span_days: int               # 반복 기간 (일)
```

### 4.7 EmotionalManipulation (감정적 조작)

```python
class EmotionalManipulation(BaseModel):
    """감정적 조작 패턴 모델"""
    id: str                           # ID
    manipulation_type: Literal[
        "GUILT_TRIPPING",    # 죄책감 유발
        "SHAMING",           # 수치심 유발
        "FEAR_INDUCING",     # 공포 유발
        "LOVE_BOMBING",      # 과도한 애정 표현
        "SILENT_TREATMENT",  # 침묵/무시
        "VICTIMHOOD"         # 피해자 역할
    ]
    segment_ids: list[str]            # 관련 세그먼트 ID
    speaker: str                      # 발화자
    content_sample: str               # 대표 발언 샘플
    intensity: Literal["HIGH", "MEDIUM", "LOW"]  # 강도
```

### 4.8 ThreatPattern (위협/압박)

```python
class ThreatPattern(BaseModel):
    """위협/압박 패턴 모델"""
    id: str                           # ID
    threat_type: Literal[
        "EXPLICIT_THREAT",   # 명시적 위협
        "IMPLICIT_THREAT",   # 암시적 위협
        "FINANCIAL_THREAT",  # 경제적 압박
        "SOCIAL_THREAT",     # 사회적 위협 (관계 단절 등)
        "LEGAL_THREAT"       # 법적 위협
    ]
    segment_ids: list[str]            # 관련 세그먼트 ID
    speaker: str                      # 발화자
    content_sample: str               # 대표 발언 샘플
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
```

---

## 5. 패턴 인식 키워드 사전

### 5.1 가스라이팅 패턴 키워드

```yaml
gaslighting_keywords:
  denial:
    - "그런 적 없어"
    - "내가 언제"
    - "무슨 소리야"
    - "말도 안 돼"

  trivializing:
    - "별거 아니야"
    - "예민해"
    - "오버하네"
    - "그게 뭐가 문제야"

  countering:
    - "네가 잘못 기억해"
    - "그렇게 말한 적 없어"
    - "착각하는 거야"
    - "기억력이 왜 그래"

  blocking:
    - "그 얘기는 그만"
    - "지금 그게 중요해?"
    - "딴 소리 하네"
```

### 5.2 감정적 조작 키워드

```yaml
manipulation_keywords:
  guilt_tripping:
    - "네가 이렇게 해서"
    - "다 네 때문이야"
    - "나한테 왜 이래"
    - "내가 얼마나 힘든지"

  shaming:
    - "창피하지도 않아"
    - "부끄러운 줄 알아"
    - "사람이 어떻게"

  fear_inducing:
    - "두고 봐"
    - "가만 안 둬"
    - "후회하게 될 거야"
```

### 5.3 위협/압박 키워드

```yaml
threat_keywords:
  explicit:
    - "죽여버릴"
    - "가만 안 둬"
    - "없애버릴"

  financial:
    - "돈 안 줄 거야"
    - "상속에서 빼버릴"
    - "한 푼도"

  social:
    - "아는 사람한테 다 말할"
    - "다 알게 될 거야"
    - "망하게 해줄게"
```

---

## 6. 파일 구조

```
src/forensic/analysis/
├── __init__.py              # 모듈 초기화 및 공개 API
├── timeline/
│   ├── __init__.py
│   ├── builder.py           # TimelineBuilder 구현
│   ├── events.py            # TimelineEvent 추출
│   ├── grouping.py          # 기간별 그룹화
│   └── visualization.py     # 시각화 (선택)
├── speaker/
│   ├── __init__.py
│   ├── analyzer.py          # SpeakerAnalyzer 구현
│   ├── identifier.py        # 화자 식별
│   ├── aliases.py           # 별칭 매핑
│   ├── statistics.py        # 통계 계산
│   └── turn_taking.py       # 화자 전환 분석
├── pattern/
│   ├── __init__.py
│   ├── detector.py          # PatternDetector 구현
│   ├── gaslighting.py       # 가스라이팅 탐지
│   ├── repetition.py        # 반복 발언 추적
│   ├── emotional.py         # 감정적 조작 탐지
│   ├── threat.py            # 위협/압박 탐지
│   ├── keywords.py          # 키워드 사전
│   └── custom.py            # 커스텀 패턴
└── models/
    ├── __init__.py
    ├── timeline.py          # Timeline, TimelineEvent 모델
    ├── speaker.py           # SpeakerStatistics, TurnTakingEvent
    └── pattern.py           # 패턴 관련 모델
```

---

## 7. 설정 파일 확장

```yaml
# config.yaml에 추가
forensic:
  analysis:
    # 시계열 분석 설정
    timeline:
      default_grouping: "day"
      extract_events: true

    # 화자 분석 설정
    speaker:
      known_speakers:
        - id: "speaker_1"
          name: "신동식"
          aliases: ["동식", "신씨", "아버지"]
        - id: "speaker_2"
          name: "신기연"
          aliases: ["기연", "신기연씨"]
      unknown_label: "UNKNOWN"

    # 패턴 탐지 설정
    pattern:
      gaslighting:
        enabled: true
        confidence_threshold: 0.7
      repetition:
        enabled: true
        min_occurrences: 3
      emotional:
        enabled: true
        intensity_threshold: "MEDIUM"
      threat:
        enabled: true
        severity_threshold: "LOW"

    # GPU 가속 설정
    gpu:
      enabled: true
      batch_size: 100
```

---

## 8. 비기능적 요구사항

### 8.1 성능

- 183개 파일 전체 분석: < 30분 (DGX Spark 환경)
- 단일 파일 시계열 처리: < 5초
- 화자 식별 정확도: > 95% (알려진 화자)
- 패턴 탐지 처리량: > 1000 segments/second (GPU 가속 시)

### 8.2 정확도

- 가스라이팅 탐지 정밀도: > 85%
- 가스라이팅 탐지 재현율: > 80%
- 화자 별칭 인식률: > 98%

### 8.3 확장성

- 사용자 정의 패턴 무제한 추가 가능
- 새로운 화자 동적 등록 지원
- 키워드 사전 실시간 업데이트

---

## 9. 기술적 제약사항

### 9.1 의존성 목록

```toml
[project]
dependencies = [
    # SPEC-CORE-001, SPEC-IO-001 의존성 포함
    "python-dateutil>=2.8",   # 날짜 파싱
]

[project.optional-dependencies]
pattern = [
    "rapidfuzz>=3.0",         # 유사도 매칭
]
visualization = [
    "plotly>=5.0",            # 시각화
    "pandas>=2.0",            # 데이터 처리
]
gpu = [
    "torch>=2.5",             # GPU 가속 패턴 매칭
    "numpy>=2.0",
]
```

### 9.2 ARM64 호환성 고려

- rapidfuzz: ARM64 호환 확인 필요
- plotly: 순수 Python, 호환성 문제 없음
- torch: CUDA 13.0 ARM64 빌드 사용

---

Version: 1.0.0
Last Updated: 2026-01-18
