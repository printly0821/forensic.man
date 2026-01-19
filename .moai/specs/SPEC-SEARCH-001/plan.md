# SPEC-SEARCH-001 구현 계획

## 태그 추적

- **SPEC ID**: SPEC-SEARCH-001
- **관련 SPEC**: SPEC-CORE-001, SPEC-IO-001, SPEC-TIMELINE-001, SPEC-EVIDENCE-001
- **상태**: 계획 단계

---

## 1. 구현 마일스톤

### Primary Goal: 핵심 검색 엔진 구축

**목표**: 기본 키워드 검색과 인덱스 시스템 구현

**포함 작업**:
- [ ] 검색 인덱스 데이터 구조 설계
- [ ] IndexBuilder 구현 (Transcript, Segment, Evidence 인덱싱)
- [ ] 기본 KeywordSearcher 구현 (정확 일치, 부분 일치)
- [ ] SearchResult, SearchHit 모델 구현
- [ ] 검색 API 기본 인터페이스 구현

**의존성**: SPEC-CORE-001 (데이터 모델), SPEC-IO-001 (파일 읽기)

**검증 기준**:
- 183개 파일에서 30초 이내 인덱스 구축
- 10,000 세그먼트 기준 500ms 이내 검색 응답
- 테스트 커버리지 85% 이상

---

### Secondary Goal: 한국어 형태소 분석 통합

**목표**: 한국어 특화 검색 기능 구현

**포함 작업**:
- [ ] MorphemeAnalyzer 인터페이스 설계
- [ ] MeCab 기반 형태소 분석기 구현
- [ ] ARM64 호환 폴백 구현 (순수 Python)
- [ ] MorphemeToken 모델 구현
- [ ] 형태소 기반 검색 인덱스 확장

**의존성**: Primary Goal 완료

**검증 기준**:
- 한국어 형태소 분석 정확도 95% 이상
- 처리량 10,000 tokens/second 이상
- ARM64 환경에서 정상 동작

---

### Tertiary Goal: 필터링 및 고급 검색

**목표**: 복합 조건 검색 및 필터 시스템 구현

**포함 작업**:
- [ ] FilterEngine 구현 (날짜, 화자, 중요도, 패턴 유형)
- [ ] QueryBuilder 구현 (AND, OR, NOT 연산)
- [ ] 근접 검색 (Proximity Search) 구현
- [ ] 와일드카드 검색 구현
- [ ] 정규표현식 검색 구현
- [ ] 쿼리 파서 및 검증기 구현

**의존성**: Secondary Goal 완료

**검증 기준**:
- 복합 조건 쿼리 정확한 처리
- 모든 필터 조합 테스트 통과
- 유효하지 않은 쿼리 적절한 오류 처리

---

### Final Goal: 결과 처리 및 CLI 통합

**목표**: 검색 결과 포맷팅 및 CLI 명령 통합

**포함 작업**:
- [ ] ResultFormatter 구현 (하이라이트, 맥락 미리보기)
- [ ] 페이지네이션 구현
- [ ] 정렬 기능 구현 (관련도, 날짜, 중요도)
- [ ] 검색 결과 내보내기 (JSON, CSV, Markdown)
- [ ] CLI search 명령 구현
- [ ] 검색 기록 저장/로드 기능

**의존성**: Tertiary Goal 완료

**검증 기준**:
- 모든 정렬 옵션 정상 동작
- 페이지네이션 정확한 분할
- CLI 명령 통합 테스트 통과

---

### Optional Goal: 성능 최적화

**목표**: 대용량 데이터 처리 최적화

**포함 작업**:
- [ ] 스트리밍 검색 구현 (대용량 파일)
- [ ] 인덱스 캐싱 전략 구현
- [ ] 메모리 사용량 최적화
- [ ] 병렬 검색 구현 (멀티코어 활용)
- [ ] GPU 가속 검색 (선택, CUDA 활용)

**의존성**: Final Goal 완료

**검증 기준**:
- 100MB 이상 파일 스트리밍 검색 지원
- 메모리 사용량 2GB 이하 유지
- 병렬 처리 시 2배 이상 성능 향상

---

## 2. 기술적 접근

### 2.1 검색 인덱스 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Search Engine                         │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Inverted   │  │  Forward    │  │  Position   │     │
│  │  Index      │  │  Index      │  │  Index      │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│         │               │               │               │
│  Token → Doc IDs  Doc ID → Tokens  Token → Positions   │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │              Morpheme Analyzer                   │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │   │
│  │  │  MeCab  │  │ Komoran │  │ Fallback│         │   │
│  │  └─────────┘  └─────────┘  └─────────┘         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 검색 흐름

```
Query → Parser → Tokenizer → Morpheme Analyzer
                      │
                      ▼
               Index Lookup
                      │
                      ▼
               Filter Engine
                      │
                      ▼
               Result Scorer
                      │
                      ▼
               Result Formatter → Output
```

### 2.3 인덱스 데이터 구조

```python
# 역색인 (Inverted Index)
{
    "토큰": {
        "doc_ids": ["seg_001", "seg_005", "seg_012"],
        "term_freq": {"seg_001": 3, "seg_005": 1, "seg_012": 2},
        "doc_freq": 3
    }
}

# 순방향 인덱스 (Forward Index)
{
    "seg_001": {
        "tokens": ["토큰1", "토큰2", "토큰3"],
        "speaker": "신동식",
        "timestamp": "2025-07-15T10:30:00",
        "transcript_id": "trans_001"
    }
}

# 위치 인덱스 (Position Index)
{
    "토큰": {
        "seg_001": [0, 15, 42],  # 문서 내 위치
        "seg_005": [8]
    }
}
```

### 2.4 관련도 점수 계산

```python
# TF-IDF 기반 점수 계산
def calculate_score(term: str, doc_id: str, index: Index) -> float:
    tf = index.term_freq(term, doc_id)
    df = index.doc_freq(term)
    n = index.total_docs

    # TF-IDF 계산
    tf_score = 1 + math.log(tf) if tf > 0 else 0
    idf_score = math.log(n / (df + 1))

    return tf_score * idf_score
```

---

## 3. 의존성 관리

### 3.1 내부 의존성

| 의존 SPEC | 사용 컴포넌트 | 용도 |
|-----------|---------------|------|
| SPEC-CORE-001 | Transcript, Segment, Speaker, Evidence | 검색 대상 데이터 모델 |
| SPEC-IO-001 | StreamReader, ChunkProcessor | 대용량 파일 스트리밍 읽기 |
| SPEC-TIMELINE-001 | PatternDetector | 패턴 기반 필터링 |
| SPEC-EVIDENCE-001 | Evidence, EvidenceCategory | 증거 검색 및 필터링 |

### 3.2 외부 의존성

| 패키지 | 버전 | 용도 | ARM64 호환 |
|--------|------|------|------------|
| mecab-python3 | >=1.0 | 한국어 형태소 분석 | 소스 컴파일 필요 |
| konlpy | >=0.6 | 한국어 NLP (대안) | 확인 필요 |
| pydantic | >=2.0 | 데이터 모델 | O |

### 3.3 대안 전략

형태소 분석기 ARM64 호환 문제 발생 시:
1. 순수 Python 기반 간단한 토크나이저 구현
2. 음절 단위 n-gram 검색으로 대체
3. 서버 기반 형태소 분석 API 활용 (선택)

---

## 4. 아키텍처 설계

### 4.1 모듈 구조

```
forensic.search
├── engine           # 검색 엔진 코어
│   ├── SearchEngine
│   ├── IndexBuilder
│   └── IndexStore
├── keyword          # 키워드 검색
│   ├── KeywordSearcher
│   ├── Tokenizer
│   ├── MorphemeAnalyzer
│   └── FuzzyMatcher
├── filter           # 필터 엔진
│   ├── FilterEngine
│   ├── DateFilter
│   ├── SpeakerFilter
│   └── PatternFilter
├── query            # 쿼리 처리
│   ├── QueryBuilder
│   ├── QueryParser
│   └── QueryOptimizer
├── result           # 결과 처리
│   ├── ResultFormatter
│   ├── Highlighter
│   ├── Paginator
│   └── Exporter
└── models           # 데이터 모델
    ├── SearchOptions
    ├── SearchResult
    ├── Query
    └── FilterConfig
```

### 4.2 클래스 다이어그램

```
┌─────────────────┐     ┌─────────────────┐
│  SearchEngine   │────>│  IndexBuilder   │
└─────────────────┘     └─────────────────┘
        │                       │
        │                       ▼
        │               ┌─────────────────┐
        │               │   IndexStore    │
        │               └─────────────────┘
        │
        ▼
┌─────────────────┐     ┌─────────────────┐
│ KeywordSearcher │────>│ MorphemeAnalyzer│
└─────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐     ┌─────────────────┐
│  FilterEngine   │────>│   QueryBuilder  │
└─────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐
│ ResultFormatter │
└─────────────────┘
```

---

## 5. 리스크 및 대응

### 5.1 기술적 리스크

| 리스크 | 영향도 | 발생 가능성 | 대응 방안 |
|--------|--------|-------------|-----------|
| MeCab ARM64 호환 문제 | 높음 | 중간 | 순수 Python 폴백 구현 |
| 대용량 인덱스 메모리 초과 | 중간 | 낮음 | 디스크 기반 인덱스 |
| 형태소 분석 정확도 저하 | 중간 | 낮음 | 여러 분석기 앙상블 |
| 복합 쿼리 성능 저하 | 중간 | 중간 | 쿼리 최적화 및 캐싱 |

### 5.2 완화 전략

**MeCab ARM64 호환**:
```bash
# ARM64 소스 컴파일
git clone https://github.com/taku910/mecab.git
cd mecab/mecab && ./configure && make && sudo make install
pip install mecab-python3
```

**메모리 최적화**:
- 인덱스 압축 (gzip)
- 메모리 매핑 (mmap) 활용
- LRU 캐시 적용

---

## 6. 테스트 전략

### 6.1 단위 테스트

- 각 검색 컴포넌트 개별 테스트
- 형태소 분석 정확도 테스트
- 필터 조합 테스트
- 쿼리 파서 테스트

### 6.2 통합 테스트

- 전체 검색 파이프라인 테스트
- 대용량 데이터 검색 테스트
- CLI 명령 통합 테스트

### 6.3 성능 테스트

- 인덱스 구축 시간 측정
- 검색 응답 시간 측정
- 메모리 사용량 모니터링
- 동시 검색 요청 처리

---

## 7. CLI 명령 설계

```bash
# 기본 검색
forensic search "키워드"

# 옵션 포함 검색
forensic search "가스라이팅" --speaker 신동식 --date-from 2025-07-01 --date-to 2025-08-31

# 정규표현식 검색
forensic search --regex "가스.*팅"

# 복합 검색
forensic search "(가스라이팅 OR 위협) AND 신동식"

# 결과 내보내기
forensic search "키워드" --output results.json --format json

# 인덱스 관리
forensic index build
forensic index status
forensic index update
```

---

Version: 1.0.0
Last Updated: 2026-01-19
