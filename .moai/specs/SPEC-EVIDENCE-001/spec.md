---
id: SPEC-EVIDENCE-001
version: "1.0.0"
status: "draft"
created: "2026-01-18"
updated: "2026-01-18"
author: "지니"
priority: "HIGH"
dependencies:
  - SPEC-CORE-001
  - SPEC-IO-001
  - SPEC-TIMELINE-001
---

# SPEC-EVIDENCE-001: 증거 추출 및 맥락 보존 시스템

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-01-18 | 지니 | 초기 작성 - 증거 추출, 맥락 보존, 검증, 내보내기 모듈 |

---

## 1. 개요

### 1.1 목적

SPEC-TIMELINE-001에서 탐지된 패턴을 법적 증거 형식으로 변환하고, 증거의 맥락을 보존하며, 무결성을 검증하는 시스템을 구현합니다. 형사소송에서 사용될 수 있는 체계적이고 신뢰할 수 있는 증거 자료를 생성합니다.

### 1.2 범위

- **증거 추출**: 탐지된 패턴에서 법적 증거 생성
- **맥락 보존**: 증거 전후 발언의 맥락 자동 추출 및 연결
- **증거 검증**: 무결성 검증 및 원본 참조 유지
- **증거 내보내기**: JSON 및 법적 문서 형식 출력

### 1.3 의존성

- **SPEC-CORE-001**: Transcript, Segment, Speaker, Evidence 데이터 모델
- **SPEC-IO-001**: StreamReader, ChunkProcessor, BatchProcessor
- **SPEC-TIMELINE-001**: PatternDetector, GaslightingPattern, ThreatPattern 등

### 1.4 대상 시스템

| 항목 | 사양 |
|------|------|
| 플랫폼 | NVIDIA DGX Spark |
| CPU | 20코어 ARM (Cortex-X925 + A725) |
| GPU | Blackwell 6,144 CUDA cores |
| 메모리 | 128GB 통합 LPDDR5x |
| 분석 대상 | 183개 파일, 30분+ 분량, 2025.06~12 |
| 화자 | 신동식, 신기연 (2인) |

---

## 2. 요구사항 (EARS 형식)

### 2.1 유비쿼터스 요구사항 (Ubiquitous)

**[REQ-U-001]** 시스템은 항상 증거 ID를 고유하게 생성해야 한다.

**[REQ-U-002]** 모든 증거는 원본 녹취 파일에 대한 참조를 유지해야 한다.

**[REQ-U-003]** 증거의 타임스탬프는 원본 세그먼트의 타임스탬프와 일치해야 한다.

**[REQ-U-004]** 증거 내보내기 시 UTF-8 인코딩을 사용해야 한다.

**[REQ-U-005]** 모든 증거는 생성 시점의 메타데이터를 포함해야 한다.

### 2.2 이벤트 기반 요구사항 (Event-Driven)

**[REQ-E-001]** 패턴이 탐지될 때, Evidence 모델로 자동 변환되어야 한다.

**[REQ-E-002]** 증거가 생성될 때, 전후 맥락(context_before, context_after)을 자동 추출해야 한다.

**[REQ-E-003]** 증거가 저장될 때, SHA-256 해시를 생성하여 무결성 검증 데이터를 저장해야 한다.

**[REQ-E-004]** 중복 증거가 감지될 때, 기존 증거에 참조를 추가하고 병합을 제안해야 한다.

**[REQ-E-005]** 내보내기 요청 시, 지정된 형식(JSON/Legal)으로 변환되어야 한다.

**[REQ-E-006]** 증거 체인이 요청될 때, 관련 증거들의 연결 관계를 추출해야 한다.

### 2.3 상태 기반 요구사항 (State-Driven)

**[REQ-S-001]** 증거 중요도가 HIGH인 상태일 때, 우선 내보내기 대상으로 표시해야 한다.

**[REQ-S-002]** 맥락 범위가 설정된 상태일 때, 해당 범위 내의 발언을 추출해야 한다.

**[REQ-S-003]** 동일 날짜에 다수의 증거가 존재하는 상태일 때, 시간순으로 그룹화해야 한다.

**[REQ-S-004]** 검증이 실패한 상태일 때, 경고 플래그를 설정하고 관리자에게 알려야 한다.

### 2.4 원치 않는 동작 요구사항 (Unwanted Behavior)

**[REQ-W-001]** 시스템은 원본 녹취 데이터를 수정하지 않아야 한다.

**[REQ-W-002]** 시스템은 맥락 없이 단독 증거를 생성하지 않아야 한다.

**[REQ-W-003]** 시스템은 무결성 검증 없이 증거를 내보내지 않아야 한다.

**[REQ-W-004]** 시스템은 원본 참조가 없는 증거를 생성하지 않아야 한다.

**[REQ-W-005]** 시스템은 이미 내보낸 증거를 수정하지 않아야 한다.

### 2.5 선택적 요구사항 (Optional Feature)

**[REQ-O-001]** 사용자가 맥락 범위를 지정하면, 해당 범위의 발언을 추출해야 한다.

**[REQ-O-002]** 사용자가 증거 필터를 지정하면, 해당 조건의 증거만 내보내야 한다.

**[REQ-O-003]** 사용자가 법적 형식을 요청하면, 소송용 문서 형식으로 내보내야 한다.

**[REQ-O-004]** 사용자가 시각화를 요청하면, 증거 관계 그래프를 생성해야 한다.

### 2.6 복합 요구사항 (Complex)

**[REQ-C-001]** 가스라이팅 패턴이 탐지되고 반복 횟수가 3회 이상일 때, 중요도를 HIGH로 자동 설정하고 관련 증거를 체인으로 연결해야 한다.

**[REQ-C-002]** 위협 패턴이 탐지되고 심각도가 CRITICAL일 때, 즉시 우선 증거로 분류하고 알림을 생성해야 한다.

**[REQ-C-003]** 동일 화자가 동일 패턴을 5일 이상 반복할 때, 지속적 학대 증거로 분류하고 시계열 요약을 생성해야 한다.

---

## 3. 인터페이스 정의

### 3.1 EvidenceExtractor

```python
class EvidenceExtractor(Protocol):
    """증거 추출 인터페이스"""

    def extract_from_pattern(
        self,
        pattern: Union[GaslightingPattern, ThreatPattern, EmotionalManipulation],
        segments: list[Segment]
    ) -> Evidence:
        """탐지된 패턴에서 증거를 추출한다."""
        ...

    def extract_batch(
        self,
        patterns: list[Union[GaslightingPattern, ThreatPattern, EmotionalManipulation]],
        segments: list[Segment]
    ) -> list[Evidence]:
        """다수의 패턴에서 증거를 일괄 추출한다."""
        ...

    def assign_importance(
        self,
        evidence: Evidence,
        occurrence_count: int,
        pattern_type: str
    ) -> Literal["HIGH", "MEDIUM", "LOW"]:
        """증거 중요도를 할당한다."""
        ...

    def categorize(
        self,
        evidence: Evidence
    ) -> Literal["GASLIGHTING", "EMOTIONAL_MANIPULATION", "THREAT", "REPEATED_ABUSE"]:
        """증거를 카테고리로 분류한다."""
        ...

    def generate_id(self) -> str:
        """고유 증거 ID를 생성한다. (형식: EVD-YYYYMMDD-XXXX)"""
        ...
```

### 3.2 ContextPreserver

```python
class ContextPreserver(Protocol):
    """맥락 보존 인터페이스"""

    def extract_context(
        self,
        segment: Segment,
        all_segments: list[Segment],
        before_count: int = 3,
        after_count: int = 3
    ) -> tuple[str, str]:
        """대상 세그먼트의 전후 맥락을 추출한다."""
        ...

    def get_conversation_flow(
        self,
        evidence: Evidence,
        all_segments: list[Segment],
        window_size: int = 10
    ) -> list[Segment]:
        """증거 주변의 전체 대화 흐름을 추출한다."""
        ...

    def link_related_segments(
        self,
        evidence: Evidence,
        all_segments: list[Segment],
        similarity_threshold: float = 0.7
    ) -> list[str]:
        """관련된 발언 세그먼트 ID를 연결한다."""
        ...

    def get_position_in_transcript(
        self,
        segment: Segment,
        transcript: Transcript
    ) -> dict[str, Any]:
        """전체 녹취 내에서의 위치 정보를 반환한다."""
        ...

    def set_context_range(
        self,
        before_count: int,
        after_count: int
    ) -> None:
        """맥락 범위 설정을 변경한다."""
        ...
```

### 3.3 EvidenceValidator

```python
class EvidenceValidator(Protocol):
    """증거 검증 인터페이스"""

    def validate_integrity(
        self,
        evidence: Evidence
    ) -> ValidationResult:
        """증거 무결성을 검증한다."""
        ...

    def verify_timestamp(
        self,
        evidence: Evidence,
        original_segment: Segment
    ) -> bool:
        """타임스탬프 일치를 검증한다."""
        ...

    def verify_source_reference(
        self,
        evidence: Evidence,
        transcript: Transcript
    ) -> bool:
        """원본 참조 유효성을 검증한다."""
        ...

    def compute_hash(
        self,
        evidence: Evidence
    ) -> str:
        """증거의 SHA-256 해시를 계산한다."""
        ...

    def detect_duplicates(
        self,
        evidence: Evidence,
        existing_evidence: list[Evidence]
    ) -> list[Evidence]:
        """중복 증거를 탐지한다."""
        ...

    def merge_duplicates(
        self,
        evidence_list: list[Evidence]
    ) -> Evidence:
        """중복 증거를 병합한다."""
        ...

    def get_validation_report(
        self,
        evidence_list: list[Evidence]
    ) -> ValidationReport:
        """전체 증거 검증 보고서를 생성한다."""
        ...
```

### 3.4 EvidenceExporter

```python
class EvidenceExporter(Protocol):
    """증거 내보내기 인터페이스"""

    def export_json(
        self,
        evidence_list: list[Evidence],
        output_path: Path,
        include_context: bool = True
    ) -> Path:
        """JSON 형식으로 내보낸다."""
        ...

    def export_legal_format(
        self,
        evidence_list: list[Evidence],
        output_path: Path,
        template: str = "korean_civil"
    ) -> Path:
        """법적 증거 형식으로 내보낸다."""
        ...

    def export_chain_of_custody(
        self,
        evidence_list: list[Evidence],
        output_path: Path
    ) -> Path:
        """증거 체인 (연속성) 문서를 생성한다."""
        ...

    def export_summary(
        self,
        evidence_list: list[Evidence],
        output_path: Path
    ) -> Path:
        """증거 요약 보고서를 생성한다."""
        ...

    def filter_by_importance(
        self,
        evidence_list: list[Evidence],
        min_importance: Literal["HIGH", "MEDIUM", "LOW"]
    ) -> list[Evidence]:
        """중요도로 증거를 필터링한다."""
        ...

    def filter_by_category(
        self,
        evidence_list: list[Evidence],
        categories: list[str]
    ) -> list[Evidence]:
        """카테고리로 증거를 필터링한다."""
        ...

    def filter_by_date_range(
        self,
        evidence_list: list[Evidence],
        start_date: datetime.date,
        end_date: datetime.date
    ) -> list[Evidence]:
        """날짜 범위로 증거를 필터링한다."""
        ...
```

---

## 4. 데이터 모델

### 4.1 Evidence (증거) - 확장

SPEC-CORE-001의 Evidence 모델을 확장합니다.

```python
class Evidence(BaseModel):
    """증거 모델 (확장)"""
    # 기본 필드 (SPEC-CORE-001)
    id: str                           # 증거 ID (EVD-YYYYMMDD-XXXX)
    transcript_id: str                # 원본 녹취 ID
    segment_ids: list[str]            # 관련 세그먼트 ID 목록
    category: EvidenceCategory        # 증거 분류
    description: str                  # 증거 설명
    importance: Literal["HIGH", "MEDIUM", "LOW"]
    context_before: str               # 전후 맥락 (이전)
    context_after: str                # 전후 맥락 (이후)

    # 확장 필드
    created_at: datetime              # 증거 생성 시점
    source_pattern_type: str          # 원본 패턴 유형
    source_pattern_id: str            # 원본 패턴 ID
    speaker: str                      # 발화자
    target: Optional[str]             # 대상자 (있는 경우)
    timestamp: datetime               # 증거 발생 시점
    content_sample: str               # 대표 발언 샘플
    occurrence_count: int             # 발생 횟수
    confidence: float                 # 탐지 신뢰도 (0.0 ~ 1.0)
    integrity_hash: str               # SHA-256 해시
    related_evidence_ids: list[str]   # 관련 증거 ID 목록
    validation_status: Literal["VALID", "INVALID", "PENDING"]
    export_status: Literal["NOT_EXPORTED", "EXPORTED", "MODIFIED"]
    metadata: dict[str, Any]          # 추가 메타데이터
```

### 4.2 EvidenceCategory (증거 카테고리)

```python
class EvidenceCategory(str, Enum):
    """증거 카테고리"""
    GASLIGHTING = "GASLIGHTING"                 # 가스라이팅
    EMOTIONAL_MANIPULATION = "EMOTIONAL_MANIPULATION"  # 감정조작
    THREAT = "THREAT"                           # 위협/압박
    REPEATED_ABUSE = "REPEATED_ABUSE"           # 반복적 학대
    DENIAL = "DENIAL"                           # 부정
    ISOLATION = "ISOLATION"                     # 고립화
    FINANCIAL_ABUSE = "FINANCIAL_ABUSE"         # 경제적 학대
    OTHER = "OTHER"                             # 기타
```

### 4.3 ValidationResult (검증 결과)

```python
class ValidationResult(BaseModel):
    """검증 결과 모델"""
    evidence_id: str                  # 증거 ID
    is_valid: bool                    # 유효 여부
    timestamp_valid: bool             # 타임스탬프 일치
    source_valid: bool                # 원본 참조 유효
    hash_valid: bool                  # 해시 일치
    duplicate_found: bool             # 중복 발견 여부
    duplicate_ids: list[str]          # 중복 증거 ID 목록
    validation_time: datetime         # 검증 시점
    issues: list[str]                 # 발견된 문제점
    recommendations: list[str]        # 권장 조치
```

### 4.4 ValidationReport (검증 보고서)

```python
class ValidationReport(BaseModel):
    """검증 보고서 모델"""
    report_id: str                    # 보고서 ID
    generated_at: datetime            # 생성 시점
    total_evidence: int               # 총 증거 수
    valid_count: int                  # 유효 증거 수
    invalid_count: int                # 무효 증거 수
    duplicate_count: int              # 중복 증거 수
    validation_results: list[ValidationResult]  # 개별 결과
    summary: str                      # 요약
    integrity_score: float            # 전체 무결성 점수 (0.0 ~ 1.0)
```

### 4.5 EvidenceChain (증거 체인)

```python
class EvidenceChain(BaseModel):
    """증거 체인 모델"""
    chain_id: str                     # 체인 ID
    evidence_ids: list[str]           # 연결된 증거 ID 목록
    chain_type: Literal["TEMPORAL", "PATTERN", "SPEAKER", "TOPIC"]
    start_date: datetime.date         # 시작 날짜
    end_date: datetime.date           # 종료 날짜
    speaker: str                      # 관련 화자
    pattern_type: str                 # 주요 패턴 유형
    description: str                  # 체인 설명
    total_occurrences: int            # 총 발생 횟수
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
```

### 4.6 LegalDocument (법적 문서)

```python
class LegalDocument(BaseModel):
    """법적 문서 모델"""
    document_id: str                  # 문서 ID
    title: str                        # 제목
    case_reference: Optional[str]     # 사건 번호 (있는 경우)
    generated_at: datetime            # 생성 시점
    evidence_summary: list[EvidenceSummary]  # 증거 요약
    timeline_summary: str             # 시계열 요약
    pattern_analysis: str             # 패턴 분석 결과
    speaker_analysis: str             # 화자 분석 결과
    conclusion: str                   # 결론
    appendix_paths: list[Path]        # 첨부 파일 경로
    integrity_statement: str          # 무결성 진술
    signature_placeholder: str        # 서명 위치
```

### 4.7 ExportConfig (내보내기 설정)

```python
class ExportConfig(BaseModel):
    """내보내기 설정 모델"""
    format: Literal["JSON", "LEGAL", "SUMMARY", "CHAIN"]
    include_context: bool = True
    include_metadata: bool = True
    min_importance: Literal["HIGH", "MEDIUM", "LOW"] = "LOW"
    categories: Optional[list[EvidenceCategory]] = None
    date_range: Optional[tuple[datetime.date, datetime.date]] = None
    template: str = "korean_civil"
    output_encoding: str = "utf-8"
    include_hash: bool = True
```

---

## 5. 증거 ID 규칙

### 5.1 ID 형식

```
EVD-YYYYMMDD-XXXX

예시:
- EVD-20250715-0001  # 2025년 7월 15일 첫 번째 증거
- EVD-20251201-0047  # 2025년 12월 1일 47번째 증거
```

### 5.2 체인 ID 형식

```
CHN-YYYYMM-XXXX

예시:
- CHN-202507-0001  # 2025년 7월 첫 번째 체인
```

---

## 6. 파일 구조

```
src/forensic/evidence/
├── __init__.py              # 모듈 초기화 및 공개 API
├── extractor/
│   ├── __init__.py
│   ├── evidence_extractor.py    # EvidenceExtractor 구현
│   ├── importance.py            # 중요도 할당 로직
│   ├── categorizer.py           # 카테고리 분류 로직
│   └── id_generator.py          # ID 생성기
├── context/
│   ├── __init__.py
│   ├── preserver.py             # ContextPreserver 구현
│   ├── flow_extractor.py        # 대화 흐름 추출
│   └── linker.py                # 관련 세그먼트 연결
├── validator/
│   ├── __init__.py
│   ├── evidence_validator.py    # EvidenceValidator 구현
│   ├── integrity.py             # 무결성 검증
│   ├── duplicate.py             # 중복 탐지
│   └── report.py                # 검증 보고서 생성
├── exporter/
│   ├── __init__.py
│   ├── evidence_exporter.py     # EvidenceExporter 구현
│   ├── json_exporter.py         # JSON 내보내기
│   ├── legal_exporter.py        # 법적 문서 내보내기
│   ├── chain_exporter.py        # 체인 문서 내보내기
│   └── templates/               # 법적 문서 템플릿
│       ├── korean_civil.md      # 한국 민사소송용
│       └── korean_criminal.md   # 한국 형사소송용
└── models/
    ├── __init__.py
    ├── evidence.py              # Evidence 확장 모델
    ├── validation.py            # 검증 관련 모델
    ├── chain.py                 # 체인 모델
    └── export.py                # 내보내기 관련 모델
```

---

## 7. 설정 파일 확장

```yaml
# config.yaml에 추가
forensic:
  evidence:
    # 증거 추출 설정
    extraction:
      auto_categorize: true
      importance_rules:
        high_threshold: 3           # 3회 이상 반복 시 HIGH
        critical_patterns:
          - "EXPLICIT_THREAT"
          - "FINANCIAL_THREAT"

    # 맥락 보존 설정
    context:
      default_before_count: 3       # 이전 발언 개수
      default_after_count: 3        # 이후 발언 개수
      max_context_length: 1000      # 최대 맥락 길이 (문자)

    # 검증 설정
    validation:
      compute_hash: true
      hash_algorithm: "sha256"
      duplicate_threshold: 0.9      # 중복 판정 임계값
      auto_merge_duplicates: false

    # 내보내기 설정
    export:
      default_format: "JSON"
      include_context: true
      include_metadata: true
      output_encoding: "utf-8"
      legal_template: "korean_criminal"

    # 체인 설정
    chain:
      min_occurrences: 3            # 체인 생성 최소 발생 횟수
      max_gap_days: 7               # 체인 내 최대 간격 (일)
```

---

## 8. 비기능적 요구사항

### 8.1 성능

- 증거 추출 처리량: > 500 patterns/second
- 맥락 추출 시간: < 10ms per segment
- 검증 처리 시간: < 50ms per evidence
- 내보내기 시간: < 5초 (100개 증거 기준)

### 8.2 정확도

- 중복 탐지 정확도: > 95%
- 카테고리 분류 정확도: > 90%
- 타임스탬프 일치율: 100%

### 8.3 무결성

- 모든 증거의 해시 검증 가능
- 원본 참조 100% 유지
- 내보내기 후 불변성 보장

### 8.4 확장성

- 새로운 카테고리 동적 추가 가능
- 법적 문서 템플릿 커스터마이징 가능
- 다국어 내보내기 형식 지원 (향후)

---

## 9. 기술적 제약사항

### 9.1 의존성 목록

```toml
[project]
dependencies = [
    # SPEC-CORE-001, SPEC-IO-001, SPEC-TIMELINE-001 의존성 포함
    "pydantic>=2.0",
    "python-dateutil>=2.8",
]

[project.optional-dependencies]
export = [
    "jinja2>=3.0",            # 템플릿 엔진
    "markdown>=3.0",          # 마크다운 변환
]
pdf = [
    "weasyprint>=60.0",       # PDF 생성 (선택)
]
```

### 9.2 ARM64 호환성 고려

- jinja2: 순수 Python, 호환성 문제 없음
- markdown: 순수 Python, 호환성 문제 없음
- weasyprint: ARM64 빌드 확인 필요 (선택적 기능)

---

Version: 1.0.0
Last Updated: 2026-01-18
