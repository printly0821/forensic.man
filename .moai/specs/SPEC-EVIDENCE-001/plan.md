---
id: SPEC-EVIDENCE-001
type: plan
version: "1.0.0"
created: "2026-01-18"
updated: "2026-01-18"
author: "지니"
---

# SPEC-EVIDENCE-001 구현 계획

## 1. 구현 개요

### 1.1 목표

SPEC-TIMELINE-001에서 탐지된 패턴을 법적으로 유효한 증거 형식으로 변환하고, 증거의 맥락을 보존하며, 무결성을 보장하는 시스템을 구현합니다. 형사소송에서 신뢰할 수 있는 증거자료 생성을 목표로 합니다.

### 1.2 의존성 확인

| 의존 SPEC | 필요 컴포넌트 | 상태 |
|-----------|--------------|------|
| SPEC-CORE-001 | Transcript, Segment, Speaker, Evidence 모델 | 대기 중 |
| SPEC-IO-001 | StreamReader, ChunkProcessor, BatchProcessor | 대기 중 |
| SPEC-TIMELINE-001 | PatternDetector, GaslightingPattern, ThreatPattern 등 | 대기 중 |

---

## 2. 구현 단계

### Phase 1: 데이터 모델 정의 (Priority: HIGH)

**목표**: 증거 시스템의 기반 데이터 모델 정의

**작업 항목**:

1. Evidence 모델 확장
   - SPEC-CORE-001의 Evidence 모델 확장
   - 새로운 필드 추가 (integrity_hash, validation_status 등)
   - Pydantic v2 validator 적용

2. 검증 관련 모델 정의
   - `ValidationResult` 모델 구현
   - `ValidationReport` 모델 구현

3. 체인 및 내보내기 모델 정의
   - `EvidenceChain` 모델 구현
   - `LegalDocument` 모델 구현
   - `ExportConfig` 모델 구현

4. 열거형 정의
   - `EvidenceCategory` Enum 구현
   - 상태 관련 Literal 타입 정의

**완료 조건**:
- 모든 모델이 Pydantic BaseModel 기반
- 직렬화/역직렬화 테스트 통과
- 타입 힌트 완전성

---

### Phase 2: 증거 추출 (EvidenceExtractor) (Priority: HIGH)

**목표**: 탐지된 패턴에서 법적 증거 자동 추출

**작업 항목**:

1. EvidenceExtractor 핵심 구현
   - `extract_from_pattern()` - 단일 패턴에서 증거 추출
   - `extract_batch()` - 다수 패턴 일괄 추출
   - 패턴 유형별 변환 로직

2. 증거 ID 생성기 구현
   - `generate_id()` - EVD-YYYYMMDD-XXXX 형식
   - 순번 관리 및 중복 방지
   - 날짜별 리셋 로직

3. 중요도 할당 구현
   - `assign_importance()` 구현
   - 반복 횟수 기반 자동 상향
   - 패턴 유형별 기본 중요도

4. 카테고리 분류 구현
   - `categorize()` 구현
   - 패턴 유형 -> 카테고리 매핑
   - 복합 패턴 처리

**기술적 접근**:

```python
IMPORTANCE_RULES = {
    "HIGH": {
        "min_occurrences": 3,
        "critical_patterns": ["EXPLICIT_THREAT", "FINANCIAL_THREAT"]
    },
    "MEDIUM": {
        "min_occurrences": 2,
        "patterns": ["DENIAL", "COUNTERING", "GUILT_TRIPPING"]
    }
}
```

**완료 조건**:
- 모든 패턴 유형에서 증거 추출 가능
- ID 중복 없음
- 중요도/카테고리 자동 할당 동작

---

### Phase 3: 맥락 보존 (ContextPreserver) (Priority: HIGH)

**목표**: 증거 전후 발언의 맥락 자동 추출 및 연결

**작업 항목**:

1. ContextPreserver 핵심 구현
   - `extract_context()` - 전후 맥락 추출
   - 설정 가능한 범위 (기본 3개 발언)
   - 문자 수 제한 적용

2. 대화 흐름 추출 구현
   - `get_conversation_flow()` - 전체 대화 흐름
   - 화자 전환 포함
   - 시간순 정렬

3. 관련 세그먼트 연결 구현
   - `link_related_segments()` - 유사 발언 연결
   - 유사도 임계값 적용
   - 관련 ID 목록 생성

4. 위치 정보 추출 구현
   - `get_position_in_transcript()` - 전체 녹취 내 위치
   - 상대적 위치 계산 (시작부/중간/끝부분)
   - 시간 정보 포함

**기술적 접근**:

```python
def extract_context(
    self,
    segment: Segment,
    all_segments: list[Segment],
    before_count: int = 3,
    after_count: int = 3
) -> tuple[str, str]:
    # 세그먼트 인덱스 찾기
    idx = self._find_segment_index(segment, all_segments)

    # 이전 맥락
    before_segments = all_segments[max(0, idx - before_count):idx]
    context_before = self._format_context(before_segments)

    # 이후 맥락
    after_segments = all_segments[idx + 1:idx + 1 + after_count]
    context_after = self._format_context(after_segments)

    return context_before, context_after
```

**완료 조건**:
- 맥락 추출 정확도 100%
- 설정 가능한 범위 동작
- 위치 정보 정확성

---

### Phase 4: 증거 검증 (EvidenceValidator) (Priority: HIGH)

**목표**: 증거 무결성 검증 및 원본 참조 유지

**작업 항목**:

1. 무결성 검증 구현
   - `validate_integrity()` - 전체 검증
   - SHA-256 해시 계산 및 비교
   - 검증 결과 생성

2. 개별 검증 구현
   - `verify_timestamp()` - 타임스탬프 일치 확인
   - `verify_source_reference()` - 원본 참조 유효성
   - `compute_hash()` - 해시 계산

3. 중복 탐지 구현
   - `detect_duplicates()` - 중복 증거 탐지
   - 유사도 기반 비교
   - 중복 ID 목록 반환

4. 중복 병합 구현
   - `merge_duplicates()` - 중복 증거 병합
   - 대표 증거 선정
   - 참조 통합

5. 검증 보고서 구현
   - `get_validation_report()` - 전체 보고서 생성
   - 통계 계산
   - 권장 조치 제시

**기술적 접근**:

```python
import hashlib
import json

def compute_hash(self, evidence: Evidence) -> str:
    # 해시 대상 필드 추출
    hash_data = {
        "id": evidence.id,
        "transcript_id": evidence.transcript_id,
        "segment_ids": evidence.segment_ids,
        "content_sample": evidence.content_sample,
        "timestamp": evidence.timestamp.isoformat()
    }

    # JSON 직렬화 후 해시 계산
    data_str = json.dumps(hash_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()
```

**완료 조건**:
- 모든 증거 해시 계산 가능
- 중복 탐지 정확도 > 95%
- 검증 보고서 생성 완료

---

### Phase 5: 증거 내보내기 (EvidenceExporter) (Priority: HIGH)

**목표**: JSON 및 법적 문서 형식으로 증거 내보내기

**작업 항목**:

1. JSON 내보내기 구현
   - `export_json()` - JSON 형식 출력
   - 맥락 포함 옵션
   - 메타데이터 포함 옵션

2. 법적 문서 내보내기 구현
   - `export_legal_format()` - 법적 형식 출력
   - Jinja2 템플릿 기반
   - 한국어 형사소송 형식 지원

3. 증거 체인 내보내기 구현
   - `export_chain_of_custody()` - 체인 문서 생성
   - 연속성 입증 형식
   - 시계열 표현

4. 요약 보고서 내보내기 구현
   - `export_summary()` - 요약 보고서 생성
   - 주요 증거 하이라이트
   - 통계 포함

5. 필터링 기능 구현
   - `filter_by_importance()` - 중요도 필터
   - `filter_by_category()` - 카테고리 필터
   - `filter_by_date_range()` - 날짜 필터

**법적 문서 템플릿 예시**:

```markdown
# 증거 자료 목록

## 사건 개요
- 분석 기간: {{ start_date }} ~ {{ end_date }}
- 녹취 파일 수: {{ file_count }}개
- 총 녹취 시간: {{ total_duration }}

## 증거 목록

{% for evidence in evidence_list %}
### 증거 {{ loop.index }}: {{ evidence.id }}

- **카테고리**: {{ evidence.category }}
- **중요도**: {{ evidence.importance }}
- **일시**: {{ evidence.timestamp }}
- **화자**: {{ evidence.speaker }}

#### 발언 내용
> {{ evidence.content_sample }}

#### 전후 맥락
**이전 맥락**:
{{ evidence.context_before }}

**이후 맥락**:
{{ evidence.context_after }}

---
{% endfor %}
```

**완료 조건**:
- JSON 내보내기 동작
- 법적 문서 형식 생성
- 모든 필터 기능 동작

---

### Phase 6: 증거 체인 시스템 (Priority: MEDIUM)

**목표**: 관련 증거들의 연결 관계 구축

**작업 항목**:

1. 체인 탐지 구현
   - 시간적 체인 (연속 발생)
   - 패턴 체인 (동일 패턴 반복)
   - 화자 체인 (동일 화자)

2. 체인 구축 구현
   - 자동 체인 생성
   - 수동 체인 편집
   - 체인 병합

3. 체인 분석 구현
   - 체인 심각도 계산
   - 체인 요약 생성

**완료 조건**:
- 자동 체인 탐지 동작
- 체인 문서 생성 가능

---

### Phase 7: 통합 및 최적화 (Priority: MEDIUM)

**목표**: 전체 시스템 통합 및 성능 최적화

**작업 항목**:

1. 파이프라인 통합
   - PatternDetector -> EvidenceExtractor 연동
   - 자동 처리 파이프라인

2. 배치 처리 최적화
   - 대량 증거 병렬 처리
   - 메모리 효율화

3. 캐싱 구현
   - 해시 캐싱
   - 중복 탐지 결과 캐싱

**완료 조건**:
- 183개 파일 증거 처리 < 10분
- 메모리 사용량 안정

---

## 3. 기술적 의존성

### 3.1 필수 의존성

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "python-dateutil>=2.8",
]
```

### 3.2 선택적 의존성

```toml
[project.optional-dependencies]
export = [
    "jinja2>=3.0",
    "markdown>=3.0",
]
pdf = [
    "weasyprint>=60.0",
]
```

---

## 4. 위험 분석 및 대응

### 4.1 기술적 위험

| 위험 | 영향 | 대응 방안 |
|------|------|-----------|
| 중복 탐지 오류 | 증거 중복/누락 | 다중 기준 비교, 수동 검증 옵션 |
| 해시 충돌 | 무결성 검증 실패 | SHA-256 사용 (충돌 확률 극히 낮음) |
| 맥락 손실 | 증거 신뢰성 저하 | 충분한 맥락 범위, 원본 참조 유지 |
| ARM64 호환성 | weasyprint 미동작 | Markdown/HTML 대안 제공 |

### 4.2 법적 위험

| 위험 | 영향 | 대응 방안 |
|------|------|-----------|
| 원본 변조 가능성 | 증거 무효화 | 읽기 전용 처리, 해시 검증 |
| 맥락 왜곡 | 증거 신뢰성 저하 | 충분한 전후 맥락, 전체 녹취 참조 |
| 증거 연속성 | 증거 채택 불가 | 체인 문서, 타임스탬프 검증 |

---

## 5. 테스트 전략

### 5.1 단위 테스트

- 증거 ID 생성기 고유성
- 해시 계산 정확성
- 중복 탐지 정확도
- 맥락 추출 정확성

### 5.2 통합 테스트

- PatternDetector -> EvidenceExtractor 연동
- 전체 내보내기 파이프라인
- 검증 -> 내보내기 흐름

### 5.3 법적 검증 테스트

- 법적 문서 형식 적합성
- 증거 연속성 표현 적합성
- 무결성 검증 완전성

---

## 6. 마일스톤 요약

| 단계 | 우선순위 | 주요 산출물 |
|------|----------|-------------|
| Phase 1 | HIGH | 데이터 모델 완성 |
| Phase 2 | HIGH | EvidenceExtractor 완성 |
| Phase 3 | HIGH | ContextPreserver 완성 |
| Phase 4 | HIGH | EvidenceValidator 완성 |
| Phase 5 | HIGH | EvidenceExporter 완성 |
| Phase 6 | MEDIUM | 증거 체인 시스템 |
| Phase 7 | MEDIUM | 통합 및 최적화 |

---

Version: 1.0.0
Last Updated: 2026-01-18
