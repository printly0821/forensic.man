---
id: SPEC-CORE-001
version: "1.0.0"
status: "draft"
created: "2026-01-18"
updated: "2026-01-18"
author: "지니"
priority: "HIGH"
---

# SPEC-CORE-001: DGX Spark 최적화 기반 인프라 및 데이터 모델

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-01-18 | 지니 | 초기 작성 - DGX Spark 환경 반영 |

---

## 1. 개요

### 1.1 목적

forensic.man 프로젝트의 기반 인프라를 구축합니다. NVIDIA DGX Spark 시스템의 특성(ARM64 아키텍처, 128GB 통합 메모리, CUDA 13.0)을 최대한 활용하는 설계를 적용합니다.

### 1.2 범위

- Pydantic v2 기반 데이터 모델 정의
- DGX Spark 최적화 설정 관리 시스템
- 프로젝트 패키지 구조 및 빌드 설정
- ARM64 호환성 검증 프로세스

### 1.3 대상 시스템

| 항목 | 사양 |
|------|------|
| 플랫폼 | NVIDIA DGX Spark |
| CPU | 20코어 ARM (Cortex-X925 + A725) |
| GPU | Blackwell 6,144 CUDA cores |
| 메모리 | 128GB 통합 LPDDR5x |
| Python | 3.12+ (ARM64) |

---

## 2. 요구사항 (EARS 형식)

### 2.1 유비쿼터스 요구사항 (Ubiquitous)

**[REQ-U-001]** 시스템은 항상 ARM64 아키텍처에서 실행 가능해야 한다.

**[REQ-U-002]** 모든 데이터 모델은 Pydantic v2를 사용하여 정의되어야 한다.

**[REQ-U-003]** 설정 파일은 YAML 형식으로 작성되어야 한다.

### 2.2 이벤트 기반 요구사항 (Event-Driven)

**[REQ-E-001]** 시스템이 시작될 때, DGX Spark 환경 감지를 수행해야 한다.

**[REQ-E-002]** 녹취 파일이 로드될 때, Transcript 모델로 파싱되어야 한다.

**[REQ-E-003]** 설정 파일이 변경될 때, 자동으로 재로드되어야 한다.

### 2.3 상태 기반 요구사항 (State-Driven)

**[REQ-S-001]** GPU가 사용 가능한 상태일 때, CUDA 가속 옵션을 활성화해야 한다.

**[REQ-S-002]** 메모리 사용량이 100GB를 초과한 상태일 때, 배치 크기를 자동 조절해야 한다.

### 2.4 선택적 요구사항 (Optional Feature)

**[REQ-O-001]** 사용자가 GPU 가속을 비활성화하면, CPU 전용 모드로 동작해야 한다.

**[REQ-O-002]** 사용자가 메모리 제한을 설정하면, 해당 제한 내에서 동작해야 한다.

### 2.5 복합 요구사항 (Complex)

**[REQ-C-001]** DGX Spark 환경이고 메모리가 64GB 이상 사용 가능할 때, 전체 파일 배치 로딩 모드를 활성화해야 한다.

---

## 3. 데이터 모델

### 3.1 Transcript (녹취 데이터)

```python
class Transcript(BaseModel):
    """녹취 데이터 모델"""
    id: str                      # 고유 식별자
    file_path: Path              # 원본 파일 경로
    date: datetime               # 녹취 날짜
    duration_seconds: float      # 녹취 길이 (초)
    speakers: list[str]          # 화자 목록
    content: str                 # 전체 내용
    segments: list[Segment]      # 세그먼트 목록
    metadata: dict[str, Any]     # 추가 메타데이터
```

### 3.2 Segment (발언 세그먼트)

```python
class Segment(BaseModel):
    """발언 세그먼트 모델"""
    id: str                      # 세그먼트 ID
    speaker: str                 # 화자
    start_time: float            # 시작 시간 (초)
    end_time: float              # 종료 시간 (초)
    content: str                 # 발언 내용
    confidence: float            # 신뢰도 (0.0 ~ 1.0)
```

### 3.3 Speaker (화자)

```python
class Speaker(BaseModel):
    """화자 모델"""
    id: str                      # 화자 ID
    name: str                    # 화자 이름
    aliases: list[str]           # 별칭 목록
    total_duration: float        # 총 발언 시간
    segment_count: int           # 총 발언 횟수
```

### 3.4 Evidence (증거)

```python
class Evidence(BaseModel):
    """증거 모델"""
    id: str                      # 증거 ID
    transcript_id: str           # 원본 녹취 ID
    segment_ids: list[str]       # 관련 세그먼트 ID 목록
    category: str                # 증거 분류
    description: str             # 증거 설명
    importance: Literal["HIGH", "MEDIUM", "LOW"]
    context_before: str          # 전후 맥락 (이전)
    context_after: str           # 전후 맥락 (이후)
```

---

## 4. 설정 관리

### 4.1 설정 파일 구조

```yaml
# config.yaml
forensic:
  version: "0.1.0"
  
  # DGX Spark 최적화
  dgx_spark:
    enabled: true
    auto_detect: true
    gpu_acceleration: true
    memory_limit_gb: 100
    batch_size: 50
    
  # 화자 설정
  speakers:
    - id: "speaker_1"
      name: "신동식"
      aliases: ["동식", "신씨"]
    - id: "speaker_2"
      name: "신기연"
      aliases: ["기연", "신기연씨"]
      
  # 분석 기간
  analysis_period:
    start: "2025-06-01"
    end: "2025-12-31"
```

### 4.2 환경 감지

```python
class DGXSparkDetector:
    """DGX Spark 환경 감지"""
    
    def detect(self) -> DGXSparkInfo:
        """시스템 환경 감지"""
        return DGXSparkInfo(
            is_dgx_spark=self._check_dgx_spark(),
            is_arm64=self._check_arm64(),
            cuda_available=self._check_cuda(),
            memory_gb=self._get_memory_gb(),
            gpu_name=self._get_gpu_name()
        )
```

---

## 5. 기술적 제약사항

### 5.1 ARM64 호환성

- 모든 Python 패키지는 ARM64 호환 필수
- C/C++ 확장이 포함된 패키지는 ARM64 빌드 확인 필요
- 순수 Python 패키지 우선 사용

### 5.2 CUDA 13.0

- PyTorch는 CUDA 13 인덱스에서 설치
- SM_121 (Blackwell) 지원 확인
- TensorRT 옵션 사용 가능

### 5.3 의존성 목록

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "rich>=13.0",
    "python-dateutil>=2.8",
]

[project.optional-dependencies]
gpu = [
    "torch>=2.5",  # CUDA 13 index
    "numpy>=2.0",
]
```

---

## 6. 인터페이스 정의

### 6.1 설정 로더

```python
class ConfigLoader(Protocol):
    def load(self, path: Path) -> Config: ...
    def reload(self) -> Config: ...
    def get(self, key: str, default: Any = None) -> Any: ...
```

### 6.2 모델 팩토리

```python
class TranscriptFactory(Protocol):
    def from_file(self, path: Path) -> Transcript: ...
    def from_dict(self, data: dict) -> Transcript: ...
    def to_dict(self, transcript: Transcript) -> dict: ...
```

---

## 7. 비기능적 요구사항

### 7.1 성능

- 설정 로드 시간: < 100ms
- 모델 직렬화/역직렬화: < 10ms per record
- 메모리 오버헤드: < 1GB for base infrastructure

### 7.2 안정성

- 설정 파일 오류 시 기본값 사용
- ARM64 미호환 패키지 감지 및 경고
- 우아한 CUDA 폴백 (GPU 미사용 시 CPU 모드)

---

Version: 1.0.0
Last Updated: 2026-01-18
