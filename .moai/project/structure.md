# forensic.man 프로젝트 구조

## 디렉토리 구조

```
forensic.man/
├── .moai/                      # MoAI-ADK 설정
│   ├── config/                 # 프로젝트 설정
│   │   └── sections/           # 설정 섹션 파일
│   ├── project/                # 프로젝트 문서
│   └── specs/                  # SPEC 문서
│
├── src/                        # 소스 코드
│   └── forensic/               # 메인 패키지
│       ├── __init__.py
│       ├── __main__.py         # CLI 진입점
│       ├── cli/                # CLI 명령 정의
│       │   ├── __init__.py
│       │   ├── analyze.py      # analyze 명령
│       │   ├── search.py       # search 명령
│       │   └── report.py       # report 명령
│       │
│       ├── core/               # 핵심 비즈니스 로직
│       │   ├── __init__.py
│       │   ├── analyzer.py     # 녹취 분석 엔진
│       │   ├── timeline.py     # 시계열 분석
│       │   ├── speaker.py      # 화자 분리
│       │   └── pattern.py      # 패턴 인식
│       │
│       ├── io/                 # 입출력 처리
│       │   ├── __init__.py
│       │   ├── reader.py       # 파일 스트리밍 리더
│       │   ├── writer.py       # 결과 출력
│       │   └── chunk.py        # 청크 기반 처리
│       │
│       ├── models/             # 데이터 모델
│       │   ├── __init__.py
│       │   ├── transcript.py   # 녹취 데이터 모델
│       │   ├── speaker.py      # 화자 모델
│       │   └── evidence.py     # 증거 모델
│       │
│       ├── report/             # 보고서 생성
│       │   ├── __init__.py
│       │   ├── legal.py        # 법적 증거 형식
│       │   ├── timeline.py     # 타임라인 형식
│       │   └── summary.py      # 요약 형식
│       │
│       └── utils/              # 유틸리티
│           ├── __init__.py
│           ├── memory.py       # 메모리 관리
│           └── config.py       # 설정 관리
│
├── tests/                      # 테스트
│   ├── __init__.py
│   ├── conftest.py             # pytest 설정
│   ├── unit/                   # 단위 테스트
│   │   ├── test_analyzer.py
│   │   ├── test_timeline.py
│   │   └── test_pattern.py
│   └── integration/            # 통합 테스트
│       └── test_cli.py
│
├── data/                       # 데이터 디렉토리
│   ├── recordings/             # 녹취 파일 (gitignore)
│   ├── output/                 # 분석 결과 (gitignore)
│   └── samples/                # 샘플 데이터
│
├── docs/                       # 문서
│   ├── usage.md                # 사용 가이드
│   └── api.md                  # API 문서
│
├── pyproject.toml              # 프로젝트 설정
├── README.md                   # 프로젝트 소개
├── .gitignore                  # Git 제외 파일
└── CLAUDE.md                   # Claude Code 설정
```

---

## 주요 디렉토리 설명

### src/forensic/

메인 패키지로 모든 비즈니스 로직이 포함됩니다.

- **cli/**: Click 기반 CLI 명령 정의
- **core/**: 녹취 분석의 핵심 알고리즘
- **io/**: 대용량 파일 스트리밍 및 청크 처리
- **models/**: Pydantic 기반 데이터 모델
- **report/**: 다양한 형식의 보고서 생성기
- **utils/**: 공통 유틸리티 함수

### tests/

pytest 기반 테스트 구조

- **unit/**: 개별 모듈 단위 테스트
- **integration/**: CLI 명령 통합 테스트

### data/

실제 녹취 데이터 및 분석 결과 저장

- **recordings/**: 183개 녹취 파일 (민감 데이터, gitignore 필수)
- **output/**: 분석 결과물
- **samples/**: 테스트용 샘플 데이터

---

## 모듈 의존성

```
cli/ ──────────────► core/ ──────────────► models/
  │                    │
  │                    ▼
  │                   io/
  │                    │
  ▼                    ▼
report/ ◄────────── utils/
```

### 의존성 규칙

1. **cli/** → **core/**: CLI는 핵심 로직 호출
2. **core/** → **io/**: 분석 시 파일 읽기/쓰기
3. **core/** → **models/**: 데이터 구조 사용
4. **report/** → **models/**: 보고서 생성 시 모델 사용
5. **모든 모듈** → **utils/**: 공통 유틸리티

---

## 파일 명명 규칙

### Python 파일

- 소문자 + 언더스코어 (snake_case)
- 예: `timeline_analyzer.py`, `speaker_detection.py`

### 테스트 파일

- `test_` 접두사 사용
- 테스트 대상과 동일한 이름
- 예: `test_analyzer.py`

### 설정 파일

- 표준 명명 규칙 준수
- 예: `pyproject.toml`, `.gitignore`

---

## 확장 지점

### 새로운 분석 알고리즘 추가

`src/forensic/core/` 디렉토리에 새 모듈 추가

### 새로운 보고서 형식 추가

`src/forensic/report/` 디렉토리에 새 형식 구현

### 새로운 CLI 명령 추가

`src/forensic/cli/` 디렉토리에 새 명령 정의

---

Version: 1.0.0
Last Updated: 2026-01-18
