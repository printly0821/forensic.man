# SPEC-SPEECH-002: 구현 계획

## 1. 구현 개요

### 1.1 목표

Chroma-4B 기반 End-to-End 음성 처리 시스템을 forensic.man에 통합하여 화자 분리 정확도와 운율 정보 보존을 향상시킵니다.

### 1.2 예상 산출물

| 파일 | 설명 |
|------|------|
| `src/forensic/speech/__init__.py` | 음성 모듈 공개 API |
| `src/forensic/speech/e2e/chroma_transcriber.py` | Chroma-4B E2E 전사기 |
| `src/forensic/speech/e2e/streaming_processor.py` | 1:2 인터리빙 스트리밍 |
| `src/forensic/speech/e2e/speaker_encoder.py` | CSM-1B 화자 인코더 |
| `src/forensic/speech/e2e/codec_wrapper.py` | Mimi 코덱 래퍼 |
| `src/forensic/speech/adapters/whisper_adapter.py` | faster-whisper 폴백 |
| `src/forensic/speech/unified/transcriber_factory.py` | 통합 전사기 팩토리 |
| `src/forensic/models/transcript.py` | Segment, Speaker 모델 확장 |
| `tests/unit/test_speech_e2e_*.py` | E2E 모듈 단위 테스트 |

---

## 2. 태스크 분해

### Phase 1: 모듈 구조 및 데이터 모델 확장 (Primary Goal)

```
[TASK-1.1] speech 모듈 구조 생성
├── src/forensic/speech/ 디렉토리 생성
├── e2e/, adapters/, unified/ 하위 디렉토리 생성
└── __init__.py 파일 생성

[TASK-1.2] 데이터 모델 확장
├── Segment 모델에 E2E 필드 추가
│   ├── speaker_embedding_id: str | None
│   ├── prosody_features: ProsodyFeatures | None
│   └── audio_token_count: int | None
├── Speaker 모델에 임베딩 필드 추가
│   ├── embedding: np.ndarray | None
│   ├── reference_audio: Path | None
│   └── embedding_updated: datetime | None
└── ProsodyFeatures 모델 생성
    ├── emotion: str
    ├── tone: str
    ├── speaking_rate: float
    └── timbre_features: np.ndarray
```

### Phase 2: 코덱 래퍼 및 화자 인코더 (Primary Goal)

```
[TASK-2.1] Mimi 코덱 래퍼
├── 24kHz 8 codebooks 코덱 로딩
├── 오디오 인코딩/디코딩
├── 배치 처리 지원
└── 단위 테스트

[TASK-2.2] CSM-1B 화자 인코더
├── 참조 오디오에서 임베딩 추출
├── 코사인 유사도 계산
├── 임베딩 캐싱
└── 단위 테스트
```

### Phase 3: 스트리밍 프로세서 (Primary Goal)

```
[TASK-3.1] 1:2 인터리빙 스트리밍
├── 토큰 스케줄러 구현
│   ├── 1 Text 토큰 + 2 Audio 토큰 패턴
│   └── 청크 단위 처리 (1-10초)
├── TTFT 측정 (< 150ms 목표)
├── 진행률 추적
└── 단위 테스트

[TASK-3.2] ChromaTranscriber 코어
├── Chroma-4B 모델 로딩 (Lazy + Cache)
├── GPU/CPU 자동 전환
├── 배치 크기 최적화
└── 단위 테스트
```

### Phase 4: 통합 인터페이스 (Secondary Goal)

```
[TASK-4.1] WhisperAdapter 폴백
├── faster-whisper 기반 전사
├── 통합 TranscriberBackend 인터페이스 구현
└── 단위 테스트

[TASK-4.2] TranscriberFactory
├── 자동 백엔드 선택
├── Chroma 가용성 감지
├── 폴백 로직
└── 단위 테스트
```

### Phase 5: 통합 및 검증 (Secondary Goal)

```
[TASK-5.1] 통합 테스트
├── 전체 E2E 파이프라인 테스트
├── 스트리밍 처리 테스트
├── 폴백 동작 테스트
└── 한국어 오디오 테스트

[TASK-5.2] 성능 검증
├── RTF < 0.5 측정
├── TTFT < 150ms 측정
├── GPU 메모리 < 8GB 검증
└── 화자 분리 정확도 비교
```

---

## 3. 기술 스택

### 3.1 런타임 의존성

| 패키지 | 버전 | 용도 | ARM64 호환 |
|--------|------|------|:----------:|
| transformers | >=4.40 | Hugging Face 모델 | Yes |
| torch | >=2.5 | 텐서 연산, CUDA 13 | Yes |
| torchaudio | >=2.5 | 오디오 처리 | Yes |
| accelerate | >=0.30 | 모델 가속 | Yes |

### 3.2 기존 의존성 (재사용)

| 패키지 | 용도 |
|--------|------|
| pydantic | 데이터 모델 (이미 SPEC-CORE-001에서 사용) |
| numpy | 배열 연산 (이미 사용) |
| faster-whisper | 폴백 전사기 (이미 SPEC-SPEECH-001에서 사용) |

### 3.3 선택적 의존성 (GPU)

```toml
[project.optional-dependencies]
e2e = [
    "transformers>=4.40",
    "torch>=2.5",
    "torchaudio>=2.5",
    "accelerate>=0.30",
]
```

---

## 4. 아키텍처 설계

### 4.1 계층 구조

```
┌─────────────────────────────────────────────┐
│          CLI / Analysis Layer               │
│  (calls TranscriberFactory.create())        │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│        Unified Interface Layer              │
│  TranscriberFactory (Auto Fallback)         │
│  ├── ChromaTranscriber (Primary)            │
│  └── WhisperAdapter (Fallback)              │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│          E2E Processing Layer               │
│  ├── StreamingProcessor (1:2 Interleaved)   │
│  ├── SpeakerEncoder (CSM-1B)                │
│  └── CodecWrapper (Mimi 24kHz)              │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│            Model Layer                      │
│  ├── Chroma-4B (Reasoner + Decoder)         │
│  ├── CSM-1B (Speaker Encoder)               │
│  └── Mimi (Codec)                           │
└─────────────────────────────────────────────┘
```

### 4.2 데이터 흐름

```
Audio File
    │
    ▼
[CodecWrapper] ──► Encoded Audio (24kHz, 8 codebooks)
    │
    ▼
[StreamingProcessor] ──► 1:2 Interleaved Tokens
    │                           │
    ▼                           ▼
[ChromaTranscriber]      [SpeakerEncoder]
    │                           │
    └───────────┬───────────────┘
                ▼
        [Transcript Model]
        ├── Segment (with prosody)
        ├── Speaker (with embedding)
        └── Metadata
```

---

## 5. 리스크 분석

### 5.1 기술적 리스크

| 리스크 | 영향 | 확률 | 완화 전략 |
|--------|------|------|-----------|
| Chroma-4B 모델 공개 지연 | 높음 | 중간 | Mock으로 먼저 인터페이스 구현 |
| 한국어 성능 저하 | 높음 | 중간 | 커스텀 코덱 어댑터 준비 |
| GPU 메모리 초과 | 중간 | 낮음 | 동적 배치 조절, CPU 폴백 |
| ARM64 호환성 문제 | 중간 | 낮음 | Docker 컨테이너 테스트 |

### 5.2 완화 전략

1. **모델 가용성**: Mock 구현으로 인터페이스 먼저 정의, 실제 모델은 통합 단계에서 연결
2. **한국어 지원**: 멀티언어 버전 활용, 필요시 파인튜닝 계획
3. **메모리 관리**: VRAM 모니터링, 배치 크기 동적 조절
4. **폴백 구현**: Chroma 사용 불가 시 faster-whisper 자동 전환

---

## 6. 검증 기준

### 6.1 단위 테스트

- 모든 E2E 모듈 80% 이상 커버리지
- Mock 기반 모델 테스트 (외부 의존성 제거)
- 스트리밍 처리 시뮬레이션 테스트

### 6.2 통합 테스트

- 전체 E2E 파이프라인 정상 동작
- 폴백 로직 검증
- 한국어 오디오 샘플 테스트

### 6.3 성능 기준

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| RTF | < 0.5 | 처리 시간 / 오디오 길이 |
| TTFT | < 150ms | 첫 토큰 생성 시간 |
| GPU VRAM | < 8GB | nvidia-smi 또는 torch.cuda.memory_allocated() |

---

## 7. 일정

| 단계 | 우선순위 | 산출물 |
|------|----------|--------|
| Phase 1 | Primary | 모듈 구조, 데이터 모델 확장 |
| Phase 2 | Primary | 코덱 래퍼, 화자 인코더 |
| Phase 3 | Primary | 스트리밍 프로세서, ChromaTranscriber |
| Phase 4 | Secondary | 통합 인터페이스, 폴백 |
| Phase 5 | Secondary | 통합 테스트, 성능 검증 |

---

## 8. 의존성

### 8.1 선행 조건

- **SPEC-CORE-001 완료**: 데이터 모델 (Transcript, Segment, Speaker)
- **SPEC-IO-001 완료**: 대용량 파일 스트리밍 처리
- Python 3.12+ 환경
- GPU 환경 (선택, CUDA 13)

### 8.2 후속 SPEC

- **SPEC-TIMELINE-001**: E2E 전사 결과 사용
- **SPEC-EVIDENCE-001**: 운율 정보 기반 증거 추출
- **SPEC-ANALYSIS-001**: 화자 임베딩 기반 패턴 분석

---

## 9. 마이그레이션 경로

### 9.1 기존 데이터 호환성

```python
# 기존 Whisper 기반 데이터와 호환
class Transcript(BaseModel):
    # 기존 필드 (호환성 유지)
    segments: list[Segment]

    # E2E 확장 필드 (선택적)
    e2e_model_version: str | None = None
    e2e_processed: bool = False
```

### 9.2 설정 추가

```yaml
# forensic.yaml
forensic:
  speech:
    backend: "auto"  # auto, chroma, whisper
    chroma:
      model_path: "/models/chroma-4b"
      batch_size: 1
      use_gpu: true
      ttft_target_ms: 150
    whisper:
      model_size: "large-v3"
      device: "auto"
```

---

Version: 1.0.0
Last Updated: 2026-01-22
