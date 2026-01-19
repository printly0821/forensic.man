# forensic.man

녹취자료 분석 CLI 도구 - DGX Spark 최적화

## Overview

forensic.man은 NVIDIA DGX Spark 시스템의 특성(ARM64 아키텍처, 128GB 통합 메모리, CUDA 13.0)을 최대한 활용하도록 설계된 녹취자료 분석 도구입니다.

## Features

- Pydantic v2 기반 강력한 데이터 모델
- DGX Spark 자동 감지 및 최적화
- YAML 기반 설정 관리
- 화자 분류 및 증거 추적
- GPU 가_acceleration 지원

## Installation

```bash
pip install -e .
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
