---
id: SPEC-REPORT-001
version: "1.0.0"
status: "draft"
created: "2026-01-19"
updated: "2026-01-19"
author: "지니"
priority: "HIGH"
dependencies:
  - SPEC-CORE-001
  - SPEC-IO-001
  - SPEC-TIMELINE-001
  - SPEC-EVIDENCE-001
---

# SPEC-REPORT-001: 보고서 생성 시스템

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-01-19 | 지니 | 초기 작성 - 법적 증거 보고서, 타임라인 보고서, 요약 보고서, 출력 형식 |

---

## 1. 개요

### 1.1 목적

SPEC-EVIDENCE-001에서 추출된 증거와 SPEC-TIMELINE-001의 분석 결과를 기반으로 다양한 형식의 보고서를 생성합니다. 법정 제출용 공식 문서, 시계열 타임라인, 요약 보고서 등 목적에 맞는 체계적인 보고서를 자동으로 생성합니다.

### 1.2 범위

- **법적 증거 보고서**: 법정 제출용 공식 형식의 증거 문서
- **타임라인 보고서**: 시간순 이벤트 정리 및 패턴 발생 시점 표시
- **요약 보고서**: 전체 분석 개요 및 주요 발견사항
- **출력 형식**: Markdown, HTML, PDF(선택적), JSON 지원

### 1.3 의존성

- **SPEC-CORE-001**: Transcript, Segment, Speaker, Evidence 데이터 모델
- **SPEC-IO-001**: StreamReader, ChunkProcessor, BatchProcessor
- **SPEC-TIMELINE-001**: Timeline, TimelineEvent, PatternOccurrence
- **SPEC-EVIDENCE-001**: Evidence, EvidenceChain, ValidationReport

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

**[REQ-U-001]** 시스템은 항상 보고서 ID를 고유하게 생성해야 한다.

**[REQ-U-002]** 모든 보고서는 생성 일시 및 버전 정보를 포함해야 한다.

**[REQ-U-003]** 보고서 출력 시 UTF-8 인코딩을 사용해야 한다.

**[REQ-U-004]** 모든 보고서는 원본 증거에 대한 추적 가능한 참조를 유지해야 한다.

**[REQ-U-005]** 보고서에 포함된 모든 타임스탬프는 ISO 8601 형식을 따라야 한다.

**[REQ-U-006]** 시스템은 항상 보고서 메타데이터(제목, 생성자, 기간)를 포함해야 한다.

### 2.2 이벤트 기반 요구사항 (Event-Driven)

**[REQ-E-001]** 법적 증거 보고서 요청 시, 증거 목록을 중요도순으로 정렬하여 포함해야 한다.

**[REQ-E-002]** 타임라인 보고서 요청 시, 이벤트를 시간순으로 정렬하여 표시해야 한다.

**[REQ-E-003]** 요약 보고서 요청 시, 통계 데이터와 주요 발견사항을 계산하여 포함해야 한다.

**[REQ-E-004]** 보고서 내보내기 요청 시, 지정된 형식(Markdown/HTML/PDF/JSON)으로 변환해야 한다.

**[REQ-E-005]** 증거 체인이 포함될 때, 연결된 증거들의 관계를 시각적으로 표현해야 한다.

**[REQ-E-006]** 화자별 분석 요청 시, 각 화자의 발언 통계와 패턴을 별도로 분류해야 한다.

**[REQ-E-007]** 보고서 생성 완료 시, 무결성 해시를 계산하여 메타데이터에 저장해야 한다.

### 2.3 상태 기반 요구사항 (State-Driven)

**[REQ-S-001]** 증거 중요도가 HIGH인 상태일 때, 보고서 상단에 하이라이트하여 표시해야 한다.

**[REQ-S-002]** 분석 기간이 30일 이상인 상태일 때, 월별 요약 섹션을 자동 생성해야 한다.

**[REQ-S-003]** 패턴 반복 횟수가 5회 이상인 상태일 때, 별도의 반복 패턴 섹션을 생성해야 한다.

**[REQ-S-004]** PDF 출력이 요청된 상태일 때, 인쇄 친화적 레이아웃을 적용해야 한다.

**[REQ-S-005]** 다수의 증거 체인이 존재하는 상태일 때, 체인별 요약을 생성해야 한다.

### 2.4 원치 않는 동작 요구사항 (Unwanted Behavior)

**[REQ-W-001]** 시스템은 검증되지 않은 증거를 보고서에 포함하지 않아야 한다.

**[REQ-W-002]** 시스템은 원본 증거 데이터를 수정하지 않아야 한다.

**[REQ-W-003]** 시스템은 맥락 없이 단독 발언만 보고서에 포함하지 않아야 한다.

**[REQ-W-004]** 시스템은 개인 식별 정보(주민번호, 전화번호 등)를 마스킹 없이 포함하지 않아야 한다.

**[REQ-W-005]** 시스템은 이미 생성된 보고서 파일을 덮어쓰지 않아야 한다.

### 2.5 선택적 요구사항 (Optional Feature)

**[REQ-O-001]** 사용자가 특정 날짜 범위를 지정하면, 해당 기간의 데이터만 보고서에 포함해야 한다.

**[REQ-O-002]** 사용자가 특정 카테고리를 지정하면, 해당 카테고리의 증거만 포함해야 한다.

**[REQ-O-003]** 사용자가 화자 필터를 지정하면, 특정 화자 관련 데이터만 포함해야 한다.

**[REQ-O-004]** 사용자가 목차 생성을 요청하면, 자동으로 목차를 생성해야 한다.

**[REQ-O-005]** 사용자가 그래프 포함을 요청하면, 통계 데이터를 시각화하여 포함해야 한다.

### 2.6 복합 요구사항 (Complex)

**[REQ-C-001]** 법적 증거 보고서가 요청되고 증거가 50개 이상일 때, 자동으로 페이지 구분과 색인을 생성해야 한다.

**[REQ-C-002]** 타임라인 보고서가 요청되고 분석 기간이 6개월 이상일 때, 월별 요약과 전체 요약을 모두 포함해야 한다.

**[REQ-C-003]** 요약 보고서가 요청되고 위협 패턴이 탐지되었을 때, 위협 분석 섹션을 우선적으로 배치하고 권장 조치를 포함해야 한다.

---

## 3. 인터페이스 정의

### 3.1 ReportGenerator

\`\`\`python
class ReportGenerator(Protocol):
    """보고서 생성 기본 인터페이스"""

    def generate_report(
        self,
        report_type: Literal["LEGAL", "TIMELINE", "SUMMARY"],
        data: ReportData,
        config: ReportConfig
    ) -> Report:
        """지정된 유형의 보고서를 생성한다."""
        ...

    def get_supported_formats(self) -> list[str]:
        """지원하는 출력 형식 목록을 반환한다."""
        ...

    def validate_data(
        self,
        data: ReportData
    ) -> ValidationResult:
        """보고서 데이터의 유효성을 검증한다."""
        ...

    def generate_id(self) -> str:
        """고유 보고서 ID를 생성한다. (형식: RPT-YYYYMMDD-XXXX)"""
        ...

    def compute_hash(
        self,
        report: Report
    ) -> str:
        """보고서의 SHA-256 해시를 계산한다."""
        ...
\`\`\`

### 3.2 LegalReportBuilder

\`\`\`python
class LegalReportBuilder(Protocol):
    """법적 증거 보고서 빌더 인터페이스"""

    def set_case_info(
        self,
        case_number: Optional[str],
        court_name: Optional[str],
        parties: dict[str, str]
    ) -> "LegalReportBuilder":
        """사건 정보를 설정한다."""
        ...

    def add_evidence_list(
        self,
        evidence_list: list[Evidence],
        sort_by: Literal["importance", "timestamp", "category"] = "importance"
    ) -> "LegalReportBuilder":
        """증거 목록을 추가한다."""
        ...

    def add_evidence_chain(
        self,
        chain: EvidenceChain
    ) -> "LegalReportBuilder":
        """증거 체인을 추가한다."""
        ...

    def add_chain_of_custody(
        self,
        custody_records: list[CustodyRecord]
    ) -> "LegalReportBuilder":
        """증거 보관 연속성 기록을 추가한다."""
        ...

    def add_integrity_statement(
        self,
        verification_results: list[ValidationResult]
    ) -> "LegalReportBuilder":
        """무결성 진술 섹션을 추가한다."""
        ...

    def add_appendix(
        self,
        title: str,
        content: str
    ) -> "LegalReportBuilder":
        """부록을 추가한다."""
        ...

    def build(self) -> LegalReport:
        """법적 증거 보고서를 생성한다."""
        ...
\`\`\`

### 3.3 TimelineReportBuilder

\`\`\`python
class TimelineReportBuilder(Protocol):
    """타임라인 보고서 빌더 인터페이스"""

    def set_date_range(
        self,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> "TimelineReportBuilder":
        """분석 기간을 설정한다."""
        ...

    def add_timeline_events(
        self,
        events: list[TimelineEvent]
    ) -> "TimelineReportBuilder":
        """타임라인 이벤트를 추가한다."""
        ...

    def add_pattern_occurrences(
        self,
        occurrences: list[PatternOccurrence]
    ) -> "TimelineReportBuilder":
        """패턴 발생 정보를 추가한다."""
        ...

    def add_speaker_activity(
        self,
        speaker: str,
        activity_summary: SpeakerActivitySummary
    ) -> "TimelineReportBuilder":
        """화자별 활동 요약을 추가한다."""
        ...

    def highlight_key_events(
        self,
        event_ids: list[str]
    ) -> "TimelineReportBuilder":
        """주요 이벤트를 하이라이트한다."""
        ...

    def add_monthly_summary(
        self,
        month: str,
        summary: MonthlySummary
    ) -> "TimelineReportBuilder":
        """월별 요약을 추가한다."""
        ...

    def build(self) -> TimelineReport:
        """타임라인 보고서를 생성한다."""
        ...
\`\`\`

### 3.4 SummaryReportBuilder

\`\`\`python
class SummaryReportBuilder(Protocol):
    """요약 보고서 빌더 인터페이스"""

    def set_analysis_overview(
        self,
        total_files: int,
        total_duration: float,
        date_range: tuple[datetime.date, datetime.date]
    ) -> "SummaryReportBuilder":
        """분석 개요를 설정한다."""
        ...

    def add_key_findings(
        self,
        findings: list[KeyFinding]
    ) -> "SummaryReportBuilder":
        """주요 발견사항을 추가한다."""
        ...

    def add_statistics(
        self,
        stats: AnalysisStatistics
    ) -> "SummaryReportBuilder":
        """통계 데이터를 추가한다."""
        ...

    def add_pattern_summary(
        self,
        pattern_stats: PatternStatistics
    ) -> "SummaryReportBuilder":
        """패턴 요약을 추가한다."""
        ...

    def add_speaker_comparison(
        self,
        comparison: SpeakerComparison
    ) -> "SummaryReportBuilder":
        """화자 비교 분석을 추가한다."""
        ...

    def add_recommendations(
        self,
        recommendations: list[Recommendation]
    ) -> "SummaryReportBuilder":
        """권장 조치사항을 추가한다."""
        ...

    def add_conclusion(
        self,
        conclusion: str
    ) -> "SummaryReportBuilder":
        """결론을 추가한다."""
        ...

    def build(self) -> SummaryReport:
        """요약 보고서를 생성한다."""
        ...
\`\`\`

### 3.5 ReportExporter

\`\`\`python
class ReportExporter(Protocol):
    """보고서 내보내기 인터페이스"""

    def export_markdown(
        self,
        report: Report,
        output_path: Path
    ) -> Path:
        """Markdown 형식으로 내보낸다."""
        ...

    def export_html(
        self,
        report: Report,
        output_path: Path,
        include_css: bool = True
    ) -> Path:
        """HTML 형식으로 내보낸다."""
        ...

    def export_pdf(
        self,
        report: Report,
        output_path: Path,
        page_size: str = "A4"
    ) -> Path:
        """PDF 형식으로 내보낸다. (선택적)"""
        ...

    def export_json(
        self,
        report: Report,
        output_path: Path,
        include_metadata: bool = True
    ) -> Path:
        """JSON 형식으로 내보낸다."""
        ...

    def get_template(
        self,
        report_type: str,
        format: str
    ) -> str:
        """보고서 유형과 형식에 맞는 템플릿을 반환한다."""
        ...

    def register_custom_template(
        self,
        name: str,
        template: str
    ) -> None:
        """커스텀 템플릿을 등록한다."""
        ...
\`\`\`

---

## 4. 데이터 모델

### 4.1 Report (보고서 기본)

\`\`\`python
class Report(BaseModel):
    """보고서 기본 모델"""
    id: str                           # 보고서 ID (RPT-YYYYMMDD-XXXX)
    report_type: ReportType           # 보고서 유형
    title: str                        # 보고서 제목
    created_at: datetime              # 생성 일시
    created_by: str                   # 생성자
    version: str                      # 버전
    date_range: tuple[datetime.date, datetime.date]  # 분석 기간
    integrity_hash: str               # SHA-256 해시
    metadata: dict[str, Any]          # 추가 메타데이터
\`\`\`

### 4.2 ReportType (보고서 유형)

\`\`\`python
class ReportType(str, Enum):
    """보고서 유형"""
    LEGAL = "LEGAL"           # 법적 증거 보고서
    TIMELINE = "TIMELINE"     # 타임라인 보고서
    SUMMARY = "SUMMARY"       # 요약 보고서
\`\`\`

### 4.3 LegalReport (법적 증거 보고서)

\`\`\`python
class LegalReport(Report):
    """법적 증거 보고서 모델"""
    case_info: Optional[CaseInfo]     # 사건 정보
    evidence_list: list[EvidenceSummary]  # 증거 목록
    evidence_chains: list[EvidenceChainSummary]  # 증거 체인
    chain_of_custody: list[CustodyRecord]  # 증거 보관 연속성
    integrity_statement: str          # 무결성 진술
    appendices: list[Appendix]        # 부록
    signature_placeholder: str        # 서명 위치
\`\`\`

### 4.4 TimelineReport (타임라인 보고서)

\`\`\`python
class TimelineReport(Report):
    """타임라인 보고서 모델"""
    total_events: int                 # 총 이벤트 수
    events: list[TimelineEventSummary]  # 이벤트 목록
    pattern_occurrences: list[PatternOccurrenceSummary]  # 패턴 발생
    speaker_activities: dict[str, SpeakerActivitySummary]  # 화자별 활동
    key_events: list[str]             # 주요 이벤트 ID
    monthly_summaries: dict[str, MonthlySummary]  # 월별 요약
\`\`\`

### 4.5 SummaryReport (요약 보고서)

\`\`\`python
class SummaryReport(Report):
    """요약 보고서 모델"""
    analysis_overview: AnalysisOverview  # 분석 개요
    key_findings: list[KeyFinding]    # 주요 발견사항
    statistics: AnalysisStatistics    # 통계 데이터
    pattern_summary: PatternStatistics  # 패턴 요약
    speaker_comparison: SpeakerComparison  # 화자 비교
    recommendations: list[Recommendation]  # 권장 조치
    conclusion: str                   # 결론
\`\`\`

### 4.6 CaseInfo (사건 정보)

\`\`\`python
class CaseInfo(BaseModel):
    """사건 정보 모델"""
    case_number: Optional[str]        # 사건 번호
    court_name: Optional[str]         # 법원명
    plaintiff: Optional[str]          # 원고/고소인
    defendant: Optional[str]          # 피고/피고소인
    case_type: Optional[str]          # 사건 유형 (민사/형사)
    filing_date: Optional[datetime.date]  # 제소/고소 일자
\`\`\`

### 4.7 EvidenceSummary (증거 요약)

\`\`\`python
class EvidenceSummary(BaseModel):
    """증거 요약 모델"""
    evidence_id: str                  # 증거 ID
    category: str                     # 카테고리
    importance: Literal["HIGH", "MEDIUM", "LOW"]
    timestamp: datetime               # 발생 시점
    speaker: str                      # 화자
    content_sample: str               # 대표 발언
    context_summary: str              # 맥락 요약
    source_reference: str             # 원본 참조
\`\`\`

### 4.8 KeyFinding (주요 발견사항)

\`\`\`python
class KeyFinding(BaseModel):
    """주요 발견사항 모델"""
    finding_id: str                   # 발견사항 ID
    title: str                        # 제목
    description: str                  # 설명
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    supporting_evidence: list[str]    # 근거 증거 ID
    first_occurrence: datetime.date   # 최초 발생일
    occurrence_count: int             # 발생 횟수
\`\`\`

### 4.9 AnalysisStatistics (분석 통계)

\`\`\`python
class AnalysisStatistics(BaseModel):
    """분석 통계 모델"""
    total_files: int                  # 총 파일 수
    total_duration_minutes: float     # 총 녹취 시간 (분)
    total_segments: int               # 총 세그먼트 수
    total_evidence: int               # 총 증거 수
    evidence_by_category: dict[str, int]  # 카테고리별 증거 수
    evidence_by_importance: dict[str, int]  # 중요도별 증거 수
    patterns_detected: dict[str, int]  # 탐지된 패턴 유형별 수
    speaker_segment_counts: dict[str, int]  # 화자별 발언 수
\`\`\`

### 4.10 Recommendation (권장 조치)

\`\`\`python
class Recommendation(BaseModel):
    """권장 조치 모델"""
    recommendation_id: str            # 권장 ID
    priority: Literal["URGENT", "HIGH", "MEDIUM", "LOW"]
    title: str                        # 제목
    description: str                  # 설명
    rationale: str                    # 근거
    related_findings: list[str]       # 관련 발견사항 ID
\`\`\`

### 4.11 ReportConfig (보고서 설정)

\`\`\`python
class ReportConfig(BaseModel):
    """보고서 설정 모델"""
    output_format: Literal["MARKDOWN", "HTML", "PDF", "JSON"]
    language: str = "ko"              # 출력 언어
    include_toc: bool = True          # 목차 포함
    include_statistics: bool = True   # 통계 포함
    include_charts: bool = False      # 차트 포함 (선택적)
    date_filter: Optional[tuple[datetime.date, datetime.date]] = None
    category_filter: Optional[list[str]] = None
    speaker_filter: Optional[list[str]] = None
    min_importance: Literal["HIGH", "MEDIUM", "LOW"] = "LOW"
    page_size: str = "A4"             # PDF 페이지 크기
    template: Optional[str] = None    # 커스텀 템플릿
\`\`\`

---

## 5. 보고서 ID 규칙

### 5.1 ID 형식

\`\`\`
RPT-YYYYMMDD-XXXX

예시:
- RPT-20250715-0001  # 2025년 7월 15일 첫 번째 보고서
- RPT-20251201-0047  # 2025년 12월 1일 47번째 보고서
\`\`\`

### 5.2 파일명 규칙

\`\`\`
{report_id}_{report_type}.{extension}

예시:
- RPT-20250715-0001_LEGAL.md
- RPT-20250715-0002_TIMELINE.html
- RPT-20250715-0003_SUMMARY.json
\`\`\`

---

## 6. 파일 구조

\`\`\`
src/forensic/report/
├── __init__.py              # 모듈 초기화 및 공개 API
├── generator/
│   ├── __init__.py
│   ├── report_generator.py      # ReportGenerator 구현
│   ├── id_generator.py          # ID 생성기
│   └── validator.py             # 데이터 검증
├── builders/
│   ├── __init__.py
│   ├── legal_builder.py         # LegalReportBuilder 구현
│   ├── timeline_builder.py      # TimelineReportBuilder 구현
│   └── summary_builder.py       # SummaryReportBuilder 구현
├── exporters/
│   ├── __init__.py
│   ├── report_exporter.py       # ReportExporter 구현
│   ├── markdown_exporter.py     # Markdown 내보내기
│   ├── html_exporter.py         # HTML 내보내기
│   ├── pdf_exporter.py          # PDF 내보내기 (선택)
│   └── json_exporter.py         # JSON 내보내기
├── templates/
│   ├── __init__.py
│   ├── legal/
│   │   ├── korean_criminal.md   # 한국 형사소송용
│   │   ├── korean_civil.md      # 한국 민사소송용
│   │   └── base_legal.html      # 기본 HTML 템플릿
│   ├── timeline/
│   │   ├── chronological.md     # 시간순 템플릿
│   │   └── monthly.md           # 월별 템플릿
│   └── summary/
│       ├── executive.md         # 요약 보고서
│       └── detailed.md          # 상세 보고서
├── models/
│   ├── __init__.py
│   ├── report.py                # 보고서 기본 모델
│   ├── legal.py                 # 법적 보고서 모델
│   ├── timeline.py              # 타임라인 모델
│   ├── summary.py               # 요약 모델
│   └── config.py                # 설정 모델
└── utils/
    ├── __init__.py
    ├── formatters.py            # 포맷팅 유틸리티
    ├── sanitizers.py            # 데이터 정제 (PII 마스킹)
    └── statistics.py            # 통계 계산
\`\`\`

---

## 7. 설정 파일 확장

\`\`\`yaml
# config.yaml에 추가
forensic:
  report:
    # 기본 설정
    default_format: "MARKDOWN"
    default_language: "ko"
    include_toc: true
    include_statistics: true

    # 법적 보고서 설정
    legal:
      default_template: "korean_criminal"
      include_chain_of_custody: true
      include_integrity_statement: true
      max_evidence_per_page: 10

    # 타임라인 보고서 설정
    timeline:
      default_template: "chronological"
      highlight_threshold: 3  # 3회 이상 반복 시 하이라이트
      include_monthly_summary: true

    # 요약 보고서 설정
    summary:
      default_template: "executive"
      max_key_findings: 10
      include_recommendations: true

    # 내보내기 설정
    export:
      output_encoding: "utf-8"
      pdf_page_size: "A4"
      html_include_css: true
      json_include_metadata: true

    # PII 마스킹 설정
    pii_masking:
      enabled: true
      patterns:
        - "phone"       # 전화번호
        - "id_number"   # 주민번호
        - "address"     # 주소
\`\`\`

---

## 8. 비기능적 요구사항

### 8.1 성능

- 보고서 생성 시간: < 5초 (100개 증거 기준)
- 대용량 보고서 생성: < 30초 (1000개 증거 기준)
- HTML 렌더링 시간: < 2초
- PDF 생성 시간: < 10초 (100페이지 기준)

### 8.2 정확도

- 타임스탬프 정확도: 100%
- 증거 참조 정확도: 100%
- 통계 계산 정확도: 100%

### 8.3 확장성

- 새로운 보고서 유형 추가 가능
- 커스텀 템플릿 등록 가능
- 다국어 지원 (한국어, 영어)

### 8.4 보안

- PII 자동 마스킹
- 민감 정보 로깅 방지
- 출력 파일 권한 제한

---

## 9. 기술적 제약사항

### 9.1 의존성 목록

\`\`\`toml
[project]
dependencies = [
    # SPEC-CORE-001, SPEC-IO-001, SPEC-TIMELINE-001, SPEC-EVIDENCE-001 의존성 포함
    "pydantic>=2.0",
    "python-dateutil>=2.8",
    "jinja2>=3.0",        # 템플릿 엔진
    "markdown>=3.0",      # 마크다운 변환
]

[project.optional-dependencies]
html = [
    "pygments>=2.0",      # 코드 하이라이팅
]
pdf = [
    "weasyprint>=60.0",   # PDF 생성 (선택)
]
charts = [
    "plotly>=5.0",        # 차트 생성 (선택)
]
\`\`\`

### 9.2 ARM64 호환성 고려

- jinja2: 순수 Python, 호환성 문제 없음
- markdown: 순수 Python, 호환성 문제 없음
- weasyprint: ARM64 빌드 확인 필요 (선택적 기능)
- plotly: 순수 Python + JS, 호환성 문제 없음

---

Version: 1.0.0
Last Updated: 2026-01-19
