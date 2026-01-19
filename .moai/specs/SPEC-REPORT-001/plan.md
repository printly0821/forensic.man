---
id: SPEC-REPORT-001
type: plan
version: "1.0.0"
created: "2026-01-19"
updated: "2026-01-19"
author: "지니"
---

# SPEC-REPORT-001 구현 계획

## 1. 구현 개요

### 1.1 목표

SPEC-EVIDENCE-001에서 추출된 증거와 SPEC-TIMELINE-001의 분석 결과를 기반으로, 법정 제출용 보고서, 타임라인 보고서, 요약 보고서를 다양한 형식(Markdown, HTML, PDF, JSON)으로 생성하는 시스템을 구현합니다.

### 1.2 의존성 확인

| 의존 SPEC | 필요 컴포넌트 | 상태 |
|-----------|--------------|------|
| SPEC-CORE-001 | Transcript, Segment, Speaker, Evidence 모델 | 대기 중 |
| SPEC-IO-001 | StreamReader, ChunkProcessor, BatchProcessor | 대기 중 |
| SPEC-TIMELINE-001 | Timeline, TimelineEvent, PatternOccurrence | 대기 중 |
| SPEC-EVIDENCE-001 | Evidence, EvidenceChain, ValidationReport | 대기 중 |

---

## 2. 구현 단계

### Phase 1: 데이터 모델 정의 (Priority: HIGH)

**목표**: 보고서 시스템의 기반 데이터 모델 정의

**작업 항목**:

1. 보고서 기본 모델 정의
   - `Report` 기본 모델 구현
   - `ReportType` Enum 정의
   - `ReportConfig` 설정 모델 구현

2. 법적 보고서 모델 정의
   - `LegalReport` 모델 구현
   - `CaseInfo` 사건 정보 모델
   - `EvidenceSummary` 증거 요약 모델
   - `CustodyRecord` 증거 보관 기록 모델

3. 타임라인 보고서 모델 정의
   - `TimelineReport` 모델 구현
   - `TimelineEventSummary` 이벤트 요약 모델
   - `SpeakerActivitySummary` 화자 활동 요약 모델
   - `MonthlySummary` 월별 요약 모델

4. 요약 보고서 모델 정의
   - `SummaryReport` 모델 구현
   - `AnalysisOverview` 분석 개요 모델
   - `KeyFinding` 주요 발견사항 모델
   - `AnalysisStatistics` 통계 모델
   - `Recommendation` 권장 조치 모델

**완료 조건**:
- 모든 모델이 Pydantic BaseModel 기반
- 직렬화/역직렬화 테스트 통과
- 타입 힌트 완전성

---

### Phase 2: 보고서 생성기 핵심 (ReportGenerator) (Priority: HIGH)

**목표**: 보고서 생성의 기본 인프라 구현

**작업 항목**:

1. ReportGenerator 기본 구현
   - `generate_report()` - 보고서 생성 진입점
   - `validate_data()` - 입력 데이터 검증
   - `get_supported_formats()` - 지원 형식 조회

2. 보고서 ID 생성기 구현
   - `generate_id()` - RPT-YYYYMMDD-XXXX 형식
   - 순번 관리 및 중복 방지
   - 날짜별 리셋 로직

3. 무결성 검증 구현
   - `compute_hash()` - SHA-256 해시 계산
   - 보고서 메타데이터 해시 포함

4. 데이터 검증 구현
   - 입력 데이터 유효성 검사
   - 필수 필드 확인
   - 참조 무결성 검증

**기술적 접근**:

\`\`\`python
class ReportGeneratorImpl:
    def generate_report(
        self,
        report_type: ReportType,
        data: ReportData,
        config: ReportConfig
    ) -> Report:
        # 1. 데이터 검증
        validation = self.validate_data(data)
        if not validation.is_valid:
            raise ValidationError(validation.errors)

        # 2. 빌더 선택
        builder = self._get_builder(report_type)

        # 3. 보고서 생성
        report = builder.build(data, config)

        # 4. 해시 계산
        report.integrity_hash = self.compute_hash(report)

        return report
\`\`\`

**완료 조건**:
- 모든 보고서 유형 생성 가능
- ID 중복 없음
- 해시 계산 정확성

---

### Phase 3: 법적 증거 보고서 빌더 (LegalReportBuilder) (Priority: HIGH)

**목표**: 법정 제출용 공식 증거 보고서 생성

**작업 항목**:

1. LegalReportBuilder 핵심 구현
   - `set_case_info()` - 사건 정보 설정
   - `add_evidence_list()` - 증거 목록 추가
   - `build()` - 보고서 빌드

2. 증거 정렬 및 구성
   - 중요도순 정렬
   - 시간순 정렬
   - 카테고리별 그룹화

3. 증거 체인 섹션 구현
   - `add_evidence_chain()` - 체인 추가
   - 연결 관계 시각화
   - 체인별 요약 생성

4. 증거 보관 연속성 구현
   - `add_chain_of_custody()` - 보관 기록 추가
   - 타임라인 형식 표현
   - 무결성 진술 생성

5. 부록 및 서명 섹션
   - `add_appendix()` - 부록 추가
   - 서명 위치 지정
   - 페이지 번호 처리

**법적 문서 구조**:

\`\`\`markdown
# 증거 자료 목록

## 1. 사건 개요
- 사건번호: {{ case_number }}
- 법원: {{ court_name }}
- 원고: {{ plaintiff }}
- 피고: {{ defendant }}

## 2. 분석 기간
- 시작일: {{ start_date }}
- 종료일: {{ end_date }}
- 총 녹취 파일: {{ file_count }}개
- 총 녹취 시간: {{ total_duration }}

## 3. 증거 목록

### 3.1 중요 증거 (HIGH)
{% for evidence in high_importance_evidence %}
#### 증거 {{ loop.index }}: {{ evidence.id }}
...
{% endfor %}

## 4. 증거 체인 분석
...

## 5. 무결성 진술
본 보고서에 포함된 모든 증거는...

## 6. 부록
...
\`\`\`

**완료 조건**:
- 법적 형식 준수
- 모든 필수 섹션 포함
- 증거 참조 정확성

---

### Phase 4: 타임라인 보고서 빌더 (TimelineReportBuilder) (Priority: HIGH)

**목표**: 시간순 이벤트 정리 및 패턴 시점 표시

**작업 항목**:

1. TimelineReportBuilder 핵심 구현
   - `set_date_range()` - 기간 설정
   - `add_timeline_events()` - 이벤트 추가
   - `build()` - 보고서 빌드

2. 이벤트 시간순 정렬
   - 날짜별 그룹화
   - 시간순 정렬
   - 연속 이벤트 연결

3. 패턴 발생 표시
   - `add_pattern_occurrences()` - 패턴 추가
   - 패턴별 색상 구분 (HTML)
   - 발생 시점 하이라이트

4. 화자별 활동 요약
   - `add_speaker_activity()` - 화자 활동 추가
   - 발언 빈도 분석
   - 패턴 분포 분석

5. 주요 이벤트 하이라이트
   - `highlight_key_events()` - 하이라이트 설정
   - 시각적 강조
   - 요약 박스 생성

6. 월별 요약 생성
   - `add_monthly_summary()` - 월별 요약
   - 월간 통계
   - 트렌드 분석

**타임라인 구조**:

\`\`\`markdown
# 타임라인 보고서

## 분석 기간: 2025.06 ~ 2025.12

## 월별 요약

### 2025년 6월
- 총 이벤트: 45건
- 가스라이팅 패턴: 12건
- 주요 사건: ...

### 2025년 7월
...

## 상세 타임라인

### 2025-06-15 (화)
| 시간 | 화자 | 내용 | 패턴 |
|------|------|------|------|
| 14:30 | 신동식 | "..." | DENIAL |
| 14:32 | 신기연 | "..." | - |
...
\`\`\`

**완료 조건**:
- 시간순 정렬 정확성
- 패턴 표시 동작
- 월별 요약 생성

---

### Phase 5: 요약 보고서 빌더 (SummaryReportBuilder) (Priority: HIGH)

**목표**: 전체 분석 개요 및 주요 발견사항 정리

**작업 항목**:

1. SummaryReportBuilder 핵심 구현
   - `set_analysis_overview()` - 개요 설정
   - `add_key_findings()` - 발견사항 추가
   - `build()` - 보고서 빌드

2. 분석 개요 구현
   - 총 파일 수, 시간, 기간
   - 화자 정보
   - 분석 범위

3. 주요 발견사항 구현
   - 심각도별 정렬
   - 근거 증거 연결
   - 발생 빈도 표시

4. 통계 데이터 구현
   - `add_statistics()` - 통계 추가
   - 카테고리별 분포
   - 화자별 분포
   - 시간별 분포

5. 패턴 요약 구현
   - `add_pattern_summary()` - 패턴 요약
   - 패턴 유형별 통계
   - 반복 패턴 식별

6. 화자 비교 분석
   - `add_speaker_comparison()` - 비교 분석
   - 발언량 비교
   - 패턴 빈도 비교

7. 권장 조치 구현
   - `add_recommendations()` - 권장사항
   - 우선순위별 정렬
   - 근거 연결

**요약 구조**:

\`\`\`markdown
# 분석 요약 보고서

## 1. 개요
- 분석 대상: 183개 녹취 파일
- 분석 기간: 2025.06.01 ~ 2025.12.31
- 총 녹취 시간: 약 120시간

## 2. 주요 발견사항

### [CRITICAL] 지속적 가스라이팅 패턴
- 총 47회 탐지
- 주요 유형: DENIAL, COUNTERING
- 최초 발생: 2025-06-15
...

## 3. 통계 데이터

### 3.1 카테고리별 증거 분포
| 카테고리 | 건수 | 비율 |
|----------|------|------|
| GASLIGHTING | 89 | 45% |
...

## 4. 권장 조치사항
1. [URGENT] 위협 발언 관련 법적 대응 검토
2. [HIGH] 가스라이팅 패턴 증거 보전
...

## 5. 결론
...
\`\`\`

**완료 조건**:
- 통계 정확성
- 발견사항 분류 정확성
- 권장사항 생성

---

### Phase 6: 보고서 내보내기 (ReportExporter) (Priority: HIGH)

**목표**: 다양한 형식으로 보고서 내보내기

**작업 항목**:

1. Markdown 내보내기 구현
   - `export_markdown()` - Markdown 출력
   - Jinja2 템플릿 기반
   - 목차 자동 생성

2. HTML 내보내기 구현
   - `export_html()` - HTML 출력
   - CSS 스타일 포함
   - 인쇄 친화적 레이아웃
   - 반응형 디자인

3. JSON 내보내기 구현
   - `export_json()` - JSON 출력
   - 메타데이터 포함
   - 데이터 교환용 구조

4. PDF 내보내기 구현 (선택적)
   - `export_pdf()` - PDF 출력
   - weasyprint 기반
   - 페이지 설정 (A4)
   - 헤더/푸터 포함

5. 템플릿 관리 구현
   - `get_template()` - 템플릿 조회
   - `register_custom_template()` - 커스텀 등록
   - 다국어 템플릿 지원

**HTML 템플릿 예시**:

\`\`\`html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>{{ report.title }}</title>
    <style>
        @media print {
            .no-print { display: none; }
            .page-break { page-break-before: always; }
        }
        .evidence-high { border-left: 4px solid #dc3545; }
        .evidence-medium { border-left: 4px solid #ffc107; }
        .evidence-low { border-left: 4px solid #28a745; }
    </style>
</head>
<body>
    <header>
        <h1>{{ report.title }}</h1>
        <p>생성일: {{ report.created_at }}</p>
    </header>
    <nav class="toc">
        <h2>목차</h2>
        {{ toc }}
    </nav>
    <main>
        {{ content }}
    </main>
    <footer>
        <p>보고서 ID: {{ report.id }}</p>
        <p>무결성 해시: {{ report.integrity_hash }}</p>
    </footer>
</body>
</html>
\`\`\`

**완료 조건**:
- 모든 형식 출력 동작
- 템플릿 렌더링 정확성
- 인코딩 정확성

---

### Phase 7: 유틸리티 및 보안 (Priority: MEDIUM)

**목표**: 보조 기능 및 보안 기능 구현

**작업 항목**:

1. 포맷팅 유틸리티
   - 날짜/시간 포맷팅
   - 숫자 포맷팅
   - 텍스트 정제

2. PII 마스킹 구현
   - 전화번호 마스킹 (010-****-1234)
   - 주민번호 마스킹 (******-*******)
   - 주소 마스킹
   - 정규식 기반 탐지

3. 통계 계산 유틸리티
   - 빈도 계산
   - 비율 계산
   - 분포 분석

4. 파일명 생성
   - 안전한 파일명 변환
   - 중복 방지
   - 확장자 관리

**PII 마스킹 예시**:

\`\`\`python
class PIIMasker:
    PATTERNS = {
        "phone": r"01[0-9]-\d{4}-\d{4}",
        "id_number": r"\d{6}-[1-4]\d{6}",
        "email": r"[\w.-]+@[\w.-]+\.\w+",
    }

    def mask(self, text: str) -> str:
        for pattern_name, pattern in self.PATTERNS.items():
            text = re.sub(pattern, self._get_mask(pattern_name), text)
        return text

    def _get_mask(self, pattern_name: str) -> str:
        masks = {
            "phone": "***-****-****",
            "id_number": "******-*******",
            "email": "****@****.***",
        }
        return masks.get(pattern_name, "****")
\`\`\`

**완료 조건**:
- PII 마스킹 동작
- 통계 계산 정확성
- 파일명 안전성

---

### Phase 8: 통합 및 최적화 (Priority: MEDIUM)

**목표**: 전체 시스템 통합 및 성능 최적화

**작업 항목**:

1. 파이프라인 통합
   - Evidence -> Report 변환 파이프라인
   - Timeline -> Report 변환 파이프라인
   - 자동 처리 워크플로우

2. 대용량 보고서 최적화
   - 스트리밍 출력
   - 메모리 효율화
   - 청크 기반 생성

3. 캐싱 구현
   - 템플릿 캐싱
   - 통계 결과 캐싱
   - 중간 결과 캐싱

4. CLI 통합
   - `forensic report` 명령
   - 옵션 처리
   - 진행 상황 표시

**CLI 명령 예시**:

\`\`\`bash
# 법적 증거 보고서 생성
forensic report --type legal --input ./analysis/ --output ./reports/ --format html

# 타임라인 보고서 생성
forensic report --type timeline --input ./analysis/ --output ./reports/ --format markdown

# 요약 보고서 생성 (PDF)
forensic report --type summary --input ./analysis/ --output ./reports/ --format pdf
\`\`\`

**완료 조건**:
- CLI 통합 동작
- 대용량 보고서 생성 안정성
- 183개 파일 기반 보고서 생성 < 30초

---

## 3. 기술적 의존성

### 3.1 필수 의존성

\`\`\`toml
[project]
dependencies = [
    "pydantic>=2.0",
    "python-dateutil>=2.8",
    "jinja2>=3.0",
    "markdown>=3.0",
]
\`\`\`

### 3.2 선택적 의존성

\`\`\`toml
[project.optional-dependencies]
html = [
    "pygments>=2.0",
]
pdf = [
    "weasyprint>=60.0",
]
charts = [
    "plotly>=5.0",
]
\`\`\`

---

## 4. 위험 분석 및 대응

### 4.1 기술적 위험

| 위험 | 영향 | 대응 방안 |
|------|------|-----------|
| PDF 생성 실패 | 일부 형식 미지원 | Markdown/HTML 대안 제공 |
| 대용량 보고서 메모리 부족 | 시스템 불안정 | 스트리밍 출력, 청크 처리 |
| 템플릿 렌더링 오류 | 보고서 생성 실패 | 기본 템플릿 폴백 |
| ARM64 호환성 | weasyprint 미동작 | PDF 기능 선택적 제공 |

### 4.2 법적 위험

| 위험 | 영향 | 대응 방안 |
|------|------|-----------|
| PII 노출 | 개인정보 유출 | 자동 마스킹, 검토 단계 |
| 증거 왜곡 | 법적 증거력 상실 | 원본 참조 유지, 해시 검증 |
| 형식 부적합 | 법원 제출 거부 | 법적 템플릿 검증 |

---

## 5. 테스트 전략

### 5.1 단위 테스트

- 보고서 ID 생성기 고유성
- 해시 계산 정확성
- PII 마스킹 동작
- 통계 계산 정확성
- 템플릿 렌더링

### 5.2 통합 테스트

- Evidence -> LegalReport 변환
- Timeline -> TimelineReport 변환
- 전체 내보내기 파이프라인
- CLI 명령 동작

### 5.3 형식 검증 테스트

- Markdown 문법 유효성
- HTML 유효성 (W3C)
- JSON 스키마 유효성
- PDF 생성 완료 확인

---

## 6. 마일스톤 요약

| 단계 | 우선순위 | 주요 산출물 |
|------|----------|-------------|
| Phase 1 | HIGH | 데이터 모델 완성 |
| Phase 2 | HIGH | ReportGenerator 완성 |
| Phase 3 | HIGH | LegalReportBuilder 완성 |
| Phase 4 | HIGH | TimelineReportBuilder 완성 |
| Phase 5 | HIGH | SummaryReportBuilder 완성 |
| Phase 6 | HIGH | ReportExporter 완성 |
| Phase 7 | MEDIUM | 유틸리티 및 보안 |
| Phase 8 | MEDIUM | 통합 및 최적화 |

---

Version: 1.0.0
Last Updated: 2026-01-19
