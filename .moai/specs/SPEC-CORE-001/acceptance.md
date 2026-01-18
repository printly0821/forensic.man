# SPEC-CORE-001: 인수 조건

## 1. 기능 테스트 시나리오

### 1.1 Transcript 모델 생성

**시나리오: 유효한 녹취 데이터로 Transcript 모델 생성**

```gherkin
Given 유효한 녹취 파일 정보가 있을 때
  | 필드 | 값 |
  | file_path | /data/recordings/2025-06-15.txt |
  | date | 2025-06-15T14:30:00 |
  | duration_seconds | 1800 |
  | speakers | ["신동식", "신기연"] |

When Transcript 모델을 생성하면

Then 모델이 성공적으로 생성되어야 한다
And id가 자동으로 생성되어야 한다
And speakers 목록에 2명이 포함되어야 한다
And duration_seconds가 1800이어야 한다
```

**시나리오: 잘못된 데이터로 Transcript 모델 생성 실패**

```gherkin
Given 잘못된 녹취 파일 정보가 있을 때
  | 필드 | 값 |
  | date | "invalid-date" |
  | duration_seconds | -100 |

When Transcript 모델을 생성하면

Then ValidationError가 발생해야 한다
And 오류 메시지에 잘못된 필드 정보가 포함되어야 한다
```

---

### 1.2 설정 로드

**시나리오: YAML 설정 파일 로드 성공**

```gherkin
Given 유효한 config.yaml 파일이 존재할 때
  """yaml
  forensic:
    version: "0.1.0"
    dgx_spark:
      enabled: true
      memory_limit_gb: 100
  """

When ConfigLoader.load()를 호출하면

Then Config 객체가 반환되어야 한다
And config.dgx_spark.enabled가 True이어야 한다
And config.dgx_spark.memory_limit_gb가 100이어야 한다
```

**시나리오: 설정 파일 없을 때 기본값 사용**

```gherkin
Given config.yaml 파일이 존재하지 않을 때

When ConfigLoader.load()를 호출하면

Then 기본 Config 객체가 반환되어야 한다
And config.dgx_spark.enabled가 True (기본값)이어야 한다
And 경고 로그가 출력되어야 한다
```

---

### 1.3 DGX Spark 환경 감지

**시나리오: DGX Spark 환경 감지 성공**

```gherkin
Given DGX Spark 시스템에서 실행 중일 때

When DGXSparkDetector.detect()를 호출하면

Then DGXSparkInfo 객체가 반환되어야 한다
And is_dgx_spark가 True이어야 한다
And is_arm64가 True이어야 한다
And memory_gb가 128 이상이어야 한다
```

**시나리오: 일반 시스템에서 감지**

```gherkin
Given 일반 x86_64 시스템에서 실행 중일 때

When DGXSparkDetector.detect()를 호출하면

Then DGXSparkInfo 객체가 반환되어야 한다
And is_dgx_spark가 False이어야 한다
And is_arm64가 False이어야 한다
```

---

### 1.4 Speaker 모델

**시나리오: 화자 별칭 매칭**

```gherkin
Given Speaker 모델이 생성되어 있을 때
  | 필드 | 값 |
  | name | 신동식 |
  | aliases | ["동식", "신씨"] |

When "동식"으로 화자를 검색하면

Then 해당 Speaker 모델이 반환되어야 한다
And name이 "신동식"이어야 한다
```

---

### 1.5 Evidence 모델

**시나리오: 증거 생성 및 맥락 포함**

```gherkin
Given Transcript와 관련 Segment가 있을 때

When Evidence 모델을 생성하면

Then context_before에 이전 발언이 포함되어야 한다
And context_after에 이후 발언이 포함되어야 한다
And importance가 유효한 레벨이어야 한다
```

---

## 2. 비기능 테스트

### 2.1 성능 테스트

**시나리오: 설정 로드 성능**

```gherkin
Given 표준 크기의 config.yaml 파일이 있을 때

When ConfigLoader.load()를 100번 반복 실행하면

Then 평균 로드 시간이 100ms 미만이어야 한다
And 최대 로드 시간이 200ms 미만이어야 한다
```

**시나리오: 모델 직렬화 성능**

```gherkin
Given 1000개의 Transcript 모델이 있을 때

When 전체를 JSON으로 직렬화하면

Then 소요 시간이 10초 미만이어야 한다
And 메모리 사용량 증가가 500MB 미만이어야 한다
```

---

### 2.2 ARM64 호환성 테스트

**시나리오: ARM64 환경 패키지 호환성**

```gherkin
Given ARM64 (aarch64) 환경에서 실행 중일 때

When 모든 의존성 패키지를 import하면

Then ImportError가 발생하지 않아야 한다
And 모든 기능이 정상 동작해야 한다
```

---

### 2.3 메모리 안정성 테스트

**시나리오: 대용량 데이터 처리 시 메모리 안정성**

```gherkin
Given 1000개의 Transcript 모델 (각 10MB)이 있을 때

When 순차적으로 로드하고 처리하면

Then 메모리 사용량이 설정된 limit_gb를 초과하지 않아야 한다
And OOM (Out of Memory) 오류가 발생하지 않아야 한다
```

---

## 3. 품질 게이트

### 3.1 코드 품질

| 항목 | 기준 | 현재 |
|------|------|------|
| 테스트 커버리지 | >= 80% | - |
| Ruff 린트 오류 | 0개 | - |
| Pyright 타입 오류 | 0개 | - |

### 3.2 문서화

| 항목 | 기준 | 현재 |
|------|------|------|
| 공개 함수 docstring | 100% | - |
| 모듈 docstring | 100% | - |
| README 업데이트 | 완료 | - |

### 3.3 호환성

| 항목 | 기준 | 현재 |
|------|------|------|
| Python 3.12 호환 | 통과 | - |
| ARM64 호환 | 통과 | - |
| x86_64 호환 | 통과 | - |

---

## 4. 완료 체크리스트

### 4.1 필수 항목

- [ ] 모든 데이터 모델 구현 완료 (Transcript, Segment, Speaker, Evidence)
- [ ] 설정 관리 시스템 구현 완료
- [ ] DGX Spark 환경 감지 구현 완료
- [ ] 단위 테스트 80% 이상 커버리지
- [ ] pyproject.toml 설정 완료
- [ ] 패키지 구조 생성 완료

### 4.2 선택 항목

- [ ] GPU 가속 인터페이스 정의
- [ ] Docker 컨테이너 설정
- [ ] CI/CD 파이프라인 구성

---

## 5. 서명

| 역할 | 이름 | 날짜 | 서명 |
|------|------|------|------|
| 작성자 | 지니 | 2026-01-18 | |
| 검토자 | | | |
| 승인자 | | | |

---

Version: 1.0.0
Last Updated: 2026-01-18
