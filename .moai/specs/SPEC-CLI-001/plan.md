# SPEC-CLI-001 구현 계획

## 태그 추적

- **SPEC ID**: SPEC-CLI-001
- **관련 SPEC**: SPEC-CORE-001, SPEC-IO-001, SPEC-TIMELINE-001, SPEC-EVIDENCE-001, SPEC-REPORT-001, SPEC-SEARCH-001
- **상태**: 계획 단계

---

## 1. 구현 마일스톤

### Primary Goal: CLI 기본 프레임워크 구축

**목표**: Click 기반 CLI 구조와 Rich 출력 시스템 구현

**포함 작업**:
- [ ] Click 그룹 및 메인 진입점 구현 (`forensic` 명령)
- [ ] CLIContext 및 ForensicConfig 모델 구현
- [ ] 설정 파일 로더 구현 (`config_loader.py`)
- [ ] Rich 콘솔 출력 유틸리티 구현
- [ ] 진행률 표시 컴포넌트 구현
- [ ] 시그널 핸들러 구현 (Ctrl+C 안전 중단)

**의존성**: 없음 (기반 작업)

**검증 기준**:
- `forensic --help` 정상 출력
- `forensic --version` 버전 정보 표시
- 설정 파일 로드/저장 정상 동작
- CLI 시작 시간 1초 미만

---

### Secondary Goal: forensic analyze 명령 구현

**목표**: 전체 분석 파이프라인을 통합하는 analyze 명령 구현

**포함 작업**:
- [ ] analyze 명령 구조 구현
- [ ] 입출력 디렉토리 검증 로직
- [ ] 분석 파이프라인 통합 (SPEC-IO-001, SPEC-TIMELINE-001, SPEC-EVIDENCE-001)
- [ ] Rich 진행률 표시 통합
- [ ] 분석 결과 요약 패널 출력
- [ ] 캐시 시스템 구현 (결과 저장/로드)
- [ ] 중단 후 재개 기능 구현

**의존성**: Primary Goal 완료, SPEC-IO-001, SPEC-TIMELINE-001, SPEC-EVIDENCE-001

**검증 기준**:
- 183개 파일 분석 완료
- 진행률 표시 정상 동작
- Ctrl+C 시 안전 중단 및 부분 결과 저장
- 캐시 히트 시 재분석 건너뛰기

---

### Tertiary Goal: forensic search 명령 구현

**목표**: 검색 기능을 CLI로 노출

**포함 작업**:
- [ ] search 명령 구조 구현
- [ ] 검색 쿼리 파싱 및 검증
- [ ] 필터 옵션 처리 (화자, 날짜, 중요도, 패턴)
- [ ] SPEC-SEARCH-001 통합
- [ ] 결과 테이블 포맷팅
- [ ] 하이라이트 출력
- [ ] 결과 내보내기 (JSON, CSV)

**의존성**: Primary Goal 완료, SPEC-SEARCH-001

**검증 기준**:
- 키워드 검색 정상 동작
- 필터 조합 정상 적용
- 결과 하이라이트 표시
- 내보내기 기능 동작

---

### Quaternary Goal: forensic report 명령 구현

**목표**: 보고서 생성 기능을 CLI로 노출

**포함 작업**:
- [ ] report 명령 구조 구현
- [ ] 보고서 유형 선택 로직 (legal, timeline, summary, evidence, statistical)
- [ ] SPEC-REPORT-001 통합
- [ ] 다양한 출력 형식 지원 (Markdown, HTML, JSON)
- [ ] 템플릿 시스템 연동
- [ ] 필터 적용 (날짜, 화자, 중요도)

**의존성**: Secondary Goal 완료, SPEC-REPORT-001

**검증 기준**:
- 5가지 보고서 유형 생성 가능
- 3가지 출력 형식 지원
- 필터 적용 정상 동작

---

### Quinary Goal: forensic timeline 명령 구현

**목표**: 시계열 분석 결과를 CLI로 표시

**포함 작업**:
- [ ] timeline 명령 구조 구현
- [ ] SPEC-TIMELINE-001 통합
- [ ] 텍스트 기반 타임라인 시각화
- [ ] 날짜 범위 필터 처리
- [ ] 시간 해상도 옵션 (일/주/월)
- [ ] HTML 타임라인 내보내기

**의존성**: Secondary Goal 완료, SPEC-TIMELINE-001

**검증 기준**:
- 타임라인 텍스트 출력 정상
- 날짜 필터 정상 동작
- HTML 내보내기 정상 동작

---

### Final Goal: forensic config 명령 및 시스템 통합

**목표**: 설정 관리 및 전체 시스템 통합 테스트

**포함 작업**:
- [ ] config 명령 구조 구현
- [ ] 설정 조회/수정/초기화 기능
- [ ] DGX Spark 시스템 정보 표시
- [ ] 설정 파일 편집기 연동 (`$EDITOR`)
- [ ] 전체 CLI 통합 테스트
- [ ] 엔드투엔드 워크플로우 테스트

**의존성**: 모든 이전 Goal 완료

**검증 기준**:
- 설정 CRUD 동작
- 시스템 정보 정확히 표시
- 전체 워크플로우 테스트 통과

---

### Optional Goal: 성능 최적화 및 GPU 가속

**목표**: 병렬 처리 및 GPU 가속 옵션 구현

**포함 작업**:
- [ ] `--parallel` 옵션 구현 (multiprocessing)
- [ ] `--gpu` 옵션 구현 (CUDA 활용)
- [ ] 메모리 사용량 최적화
- [ ] 대용량 파일 스트리밍 처리 개선
- [ ] 벤치마크 테스트 스위트 작성

**의존성**: Final Goal 완료

**검증 기준**:
- 병렬 처리 시 2배 이상 성능 향상
- 메모리 사용량 2GB 이하 유지
- GPU 가속 정상 동작 (DGX Spark 환경)

---

## 2. 기술적 접근

### 2.1 CLI 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         forensic CLI                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ analyze │ │ search  │ │ report  │ │timeline │ │ config  │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
│       │           │           │           │           │         │
├───────┴───────────┴───────────┴───────────┴───────────┴─────────┤
│                        CLI Context                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Config Mgr  │  │ Cache Mgr   │  │ Signal Hdlr │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│                         Rich Output                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ Console │  │ Progress│  │  Table  │  │  Panel  │           │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │
├─────────────────────────────────────────────────────────────────┤
│                     Core Modules (SPECs)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ IO       │ │ Timeline │ │ Evidence │ │ Search   │          │
│  │ (IO-001) │ │(TL-001)  │ │(EV-001)  │ │(SR-001)  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 명령 실행 흐름

```
사용자 입력
    │
    ▼
┌─────────────────┐
│  Click Parser   │  ← 명령/옵션 파싱
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Config Loader  │  ← 설정 파일 로드
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Input Validator│  ← 입력 검증
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Core Module    │  ← SPEC 모듈 호출
│  Integration    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Progress       │  ← 진행률 표시
│  Display        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Result         │  ← 결과 포맷팅
│  Formatter      │
└────────┬────────┘
         │
         ▼
    출력 (터미널/파일)
```

### 2.3 캐시 시스템

```python
# 캐시 키 생성
def get_cache_key(file_path: Path, operation: str) -> str:
    file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
    return f"{operation}:{file_hash}"

# 캐시 저장 구조
.forensic/cache/
├── index.json           # 캐시 인덱스
├── analyze/
│   ├── {hash1}.json     # 분석 결과 캐시
│   └── {hash2}.json
├── search/
│   └── index.db         # 검색 인덱스 캐시
└── metadata.json        # 캐시 메타데이터
```

### 2.4 시그널 핸들링

```python
import signal
from contextlib import contextmanager

@contextmanager
def graceful_interrupt():
    """Ctrl+C 안전 핸들링"""
    original_handler = signal.getsignal(signal.SIGINT)
    interrupted = False

    def handler(signum, frame):
        nonlocal interrupted
        if interrupted:
            # 두 번째 Ctrl+C는 강제 종료
            raise KeyboardInterrupt()
        interrupted = True
        console.print("\n[yellow]중단 요청됨. 현재 작업 완료 후 안전하게 종료합니다...[/yellow]")

    signal.signal(signal.SIGINT, handler)
    try:
        yield lambda: interrupted
    finally:
        signal.signal(signal.SIGINT, original_handler)
```

---

## 3. 의존성 관리

### 3.1 내부 의존성

| 의존 SPEC | 사용 컴포넌트 | 용도 |
|-----------|---------------|------|
| SPEC-CORE-001 | 모든 데이터 모델 | 데이터 타입 정의 |
| SPEC-IO-001 | StreamReader, BatchProcessor | 파일 읽기 |
| SPEC-TIMELINE-001 | TimelineAnalyzer, PatternDetector | 시계열 분석 |
| SPEC-EVIDENCE-001 | EvidenceExtractor, EvidenceChain | 증거 추출 |
| SPEC-REPORT-001 | ReportGenerator, ReportFormatter | 보고서 생성 |
| SPEC-SEARCH-001 | SearchEngine, FilterEngine | 검색 기능 |

### 3.2 외부 의존성

| 패키지 | 버전 | 용도 | ARM64 호환 |
|--------|------|------|------------|
| click | >=8.0 | CLI 프레임워크 | O (순수 Python) |
| rich | >=13.0 | 터미널 출력 | O (순수 Python) |
| pyyaml | >=6.0 | YAML 설정 | O (C 폴백 가능) |
| pydantic | >=2.0 | 데이터 모델 | O |

### 3.3 통합 순서

```
1. SPEC-CORE-001 (데이터 모델)
       │
       ▼
2. SPEC-IO-001 (파일 I/O)
       │
       ├──────────────────────────┐
       ▼                          ▼
3. SPEC-TIMELINE-001        SPEC-EVIDENCE-001
   (시계열 분석)              (증거 추출)
       │                          │
       └──────────┬───────────────┘
                  ▼
4. SPEC-SEARCH-001 (검색)
       │
       ▼
5. SPEC-REPORT-001 (보고서)
       │
       ▼
6. SPEC-CLI-001 (CLI 통합)
```

---

## 4. 아키텍처 설계

### 4.1 모듈 구조

```
forensic.cli
├── main.py                    # CLI 진입점
├── commands/                  # 명령 모듈
│   ├── analyze.py            # analyze 명령
│   ├── search.py             # search 명령
│   ├── report.py             # report 명령
│   ├── timeline.py           # timeline 명령
│   └── config.py             # config 명령
├── output/                    # 출력 모듈
│   ├── console.py            # Rich 콘솔
│   ├── progress.py           # 진행률 표시
│   ├── table.py              # 테이블 포맷터
│   └── panel.py              # 패널 포맷터
├── models/                    # 데이터 모델
│   ├── context.py            # CLIContext
│   ├── config.py             # ForensicConfig
│   └── result.py             # 결과 모델
└── utils/                     # 유틸리티
    ├── config_loader.py      # 설정 로더
    ├── cache.py              # 캐시 관리
    ├── signal_handler.py     # 시그널 핸들링
    └── validators.py         # 입력 검증
```

### 4.2 클래스 다이어그램

```
┌─────────────────┐
│   CLIContext    │
├─────────────────┤
│ - config        │
│ - console       │
│ - verbose       │
│ - quiet         │
└────────┬────────┘
         │ uses
         ▼
┌─────────────────┐     ┌─────────────────┐
│ ForensicConfig  │────>│   CacheManager  │
├─────────────────┤     └─────────────────┘
│ - analysis      │
│ - search        │     ┌─────────────────┐
│ - report        │────>│  SignalHandler  │
│ - cache         │     └─────────────────┘
└─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│ AnalyzeCommand  │────>│    IO Module    │
├─────────────────┤     │  (SPEC-IO-001)  │
│ + execute()     │     └─────────────────┘
└─────────────────┘
         │
         ├────────────>┌─────────────────┐
         │             │ Timeline Module │
         │             │(SPEC-TL-001)    │
         │             └─────────────────┘
         │
         └────────────>┌─────────────────┐
                       │ Evidence Module │
                       │(SPEC-EV-001)    │
                       └─────────────────┘
```

---

## 5. 리스크 및 대응

### 5.1 기술적 리스크

| 리스크 | 영향도 | 발생 가능성 | 대응 방안 |
|--------|--------|-------------|-----------|
| SPEC 모듈 통합 복잡성 | 높음 | 중간 | 단계별 통합, 인터페이스 추상화 |
| 대용량 파일 처리 시 메모리 부족 | 중간 | 낮음 | 스트리밍 처리, 청크 단위 작업 |
| 터미널 호환성 문제 | 낮음 | 낮음 | Rich fallback, 단순 텍스트 모드 |
| 캐시 무효화 로직 버그 | 중간 | 중간 | 파일 해시 기반 검증, 철저한 테스트 |

### 5.2 완화 전략

**SPEC 모듈 통합**:
- 각 SPEC의 공개 API만 사용
- 의존성 주입 패턴 적용
- 단위 테스트로 통합 전 검증

**메모리 관리**:
- 제너레이터 기반 스트리밍
- 청크 단위 처리
- 진행 중 메모리 모니터링

**터미널 호환성**:
- TTY 감지 및 fallback
- `--no-color` 옵션 제공
- 파이프 모드 지원

---

## 6. 테스트 전략

### 6.1 단위 테스트

- 각 명령 핸들러 개별 테스트
- 설정 로더 테스트
- 캐시 시스템 테스트
- 출력 포맷터 테스트

### 6.2 통합 테스트

- 전체 분석 파이프라인 테스트
- CLI 명령 조합 테스트
- 캐시 히트/미스 시나리오 테스트
- 시그널 핸들링 테스트

### 6.3 엔드투엔드 테스트

- 실제 녹취 파일로 전체 워크플로우 테스트
- 다양한 옵션 조합 테스트
- 오류 복구 시나리오 테스트

### 6.4 성능 테스트

- CLI 시작 시간 측정
- 분석 처리량 측정
- 메모리 사용량 모니터링
- 대용량 파일 처리 테스트

---

## 7. 인수인계 및 문서화

### 7.1 문서화 항목

- [ ] CLI 사용 가이드 (README)
- [ ] 명령별 상세 문서
- [ ] 설정 파일 레퍼런스
- [ ] 개발자 가이드 (기여 방법)
- [ ] API 문서 (내부 모듈)

### 7.2 예제 스크립트

- [ ] 기본 분석 워크플로우 예제
- [ ] 검색 및 필터링 예제
- [ ] 보고서 생성 예제
- [ ] 자동화 스크립트 예제 (cron job)

---

Version: 1.0.0
Last Updated: 2026-01-19
