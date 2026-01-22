# forensic.man

녹취자료 분석 CLI 도구 - DGX Spark 최적화

## Overview

forensic.man은 NVIDIA DGX Spark 시스템의 특성(ARM64 아키텍처, 128GB 통합 메모리, CUDA 13.0)을 최대한 활용하도록 설계된 녹취자료 분석 도구입니다.

## Features

- **Pydantic v2 기반 강력한 데이터 모델** - Segment, Speaker, Transcript, Evidence 모델
- **DGX Spark 자동 감지 및 최적화** - 시스템 환경에 따른 적응형 처리
- **대용량 파일 스트리밍 처리** - 메모리 효율적인 청크 기반 처리
- **YAML 기반 설정 관리** - 유연한 구성 관리
- **화자 분류 및 증거 추적** - 시간 기반 검색 및 분석 지원
- **GPU 가속화 지원** - CUDA 13.0 호환

## Installation

```bash
pip install -e .
```

## Documentation

### API 문서

- **[IO Module API](docs/api/io.md)** - 대용량 파일 스트리밍 및 청크 처리 API
  - Memory Monitor - 메모리 모니터링 및 적응형 청크 크기 추천
  - Stream Reader - 자동 인코딩 감지 스트리밍 파일 읽기
  - Chunk Processor - 바이트 청크를 Segment로 변환
  - Buffer Manager - UTF-8 멀티바이트 문자 처리
  - Segment Merger - 청크 경계 분할 세그먼트 병합
  - File Discovery - 패턴 기반 파일 검색 및 필터링
  - Progress Tracker - 파일 및 배치 진행률 추적
  - Batch Processor - 여러 파일 순차 처리

### 사용 예제

IO 모듈의 전체 사용 예제는 `examples/io_examples.py`에서 확인할 수 있습니다.

```bash
# 모든 예제 실행
python -m examples.io_examples
```

### DGX Spark 최적화

| 메모리 상태 | 청크 크기 | 배치 크기 | 동작 |
|-------------|-----------|-----------|------|
| Normal + DGX (64GB+) | 4MB | 50 | 최대 처리량 |
| Normal | 1MB | 10 | 표준 처리 |
| Warning (80GB+) | 512KB | 5 | 보수적 처리 |
| Critical (100GB+) | 256KB | 1 | 최소 처리, GC 트리거 |

```python
from forensic.io.memory import get_memory_monitor
from forensic.io.batch import TranscriptBatchProcessor

# 메모리 상태 확인
monitor = get_memory_monitor()
state = monitor.get_memory_state()

# 적응형 청크 크기 적용
config = BatchConfig(
    default_chunk_size=monitor.get_recommended_chunk_size(),
    merge_segments=True,
)

processor = TranscriptBatchProcessor(config=config)
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=forensic --cov-report=html
```

## Requirements

- Python 3.12+
- pydantic >= 2.0
- pyyaml >= 6.0
- rich >= 13.0
- psutil >= 5.9
- chardet >= 5.0

## Project Structure

```
forensic.man/
├── src/forensic/
│   ├── io/           # 대용량 파일 스트리밍 처리
│   ├── models/       # Pydantic 데이터 모델
│   └── utils/        # 유틸리티 (DGX Spark 감지 등)
├── docs/
│   └── api/          # API 문서
├── examples/         # 사용 예제
└── tests/            # 테스트 코드
```

## License

MIT License
