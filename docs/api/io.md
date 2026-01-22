# IO Module API Documentation

DGX Spark 최적화 대용량 파일 스트리밍 및 청크 처리 API 문서입니다.

## Table of Contents

- [Memory Monitor](#memory-monitor)
- [Stream Reader](#stream-reader)
- [Chunk Processor](#chunk-processor)
- [Buffer Manager](#buffer-manager)
- [Segment Merger](#segment-merger)
- [File Discovery](#file-discovery)
- [Progress Tracker](#progress-tracker)
- [Batch Processor](#batch-processor)
- [DGX Spark Optimization](#dgx-spark-optimization)

---

## Memory Monitor

메모리 사용량 모니터링 및 적응형 청크 크기 추천을 제공합니다.

### Classes

#### `MemoryState`

현재 메모리 상태 정보를 나타내는 데이터 클래스입니다.

| Attribute | Type | Description |
|-----------|------|-------------|
| `usage_gb` | `float` | 현재 메모리 사용량 (GB) |
| `available_gb` | `float` | 사용 가능한 메모리 (GB) |
| `total_gb` | `float` | 전체 시스템 메모리 (GB) |
| `level` | `str` | 메모리 압력 수준 (`'normal'`, `'warning'`, `'critical'`) |

#### `MemoryMonitor`

DGX Spark 최적화 메모리 모니터입니다.

```python
from forensic.io.memory import MemoryMonitor, MemoryState

monitor = MemoryMonitor()
state = monitor.get_memory_state()
print(f"Memory: {state.usage_gb:.1f}GB / {state.total_gb:.1f}GB ({state.level})")
```

**Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_usage_gb()` | `float` | 현재 메모리 사용량 반환 (GB) |
| `get_available_gb()` | `float` | 사용 가능한 메모리 반환 (GB) |
| `get_total_gb()` | `float` | 전체 시스템 메모리 반환 (GB) |
| `get_memory_state()` | `MemoryState` | 전체 메모리 상태 반환 |
| `should_reduce_chunk_size()` | `bool` | 청크 크기 감소 필요 여부 (80GB 초과시) |
| `should_force_gc()` | `bool` | 강제 GC 필요 여부 (100GB 초과시) |
| `force_gc()` | `int` | 가비지 컬렉션 실행 및 해제된 바이트 반환 |
| `get_recommended_chunk_size()` | `int` | 메모리 상태 기반 추천 청크 크기 (바이트) |
| `get_recommended_batch_size()` | `int` | 메모리 상태 기반 추천 배치 크기 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `dgx_info` | `DGXSparkInfo` | DGX Spark 시스템 정보 |

**추천 청크 크기:**

| 메모리 상태 | DGX Spark (64GB+) | 일반 환경 |
|-------------|-------------------|-----------|
| Normal | 4MB | 1MB |
| Warning | 512KB | 512KB |
| Critical | 256KB | 256KB |

### Module Functions

| Function | Return Type | Description |
|----------|-------------|-------------|
| `get_memory_monitor()` | `MemoryMonitor` | 전역 MemoryMonitor 인스턴스 반환 |
| `clear_memory_monitor()` | `None` | 전역 MemoryMonitor 인스턴스 초기화 |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MEMORY_WARNING_THRESHOLD_GB` | `80.0` | 경고 임계값 (GB) |
| `MEMORY_CRITICAL_THRESHOLD_GB` | `100.0` | 위험 임계값 (GB) |
| `DEFAULT_CHUNK_SIZE` | `1048576` | 기본 청크 크기 (1MB) |
| `DGX_SPARK_CHUNK_SIZE` | `4194304` | DGX Spark 청크 크기 (4MB) |

---

## Stream Reader

효율적인 파일 스트리밍 읽기를 제공합니다. 자동 인코딩 감지, 진행률 추적, 메모리 인식 청크 크기를 지원합니다.

### Classes

#### `StreamReader`

스트리밍 파일 리더입니다.

```python
from pathlib import Path
from forensic.io.reader import StreamReader

with StreamReader() as reader:
    reader.open(Path("transcript.txt"))
    for chunk in reader.read_chunks():
        process(chunk)
        print(f"Progress: {reader.get_progress_percent():.1f}%")
```

**Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `open(path: Path)` | `StreamReader` | 파일 열기 및 인코딩 자동 감지 (체이닝 지원) |
| `read_chunks(chunk_size: int | None)` | `Iterator[bytes]` | 청크 단위 파일 읽기 |
| `get_progress()` | `float` | 진행률 반환 (0.0 ~ 1.0) |
| `get_progress_percent()` | `float` | 진행률 퍼센트 반환 (0.0 ~ 100.0) |
| `close()` | `None` | 파일 핸들 닫기 |
| `is_open()` | `bool` | 파일 열림 상태 확인 |
| `reset()` | `None` | 읽기 위치를 파일 시작으로 재설정 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `path` | `Path \| None` | 현재 열린 파일 경로 |
| `encoding` | `str` | 감지된 파일 인코딩 |
| `file_size` | `int` | 전체 파일 크기 (바이트) |
| `bytes_read` | `int` | 현재까지 읽은 바이트 수 |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `FileNotOpenError` | 열리지 않은 파일에서 읽기 시도 시 |
| `EncodingDetectionError` | 인코딩 감지 실패 시 |

### Module Functions

| Function | Return Type | Description |
|----------|-------------|-------------|
| `read_file_streaming(path: Path, chunk_size: int \| None)` | `Iterator[bytes]` | 편의 함수: 파일 스트리밍 읽기 |

---

## Chunk Processor

바이트 청크를 Segment 객체로 변환합니다. 청크 경계 처리와 UTF-8 멀티바이트 문자 지원을 포함합니다.

### Classes

#### `ChunkProcessor`

바이트 청크를 Segment 객체로 변환하는 프로세서입니다.

```python
from forensic.io.chunk import ChunkProcessor

processor = ChunkProcessor(encoding="utf-8", default_speaker="unknown")

for chunk in byte_chunks:
    segments = processor.process(chunk, is_last=False)
    for segment in segments:
        print(f"{segment.speaker}: {segment.content}")

# 마지막 버퍼 처리
remaining = processor.flush()
```

**Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `process(chunk: bytes, is_last: bool)` | `list[Segment]` | 청크 처리 및 세그먼트 반환 |
| `get_pending()` | `str \| None` | 버퍼의 미완성 텍스트 반환 |
| `flush()` | `list[Segment]` | 버퍼 플러시 및 남은 세그먼트 반환 |
| `reset()` | `None` | 프로세서 상태 초기화 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `encoding` | `str` | 텍스트 인코딩 |

#### `TimestampedChunkProcessor`

타임스탬프 추출을 지원하는 청크 프로세서입니다.

```python
from forensic.io.chunk import TimestampedChunkProcessor

processor = TimestampedChunkProcessor()
# [00:01:23] Speaker: Content 형식 처리
```

### Exceptions

| Exception | Description |
|-----------|-------------|
| `DecodingError` | 청크 디코딩 실패 시 |

---

## Buffer Manager

청크 경계에서의 불완전한 라인과 UTF-8 멀티바이트 문자 처리를 위한 버퍼 관리자입니다.

### Classes

#### `BufferState`

현재 버퍼 상태 정보입니다.

| Attribute | Type | Description |
|-----------|------|-------------|
| `byte_buffer_size` | `int` | 현재 바이트 버퍼 크기 |
| `line_buffer_size` | `int` | 현재 라인 버퍼 크기 |
| `total_size` | `int` | 전체 버퍼 크기 |
| `is_at_limit` | `bool` | 크기 제한 도달 여부 |

#### `BufferManager`

청크 경계 처리 버퍼 관리자입니다.

```python
from forensic.io.buffer import BufferManager

buffer = BufferManager(size_limit=64 * 1024)  # 64KB

for chunk in chunks:
    complete = buffer.append(chunk)
    text = complete.decode("utf-8")
    process(text)

# 남은 데이터 플러시
remaining_bytes, remaining_line = buffer.flush()
```

**Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `append(data: bytes)` | `bytes` | 데이터 추가 및 완전한 바이트 반환 |
| `get_incomplete_line()` | `str \| None` | 불완전한 라인 반환 |
| `set_incomplete_line(line: str)` | `None` | 불완전한 라인 설정 |
| `prepend_to_text(text: str)` | `str` | 버퍼링된 라인을 텍스트 앞에 추가 |
| `flush()` | `tuple[bytes, str]` | 버퍼 플러시 및 남은 데이터 반환 |
| `flush_bytes()` | `bytes` | 바이트 버퍼만 플러시 |
| `flush_line()` | `str` | 라인 버퍼만 플러시 |
| `reset()` | `None` | 버퍼 상태 초기화 |
| `has_pending_data()` | `bool` | 대기 중인 데이터 존재 여부 |
| `decode_safe(data: bytes, encoding: str)` | `tuple[str, bytes]` | 안전한 디코딩 |
| `get_state()` | `BufferState` | 현재 버퍼 상태 반환 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `byte_buffer_size` | `int` | 현재 바이트 버퍼 크기 |
| `line_buffer_size` | `int` | 현재 라인 버퍼 크기 |
| `total_size` | `int` | 전체 버퍼 크기 |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `BufferOverflowError` | 버퍼 크기 제한 초과 시 |
| `InvalidUTF8Error` | 잘못된 UTF-8 시퀀스 감지 시 |

### Module Functions

| Function | Return Type | Description |
|----------|-------------|-------------|
| `is_valid_utf8_sequence(data: bytes)` | `bool` | UTF-8 시퀀스 유효성 확인 |
| `get_utf8_char_length(leading_byte: int)` | `int` | UTF-8 문자 길이 반환 (1-4) |
| `find_last_complete_char(data: bytes)` | `int` | 마지막 완전한 문자의 인덱스 |

---

## Segment Merger

청크 경계에서 분할된 세그먼트의 병합을 처리합니다.

### Classes

#### `MergeStats`

병합 작업 통계입니다.

| Attribute | Type | Description |
|-----------|------|-------------|
| `segments_received` | `int` | 수신된 세그먼트 총수 |
| `segments_merged` | `int` | 병합 작업 수 |
| `segments_output` | `int` | 출력된 세그먼트 총수 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `merge_ratio` | `float` | 병합 비율 (merged / received) |

#### `SegmentMerger`

세그먼트 병합기입니다.

```python
from forensic.io.merger import SegmentMerger

merger = SegmentMerger(time_tolerance=0.5)

for segments in segment_batches:
    completed = merger.add_segments(segments)
    for segment in completed:
        process(segment)

# 마지막 대기 세그먼트 플러시
final_segments = merger.flush()
```

**Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `add_segment(segment: Segment)` | `list[Segment]` | 세그먼트 추가 및 완료된 세그먼트 반환 |
| `add_segments(segments: list[Segment])` | `list[Segment]` | 여러 세그먼트 추가 |
| `should_merge(seg1: Segment, seg2: Segment)` | `bool` | 병합 여부 확인 |
| `merge(seg1: Segment, seg2: Segment)` | `Segment` | 두 세그먼트 병합 |
| `flush()` | `list[Segment]` | 대기 세그먼트 플러시 |
| `reset()` | `None` | 병합기 상태 초기화 |
| `process_batch(segments: list[Segment], is_last: bool)` | `list[Segment]` | 배치 처리 편의 함수 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `stats` | `MergeStats` | 병합 통계 |
| `has_pending` | `bool` | 대기 세그먼트 존재 여부 |
| `pending_segment` | `Segment \| None` | 대기 세그먼트 |

**병합 기준:**
- 동일 화자
- 시간 연속성 (seg1.end_time ~= seg2.start_time)
- 유의미한 간격 없음

### Module Functions

| Function | Return Type | Description |
|----------|-------------|-------------|
| `detect_split_segments(segments: list[Segment])` | `list[tuple[int, int]]` | 분할된 세그먼트 쌍 감지 |
| `merge_all_continuous(segments: list[Segment])` | `list[Segment]` | 모든 연속 세그먼트 병합 |
| `validate_segment_continuity(segments: list[Segment])` | `list[str]` | 세그먼트 시간 연속성 검증 |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_TIME_TOLERANCE` | `0.5` | 연속 세그먼트 판정 시간 허용오차 (초) |
| `DEFAULT_MIN_GAP` | `0.1` | 별도 세그먼트 판정 최소 간격 (초) |

---

## File Discovery

글롭 패턴 기반 파일 검색 및 필터링을 제공합니다.

### Enums

#### `SortOrder`

파일 정렬 순서입니다.

| Value | Description |
|-------|-------------|
| `NAME` | 이름 오름차순 |
| `SIZE` | 크기 오름차순 |
| `DATE` | 날짜 오름차순 |
| `NAME_DESC` | 이름 내림차순 |
| `SIZE_DESC` | 크기 내림차순 |
| `DATE_DESC` | 날짜 내림차순 |

### Classes

#### `FileFilter`

파일 검색 필터 조건입니다.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `pattern` | `str` | `"*.txt"` | 글롭 패턴 |
| `recursive` | `bool` | `False` | 하위 디렉토리 검색 여부 |
| `min_size` | `int \| None` | `None` | 최소 파일 크기 (바이트) |
| `max_size` | `int \| None` | `None` | 최대 파일 크기 (바이트) |
| `after_date` | `datetime \| None` | `None` | 이후 수정된 파일만 |
| `before_date` | `datetime \| None` | `None` | 이전 수정된 파일만 |
| `extensions` | `list[str]` | `[]` | 허용 파일 확장자 |

**Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `matches_size(size: int)` | `bool` | 크기 조건 일치 확인 |
| `matches_date(mtime: datetime)` | `bool` | 날짜 조건 일치 확인 |
| `matches_extension(path: Path)` | `bool` | 확장자 조건 일치 확인 |

#### `FileInfo`

파일 정보입니다.

| Attribute | Type | Description |
|-----------|------|-------------|
| `path` | `Path` | 파일 경로 |
| `size` | `int` | 파일 크기 (바이트) |
| `mtime` | `datetime` | 수정 시간 |

#### `FileDiscovery`

파일 검색 클래스입니다.

```python
from pathlib import Path
from datetime import datetime, timedelta
from forensic.io.discovery import FileDiscovery, FileFilter, SortOrder

discovery = FileDiscovery()

# 간단한 패턴 검색
files = discovery.find_by_pattern(Path("/data"), "*.txt", recursive=True)

# 고급 필터링
filter = FileFilter(
    pattern="*.txt",
    recursive=True,
    min_size=1024,
    after_date=datetime.now() - timedelta(days=7)
)
files = discovery.find(Path("/data"), filter, sort_order=SortOrder.SIZE_DESC)
```

**Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `find(directory: Path, filter: FileFilter, sort_order: SortOrder \| None)` | `list[Path]` | 필터 조건으로 파일 검색 |
| `find_by_pattern(directory: Path, pattern: str, recursive: bool, sort_order: SortOrder \| None)` | `list[Path]` | 패턴으로 파일 검색 |
| `find_transcript_files(directory: Path, recursive: bool, sort_order: SortOrder)` | `list[Path]` | 녹취록 파일 검색 (.txt, .srt, .vtt, .json) |
| `get_total_size(files: list[Path])` | `int` | 전체 파일 크기 계산 |
| `count_by_extension(files: list[Path])` | `dict[str, int]` | 확장자별 파일 수 |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `DirectoryNotFoundError` | 디렉토리가 존재하지 않을 때 |
| `InvalidFilterError` | 필터 조건이 잘못되었을 때 |

### Module Functions

| Function | Return Type | Description |
|----------|-------------|-------------|
| `discover_files(directory: Path, pattern: str, recursive: bool)` | `list[Path]` | 편의 함수: 파일 검색 |

---

## Progress Tracker

파일 및 배치 수준 진행률 추적을 제공합니다.

### Type Aliases

| Type | Definition |
|------|------------|
| `ProgressCallback` | `Callable[[Path, float, float], None]` |
| `SimpleProgressCallback` | `Callable[[Path, float], None]` |

### Classes

#### `FileProgress`

단일 파일 진행 정보입니다.

| Attribute | Type | Description |
|-----------|------|-------------|
| `path` | `Path` | 파일 경로 |
| `total_bytes` | `int` | 전체 파일 크기 (바이트) |
| `bytes_processed` | `int` | 처리된 바이트 수 |
| `is_complete` | `bool` | 완료 여부 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `progress` | `float` | 진행률 (0.0 ~ 1.0) |
| `progress_percent` | `float` | 진행률 퍼센트 (0.0 ~ 100.0) |

#### `BatchProgress`

배치 진행 정보입니다.

| Attribute | Type | Description |
|-----------|------|-------------|
| `total_files` | `int` | 전체 파일 수 |
| `files_completed` | `int` | 완료된 파일 수 |
| `total_bytes` | `int` | 전체 바이트 수 |
| `bytes_processed` | `int` | 처리된 바이트 수 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `progress` | `float` | 전체 진행률 (0.0 ~ 1.0) |
| `progress_percent` | `float` | 전체 진행률 퍼센트 (0.0 ~ 100.0) |
| `files_remaining` | `int` | 남은 파일 수 |

#### `ProgressTracker`

진행률 추적기입니다.

```python
from forensic.io.progress import ProgressTracker

tracker = ProgressTracker(total_files=10)

# 콜백 설정
def print_progress(path: Path, file_progress: float, overall_progress: float):
    print(f"{path.name}: {file_progress:.1%} - Overall: {overall_progress:.1%}")

tracker.set_callback(print_progress)

# 파일 처리
for file in files:
    tracker.start_file(file, file.stat().st_size)
    for chunk in read_chunks(file):
        process(chunk)
        tracker.update_bytes(len(chunk))
    tracker.finish_file()
```

**Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `start_file(path: Path, total_bytes: int)` | `None` | 새 파일 추적 시작 |
| `update_bytes(bytes_processed: int)` | `None` | 처리된 바이트 업데이트 |
| `update_progress(progress: float)` | `None` | 진행률 직접 업데이트 (0.0 ~ 1.0) |
| `finish_file()` | `None` | 현재 파일 완료 처리 |
| `set_callback(callback: ProgressCallback)` | `None` | 진행률 콜백 설정 |
| `set_simple_callback(callback: SimpleProgressCallback)` | `None` | 단순 콜백 설정 |
| `clear_callbacks()` | `None` | 모든 콜백 제거 |
| `get_file_history()` | `list[FileProgress]` | 완료된 파일 기록 반환 |
| `reset()` | `None` | 추적기 상태 초기화 |
| `get_summary()` | `dict[str, object]` | 진행률 요약 반환 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `current_file_progress` | `float` | 현재 파일 진행률 (0.0 ~ 1.0) |
| `overall_progress` | `float` | 전체 진행률 (0.0 ~ 1.0) |
| `current_file` | `Path \| None` | 현재 처리 중인 파일 |
| `files_completed` | `int` | 완료된 파일 수 |
| `files_remaining` | `int` | 남은 파일 수 |
| `batch_progress` | `BatchProgress` | 배치 진행 정보 |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `NoActiveFileError` | 활성 파일 없이 업데이트 시도 시 |
| `ProgressCallbackError` | 콜백 실행 실패 시 |

### Module Functions

| Function | Return Type | Description |
|----------|-------------|-------------|
| `create_progress_tracker(files: list[Path], callback: ProgressCallback \| None)` | `ProgressTracker` | 편의 함수: 진행률 추적기 생성 |

---

## Batch Processor

여러 녹취록 파일을 순차적으로 처리합니다. 메모리 인식 청크 크기 조정과 결과 스트리밍을 지원합니다.

### Classes

#### `BatchConfig`

배치 처리 설정입니다.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_chunk_size` | `int` | `1048576` | 기본 청크 크기 (바이트) |
| `skip_on_error` | `bool` | `True` | 오류 시 건너뛰기 |
| `merge_segments` | `bool` | `True` | 연속 세그먼트 병합 |
| `encoding` | `str` | `"utf-8"` | 텍스트 인코딩 |
| `default_speaker` | `str` | `"unknown"` | 기본 화자 ID |

#### `BatchResult`

배치 처리 결과입니다.

| Attribute | Type | Description |
|-----------|------|-------------|
| `total_files` | `int` | 전체 파일 수 |
| `successful_files` | `int` | 성공한 파일 수 |
| `failed_files` | `int` | 실패한 파일 수 |
| `total_segments` | `int` | 전체 세그먼트 수 |
| `total_duration` | `float` | 전체 녹취 길이 (초) |
| `errors` | `list[tuple[Path, str]]` | (파일 경로, 오류 메시지) 목록 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `success_rate` | `float` | 성공률 (0.0 ~ 1.0) |

#### `TranscriptBatchProcessor`

녹취록 배치 프로세서입니다.

```python
from pathlib import Path
from forensic.io.batch import TranscriptBatchProcessor, BatchConfig

# 프로세서 생성
config = BatchConfig(
    default_chunk_size=4 * 1024 * 1024,  # 4MB
    skip_on_error=True,
    merge_segments=True
)
processor = TranscriptBatchProcessor(config=config)

# 파일 검색
files = processor.discover_files(Path("/data/transcripts"), "*.txt", recursive=True)

# 배치 처리
for transcript in processor.process_all(files, on_progress=lambda p, prog: print(f"{p}: {prog:.1%}")):
    print(f"Processed: {transcript.file_path.name}")
    print(f"  Speakers: {', '.join(transcript.speakers)}")
    print(f"  Segments: {transcript.segment_count}")

# 결과 요약
summary = processor.get_batch_summary()
print(f"Success rate: {summary['success_rate']:.1%}")
```

**Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `discover_files(directory: Path, pattern: str, recursive: bool, sort_order: SortOrder)` | `list[Path]` | 패턴으로 파일 검색 |
| `discover_files_filtered(directory: Path, filter: FileFilter, sort_order: SortOrder)` | `list[Path]` | 필터로 파일 검색 |
| `process_all(files: list[Path], on_progress: SimpleProgressCallback, skip_on_error: bool)` | `Iterator[Transcript]` | 모든 파일 처리 및 결과 스트리밍 |
| `process_single(file_path: Path)` | `Transcript` | 단일 파일 처리 |
| `get_batch_summary()` | `dict[str, object]` | 배치 처리 요약 |

**속성 (Properties):**

| Property | Type | Description |
|----------|------|-------------|
| `config` | `BatchConfig` | 배치 처리 설정 |
| `result` | `BatchResult` | 배치 처리 결과 |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `BatchProcessingError` | 배치 처리 오류 |
| `FileProcessingError` | 단일 파일 처리 오류 |

### Module Functions

| Function | Return Type | Description |
|----------|-------------|-------------|
| `process_directory(directory: Path, pattern: str, recursive: bool, on_progress: SimpleProgressCallback)` | `Iterator[Transcript]` | 편의 함수: 디렉토리 처리 |
| `process_files(files: list[Path], on_progress: SimpleProgressCallback, skip_on_error: bool)` | `Iterator[Transcript]` | 편의 함수: 파일 목록 처리 |

---

## DGX Spark Optimization

### DGX Spark 감지

시스템은 자동으로 DGX Spark 환경을 감지하고 최적화를 적용합니다.

```python
from forensic.utils.dgx_detector import detect_dgx_spark
from forensic.io.memory import get_memory_monitor

dgx_info = detect_dgx_spark()
print(f"DGX Spark: {dgx_info.is_optimized}")
print(f"System: {dgx_info.system_info}")

monitor = get_memory_monitor()
print(f"Recommended chunk size: {monitor.get_recommended_chunk_size() / 1024 / 1024}MB")
```

### 최적화 전략

| 메모리 상태 | 청크 크기 | 배치 크기 | 동작 |
|-------------|-----------|-----------|------|
| Normal + DGX (64GB+) | 4MB | 50 | 최대 처리량 |
| Normal | 1MB | 10 | 표준 처리 |
| Warning (80GB+) | 512KB | 5 | 보수적 처리 |
| Critical (100GB+) | 256KB | 1 | 최소 처리, GC 트리거 |

### 메모리 관리 권장사항

1. **진행률 추적**: 항상 `ProgressTracker` 사용하여 메모리 사용 모니터링
2. **청크 크기 조정**: 메모리 상태에 따라 동적 조정
3. **결과 스트리밍**: 대용량 처리 시 `Iterator` 사용하여 메모리 절약
4. **명시적 GC**: 위험 수준 도달 시 `force_gc()` 호출

```python
from forensic.io.memory import get_memory_monitor

monitor = get_memory_monitor()

if monitor.should_force_gc():
    freed = monitor.force_gc()
    print(f"Freed {freed / 1024 / 1024}MB")

# 또는 청크 크기 조정
if monitor.should_reduce_chunk_size():
    chunk_size = monitor.get_recommended_chunk_size()
```
