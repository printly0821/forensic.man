---
id: SPEC-CLI-001
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
  - SPEC-REPORT-001
  - SPEC-SEARCH-001
---

# SPEC-CLI-001: CLI 명령 인터페이스 시스템

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-01-19 | 지니 | 초기 작성 - 5개 CLI 명령 (analyze, search, report, timeline, config) 정의 |

---

## 1. 개요

### 1.1 목적

forensic.man 프로젝트의 모든 기능을 통합하는 CLI 명령 인터페이스를 구현합니다. Click 프레임워크와 Rich 라이브러리를 활용하여 직관적이고 시각적으로 풍부한 사용자 경험을 제공합니다.

### 1.2 범위

- **forensic analyze**: 전체 분석 파이프라인 실행
- **forensic search**: 키워드/패턴 검색 및 필터링
- **forensic report**: 다양한 형식의 보고서 생성
- **forensic timeline**: 시계열 분석 및 타임라인 시각화
- **forensic config**: 설정 관리 및 시스템 정보 표시

### 1.3 의존성

| 의존 SPEC | 사용 컴포넌트 | 용도 |
|-----------|---------------|------|
| SPEC-CORE-001 | Transcript, Segment, Speaker, Evidence | 핵심 데이터 모델 |
| SPEC-IO-001 | StreamReader, ChunkProcessor, BatchProcessor | 파일 입출력 |
| SPEC-TIMELINE-001 | TimelineAnalyzer, PatternDetector, TimelineEvent | 시계열 분석 |
| SPEC-EVIDENCE-001 | EvidenceExtractor, EvidenceChain | 증거 추출 |
| SPEC-REPORT-001 | ReportGenerator, ReportFormatter | 보고서 생성 |
| SPEC-SEARCH-001 | SearchEngine, FilterEngine, ResultFormatter | 검색 및 필터링 |

### 1.4 대상 시스템

| 항목 | 사양 |
|------|------|
| 플랫폼 | NVIDIA DGX Spark |
| CPU | 20코어 ARM (Cortex-X925 + A725) |
| GPU | Blackwell 6,144 CUDA cores |
| 메모리 | 128GB 통합 LPDDR5x |
| CUDA | 13.0 |
| 분석 대상 | 183개 파일, 30분+ 분량, 2025.06~12 |
| 화자 | 신동식, 신기연 (2인) |

---

## 2. 요구사항 (EARS 형식)

### 2.1 유비쿼터스 요구사항 (Ubiquitous)

**[REQ-U-001]** 시스템은 항상 UTF-8 인코딩으로 입출력을 처리해야 한다.

**[REQ-U-002]** 모든 CLI 명령은 `--help` 옵션으로 도움말을 표시해야 한다.

**[REQ-U-003]** 모든 오류 메시지는 사용자가 이해할 수 있는 한국어로 표시해야 한다.

**[REQ-U-004]** 시스템은 `~/.forensic/config.yaml` 파일에서 기본 설정을 로드해야 한다.

**[REQ-U-005]** 장시간 작업은 Rich 진행률 표시줄로 진행 상태를 표시해야 한다.

**[REQ-U-006]** 시스템은 분석 결과를 `.forensic/` 디렉토리에 캐싱해야 한다.

### 2.2 이벤트 기반 요구사항 (Event-Driven)

**[REQ-E-001]** `forensic analyze` 명령이 실행될 때, 전체 분석 파이프라인이 순차적으로 실행되어야 한다.

**[REQ-E-002]** `forensic search` 명령이 실행될 때, 검색 엔진이 호출되고 결과가 포맷팅되어 표시되어야 한다.

**[REQ-E-003]** `forensic report` 명령이 실행될 때, 지정된 형식의 보고서가 생성되어야 한다.

**[REQ-E-004]** `forensic timeline` 명령이 실행될 때, 시계열 분석 결과가 시각화되어야 한다.

**[REQ-E-005]** `forensic config --show` 명령이 실행될 때, 현재 설정이 테이블 형식으로 표시되어야 한다.

**[REQ-E-006]** Ctrl+C 인터럽트가 발생할 때, 진행 중인 작업을 안전하게 중단하고 부분 결과를 저장해야 한다.

**[REQ-E-007]** 분석 완료 시, 요약 통계가 패널 형식으로 표시되어야 한다.

### 2.3 상태 기반 요구사항 (State-Driven)

**[REQ-S-001]** 검색 인덱스가 존재하지 않는 상태일 때, `forensic search` 명령은 인덱스 구축을 먼저 요청해야 한다.

**[REQ-S-002]** `--verbose` 플래그가 활성화된 상태일 때, 상세 로그가 출력되어야 한다.

**[REQ-S-003]** `--quiet` 플래그가 활성화된 상태일 때, 필수 출력만 표시해야 한다.

**[REQ-S-004]** 설정 파일이 존재하지 않는 상태일 때, 기본 설정으로 동작해야 한다.

**[REQ-S-005]** 캐시가 존재하는 상태일 때, `--force` 없이는 재분석을 건너뛰어야 한다.

### 2.4 원치 않는 동작 요구사항 (Unwanted Behavior)

**[REQ-W-001]** 시스템은 원본 녹취 파일을 수정하지 않아야 한다.

**[REQ-W-002]** 시스템은 민감한 개인정보를 로그에 기록하지 않아야 한다.

**[REQ-W-003]** 시스템은 메모리 제한(2GB)을 초과하는 단일 작업을 수행하지 않아야 한다.

**[REQ-W-004]** 시스템은 출력 디렉토리 외부에 파일을 생성하지 않아야 한다.

**[REQ-W-005]** 시스템은 사용자 확인 없이 기존 출력 파일을 덮어쓰지 않아야 한다.

### 2.5 선택적 요구사항 (Optional Feature)

**[REQ-O-001]** 사용자가 `--color` 옵션을 지정하면, 출력에 ANSI 색상을 적용해야 한다.

**[REQ-O-002]** 사용자가 `--json` 옵션을 지정하면, 결과를 JSON 형식으로 출력해야 한다.

**[REQ-O-003]** 사용자가 `--parallel` 옵션을 지정하면, 멀티코어를 활용한 병렬 처리를 수행해야 한다.

**[REQ-O-004]** 사용자가 `--gpu` 옵션을 지정하면, CUDA 가속을 활성화해야 한다.

### 2.6 복합 요구사항 (Complex)

**[REQ-C-001]** 분석이 진행 중인 상태에서 Ctrl+C가 입력될 때, 현재까지의 결과를 저장하고 재개 가능한 상태로 종료해야 한다.

**[REQ-C-002]** 캐시가 존재하고 `--force` 플래그가 없는 상태에서 분석이 요청될 때, 캐시된 결과를 사용하고 변경된 파일만 재분석해야 한다.

**[REQ-C-003]** 검색 필터가 적용된 상태에서 내보내기가 요청될 때, 필터가 적용된 결과만 내보내야 한다.

---

## 3. CLI 명령 정의

### 3.1 메인 명령 그룹

```python
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

@click.group()
@click.version_option(version="0.1.0", prog_name="forensic")
@click.option('--verbose', '-v', is_flag=True, help='상세 로그 출력')
@click.option('--quiet', '-q', is_flag=True, help='최소 출력')
@click.option('--config', '-c', type=click.Path(), default='~/.forensic/config.yaml', help='설정 파일 경로')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool, config: str) -> None:
    """forensic.man - 녹취자료 분석 CLI 도구

    가스라이팅 학대 사건의 녹취 증거를 분석하는 도구입니다.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    ctx.obj['config_path'] = config
```

### 3.2 forensic analyze

```python
@cli.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True), help='입력 디렉토리 경로')
@click.option('--output', '-o', required=True, type=click.Path(), help='출력 디렉토리 경로')
@click.option('--force', '-f', is_flag=True, help='캐시 무시하고 강제 재분석')
@click.option('--parallel', '-p', is_flag=True, help='멀티코어 병렬 처리')
@click.option('--gpu', is_flag=True, help='GPU 가속 사용')
@click.pass_context
def analyze(
    ctx: click.Context,
    input: str,
    output: str,
    force: bool,
    parallel: bool,
    gpu: bool
) -> None:
    """전체 분석 파이프라인 실행

    녹취 파일을 읽고, 패턴을 분석하고, 증거를 추출합니다.

    예시:
        forensic analyze -i ./data/recordings -o ./data/output
        forensic analyze -i ./data -o ./output --force --parallel
    """
    pass
```

### 3.3 forensic search

```python
@cli.command()
@click.argument('query', required=True)
@click.option('--speaker', '-s', help='화자 필터 (신동식 또는 신기연)')
@click.option('--date', '-d', help='날짜 범위 (YYYY-MM-DD:YYYY-MM-DD)')
@click.option('--importance', '-I', type=click.Choice(['HIGH', 'MEDIUM', 'LOW']), multiple=True, help='중요도 필터')
@click.option('--pattern', '-P', multiple=True, help='패턴 유형 필터 (GASLIGHTING, THREAT, EMOTIONAL_MANIPULATION)')
@click.option('--regex', '-r', is_flag=True, help='정규표현식 검색')
@click.option('--case-sensitive', is_flag=True, help='대소문자 구분')
@click.option('--limit', '-l', type=int, default=20, help='결과 제한 수 (기본: 20)')
@click.option('--output', '-o', type=click.Path(), help='결과 저장 경로')
@click.option('--format', '-F', type=click.Choice(['table', 'json', 'csv']), default='table', help='출력 형식')
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    speaker: str | None,
    date: str | None,
    importance: tuple[str, ...],
    pattern: tuple[str, ...],
    regex: bool,
    case_sensitive: bool,
    limit: int,
    output: str | None,
    format: str
) -> None:
    """키워드/패턴 검색

    녹취 내용에서 특정 키워드나 패턴을 검색합니다.
    검색 결과는 관련도순으로 정렬되며, 일치 부분이 하이라이트됩니다.

    예시:
        forensic search "가스라이팅"
        forensic search "위협" --speaker 신동식 --date 2025-07-01:2025-08-31
        forensic search --regex "가스.*팅" --importance HIGH
    """
    pass
```

### 3.4 forensic report

```python
@cli.command()
@click.option('--type', '-t', 'report_type', required=True,
              type=click.Choice(['legal', 'timeline', 'summary', 'evidence', 'statistical']),
              help='보고서 유형')
@click.option('--output', '-o', required=True, type=click.Path(), help='출력 파일 경로')
@click.option('--format', '-f', type=click.Choice(['markdown', 'html', 'json', 'pdf']),
              default='markdown', help='출력 형식')
@click.option('--template', type=click.Path(exists=True), help='사용자 정의 템플릿')
@click.option('--date-range', '-d', help='날짜 범위 (YYYY-MM-DD:YYYY-MM-DD)')
@click.option('--speaker', '-s', help='특정 화자만 포함')
@click.option('--min-importance', type=click.Choice(['HIGH', 'MEDIUM', 'LOW']),
              default='LOW', help='최소 중요도')
@click.pass_context
def report(
    ctx: click.Context,
    report_type: str,
    output: str,
    format: str,
    template: str | None,
    date_range: str | None,
    speaker: str | None,
    min_importance: str
) -> None:
    """보고서 생성

    분석 결과를 기반으로 다양한 형식의 보고서를 생성합니다.

    보고서 유형:
        legal       - 법적 증거 보고서 (법정 제출용)
        timeline    - 시계열 분석 보고서
        summary     - 전체 요약 보고서
        evidence    - 증거 목록 보고서
        statistical - 통계 분석 보고서

    예시:
        forensic report --type legal -o ./reports/legal_report.md
        forensic report --type timeline -o ./reports/timeline.html -f html
        forensic report --type evidence -o ./evidence.json -f json --min-importance HIGH
    """
    pass
```

### 3.5 forensic timeline

```python
@cli.command()
@click.option('--start', '-s', help='시작 날짜 (YYYY-MM-DD)')
@click.option('--end', '-e', help='종료 날짜 (YYYY-MM-DD)')
@click.option('--speaker', help='특정 화자 필터')
@click.option('--pattern', '-p', multiple=True, help='특정 패턴만 표시')
@click.option('--output', '-o', type=click.Path(), help='타임라인 저장 경로')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'html']),
              default='text', help='출력 형식')
@click.option('--resolution', '-r', type=click.Choice(['day', 'week', 'month']),
              default='day', help='시간 해상도')
@click.pass_context
def timeline(
    ctx: click.Context,
    start: str | None,
    end: str | None,
    speaker: str | None,
    pattern: tuple[str, ...],
    output: str | None,
    format: str,
    resolution: str
) -> None:
    """시계열 분석 및 타임라인 표시

    녹취 데이터의 시간적 패턴을 분석하고 타임라인으로 시각화합니다.

    예시:
        forensic timeline
        forensic timeline --start 2025-07-01 --end 2025-08-31
        forensic timeline --pattern GASLIGHTING --pattern THREAT -f html -o timeline.html
    """
    pass
```

### 3.6 forensic config

```python
@cli.command()
@click.option('--show', is_flag=True, help='현재 설정 표시')
@click.option('--edit', is_flag=True, help='설정 파일 편집')
@click.option('--reset', is_flag=True, help='기본 설정으로 초기화')
@click.option('--set', 'set_values', nargs=2, multiple=True, metavar='KEY VALUE', help='설정 값 변경')
@click.option('--get', 'get_key', help='특정 설정 값 조회')
@click.option('--system-info', is_flag=True, help='시스템 정보 표시 (DGX Spark 환경)')
@click.pass_context
def config(
    ctx: click.Context,
    show: bool,
    edit: bool,
    reset: bool,
    set_values: tuple[tuple[str, str], ...],
    get_key: str | None,
    system_info: bool
) -> None:
    """설정 관리

    forensic.man의 설정을 조회하고 변경합니다.

    예시:
        forensic config --show
        forensic config --system-info
        forensic config --set output.format html
        forensic config --get search.timeout
        forensic config --reset
    """
    pass
```

---

## 4. 데이터 모델

### 4.1 CLIContext (CLI 컨텍스트)

```python
class CLIContext(BaseModel):
    """CLI 실행 컨텍스트"""
    verbose: bool = False                 # 상세 로그 모드
    quiet: bool = False                   # 최소 출력 모드
    config_path: Path                     # 설정 파일 경로
    config: ForensicConfig               # 로드된 설정
    console: Console                      # Rich 콘솔 인스턴스
```

### 4.2 ForensicConfig (설정)

```python
class ForensicConfig(BaseModel):
    """전체 설정 모델"""
    # 분석 설정
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    # 검색 설정
    search: SearchConfig = Field(default_factory=SearchConfig)
    # 보고서 설정
    report: ReportConfig = Field(default_factory=ReportConfig)
    # 타임라인 설정
    timeline: TimelineConfig = Field(default_factory=TimelineConfig)
    # 출력 설정
    output: OutputConfig = Field(default_factory=OutputConfig)
    # 캐시 설정
    cache: CacheConfig = Field(default_factory=CacheConfig)
    # 시스템 설정
    system: SystemConfig = Field(default_factory=SystemConfig)
```

### 4.3 AnalyzeResult (분석 결과)

```python
class AnalyzeResult(BaseModel):
    """분석 결과 모델"""
    total_files: int                      # 처리된 파일 수
    total_segments: int                   # 총 세그먼트 수
    total_evidence: int                   # 추출된 증거 수
    processing_time_seconds: float        # 처리 시간
    patterns_found: dict[str, int]        # 패턴별 발견 수
    speaker_stats: dict[str, SpeakerStats]  # 화자별 통계
    errors: list[ProcessingError]         # 처리 오류 목록
    cache_hits: int                       # 캐시 히트 수
    output_path: Path                     # 출력 경로
```

### 4.4 ProgressState (진행 상태)

```python
class ProgressState(BaseModel):
    """진행 상태 모델 (중단 후 재개용)"""
    job_id: str                           # 작업 ID
    started_at: datetime                  # 시작 시간
    last_updated: datetime                # 마지막 업데이트
    total_files: int                      # 총 파일 수
    processed_files: int                  # 처리된 파일 수
    current_file: str | None              # 현재 처리 중인 파일
    completed_files: list[str]            # 완료된 파일 목록
    failed_files: list[str]               # 실패한 파일 목록
    partial_results_path: Path | None     # 부분 결과 저장 경로
    can_resume: bool                      # 재개 가능 여부
```

---

## 5. 출력 형식 정의

### 5.1 Rich 콘솔 출력 스타일

```python
# 성공 메시지
console.print("[green]✓[/green] 분석이 완료되었습니다.")

# 경고 메시지
console.print("[yellow]![/yellow] 일부 파일을 처리할 수 없습니다.")

# 오류 메시지
console.print("[red]✗[/red] 분석 중 오류가 발생했습니다.")

# 정보 메시지
console.print("[blue]ℹ[/blue] 캐시된 결과를 사용합니다.")
```

### 5.2 진행률 표시

```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    console=console,
) as progress:
    task = progress.add_task("[cyan]분석 중...", total=total_files)
    for file in files:
        # 처리
        progress.update(task, advance=1)
```

### 5.3 결과 테이블

```python
table = Table(title="검색 결과", show_header=True, header_style="bold magenta")
table.add_column("번호", style="dim", width=6)
table.add_column("화자", width=10)
table.add_column("날짜", width=12)
table.add_column("내용", width=50)
table.add_column("점수", justify="right", width=8)
console.print(table)
```

### 5.4 요약 패널

```python
summary = Panel(
    f"""
[bold]분석 완료[/bold]

파일 수: {result.total_files}
세그먼트: {result.total_segments:,}
증거: {result.total_evidence}
처리 시간: {result.processing_time_seconds:.2f}초
    """,
    title="분석 결과 요약",
    border_style="green"
)
console.print(summary)
```

---

## 6. 파일 구조

```
src/forensic/cli/
├── __init__.py                   # 모듈 초기화 및 공개 API
├── main.py                       # CLI 진입점 (cli 그룹 정의)
├── commands/
│   ├── __init__.py
│   ├── analyze.py               # forensic analyze 명령
│   ├── search.py                # forensic search 명령
│   ├── report.py                # forensic report 명령
│   ├── timeline.py              # forensic timeline 명령
│   └── config.py                # forensic config 명령
├── output/
│   ├── __init__.py
│   ├── console.py               # Rich 콘솔 출력 유틸리티
│   ├── progress.py              # 진행률 표시
│   ├── table.py                 # 테이블 포맷터
│   └── panel.py                 # 패널 포맷터
├── models/
│   ├── __init__.py
│   ├── context.py               # CLIContext 모델
│   ├── config.py                # ForensicConfig 모델
│   ├── result.py                # AnalyzeResult 모델
│   └── progress.py              # ProgressState 모델
└── utils/
    ├── __init__.py
    ├── config_loader.py         # 설정 파일 로드/저장
    ├── cache.py                 # 캐시 관리
    ├── signal_handler.py        # Ctrl+C 핸들링
    └── validators.py            # 입력 검증
```

---

## 7. 설정 파일 구조

```yaml
# ~/.forensic/config.yaml

# 분석 설정
analysis:
  chunk_size_mb: 1               # 청크 크기 (MB)
  parallel_workers: 4            # 병렬 워커 수
  enable_gpu: false              # GPU 가속 사용
  timeout_per_file: 300          # 파일당 타임아웃 (초)

# 검색 설정
search:
  max_results: 1000              # 최대 결과 수
  timeout_seconds: 30            # 검색 타임아웃
  default_page_size: 20          # 기본 페이지 크기
  enable_morpheme: true          # 형태소 분석 활성화

# 보고서 설정
report:
  default_format: markdown       # 기본 출력 형식
  include_statistics: true       # 통계 포함
  include_timeline: true         # 타임라인 포함
  legal_template: null           # 법적 보고서 템플릿

# 타임라인 설정
timeline:
  default_resolution: day        # 기본 시간 해상도
  show_patterns: true            # 패턴 표시
  highlight_important: true      # 중요 이벤트 강조

# 출력 설정
output:
  color: auto                    # 색상 출력 (auto/always/never)
  unicode: true                  # 유니코드 문자 사용
  quiet: false                   # 최소 출력 모드
  verbose: false                 # 상세 출력 모드

# 캐시 설정
cache:
  enabled: true                  # 캐시 사용
  directory: .forensic/cache     # 캐시 디렉토리
  max_size_mb: 500               # 최대 캐시 크기
  ttl_days: 7                    # 캐시 유효 기간

# 시스템 설정
system:
  memory_limit_gb: 2             # 메모리 제한 (GB)
  temp_directory: /tmp/forensic  # 임시 디렉토리
  log_level: INFO                # 로그 레벨
```

---

## 8. 비기능적 요구사항

### 8.1 성능

| 항목 | 기준 | 측정 방법 |
|------|------|-----------|
| CLI 시작 시간 | < 1초 | 벤치마크 |
| 분석 처리량 | > 10 파일/분 (단일 코어) | 벤치마크 |
| 검색 응답 시간 | < 500ms | 벤치마크 |
| 메모리 사용량 | < 2GB (단일 작업) | memory_profiler |
| 진행률 업데이트 | > 10Hz | 측정 |

### 8.2 사용성

| 항목 | 기준 |
|------|------|
| 도움말 접근 | 모든 명령에서 `--help` 지원 |
| 오류 메시지 | 원인과 해결 방법 포함 |
| 진행률 표시 | 모든 장시간 작업에 표시 |
| 취소 지원 | Ctrl+C로 안전한 중단 |
| 탭 완성 | Click 내장 지원 활용 |

### 8.3 호환성

| 항목 | 지원 |
|------|------|
| Python 버전 | 3.10+ |
| OS | Linux (ARM64), macOS (Apple Silicon) |
| 터미널 | TTY 및 파이프 모드 지원 |
| 인코딩 | UTF-8 |

---

## 9. 기술적 제약사항

### 9.1 의존성 목록

```toml
[project]
dependencies = [
    # 기존 SPEC 의존성 포함
    "click>=8.0",                 # CLI 프레임워크
    "rich>=13.0",                 # 터미널 출력 포매팅
    "pydantic>=2.0",              # 데이터 모델링
    "pyyaml>=6.0",                # YAML 설정 파일
    "python-dateutil>=2.8",       # 날짜 처리
]
```

### 9.2 ARM64 호환성

- Click: 순수 Python, 완전 호환
- Rich: 순수 Python, 완전 호환
- PyYAML: C 확장 있으나 폴백 가능

---

Version: 1.0.0
Last Updated: 2026-01-19
