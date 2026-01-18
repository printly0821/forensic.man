# SPEC-CORE-001: 구현 계획

## 1. 구현 개요

### 1.1 목표

DGX Spark 환경에 최적화된 forensic.man 프로젝트의 기반 인프라를 구축합니다.

### 1.2 예상 산출물

| 파일 | 설명 |
|------|------|
| `src/forensic/__init__.py` | 패키지 초기화 |
| `src/forensic/models/transcript.py` | Transcript, Segment 모델 |
| `src/forensic/models/speaker.py` | Speaker 모델 |
| `src/forensic/models/evidence.py` | Evidence 모델 |
| `src/forensic/utils/config.py` | 설정 관리 |
| `src/forensic/utils/dgx_detector.py` | DGX Spark 환경 감지 |
| `pyproject.toml` | 프로젝트 설정 |
| `tests/unit/test_models.py` | 모델 단위 테스트 |
| `tests/unit/test_config.py` | 설정 단위 테스트 |

---

## 2. 태스크 분해

### Phase 1: 프로젝트 구조 설정 (Day 1)

```
[TASK-1.1] pyproject.toml 생성
├── 프로젝트 메타데이터 정의
├── 의존성 목록 작성 (ARM64 호환)
├── CLI 진입점 설정
└── 빌드 시스템 구성 (hatchling)

[TASK-1.2] 패키지 구조 생성
├── src/forensic/ 디렉토리 생성
├── __init__.py 파일 생성
├── 하위 패키지 구조 생성 (models, utils, cli, core, io, report)
└── tests/ 디렉토리 구조 생성
```

### Phase 2: 데이터 모델 구현 (Day 1-2)

```
[TASK-2.1] Transcript 모델
├── Pydantic BaseModel 정의
├── 필드 검증 로직 구현
├── 직렬화/역직렬화 메서드
└── 단위 테스트 작성

[TASK-2.2] Segment 모델
├── 시간 범위 검증
├── 화자 참조 검증
└── 단위 테스트 작성

[TASK-2.3] Speaker 모델
├── 별칭 관리 로직
├── 통계 계산 메서드
└── 단위 테스트 작성

[TASK-2.4] Evidence 모델
├── 중요도 레벨 열거형
├── 맥락 추출 유틸리티
└── 단위 테스트 작성
```

### Phase 3: 설정 관리 구현 (Day 2)

```
[TASK-3.1] Config 클래스
├── YAML 파일 로딩
├── 환경 변수 오버라이드
├── 기본값 처리
└── 단위 테스트 작성

[TASK-3.2] DGX Spark 감지기
├── ARM64 아키텍처 감지
├── CUDA 가용성 확인
├── 메모리 정보 수집
├── GPU 정보 수집
└── 단위 테스트 작성
```

### Phase 4: 통합 및 검증 (Day 3)

```
[TASK-4.1] 통합 테스트
├── 전체 모델 워크플로우 테스트
├── 설정 로드 → 모델 생성 흐름 테스트
└── DGX Spark 환경 시뮬레이션 테스트

[TASK-4.2] 문서화
├── README.md 업데이트
├── 모델 docstring 완성
└── 설정 예제 작성
```

---

## 3. 기술 스택

### 3.1 런타임 의존성

| 패키지 | 버전 | 용도 | ARM64 호환 |
|--------|------|------|:----------:|
| pydantic | >=2.0 | 데이터 모델 | Yes |
| pyyaml | >=6.0 | YAML 파싱 | Yes |
| rich | >=13.0 | 터미널 출력 | Yes |
| python-dateutil | >=2.8 | 날짜 파싱 | Yes |

### 3.2 개발 의존성

| 패키지 | 버전 | 용도 | ARM64 호환 |
|--------|------|------|:----------:|
| pytest | >=8.0 | 테스트 | Yes |
| pytest-cov | >=4.0 | 커버리지 | Yes |
| ruff | >=0.1 | 린팅 | Yes |

### 3.3 선택적 의존성 (GPU)

| 패키지 | 버전 | 용도 | 설치 방법 |
|--------|------|------|-----------|
| torch | >=2.5 | GPU 가속 | CUDA 13 index |
| numpy | >=2.0 | 수치 연산 | pip |

---

## 4. 리스크 분석

### 4.1 기술적 리스크

| 리스크 | 영향 | 확률 | 완화 전략 |
|--------|------|------|-----------|
| ARM64 패키지 미호환 | 높음 | 낮음 | 순수 Python 우선 사용 |
| CUDA 13 불안정 | 중간 | 중간 | CPU 폴백 구현 |
| 메모리 오버플로우 | 높음 | 낮음 | 배치 크기 자동 조절 |

### 4.2 완화 전략

1. **ARM64 호환성**: 모든 의존성 설치 전 ARM64 지원 확인
2. **CUDA 폴백**: GPU 기능 선택적 구현, CPU 모드 기본 제공
3. **메모리 관리**: psutil로 메모리 모니터링, 동적 배치 조절

---

## 5. 검증 기준

### 5.1 단위 테스트

- 모든 모델 클래스 80% 이상 커버리지
- 설정 로드/저장 테스트 100% 통과
- DGX Spark 감지 로직 모킹 테스트

### 5.2 통합 테스트

- 전체 모델 워크플로우 정상 동작
- 설정 변경 시 재로드 동작
- ARM64 환경 시뮬레이션 통과

### 5.3 성능 기준

- 설정 로드: < 100ms
- 모델 직렬화: < 10ms per 1000 records
- 메모리 오버헤드: < 1GB

---

## 6. 일정

| 단계 | 기간 | 산출물 |
|------|------|--------|
| Phase 1 | Day 1 | pyproject.toml, 패키지 구조 |
| Phase 2 | Day 1-2 | 데이터 모델 4개, 단위 테스트 |
| Phase 3 | Day 2 | 설정 관리, DGX 감지기 |
| Phase 4 | Day 3 | 통합 테스트, 문서화 |

**총 예상 기간**: 3일

---

## 7. 의존성

### 7.1 선행 조건

- Python 3.12+ (ARM64) 설치
- uv 패키지 매니저 설치
- Git 저장소 초기화

### 7.2 후속 SPEC

- **SPEC-IO-001**: 이 SPEC의 데이터 모델을 사용
- **SPEC-ANALYSIS-001**: 이 SPEC의 설정 시스템을 사용
- **SPEC-CLI-001**: 이 SPEC의 전체 인프라를 사용

---

Version: 1.0.0
Last Updated: 2026-01-18
