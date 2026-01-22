# forensic.man Documentation

DGX Spark 최적화 녹취자료 분석 도구 문서입니다.

## API Documentation

### [IO Module API](api/io.md)

대용량 파일 스트리밍 및 청크 처리 API 문서입니다.

- **MemoryMonitor** - 메모리 사용량 모니터링 및 적응형 청크 크기 추천
- **StreamReader** - 자동 인코딩 감지 스트리밍 파일 읽기
- **ChunkProcessor** - 바이트 청크를 Segment로 변환
- **BufferManager** - UTF-8 멀티바이트 문자 처리
- **SegmentMerger** - 청크 경계 분할 세그먼트 병합
- **FileDiscovery** - 패턴 기반 파일 검색 및 필터링
- **ProgressTracker** - 파일 및 배치 진행률 추적
- **TranscriptBatchProcessor** - 여러 파일 순차 처리

## Usage Examples

전체 사용 예제는 `examples/io_examples.py`에서 확인할 수 있습니다.

```bash
python -m examples.io_examples
```

## DGX Spark Optimization

### Memory Levels

| Level | Threshold | Chunk Size | Batch Size |
|-------|-----------|------------|------------|
| Normal + DGX | 64GB+ available | 4MB | 50 |
| Normal | - | 1MB | 10 |
| Warning | 80GB+ usage | 512KB | 5 |
| Critical | 100GB+ usage | 256KB | 1 |

### Quick Start

```python
from forensic.io.memory import get_memory_monitor
from forensic.io.batch import TranscriptBatchProcessor, process_directory
from pathlib import Path

# 메모리 최적화 설정
monitor = get_memory_monitor()
chunk_size = monitor.get_recommended_chunk_size()

# 배치 처리
processor = TranscriptBatchProcessor(
    config=BatchConfig(
        default_chunk_size=chunk_size,
        merge_segments=True,
    )
)

# 디렉토리 처리
for transcript in processor.process_all(files):
    print(f"Processed: {transcript.file_path.name}")
    print(f"Speakers: {', '.join(transcript.speakers)}")
```
