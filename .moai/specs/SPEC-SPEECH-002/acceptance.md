# SPEC-SPEECH-002: 인수 조건

## 1. 기능 테스트 시나리오

### 1.1 ChromaTranscriber 모델 로딩

**시나리오: Chroma-4B 모델 지연 로딩 성공**

```gherkin
Given Chroma-4B 모델 파일이 존재할 때
  | 모델 경로 | /models/chroma-4b |
  | VRAM | 8GB |

When ChromaTranscriber.load_model()를 호출하면

Then 모델이 성공적으로 로드되어야 한다
And GPU 메모리 사용량이 8GB 이하여야 한다
And 캐싱되어 재호출 시 즉시 로드되어야 한다
```

**시나리오: Chroma 모델 로딩 실패 시 폴백**

```gherkin
Given Chroma-4B 모델 파일이 존재하지 않을 때

When TranscriberFactory.create(backend="auto")를 호출하면

Then WhisperAdapter가 반환되어야 한다
And 경고 로그가 출력되어야 한다
And 전사 기능이 정상 동작해야 한다
```

---

### 1.2 1:2 인터리빙 스트리밍 처리

**시나리오: 5초 청크 스트리밍 전사**

```gherkin
Given 5초 길이의 오디오 청크가 있을 때
  | 샘플 레이트 | 24000 Hz |
  | 채널 | 1 (mono) |

When StreamingProcessor.process_chunk()를 호출하면

Then 1:2 인터리빙 패턴으로 처리되어야 한다
  | Text 토큰 | 1개 per step |
  | Audio 토큰 | 2개 per step |
And TTFT가 150ms 미만이어야 한다
And 처리 결과가 Segment로 변환되어야 한다
```

**시나리오: 다중 청크 순차 처리**

```gherkin
Given 3개의 연속 오디오 청크가 있을 때
  | 청크 1 | 0~5초 |
  | 청크 2 | 5~10초 |
  | 청크 3 | 10~15초 |

When 순차적으로 process_chunk()를 호출하면

Then 각 청크가 순서대로 처리되어야 한다
And Segment의 start_time, end_time이 정확해야 한다
And 진행률이 0%, 33%, 66%, 100%로 업데이트되어야 한다
```

---

### 1.3 화자 임베딩 추출

**시나리오: CSM-1B 화자 임베딩 추출**

```gherkin
Given 화자 참조 오디오가 있을 때
  | 파일 | reference_speaker1.wav |
  | 길이 | 5초 |

When SpeakerEncoder.encode()를 호출하면

Then 임베딩 벡터가 반환되어야 한다
And 벡터 차원이 256이어야 한다 (CSM-1B 기준)
And 임베딩이 캐싱되어야 한다
```

**시나리오: 화자 유사도 계산**

```gherkin
Given 두 화자의 임베딩이 있을 때
  | 임베딩 1 | speaker_1 (동일인) |
  | 임베딩 2 | speaker_1 (동일인) |
  | 임베딩 3 | speaker_2 (다른인) |

When SpeakerEncoder.similarity()를 호출하면

Then 동일인 유사도가 0.9 이상이어야 한다
And 다른인 유사도가 0.5 미만이어야 한다
```

---

### 1.4 운율 정보 추출

**시나리오: 운율 특징 추출**

```gherkin
Given 감정이 포함된 오디오 세그먼트가 있을 때
  | 화자 | 신동식 |
  | 감정 | 분노 |
  | 말하기 속도 | 빠름 |

When ChromaTranscriber.transcribe()를 호출하면

Then Segment에 prosody_features가 포함되어야 한다
And prosody_features.emotion이 "분노" 또는 유사 감정이어야 한다
And prosody_features.speaking_rate가 1.0 이상이어야 한다 (빠름)
```

---

### 1.5 통합 인터페이스

**시나리오: TranscriberFactory 자동 백엔드 선택**

```gherkin
Given Chroma-4B 모델이 사용 가능한 상태일 때

When TranscriberFactory.create(backend="auto")를 호출하면

Then ChromaTranscriber가 반환되어야 한다
And transcribe() 메서드가 E2E 방식으로 동작해야 한다
```

**시나리오: TranscriberFactory 폴백**

```gherkin
Given Chroma-4B 모델이 사용 불가능한 상태일 때

When TranscriberFactory.create(backend="auto")를 호출하면

Then WhisperAdapter가 반환되어야 한다
And transcribe() 메서드가 Whisper 방식으로 동작해야 한다
And 결과가 동일한 Transcript 형식이어야 한다
```

**시나리오: 명시적 백엔드 선택**

```gherkin
Given 사용자가 backend="whisper"를 지정할 때

When TranscriberFactory.create(backend="whisper")를 호출하면

Then WhisperAdapter가 반환되어야 한다 (Chroma 가용 여부 무시)
```

---

### 1.6 데이터 모델 확장

**시나리오: E2E 필드 포함 Segment 생성**

```gherkin
Given E2E 전사가 완료된 상태일 때
  | speaker_id | speaker_1 |
  | embedding_id | emb_001 |
  | emotion | 중립 |
  | speaking_rate | 1.0 |

When Segment 모델을 생성하면

Then speaker_embedding_id가 "emb_001"이어야 한다
And prosody_features가 None이 아니어야 한다
And prosody_features.emotion이 "중립"이어야 한다
```

**시나리오: Speaker 임베딩 업데이트**

```gherkin
Given Speaker 모델이 생성되어 있을 때
  | id | speaker_1 |
  | name | 신동식 |

When 새로운 참조 오디오로 임베딩을 업데이트하면

Then embedding 필드가 새 벡터로 업데이트되어야 한다
And embedding_updated가 현재 시간이어야 한다
And reference_audio가 새 경로로 업데이트되어야 한다
```

---

## 2. 비기능 테스트

### 2.1 성능 테스트

**시나리오: RTF (Real-Time Factor) 측정**

```gherkin
Given 1분 길이의 오디오 파일이 있을 때

When ChromaTranscriber.transcribe()를 호출하면

Then 처리 시간이 30초 미만이어야 한다 (RTF < 0.5)
And 결과 Transcript의 모든 Segment가 포함되어야 한다
```

**시나리오: TTFT (Time To First Token) 측정**

```gherkin
Given 오디오 스트리밍이 시작될 때

When 첫 번째 청크가 처리될 때

Then 첫 번째 텍스트 토큰이 150ms 이내에 생성되어야 한다
And TTFT가 로그에 기록되어야 한다
```

**시나리오: GPU 메모리 사용량**

```gherkin
Given 8GB VRAM을 가진 GPU 환경일 때

When ChromaTranscriber.load_model()를 호출하고 전사를 수행하면

Then 최대 GPU 메모리 사용량이 8GB 이하여야 한다
And OOM (Out of Memory) 오류가 발생하지 않아야 한다
```

---

### 2.2 스트리밍 테스트

**시나리오: 청크 크기별 처리**

```gherkin
Given 다양한 크기의 오디오 청크들이 있을 때
  | 1초 청크 | 처리 가능 |
  | 5초 청크 | 처리 가능 |
  | 10초 청크 | 처리 가능 |

When 각 청크를 순차적으로 처리하면

Then 모든 청크가 정상 처리되어야 한다
And Segment의 시간 범위가 정확해야 한다
And 청크 간 경계에서 텍스트가 자연스러워야 한다
```

---

### 2.3 한글 지원 테스트

**시나리오: 한국어 오디오 전사**

```gherkin
Given 한국어 대화 오디오가 있을 때
  | 언어 | 한국어 |
  | 화자 | 2명 |

When ChromaTranscriber.transcribe(language="ko")를 호출하면

Then 전사 텍스트가 한국어로 변환되어야 한다
And WER (Word Error Rate)이 30% 미만이어야 한다
And 화자 분리가 정확해야 한다
```

---

### 2.4 호환성 테스트

**시나리오: 기존 Whisper 데이터와 호환성**

```gherkin
Given 기존 Whisper로 생성된 Transcript가 있을 때
  | e2e_processed | false |
  | speaker_embedding_id | null |

When E2E 모듈로 데이터를 로드하면

Then 데이터가 정상 로드되어야 한다 (ValidationError 없음)
And e2e_processed가 false로 유지되어야 한다
And 기존 기능이 정상 동작해야 한다
```

---

## 3. 품질 게이트

### 3.1 코드 품질

| 항목 | 기준 | 현재 |
|------|------|------|
| 테스트 커버리지 | >= 80% | - |
| Ruff 린트 오류 | 0개 | - |
| Pyright 타입 오류 | 0개 | - |
| 복잡도 | McCabe < 10 | - |

### 3.2 성능 기준

| 지표 | 기준 | 현재 |
|------|------|------|
| RTF | < 0.5 | - |
| TTFT | < 150ms | - |
| GPU VRAM | < 8GB | - |
| 화자 유사도 | > 0.9 (동일인) | - |
| WER (한국어) | < 30% | - |

### 3.3 기능 기준

| 항목 | 기준 | 현재 |
|------|------|------|
| E2E 전사 | 정상 동작 | - |
| 스트리밍 처리 | 1-10초 청크 지원 | - |
| 화자 임베딩 | CSM-1B 추출 가능 | - |
| 운율 정보 | ProsodyFeatures 추출 | - |
| 폴백 | Whisper 자동 전환 | - |
| 호환성 | 기존 데이터 호환 | - |

---

## 4. 완료 체크리스트

### 4.1 필수 항목 (Primary Goal)

- [ ] src/forensic/speech/ 모듈 구조 생성 완료
- [ ] 데이터 모델 확장 (Segment, Speaker)
- [ ] ProsodyFeatures 모델 구현
- [ ] CodecWrapper (Mimi 24kHz) 구현
- [ ] SpeakerEncoder (CSM-1B) 구현
- [ ] StreamingProcessor (1:2 인터리빙) 구현
- [ ] ChromaTranscriber 코어 구현
- [ ] 단위 테스트 80% 이상 커버리지
- [ ] Ruff 린트 통과

### 4.2 선택 항목 (Secondary Goal)

- [ ] WhisperAdapter 폴백 구현
- [ ] TranscriberFactory 통합 인터페이스
- [ ] 한국어 코덱 어댑터
- [ ] 통합 테스트 작성
- [ ] 성능 벤치마크 (RTF, TTFT)
- [ ] 화자 분리 정확도 비교

### 4.3 문서화

- [ ] 모듈 docstring 완료
- [ ] README 업데이트 (E2E 섹션)
- [ ] 설정 예제 (forensic.yaml)
- [ ] 사용 가이드 업데이트

---

## 5. 오류 시나리오

### 5.1 모델 로딩 실패

**시나리오: 모델 파일 손상**

```gherkin
Given 손상된 Chroma-4B 모델 파일이 있을 때

When ChromaTranscriber.load_model()를 호출하면

Then 적절한 예외가 발생해야 한다
And 오류 메시지에 문제 원인이 포함되어야 한다
And TranscriberFactory가 Whisper로 폴백해야 한다
```

---

### 5.2 메모리 부족

**시나리오: GPU 메모리 부족**

```gherkin
Given 4GB VRAM을 가진 GPU 환경일 때

When ChromaTranscriber.load_model()를 호출하면

Then CPU 전용 모드로 자동 전환해야 한다
And 경고 로그가 출력되어야 한다
And transcribe()가 CPU에서 정상 동작해야 한다
```

---

### 5.3 잘못된 입력

**시나리오: 잘못된 오디오 형식**

```gherkin
Given 지원되지 않는 오디오 파일이 있을 때
  | 형식 | video/mp4 |
  | 확장자 | .mp4 |

When ChromaTranscriber.transcribe()를 호출하면

Then ValueError가 발생해야 한다
And 오류 메시지에 지원 형식이 명시되어야 한다
```

---

## 6. 서명

| 역할 | 이름 | 날짜 | 서명 |
|------|------|------|------|
| 작성자 | 지니 | 2026-01-22 | |
| 검토자 | | | |
| 승인자 | | | |

---

Version: 1.0.0
Last Updated: 2026-01-22
