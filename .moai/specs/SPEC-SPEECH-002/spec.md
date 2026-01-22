---
id: SPEC-SPEECH-002
version: "1.0.0"
status: "draft"
created: "2026-01-22"
updated: "2026-01-22"
author: "지니"
priority: "HIGH"
tags: ["speech", "e2e", "chroma", "streaming", "speaker-diarization"]
---

# SPEC-SPEECH-002: Chroma End-to-End 음성 처리 통합

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-01-22 | 지니 | 초기 작성 - Chroma-4B E2E 음성 처리 |

---

## 1. 개요

### 1.1 목적

Chroma-4B 기반 End-to-End 음성 처리 시스템을 forensic.man에 통합합니다. 기존 faster-whisper 파이프라인을 보완하며, 화자 임베딩 보존, 운율 정보 유지, 스트리밍 처리를 통해 법의학 음성 분석의 정확도를 향상시킵니다.

### 1.2 배경

현재 forensic.man은 faster-whisper를 사용한 ASR와 pyannote-audio를 사용한 화자 분리를 별도로 수행합니다. Chroma-4B는 이를 단일 End-to-End 모델로 통합하여:

- 화자 간 유사성을 인간 기준 이상으로 보존
- 운율 정보(paralinguistic cues)를 유지
- 1:2 인터리빙 토큰 스케줄로 실시간 스트리밍 지원
- RTF < 0.5 (실시간 2배속) 달성

### 1.3 범위

- Chroma-4B 기반 E2E 전사 모델 통합
- 1:2 인터리빙 토큰 스케줄 스트리밍 처리
- CSM-1B 기반 화자 임베딩 보존
- Mimi 코덱 (24kHz, 8 codebooks) 래퍼
- 기존 faster-whisper 파이프라인과 호환성 유지
- 한국어 지원 (커스텀 코덱 어댑터)

### 1.4 의존 SPEC

- **SPEC-SPEECH-001**: 기존 음성 분석 프레임워크 (faster-whisper, pyannote-audio)
- **SPEC-CORE-001**: 데이터 모델 (Transcript, Segment, Speaker) 및 DGX Spark 최적화
- **SPEC-IO-001**: 대용량 파일 스트리밍 처리

### 1.5 대상 시스템

| 항목 | 사양 |
|------|------|
| 플랫폼 | NVIDIA DGX Spark (선택) |
| GPU | CUDA 13 호환, < 8GB VRAM |
| RTF 목표 | < 0.5 (2x faster than real-time) |
| TTFT 목표 | < 150ms |
| 샘플 레이트 | 24kHz |

---

## 2. 요구사항 (EARS 형식)

### 2.1 유비쿼터스 요구사항 (Ubiquitous)

**[REQ-U-001]** 시스템은 항상 Chroma-4B 모델을 통해 오디오를 텍스트로 변환해야 한다.

**[REQ-U-002]** 시스템은 항상 화자 임베딩을 보존하여 화자 분리 정확도를 유지해야 한다.

**[REQ-U-003]** 시스템은 항상 운율 정보(prosody features)를 추출해야 한다.

**[REQ-U-004]** 모든 모델 로딩은 지연 로딩(Lazy Loading)과 캐싱을 사용해야 한다.

### 2.2 이벤트 기반 요구사항 (Event-Driven)

**[REQ-E-001]** 오디오 청크가 수신될 때, 시스템은 1:2 인터리빙 토큰 스케줄로 처리해야 한다.

**[REQ-E-002]** 화자 참조 오디오가 제공될 때, 시스템은 CSM-1B로 화자 임베딩을 추출해야 한다.

**[REQ-E-003]** 전사 완료 시, 시스템은 Transcript, Segment 모델로 결과를 변환해야 한다.

**[REQ-E-004]** Chroma 모델 로딩 실패 시, 시스템은 faster-whisper로 자동 폴백해야 한다.

### 2.3 상태 기반 요구사항 (State-Driven)

**[REQ-S-001]** GPU가 사용 가능한 상태일 때, 시스템은 GPU 가속을 활성화해야 한다.

**[REQ-S-002]** 메모리가 6GB 미만인 상태일 때, 시스템은 CPU 전용 모드로 전환해야 한다.

**[REQ-S-003]** DGX Spark 환경일 때, 시스템은 배치 크기를 최적화해야 한다.

### 2.4 선택적 요구사항 (Optional Feature)

**[REQ-O-001]** 사용자가 faster-whisper 백엔드를 선택하면, 기존 파이프라인을 사용해야 한다.

**[REQ-O-002]** 사용자가 진행률 콜백을 제공하면, 각 청크 처리 시 콜백을 호출해야 한다.

### 2.5 복합 요구사항 (Complex)

**[REQ-C-001]** DGX Spark 환경이고 GPU가 사용 가능할 때, 시스템은 배치 처리를 통해 RTF < 0.5를 달성해야 한다.

**[REQ-C-002]** 다중 화자 대화일 때, 시스템은 CSM-1B 임베딩을 통해 화자 일관성을 유지해야 한다.

---

## 3. 상세 요구사항

### 3.1 REQ-E2E-001: Chroma-4B End-to-End 전사

Chroma-4B 아키텍처 구성:

| 컴포넌트 | 설명 | 파라미터 수 |
|----------|------|------------|
| Reasoner | Qwen2-Audio 멀티모달 이해 | 3.9B |
| Backbone/Decoder | 경량 RVQ 디코더 | 100M |
| Codec | Mimi (24kHz, 8 codebooks) | - |

성능 목표:
- RTF (Real-Time Factor): < 0.5
- TTFT (Time To First Token): < 150ms
- GPU 메모리: < 8GB

### 3.2 REQ-E2E-002: 1:2 인터리빙 스트리밍

토큰 스케줄:
- 1 Text 토큰 + 2 Audio 토큰 per step
- 청크 단위 처리 (1-10초)
- TTFT < 150ms 보장

스트리밍 처리 로직:
```python
for text_token, audio_tokens in interleaved_schedule:
    process(text_token)
    process(audio_tokens[0])
    process(audio_tokens[1])
```

### 3.3 REQ-E2E-003: 화자 임베딩 보존

CSM-1B (Conditional Speech Modeling) 기반 화자 인코딩:

| 기능 | 설명 |
|------|------|
| Reference Encoding | 참조 오디오에서 화자 임베딩 추출 |
| Similarity > Human | 화자 유사성 인간 기준 초과 |
| Multi-turn Consistency | 다중 대화 화자 일관성 유지 |

화자 임베딩 저장:
```python
class SpeakerEmbedding(BaseModel):
    speaker_id: str
    embedding: np.ndarray  # CSM-1B embedding vector
    reference_audio: Path  # Reference audio path
    confidence: float
```

### 3.4 REQ-E2E-004: 운율 정보 보존

보존할 운율 특징:
- 감정(Emotion)과 톤(Tone)
- 말하기 속도(Speaking Rate)
- 음색(Timbre)

오디오 임베딩에서 추출:
```python
class ProsodyFeatures(BaseModel):
    emotion: str
    tone: str
    speaking_rate: float
    timbre_features: np.ndarray
    confidence: float
```

### 3.5 REQ-E2E-005: 기존 파이프라인 호환성

통합 인터페이스:
```python
class TranscriberBackend(Protocol):
    def transcribe(
        self,
        audio: Path | np.ndarray,
        language: str = "ko"
    ) -> Transcript:
        ...

class ChromaTranscriber:
    """Chroma-4B based E2E transcriber"""
    ...

class WhisperTranscriber:
    """faster-whisper fallback"""
    ...

class TranscriberFactory:
    """Unified transcriber interface"""
    def create(self, backend: str) -> TranscriberBackend:
        ...
```

---

## 4. 모듈 구조

```
src/forensic/speech/
├── __init__.py
├── e2e/
│   ├── __init__.py
│   ├── chroma_transcriber.py   # Chroma-4B E2E 전사기
│   ├── streaming_processor.py  # 1:2 인터리빙 스트리밍
│   ├── speaker_encoder.py      # CSM-1B 화자 인코더
│   └── codec_wrapper.py        # Mimi 코덱 래퍼
├── adapters/
│   ├── __init__.py
│   └── whisper_adapter.py      # faster-whisper 폴백
└── unified/
    ├── __init__.py
    └── transcriber_factory.py  # 통합 전사기 팩토리
```

---

## 5. 기술적 제약사항

### 5.1 의존성

```toml
[project]
dependencies = [
    "transformers>=4.40",   # Hugging Face transformers
    "torch>=2.5",           # PyTorch with CUDA 13
    "torchaudio>=2.5",      # Audio processing
]

[project.optional-dependencies]
e2e = [
    "transformers>=4.40",
    "torch>=2.5",
    "torchaudio>=2.5",
    "accelerate>=0.30",     # Model acceleration
]
```

### 5.2 GPU 메모리 관리

| 상황 | 조치 |
|------|------|
| VRAM < 4GB | CPU 전용 모드 |
| 4GB <= VRAM < 8GB | 배치 크기 1 |
| VRAM >= 8GB | 배치 크기 최적화 |

### 5.3 한국어 지원

옵션 1: 커스텀 코덱 어댑터
- 한국어 특화 Mimi 코덱 파인튜닝

옵션 2: 멀티언어 모델 사용
- Chroma-4B 멀티언어 버전 활용

---

## 6. 비기능적 요구사항

### 6.1 성능

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| RTF | < 0.5 | 처리 시간 / 오디오 길이 |
| TTFT | < 150ms | 첫 토큰 생성 시간 |
| 메모리 | < 8GB | GPU VRAM 사용량 |

### 6.2 안정성

- 모델 로딩 실패 시 우아한 폴백
- OOM 방지를 위한 동적 배치 조절
- 진행 상황 저장 및 재개 지원

### 6.3 품질

- 화자 분리 정확도 > pyannote-audio 기준
- 전사 WER (Word Error Rate) < faster-whisper 기준
- 운율 특징 보존률 > 90%

---

## 7. 인터페이스 정의

### 7.1 ChromaTranscriber

```python
class ChromaTranscriber(Protocol):
    """Chroma-4B based end-to-end transcriber"""

    def load_model(self) -> None:
        """Lazy load Chroma-4B model with caching"""
        ...

    def transcribe(
        self,
        audio: Path | np.ndarray,
        language: str = "ko",
        speaker_references: dict[str, Path] | None = None
    ) -> Transcript:
        """Transcribe audio with speaker diarization"""
        ...

    def transcribe_streaming(
        self,
        audio_chunks: Iterator[bytes],
        chunk_duration_sec: float = 5.0
    ) -> Iterator[Segment]:
        """Stream transcribe with 1:2 interleaved tokens"""
        ...

    def get_speaker_embedding(self, audio: Path) -> np.ndarray:
        """Extract CSM-1B speaker embedding"""
        ...
```

### 7.2 StreamingProcessor

```python
class StreamingProcessor(Protocol):
    """1:2 interleaved token streaming processor"""

    def process_chunk(
        self,
        audio_chunk: np.ndarray
    ) -> tuple[str, list[float]]:
        """Process chunk with 1:2 interleaved schedule
        Returns (text_token, audio_tokens)"""
        ...

    def get_ttft(self) -> float:
        """Get Time To First Token in milliseconds"""
        ...
```

### 7.3 SpeakerEncoder

```python
class SpeakerEncoder(Protocol):
    """CSM-1B based speaker encoder"""

    def encode(self, audio: Path | np.ndarray) -> np.ndarray:
        """Encode speaker embedding from reference audio"""
        ...

    def similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """Calculate cosine similarity between embeddings"""
        ...
```

### 7.4 TranscriberFactory

```python
class TranscriberFactory:
    """Unified transcriber factory with fallback"""

    def __init__(self, config: ForensicConfig):
        self.config = config
        self._chroma: ChromaTranscriber | None = None
        self._whisper: WhisperTranscriber | None = None

    def create(self, backend: str = "auto") -> TranscriberBackend:
        """Create transcriber with automatic fallback

        Args:
            backend: "chroma", "whisper", or "auto"

        Returns:
            TranscriberBackend instance

        Raises:
            RuntimeError: If no backend available
        """
        if backend == "auto":
            if self._is_chroma_available():
                return self._create_chroma()
            return self._create_whisper()
        ...
```

---

## 8. 데이터 모델 확장

### 8.1 Segment 확장

```python
class Segment(BaseModel):
    """Extended segment with E2E features"""
    id: str
    speaker: str
    start_time: float
    end_time: float
    content: str
    confidence: float

    # E2E specific fields
    speaker_embedding_id: str | None = None  # CSM-1B embedding reference
    prosody_features: ProsodyFeatures | None = None
    audio_token_count: int | None = None     # For streaming stats
```

### 8.2 Speaker 확장

```python
class Speaker(BaseModel):
    """Extended speaker with embedding"""
    id: str
    name: str
    aliases: list[str]
    total_duration: float
    segment_count: int

    # E2E specific fields
    embedding: np.ndarray | None = None      # CSM-1B embedding
    reference_audio: Path | None = None      # Reference audio path
    embedding_updated: datetime | None = None
```

---

Version: 1.0.0
Last Updated: 2026-01-22
