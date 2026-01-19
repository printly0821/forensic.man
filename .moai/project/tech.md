# forensic.man 기술 스택

## 기술 스택 개요

| 영역 | 기술 | 버전 | 용도 |
|------|------|------|------|
| 언어 | Python | 3.10+ | 메인 개발 언어 |
| CLI | Click | 8.x | CLI 프레임워크 |
| 데이터 모델 | Pydantic | 2.x | 데이터 검증 및 직렬화 |
| 테스트 | pytest | 8.x | 테스트 프레임워크 |
| 패키지 관리 | uv | 최신 | 빠른 의존성 관리 |

---

## 핵심 라이브러리

### CLI 프레임워크

**Click** (추천)

- 직관적인 데코레이터 기반 명령 정의
- 자동 도움말 생성
- 중첩 명령 및 그룹 지원

```python
import click

@click.group()
def cli():
    """forensic.man - 녹취자료 분석 도구"""
    pass

@cli.command()
@click.option('--input', '-i', required=True, help='입력 디렉토리')
@click.option('--output', '-o', required=True, help='출력 디렉토리')
def analyze(input, output):
    """녹취 파일 분석"""
    pass
```

### 데이터 모델링

**Pydantic v2**

- 타입 안전성 보장
- 자동 검증
- JSON 직렬화/역직렬화

```python
from pydantic import BaseModel
from datetime import datetime

class Transcript(BaseModel):
    id: str
    speaker: str
    timestamp: datetime
    content: str
    duration_seconds: float
```

### 대용량 파일 처리

**메모리 효율적 스트리밍**

30분 이상 녹취 파일 처리를 위한 청크 기반 접근:

```python
def read_chunks(file_path: str, chunk_size: int = 1024 * 1024):
    """1MB 청크 단위로 파일 스트리밍"""
    with open(file_path, 'r', encoding='utf-8') as f:
        while chunk := f.read(chunk_size):
            yield chunk
```

### 비동기 처리 (선택)

**asyncio + aiofiles**

183개 파일 병렬 처리 시 성능 향상:

```python
import asyncio
import aiofiles

async def process_files(file_paths: list[str]):
    tasks = [process_single(path) for path in file_paths]
    return await asyncio.gather(*tasks)
```

---

## 개발 환경

### Python 버전

- **최소**: Python 3.10
- **권장**: Python 3.12

### 패키지 매니저

**uv** (권장)

```bash
# 프로젝트 초기화
uv init

# 의존성 설치
uv add click pydantic

# 개발 의존성
uv add --dev pytest pytest-cov ruff
```

### 코드 품질

**Ruff** - 린팅 및 포매팅

```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
```

### LSP 서버

**Pyright** (권장)

```bash
# 설치
npm install -g pyright

# 또는 pip으로
pip install pyright
```

---

## 의존성 목록

### 런타임 의존성

```toml
[project]
dependencies = [
    "click>=8.0",
    "pydantic>=2.0",
    "rich>=13.0",        # 터미널 출력 포매팅
    "python-dateutil",   # 날짜 파싱
]
```

### 개발 의존성

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.1",
    "pyright>=1.1",
]
```

---

## 성능 최적화 전략

### 메모리 관리

1. **제너레이터 사용**: 전체 파일을 메모리에 로드하지 않음
2. **청크 처리**: 1MB 단위로 순차 처리
3. **가비지 컬렉션**: 대용량 처리 후 명시적 gc.collect()

### 병렬 처리

1. **multiprocessing**: CPU 집약적 분석 작업
2. **asyncio**: I/O 바운드 파일 읽기/쓰기
3. **concurrent.futures**: 간단한 병렬 처리

### 캐싱

1. **분석 결과 캐싱**: 동일 파일 재분석 방지
2. **중간 결과 저장**: 장시간 작업 중단 대비

---

## 빌드 및 배포

### 패키징

```toml
# pyproject.toml
[project]
name = "forensic-man"
version = "0.1.0"

[project.scripts]
forensic = "forensic.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 설치

```bash
# 개발 모드 설치
uv pip install -e .

# 글로벌 설치
pip install .
```

---

## 보안 고려사항

### 민감 데이터 보호

1. **녹취 파일**: `.gitignore`에 추가
2. **분석 결과**: 로컬에만 저장
3. **개인정보**: 로그에 기록하지 않음

### 권장 .gitignore

```gitignore
# 녹취 데이터
data/recordings/
data/output/

# 분석 결과
*.analysis.json
*.report.md

# 환경 설정
.env
```

---

## 개발 워크플로우

### TDD 접근

1. 테스트 먼저 작성
2. 최소 구현으로 통과
3. 리팩토링

### 브랜치 전략

- `main`: 안정 버전
- `develop`: 개발 버전
- `feature/*`: 기능 개발

### 커밋 메시지

```
feat: 시계열 분석 기능 추가
fix: 메모리 누수 수정
docs: 사용 가이드 업데이트
```

---

Version: 1.0.0
Last Updated: 2026-01-18
