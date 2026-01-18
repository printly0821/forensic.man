---
id: SPEC-IO-001
version: "1.0.0"
status: "draft"
created: "2026-01-18"
updated: "2026-01-18"
author: "지니"
priority: "HIGH"
---

# SPEC-IO-001: 대용량 파일 스트리밍 및 청크 처리

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-01-18 | 지니 | 초기 작성 - 대용량 파일 스트리밍 및 청크 처리 모듈 |

---

## 1. 개요

### 1.1 목적

대용량 녹취 파일을 효율적으로 처리하기 위한 스트리밍 기반 I/O 모듈을 구현합니다. 128GB 통합 메모리를 가진 DGX Spark 환경에서 최적의 성능을 발휘하면서도 메모리 안정성을 보장하는 설계를 적용합니다.

### 1.2 범위

- 스트리밍 방식 파일 읽기 (전체 메모리 로드 금지)
- 제너레이터 기반 청크 처리
- 청크 경계 세그먼트 분할 처리
- 메모리 모니터링 및 자동 조절
- 배치 처리 및 비동기 병렬 처리

### 1.3 의존성

- **SPEC-CORE-001**: Transcript, Segment, DGXSparkDetector, Config 모델

### 1.4 대상 시스템

| 항목 | 사양 |
|------|------|
| 플랫폼 | NVIDIA DGX Spark |
| 메모리 | 128GB 통합 LPDDR5x |
| 청크 크기 | 기본 1MB, DGX Spark에서 4MB |
| 배치 크기 | 기본 10, DGX Spark에서 최대 50 |

---

## 2. 요구사항 (EARS 형식)

### 2.1 유비쿼터스 요구사항 (Ubiquitous)

**[REQ-U-001]** 시스템은 항상 스트리밍 방식으로 파일을 읽어야 한다 (전체 메모리 로드 금지).

**[REQ-U-002]** 모든 청크 처리는 제너레이터 패턴을 사용해야 한다.

**[REQ-U-003]** 파일 처리 중 메모리 사용량을 지속적으로 모니터링해야 한다.

**[REQ-U-004]** 청크 경계에서 발생하는 세그먼트 분할을 올바르게 처리해야 한다.

### 2.2 이벤트 기반 요구사항 (Event-Driven)

**[REQ-E-001]** 파일이 열릴 때, 인코딩을 자동 감지해야 한다.

**[REQ-E-002]** 청크 처리가 완료될 때, 진행률을 업데이트해야 한다.

**[REQ-E-003]** 배치 처리 중 파일 하나가 완료될 때, 즉시 결과를 yield해야 한다.

### 2.3 상태 기반 요구사항 (State-Driven)

**[REQ-S-001]** 메모리 사용량이 80GB를 초과한 상태일 때, 청크 크기를 자동으로 줄여야 한다.

**[REQ-S-002]** 메모리 사용량이 100GB를 초과한 상태일 때, 강제 GC를 실행하고 배치 크기를 1로 줄여야 한다.

### 2.4 원치 않는 동작 요구사항 (Unwanted Behavior)

**[REQ-W-001]** 파일 읽기 실패 시, 시스템은 명확한 오류 메시지와 함께 복구 가능한 예외를 발생시켜야 한다.

**[REQ-W-002]** 메모리 부족 상황 시, 시스템은 OOM 발생 전에 안전하게 중단하고 진행 상황을 저장해야 한다.

### 2.5 선택적 요구사항 (Optional Feature)

**[REQ-O-001]** 사용자가 병렬 처리를 활성화하면, asyncio 기반 동시 처리를 수행해야 한다.

**[REQ-O-002]** 사용자가 진행률 콜백을 제공하면, 각 청크 처리 시 콜백을 호출해야 한다.

### 2.6 복합 요구사항 (Complex)

**[REQ-C-001]** DGX Spark 환경이고 메모리가 64GB 이상 사용 가능할 때, 청크 크기를 4MB로 증가시키고 배치 크기를 최대 50으로 설정해야 한다.

---

## 3. 인터페이스 정의

### 3.1 StreamReader

```python
class StreamReader(Protocol):
    """스트리밍 방식 파일 읽기 인터페이스"""

    def open(self, path: Path) -> "StreamReader":
        """파일을 열고 인코딩을 자동 감지한다."""
        ...

    def read_chunks(self, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        """지정된 크기의 청크로 파일을 읽는다."""
        ...

    def get_progress(self) -> float:
        """현재 진행률을 반환한다 (0.0 ~ 1.0)."""
        ...

    def close(self) -> None:
        """파일 핸들을 닫고 리소스를 해제한다."""
        ...
```

### 3.2 ChunkProcessor

```python
class ChunkProcessor(Protocol):
    """청크 처리 인터페이스"""

    def process(self, chunk: bytes, is_last: bool = False) -> list[Segment]:
        """청크를 처리하여 세그먼트 목록을 반환한다."""
        ...

    def get_pending(self) -> Optional[str]:
        """미완료된 부분 텍스트를 반환한다."""
        ...

    def flush(self) -> list[Segment]:
        """버퍼에 남은 모든 데이터를 처리하고 반환한다."""
        ...
```

### 3.3 BatchProcessor

```python
class BatchProcessor(Protocol):
    """배치 처리 인터페이스"""

    def discover_files(self, directory: Path, pattern: str = "*.txt") -> list[Path]:
        """디렉토리에서 패턴에 맞는 파일을 탐색한다."""
        ...

    def process_all(
        self,
        files: list[Path],
        on_progress: Optional[Callable[[Path, float], None]] = None
    ) -> Iterator[Transcript]:
        """파일 목록을 순차 처리하고 결과를 yield한다."""
        ...

    async def process_all_async(
        self,
        files: list[Path],
        max_concurrent: int = 10
    ) -> AsyncIterator[Transcript]:
        """파일 목록을 비동기 병렬 처리하고 결과를 yield한다."""
        ...
```

### 3.4 MemoryMonitor

```python
class MemoryMonitor(Protocol):
    """메모리 모니터링 인터페이스"""

    def get_usage_gb(self) -> float:
        """현재 메모리 사용량을 GB 단위로 반환한다."""
        ...

    def get_available_gb(self) -> float:
        """사용 가능한 메모리를 GB 단위로 반환한다."""
        ...

    def should_reduce_chunk_size(self) -> bool:
        """청크 크기 감소가 필요한지 판단한다 (80GB 초과 시)."""
        ...

    def force_gc(self) -> int:
        """강제 가비지 컬렉션을 실행하고 해제된 바이트 수를 반환한다."""
        ...
```

---

## 4. 파일 구조

```
src/forensic/io/
├── __init__.py          # 모듈 초기화 및 공개 API
├── reader.py            # StreamReader 구현
├── chunk.py             # ChunkProcessor 구현
├── batch.py             # BatchProcessor 구현
├── memory.py            # MemoryMonitor 구현
├── buffer.py            # BufferManager (청크 경계 처리)
├── merger.py            # SegmentMerger (분할된 세그먼트 병합)
├── discovery.py         # FileDiscovery (파일 탐색)
└── progress.py          # ProgressTracker (진행률 추적)
```

---

## 5. 기술적 제약사항

### 5.1 메모리 임계값 시스템

| 레벨 | 임계값 | 조치 |
|------|--------|------|
| 정상 | < 80GB | 기본 설정 유지 |
| 경고 | 80GB ~ 100GB | 청크 크기 50% 감소 |
| 위험 | > 100GB | 강제 GC + 배치 크기 1 |

### 5.2 청크 크기 설정

| 환경 | 기본 청크 크기 | 최대 배치 크기 |
|------|---------------|---------------|
| 일반 | 1MB | 10 |
| DGX Spark (64GB+) | 4MB | 50 |
| 메모리 경고 상태 | 512KB | 5 |
| 메모리 위험 상태 | 256KB | 1 |

### 5.3 인코딩 우선순위

1. chardet 자동 감지
2. UTF-8 with BOM
3. UTF-8 폴백

### 5.4 의존성 목록

```toml
[project]
dependencies = [
    "psutil>=5.9",           # 메모리 모니터링
    "chardet>=5.0",          # 인코딩 감지
]

[project.optional-dependencies]
async = [
    "aiofiles>=24.0",        # 비동기 파일 I/O
]
progress = [
    "tqdm>=4.66",            # 진행률 표시
]
```

---

## 6. 비기능적 요구사항

### 6.1 성능

- 청크 읽기 속도: > 500MB/s (SSD 기준)
- 메모리 오버헤드: < 50MB (기본 인프라)
- 진행률 업데이트 빈도: 매 청크 또는 1초 간격

### 6.2 안정성

- 파일 핸들 자동 정리 (context manager 패턴)
- 중단 시 진행 상황 저장 가능
- 메모리 누수 방지를 위한 명시적 리소스 해제

### 6.3 확장성

- 제너레이터 패턴으로 무제한 파일 크기 지원
- 비동기 처리로 I/O 바운드 작업 병렬화
- 플러그인 형태의 사용자 정의 프로세서 지원

---

Version: 1.0.0
Last Updated: 2026-01-18
