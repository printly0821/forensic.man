---
id: SPEC-TIMELINE-001
type: plan
version: "1.0.0"
created: "2026-01-18"
updated: "2026-01-18"
author: "지니"
---

# SPEC-TIMELINE-001 구현 계획

## 1. 구현 개요

### 1.1 목표

183개 녹취 파일의 시계열 분석, 화자 분리, 패턴 인식 기능을 구현하여 가스라이팅 피해 증거를 체계적으로 분석하고 정리합니다.

### 1.2 의존성 확인

| 의존 SPEC | 필요 컴포넌트 | 상태 |
|-----------|--------------|------|
| SPEC-CORE-001 | Transcript, Segment, Speaker, Evidence 모델 | 대기 중 |
| SPEC-IO-001 | StreamReader, ChunkProcessor, BatchProcessor | 대기 중 |

---

## 2. 구현 단계

### Phase 1: 데이터 모델 및 기반 구조 (Priority: HIGH)

**목표**: 분석 모듈의 기반 데이터 모델 정의

**작업 항목**:

1. Timeline 관련 모델 정의
   - `Timeline` 모델 구현
   - `TimelineEvent` 모델 구현
   - Pydantic v2 validator 적용

2. Speaker 관련 모델 정의
   - `SpeakerStatistics` 모델 구현
   - `TurnTakingEvent` 모델 구현

3. Pattern 관련 모델 정의
   - `GaslightingPattern` 모델 구현
   - `RepeatedStatement` 모델 구현
   - `EmotionalManipulation` 모델 구현
   - `ThreatPattern` 모델 구현

**완료 조건**:
- 모든 모델이 Pydantic BaseModel 기반
- 직렬화/역직렬화 테스트 통과
- 타입 힌트 완전성

---

### Phase 2: 시계열 분석 (TimelineBuilder) (Priority: HIGH)

**목표**: 녹취 파일의 시간순 정렬 및 그룹화 기능 구현

**작업 항목**:

1. TimelineBuilder 핵심 구현
   - `add_transcript()` - 녹취 추가
   - `build()` - 정렬된 타임라인 생성
   - 날짜 추출 로직 (파일명, 메타데이터)

2. 조회 기능 구현
   - `get_by_date()` - 특정 날짜 조회
   - `get_by_range()` - 날짜 범위 조회
   - `group_by_period()` - 기간별 그룹화 (day/week/month)

3. 이벤트 추출 구현
   - `extract_events()` - 주요 이벤트 마커 추출
   - 이벤트 중요도 자동 할당

**기술적 접근**:
- `python-dateutil`을 사용한 유연한 날짜 파싱
- 파일명 패턴: `YYYYMMDD_HHMMSS.txt`, `YYYY-MM-DD_description.txt` 지원
- 제너레이터 패턴으로 메모리 효율적 처리

**완료 조건**:
- 183개 파일 시간순 정렬 정확도 100%
- 날짜별/주별/월별 그룹화 동작
- 이벤트 추출 기능 동작

---

### Phase 3: 화자 분리 (SpeakerAnalyzer) (Priority: HIGH)

**목표**: 두 화자(신동식, 신기연) 식별 및 통계 분석

**작업 항목**:

1. 화자 식별 구현
   - `identify_speaker()` - 세그먼트에서 화자 추출
   - 별칭 정규화 테이블 구축
   - `normalize_alias()` - 별칭 -> 정규 이름 변환

2. 통계 분석 구현
   - `get_statistics()` - 개별 화자 통계
   - `get_all_statistics()` - 전체 화자 통계
   - `get_speaking_ratio()` - 발언 비율 계산

3. 화자 전환 분석
   - `analyze_turn_taking()` - 전환 패턴 분석
   - 끼어들기(interruption) 감지
   - 전환 간격/중복 시간 계산

**화자 별칭 매핑**:

```python
SPEAKER_ALIASES = {
    "신동식": ["동식", "신씨", "아버지", "아빠"],
    "신기연": ["기연", "신기연씨", "자식"],
}
```

**완료 조건**:
- 화자 식별 정확도 > 95%
- 별칭 인식률 > 98%
- 화자 전환 패턴 기록 완성

---

### Phase 4: 패턴 인식 (PatternDetector) (Priority: HIGH)

**목표**: 가스라이팅, 감정 조작, 위협 패턴 탐지

**작업 항목**:

1. 가스라이팅 탐지
   - `detect_gaslighting()` 구현
   - 7가지 패턴 유형 탐지
   - 신뢰도 점수 계산

2. 반복 발언 추적
   - `detect_repeated_statements()` 구현
   - 유사도 기반 매칭 (rapidfuzz)
   - 임계값 기반 필터링

3. 감정적 조작 탐지
   - `detect_emotional_manipulation()` 구현
   - 6가지 조작 유형 탐지
   - 강도 평가

4. 위협/압박 탐지
   - `detect_threats()` 구현
   - 5가지 위협 유형 탐지
   - 심각도 평가

5. 통합 탐지
   - `detect_all()` 구현
   - 모든 패턴 -> Evidence 변환
   - 중요도 자동 할당

**기술적 접근**:
- 키워드 기반 1차 필터링
- 문맥 분석을 통한 2차 검증
- GPU 가속 배치 처리 (선택적)

**완료 조건**:
- 가스라이팅 탐지 정밀도 > 85%
- 모든 패턴 유형 탐지 동작
- Evidence 변환 정확성

---

### Phase 5: 커스텀 패턴 및 확장 (Priority: MEDIUM)

**목표**: 사용자 정의 패턴 지원 및 확장성 확보

**작업 항목**:

1. 커스텀 패턴 시스템
   - `add_custom_pattern()` 구현
   - 키워드 + 컨텍스트 규칙 지원
   - 동적 패턴 로딩

2. 키워드 사전 관리
   - YAML 기반 키워드 사전
   - 실시간 업데이트 지원
   - 카테고리별 관리

**완료 조건**:
- 커스텀 패턴 추가/탐지 동작
- 키워드 사전 동적 로딩

---

### Phase 6: GPU 가속 및 성능 최적화 (Priority: MEDIUM)

**목표**: DGX Spark GPU를 활용한 성능 최적화

**작업 항목**:

1. GPU 가속 패턴 매칭
   - PyTorch 기반 배치 처리
   - CUDA 커널 최적화
   - 메모리 관리

2. 병렬 분석 모드
   - asyncio 기반 병렬 처리
   - 배치 크기 자동 조절
   - 진행률 콜백

**완료 조건**:
- 183개 파일 분석 < 30분
- GPU 사용률 > 70%

---

### Phase 7: 시각화 (Priority: LOW)

**목표**: 분석 결과 시각화 (선택적)

**작업 항목**:

1. 시계열 시각화
   - plotly 기반 타임라인 차트
   - 화자별 발언량 그래프
   - 패턴 발생 히트맵

**완료 조건**:
- 시각화 출력 생성
- HTML/PNG 내보내기

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
pattern = ["rapidfuzz>=3.0"]
visualization = ["plotly>=5.0", "pandas>=2.0"]
gpu = ["torch>=2.5", "numpy>=2.0"]
```

---

## 4. 위험 분석 및 대응

### 4.1 기술적 위험

| 위험 | 영향 | 대응 방안 |
|------|------|-----------|
| 화자 식별 정확도 부족 | 분석 신뢰성 저하 | 별칭 사전 확장, 문맥 힌트 활용 |
| 패턴 탐지 오탐 | 증거 신뢰성 저하 | 신뢰도 임계값 조절, 수동 검증 지원 |
| GPU 메모리 부족 | 배치 크기 제한 | 동적 배치 크기 조절, CPU 폴백 |
| ARM64 호환성 | 일부 라이브러리 사용 불가 | 순수 Python 대안 준비 |

### 4.2 데이터 위험

| 위험 | 영향 | 대응 방안 |
|------|------|-----------|
| 날짜 추출 실패 | 시계열 정렬 오류 | 다중 날짜 패턴 지원, 수동 입력 옵션 |
| 화자 미식별 | 통계 왜곡 | UNKNOWN 레이블 분리 처리 |
| 맥락 손실 | 패턴 오탐 | 전후 N개 세그먼트 컨텍스트 보존 |

---

## 5. 테스트 전략

### 5.1 단위 테스트

- 각 모델의 직렬화/역직렬화
- 화자 별칭 정규화
- 개별 패턴 탐지 함수

### 5.2 통합 테스트

- TimelineBuilder + BatchProcessor 연동
- SpeakerAnalyzer + Segment 처리
- PatternDetector + Evidence 변환

### 5.3 성능 테스트

- 183개 파일 전체 분석 시간
- 메모리 사용량 프로파일링
- GPU 가속 효과 측정

---

## 6. 마일스톤 요약

| 단계 | 우선순위 | 주요 산출물 |
|------|----------|-------------|
| Phase 1 | HIGH | 데이터 모델 완성 |
| Phase 2 | HIGH | TimelineBuilder 완성 |
| Phase 3 | HIGH | SpeakerAnalyzer 완성 |
| Phase 4 | HIGH | PatternDetector 완성 |
| Phase 5 | MEDIUM | 커스텀 패턴 시스템 |
| Phase 6 | MEDIUM | GPU 가속 최적화 |
| Phase 7 | LOW | 시각화 기능 |

---

Version: 1.0.0
Last Updated: 2026-01-18
