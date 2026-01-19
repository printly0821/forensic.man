---
id: SPEC-SEARCH-001
version: "1.0.0"
status: "draft"
created: "2026-01-19"
updated: "2026-01-19"
author: "지니"
priority: "MEDIUM"
dependencies:
  - SPEC-CORE-001
  - SPEC-IO-001
  - SPEC-TIMELINE-001
  - SPEC-EVIDENCE-001
---

# SPEC-SEARCH-001: 검색 및 필터링 시스템

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-01-19 | 지니 | 초기 작성 - 키워드 검색, 필터링, 고급 검색, 결과 처리 모듈 |

---

## 1. 개요

### 1.1 목적

forensic.man 프로젝트에 강력한 검색 및 필터링 시스템을 구현합니다. 183개의 녹취 파일에서 특정 키워드, 패턴, 증거를 효율적으로 찾고 필터링할 수 있는 기능을 제공합니다. 한국어 형태소 분석을 지원하여 정확한 검색 결과를 보장합니다.

### 1.2 범위

- **키워드 검색**: 전문 검색, 정규표현식, 형태소 분석 기반 검색
- **필터링**: 날짜, 화자, 중요도, 패턴 유형별 필터
- **고급 검색**: 복합 조건, 근접 검색, 와일드카드, 시간 범위 검색
- **검색 결과**: 하이라이트, 맥락 미리보기, 정렬, 페이지네이션

### 1.3 의존성

- **SPEC-CORE-001**: Transcript, Segment, Speaker, Evidence 데이터 모델
- **SPEC-IO-001**: StreamReader, ChunkProcessor, BatchProcessor
- **SPEC-TIMELINE-001**: PatternDetector, TimelineEvent
- **SPEC-EVIDENCE-001**: Evidence, EvidenceCategory, EvidenceChain

### 1.4 대상 시스템

| 항목 | 사양 |
|------|------|
| 플랫폼 | NVIDIA DGX Spark |
| CPU | 20코어 ARM (Cortex-X925 + A725) |
| GPU | Blackwell 6,144 CUDA cores |
| 메모리 | 128GB 통합 LPDDR5x |
| 분석 대상 | 183개 파일, 30분+ 분량, 2025.06~12 |
| 화자 | 신동식, 신기연 (2인) |

---

## 2. 요구사항 (EARS 형식)

### 2.1 유비쿼터스 요구사항 (Ubiquitous)

**[REQ-U-001]** 시스템은 항상 UTF-8 인코딩으로 검색을 수행해야 한다.

**[REQ-U-002]** 모든 검색 결과는 원본 세그먼트에 대한 참조를 유지해야 한다.

**[REQ-U-003]** 검색 쿼리는 최대 1000자로 제한되어야 한다.

**[REQ-U-004]** 검색 결과는 기본적으로 관련도순으로 정렬되어야 한다.

**[REQ-U-005]** 검색 인덱스는 Transcript, Segment, Evidence 모델을 포함해야 한다.

### 2.2 이벤트 기반 요구사항 (Event-Driven)

**[REQ-E-001]** 검색 쿼리가 입력될 때, 형태소 분석을 수행하여 토큰화해야 한다.

**[REQ-E-002]** 정규표현식 검색이 요청될 때, 정규식 패턴을 검증하고 실행해야 한다.

**[REQ-E-003]** 필터가 적용될 때, 검색 결과에 즉시 반영되어야 한다.

**[REQ-E-004]** 검색이 완료될 때, 총 결과 수와 검색 소요 시간을 반환해야 한다.

**[REQ-E-005]** 새로운 녹취 파일이 추가될 때, 검색 인덱스가 자동으로 업데이트되어야 한다.

**[REQ-E-006]** 검색 결과가 클릭될 때, 해당 세그먼트의 전체 맥락을 표시해야 한다.

### 2.3 상태 기반 요구사항 (State-Driven)

**[REQ-S-001]** 검색 인덱스가 구축된 상태일 때, 실시간 검색을 지원해야 한다.

**[REQ-S-002]** 필터가 활성화된 상태일 때, 필터 조건에 맞는 결과만 표시해야 한다.

**[REQ-S-003]** 대소문자 무시 모드가 활성화된 상태일 때, 대소문자를 구분하지 않고 검색해야 한다.

**[REQ-S-004]** 페이지네이션이 활성화된 상태일 때, 지정된 페이지 크기로 결과를 분할해야 한다.

### 2.4 원치 않는 동작 요구사항 (Unwanted Behavior)

**[REQ-W-001]** 시스템은 원본 데이터를 검색 과정에서 수정하지 않아야 한다.

**[REQ-W-002]** 시스템은 유효하지 않은 정규표현식을 실행하지 않아야 한다.

**[REQ-W-003]** 시스템은 메모리 제한을 초과하는 검색 결과를 한 번에 로드하지 않아야 한다.

**[REQ-W-004]** 시스템은 검색 시간 제한(30초)을 초과하는 쿼리를 실행하지 않아야 한다.

**[REQ-W-005]** 시스템은 빈 검색어로 전체 검색을 수행하지 않아야 한다.

### 2.5 선택적 요구사항 (Optional Feature)

**[REQ-O-001]** 사용자가 형태소 분석을 비활성화하면, 정확히 일치하는 문자열만 검색해야 한다.

**[REQ-O-002]** 사용자가 근접 검색 거리를 지정하면, 해당 거리 내의 단어만 검색해야 한다.

**[REQ-O-003]** 사용자가 검색 결과 내보내기를 요청하면, JSON 형식으로 내보내야 한다.

**[REQ-O-004]** 사용자가 검색 기록 저장을 요청하면, 최근 100개 검색 쿼리를 저장해야 한다.

### 2.6 복합 요구사항 (Complex)

**[REQ-C-001]** AND 조건과 OR 조건이 혼합된 복합 쿼리가 입력될 때, 연산자 우선순위에 따라 올바르게 처리해야 한다.

**[REQ-C-002]** 화자 필터와 날짜 필터가 동시에 적용된 상태에서 키워드 검색이 요청될 때, 모든 조건을 만족하는 결과만 반환해야 한다.

**[REQ-C-003]** 대용량 파일(100MB 이상)에서 검색이 요청될 때, 청크 단위로 스트리밍 검색을 수행하고 결과를 점진적으로 반환해야 한다.

---

## 3. 인터페이스 정의

### 3.1 SearchEngine

```python
class SearchEngine(Protocol):
    """검색 엔진 기본 인터페이스"""

    def search(
        self,
        query: str,
        options: Optional[SearchOptions] = None
    ) -> SearchResult:
        """기본 검색을 수행한다."""
        ...

    def search_regex(
        self,
        pattern: str,
        options: Optional[SearchOptions] = None
    ) -> SearchResult:
        """정규표현식 검색을 수행한다."""
        ...

    def search_morpheme(
        self,
        query: str,
        options: Optional[SearchOptions] = None
    ) -> SearchResult:
        """형태소 분석 기반 검색을 수행한다."""
        ...

    def build_index(
        self,
        transcripts: list[Transcript],
        segments: list[Segment],
        evidence: list[Evidence]
    ) -> IndexStats:
        """검색 인덱스를 구축한다."""
        ...

    def update_index(
        self,
        items: list[Union[Transcript, Segment, Evidence]]
    ) -> IndexStats:
        """검색 인덱스를 업데이트한다."""
        ...

    def get_index_stats(self) -> IndexStats:
        """인덱스 통계를 반환한다."""
        ...
```

### 3.2 KeywordSearcher

```python
class KeywordSearcher(Protocol):
    """키워드 검색 인터페이스"""

    def search_exact(
        self,
        keyword: str,
        case_sensitive: bool = False
    ) -> list[SearchHit]:
        """정확히 일치하는 키워드를 검색한다."""
        ...

    def search_partial(
        self,
        keyword: str,
        case_sensitive: bool = False
    ) -> list[SearchHit]:
        """부분 일치하는 키워드를 검색한다."""
        ...

    def search_wildcard(
        self,
        pattern: str
    ) -> list[SearchHit]:
        """와일드카드 패턴으로 검색한다. (* = 0개 이상, ? = 1개)"""
        ...

    def search_fuzzy(
        self,
        keyword: str,
        max_distance: int = 2
    ) -> list[SearchHit]:
        """유사 키워드를 검색한다. (편집 거리 기반)"""
        ...

    def tokenize(
        self,
        text: str
    ) -> list[Token]:
        """텍스트를 토큰화한다."""
        ...

    def analyze_morpheme(
        self,
        text: str
    ) -> list[MorphemeToken]:
        """한국어 형태소 분석을 수행한다."""
        ...
```

### 3.3 FilterEngine

```python
class FilterEngine(Protocol):
    """필터링 엔진 인터페이스"""

    def filter_by_date_range(
        self,
        items: list[T],
        start_date: datetime.date,
        end_date: datetime.date
    ) -> list[T]:
        """날짜 범위로 필터링한다."""
        ...

    def filter_by_speaker(
        self,
        items: list[T],
        speakers: list[str]
    ) -> list[T]:
        """화자로 필터링한다."""
        ...

    def filter_by_importance(
        self,
        items: list[Evidence],
        importance: list[Literal["HIGH", "MEDIUM", "LOW"]]
    ) -> list[Evidence]:
        """중요도로 필터링한다."""
        ...

    def filter_by_pattern_type(
        self,
        items: list[Evidence],
        pattern_types: list[str]
    ) -> list[Evidence]:
        """패턴 유형으로 필터링한다. (GASLIGHTING, EMOTIONAL_MANIPULATION, THREAT)"""
        ...

    def filter_by_time_range(
        self,
        segments: list[Segment],
        start_time: float,
        end_time: float
    ) -> list[Segment]:
        """녹취 내 시간 범위로 필터링한다."""
        ...

    def apply_filters(
        self,
        items: list[T],
        filters: FilterConfig
    ) -> list[T]:
        """복합 필터를 적용한다."""
        ...

    def clear_filters(self) -> None:
        """모든 필터를 초기화한다."""
        ...
```

### 3.4 QueryBuilder

```python
class QueryBuilder(Protocol):
    """쿼리 생성기 인터페이스"""

    def parse(
        self,
        query_string: str
    ) -> Query:
        """쿼리 문자열을 파싱한다."""
        ...

    def build_and(
        self,
        queries: list[Query]
    ) -> Query:
        """AND 조건 쿼리를 생성한다."""
        ...

    def build_or(
        self,
        queries: list[Query]
    ) -> Query:
        """OR 조건 쿼리를 생성한다."""
        ...

    def build_not(
        self,
        query: Query
    ) -> Query:
        """NOT 조건 쿼리를 생성한다."""
        ...

    def build_proximity(
        self,
        term1: str,
        term2: str,
        distance: int
    ) -> Query:
        """근접 검색 쿼리를 생성한다."""
        ...

    def build_phrase(
        self,
        phrase: str
    ) -> Query:
        """구문 검색 쿼리를 생성한다."""
        ...

    def validate(
        self,
        query: Query
    ) -> ValidationResult:
        """쿼리 유효성을 검증한다."""
        ...

    def optimize(
        self,
        query: Query
    ) -> Query:
        """쿼리를 최적화한다."""
        ...
```

### 3.5 ResultFormatter

```python
class ResultFormatter(Protocol):
    """결과 포맷터 인터페이스"""

    def highlight(
        self,
        text: str,
        matches: list[Match],
        tag: str = "mark"
    ) -> str:
        """검색 일치 부분을 하이라이트한다."""
        ...

    def get_context_preview(
        self,
        segment: Segment,
        all_segments: list[Segment],
        before_chars: int = 100,
        after_chars: int = 100
    ) -> ContextPreview:
        """맥락 미리보기를 생성한다."""
        ...

    def sort_results(
        self,
        results: list[SearchHit],
        sort_by: Literal["relevance", "date", "importance"],
        order: Literal["asc", "desc"] = "desc"
    ) -> list[SearchHit]:
        """검색 결과를 정렬한다."""
        ...

    def paginate(
        self,
        results: list[SearchHit],
        page: int,
        page_size: int = 20
    ) -> PaginatedResult:
        """검색 결과를 페이지네이션한다."""
        ...

    def format_summary(
        self,
        result: SearchResult
    ) -> str:
        """검색 결과 요약을 생성한다."""
        ...

    def export_results(
        self,
        results: list[SearchHit],
        output_path: Path,
        format: Literal["json", "csv", "markdown"] = "json"
    ) -> Path:
        """검색 결과를 내보낸다."""
        ...
```

---

## 4. 데이터 모델

### 4.1 SearchOptions (검색 옵션)

```python
class SearchOptions(BaseModel):
    """검색 옵션 모델"""
    case_sensitive: bool = False              # 대소문자 구분
    use_morpheme: bool = True                 # 형태소 분석 사용
    use_regex: bool = False                   # 정규표현식 사용
    max_results: int = 1000                   # 최대 결과 수
    timeout_seconds: float = 30.0             # 검색 시간 제한
    include_context: bool = True              # 맥락 포함 여부
    context_chars: int = 100                  # 맥락 문자 수
    highlight: bool = True                    # 하이라이트 여부
    search_targets: list[Literal["transcript", "segment", "evidence"]] = ["segment"]
```

### 4.2 SearchResult (검색 결과)

```python
class SearchResult(BaseModel):
    """검색 결과 모델"""
    query: str                                # 검색 쿼리
    total_hits: int                           # 총 결과 수
    hits: list[SearchHit]                     # 검색 히트 목록
    search_time_ms: float                     # 검색 소요 시간 (밀리초)
    filters_applied: list[str]                # 적용된 필터 목록
    page: int                                 # 현재 페이지
    page_size: int                            # 페이지 크기
    total_pages: int                          # 총 페이지 수
    suggestions: list[str]                    # 검색어 제안
    facets: dict[str, dict[str, int]]         # 패싯 정보 (화자별, 날짜별 수)
```

### 4.3 SearchHit (검색 히트)

```python
class SearchHit(BaseModel):
    """검색 히트 모델"""
    id: str                                   # 히트 ID
    source_type: Literal["transcript", "segment", "evidence"]
    source_id: str                            # 원본 ID
    score: float                              # 관련도 점수 (0.0 ~ 1.0)
    matched_text: str                         # 일치한 텍스트
    highlighted_text: str                     # 하이라이트된 텍스트
    context_before: str                       # 이전 맥락
    context_after: str                        # 이후 맥락
    speaker: Optional[str]                    # 화자
    timestamp: Optional[datetime]             # 타임스탬프
    file_path: Optional[Path]                 # 파일 경로
    position: MatchPosition                   # 일치 위치
    metadata: dict[str, Any]                  # 추가 메타데이터
```

### 4.4 Query (쿼리)

```python
class Query(BaseModel):
    """쿼리 모델"""
    query_id: str                             # 쿼리 ID
    query_type: Literal["keyword", "phrase", "regex", "boolean", "proximity"]
    raw_query: str                            # 원본 쿼리 문자열
    parsed_tokens: list[Token]                # 파싱된 토큰
    operator: Optional[Literal["AND", "OR", "NOT"]]
    sub_queries: list["Query"]                # 하위 쿼리 (복합 쿼리용)
    options: SearchOptions                    # 검색 옵션
    created_at: datetime                      # 생성 시점
```

### 4.5 FilterConfig (필터 설정)

```python
class FilterConfig(BaseModel):
    """필터 설정 모델"""
    date_range: Optional[tuple[datetime.date, datetime.date]] = None
    speakers: Optional[list[str]] = None      # ["신동식", "신기연"]
    importance: Optional[list[Literal["HIGH", "MEDIUM", "LOW"]]] = None
    pattern_types: Optional[list[str]] = None  # ["GASLIGHTING", "THREAT", "EMOTIONAL_MANIPULATION"]
    time_range: Optional[tuple[float, float]] = None  # 녹취 내 시간 범위 (초)
    categories: Optional[list[str]] = None     # 증거 카테고리
    transcript_ids: Optional[list[str]] = None # 특정 녹취 파일
```

### 4.6 Token (토큰)

```python
class Token(BaseModel):
    """토큰 모델"""
    text: str                                 # 토큰 텍스트
    start: int                                # 시작 위치
    end: int                                  # 종료 위치
    token_type: Literal["word", "number", "punctuation", "whitespace"]
```

### 4.7 MorphemeToken (형태소 토큰)

```python
class MorphemeToken(BaseModel):
    """형태소 토큰 모델"""
    text: str                                 # 원본 텍스트
    lemma: str                                # 기본형
    pos: str                                  # 품사 태그 (NNG, VV, JKS 등)
    start: int                                # 시작 위치
    end: int                                  # 종료 위치
    is_content_word: bool                     # 내용어 여부
```

### 4.8 MatchPosition (일치 위치)

```python
class MatchPosition(BaseModel):
    """일치 위치 모델"""
    start: int                                # 시작 인덱스
    end: int                                  # 종료 인덱스
    line: Optional[int]                       # 라인 번호
    column: Optional[int]                     # 컬럼 번호
```

### 4.9 ContextPreview (맥락 미리보기)

```python
class ContextPreview(BaseModel):
    """맥락 미리보기 모델"""
    before_text: str                          # 이전 텍스트
    matched_text: str                         # 일치 텍스트
    after_text: str                           # 이후 텍스트
    before_segments: list[Segment]            # 이전 세그먼트
    after_segments: list[Segment]             # 이후 세그먼트
    highlighted: str                          # 하이라이트된 전체 텍스트
```

### 4.10 PaginatedResult (페이지네이션 결과)

```python
class PaginatedResult(BaseModel):
    """페이지네이션 결과 모델"""
    items: list[SearchHit]                    # 현재 페이지 항목
    page: int                                 # 현재 페이지 (1부터 시작)
    page_size: int                            # 페이지 크기
    total_items: int                          # 총 항목 수
    total_pages: int                          # 총 페이지 수
    has_previous: bool                        # 이전 페이지 존재 여부
    has_next: bool                            # 다음 페이지 존재 여부
```

### 4.11 IndexStats (인덱스 통계)

```python
class IndexStats(BaseModel):
    """인덱스 통계 모델"""
    total_documents: int                      # 총 문서 수
    total_segments: int                       # 총 세그먼트 수
    total_evidence: int                       # 총 증거 수
    total_tokens: int                         # 총 토큰 수
    index_size_bytes: int                     # 인덱스 크기 (바이트)
    last_updated: datetime                    # 마지막 업데이트 시점
    build_time_seconds: float                 # 구축 소요 시간
```

---

## 5. 파일 구조

```
src/forensic/search/
├── __init__.py                   # 모듈 초기화 및 공개 API
├── engine/
│   ├── __init__.py
│   ├── search_engine.py          # SearchEngine 구현
│   ├── index_builder.py          # 검색 인덱스 구축
│   └── index_store.py            # 인덱스 저장/로드
├── keyword/
│   ├── __init__.py
│   ├── keyword_searcher.py       # KeywordSearcher 구현
│   ├── tokenizer.py              # 토크나이저
│   ├── morpheme_analyzer.py      # 한국어 형태소 분석기
│   ├── wildcard.py               # 와일드카드 검색
│   └── fuzzy.py                  # 퍼지 검색
├── filter/
│   ├── __init__.py
│   ├── filter_engine.py          # FilterEngine 구현
│   ├── date_filter.py            # 날짜 필터
│   ├── speaker_filter.py         # 화자 필터
│   ├── importance_filter.py      # 중요도 필터
│   └── pattern_filter.py         # 패턴 유형 필터
├── query/
│   ├── __init__.py
│   ├── query_builder.py          # QueryBuilder 구현
│   ├── parser.py                 # 쿼리 파서
│   ├── optimizer.py              # 쿼리 최적화
│   └── validator.py              # 쿼리 검증
├── result/
│   ├── __init__.py
│   ├── result_formatter.py       # ResultFormatter 구현
│   ├── highlighter.py            # 하이라이트 처리
│   ├── paginator.py              # 페이지네이션
│   ├── sorter.py                 # 정렬 처리
│   └── exporter.py               # 결과 내보내기
└── models/
    ├── __init__.py
    ├── search.py                 # 검색 관련 모델
    ├── query.py                  # 쿼리 관련 모델
    ├── filter.py                 # 필터 관련 모델
    └── result.py                 # 결과 관련 모델
```

---

## 6. 설정 파일 확장

```yaml
# config.yaml에 추가
forensic:
  search:
    # 검색 엔진 설정
    engine:
      max_results: 1000               # 최대 결과 수
      timeout_seconds: 30             # 검색 시간 제한
      default_page_size: 20           # 기본 페이지 크기
      index_path: ".forensic/index"   # 인덱스 저장 경로

    # 키워드 검색 설정
    keyword:
      use_morpheme: true              # 형태소 분석 사용
      morpheme_analyzer: "mecab"      # 형태소 분석기 (mecab, komoran)
      case_sensitive: false           # 기본 대소문자 구분
      fuzzy_max_distance: 2           # 퍼지 검색 최대 편집 거리

    # 필터링 설정
    filter:
      speakers:                       # 화자 목록
        - "신동식"
        - "신기연"
      importance_levels:              # 중요도 목록
        - "HIGH"
        - "MEDIUM"
        - "LOW"
      pattern_types:                  # 패턴 유형 목록
        - "GASLIGHTING"
        - "EMOTIONAL_MANIPULATION"
        - "THREAT"

    # 결과 표시 설정
    result:
      context_chars: 100              # 맥락 문자 수
      highlight_tag: "mark"           # 하이라이트 태그
      default_sort: "relevance"       # 기본 정렬 (relevance, date, importance)
      default_order: "desc"           # 기본 정렬 순서

    # 검색 기록 설정
    history:
      enabled: true                   # 검색 기록 저장
      max_entries: 100                # 최대 저장 개수
      save_path: ".forensic/search_history.json"
```

---

## 7. 비기능적 요구사항

### 7.1 성능

- 검색 응답 시간: < 500ms (10,000 세그먼트 기준)
- 인덱스 구축 시간: < 30초 (183개 파일 기준)
- 형태소 분석 처리량: > 10,000 tokens/second
- 메모리 사용량: < 2GB (인덱스 포함)

### 7.2 정확도

- 키워드 검색 정확도: > 99%
- 형태소 분석 정확도: > 95% (한국어)
- 와일드카드 검색 정확도: 100%
- 정규표현식 검색 정확도: 100%

### 7.3 확장성

- 새로운 필터 유형 동적 추가 가능
- 형태소 분석기 교체 가능 (MeCab, Komoran 등)
- 검색 대상 확장 가능 (새로운 모델 추가)

### 7.4 안정성

- 유효하지 않은 정규표현식 예외 처리
- 검색 시간 초과 자동 중단
- 메모리 제한 초과 시 스트리밍 모드 전환

---

## 8. 기술적 제약사항

### 8.1 의존성 목록

```toml
[project]
dependencies = [
    # SPEC-CORE-001, SPEC-IO-001, SPEC-EVIDENCE-001 의존성 포함
    "pydantic>=2.0",
    "python-dateutil>=2.8",
]

[project.optional-dependencies]
search = [
    "mecab-python3>=1.0",     # 한국어 형태소 분석 (MeCab)
    "konlpy>=0.6",            # 한국어 NLP 툴킷 (선택)
]
```

### 8.2 ARM64 호환성 고려

- mecab-python3: ARM64 빌드 필요 (소스 컴파일)
- konlpy: ARM64 빌드 확인 필요
- 순수 Python 폴백 구현 권장

### 8.3 검색 쿼리 문법

```
# 기본 검색
"키워드"

# 정확한 구문 검색
"정확한 구문"

# AND 검색
키워드1 AND 키워드2

# OR 검색
키워드1 OR 키워드2

# NOT 검색
키워드1 NOT 키워드2

# 와일드카드
가스* (가스라이팅, 가스등 등)
감?조작 (감정조작)

# 근접 검색
"키워드1 키워드2"~5 (5단어 이내)

# 필드 지정 검색
speaker:신동식 AND content:위협
```

---

Version: 1.0.0
Last Updated: 2026-01-19
