# SPEC-CLI-001 인수 조건

## 태그 추적

- **SPEC ID**: SPEC-CLI-001
- **관련 SPEC**: SPEC-CORE-001, SPEC-IO-001, SPEC-TIMELINE-001, SPEC-EVIDENCE-001, SPEC-REPORT-001, SPEC-SEARCH-001
- **상태**: 계획 단계

---

## 1. 테스트 시나리오

### TC-001: CLI 기본 도움말 표시

**Given** forensic CLI가 설치된 상태이고
**And** 시스템 PATH에 등록되어 있을 때
**When** 사용자가 `forensic --help`를 실행하면
**Then** 사용 가능한 모든 명령 목록이 표시되어야 하고
**And** 각 명령에 대한 간단한 설명이 포함되어야 하고
**And** 글로벌 옵션 (`--verbose`, `--quiet`, `--config`)이 표시되어야 한다

---

### TC-002: CLI 버전 정보 표시

**Given** forensic CLI가 설치된 상태일 때
**When** 사용자가 `forensic --version`을 실행하면
**Then** "forensic, version 0.1.0" 형식의 버전 정보가 표시되어야 한다

---

### TC-003: forensic analyze 기본 실행

**Given** 183개의 녹취 파일이 `./data/recordings/` 디렉토리에 존재하고
**And** 출력 디렉토리가 존재하지 않을 때
**When** 사용자가 `forensic analyze -i ./data/recordings -o ./data/output`을 실행하면
**Then** 출력 디렉토리가 자동으로 생성되어야 하고
**And** 진행률 표시줄이 표시되어야 하고
**And** 모든 파일이 분석되어야 하고
**And** 분석 완료 시 요약 패널이 표시되어야 한다

---

### TC-004: forensic analyze 진행률 표시

**Given** 분석할 파일이 50개 이상 존재할 때
**When** 사용자가 `forensic analyze -i ./data -o ./output`을 실행하면
**Then** Rich 진행률 표시줄이 나타나야 하고
**And** 현재 처리 중인 파일 이름이 표시되어야 하고
**And** 완료된 파일 수 / 전체 파일 수가 표시되어야 하고
**And** 예상 남은 시간이 표시되어야 한다

---

### TC-005: forensic analyze Ctrl+C 중단

**Given** 분석이 진행 중인 상태일 때
**When** 사용자가 Ctrl+C를 입력하면
**Then** "중단 요청됨" 메시지가 표시되어야 하고
**And** 현재 처리 중인 파일 완료 후 안전하게 종료되어야 하고
**And** 부분 결과가 `.forensic/partial_results/`에 저장되어야 하고
**And** 재개 가능한 상태 파일이 생성되어야 한다

---

### TC-006: forensic analyze 캐시 사용

**Given** 이전에 분석이 완료되어 캐시가 존재하고
**And** 파일이 변경되지 않았을 때
**When** 사용자가 `forensic analyze -i ./data -o ./output`을 실행하면
**Then** "캐시된 결과를 사용합니다" 메시지가 표시되어야 하고
**And** 재분석 없이 즉시 완료되어야 하고
**And** 캐시 히트 수가 요약에 표시되어야 한다

---

### TC-007: forensic analyze 강제 재분석

**Given** 캐시가 존재하는 상태일 때
**When** 사용자가 `forensic analyze -i ./data -o ./output --force`를 실행하면
**Then** 캐시를 무시하고 전체 재분석을 수행해야 하고
**And** 기존 캐시가 새 결과로 갱신되어야 한다

---

### TC-008: forensic search 기본 검색

**Given** 분석이 완료되어 검색 인덱스가 구축된 상태이고
**And** "가스라이팅"이라는 단어가 포함된 세그먼트가 존재할 때
**When** 사용자가 `forensic search "가스라이팅"`을 실행하면
**Then** 일치하는 결과가 테이블 형식으로 표시되어야 하고
**And** 일치 부분이 하이라이트되어야 하고
**And** 결과 수와 검색 시간이 표시되어야 한다

---

### TC-009: forensic search 화자 필터

**Given** "신동식"과 "신기연" 두 화자의 데이터가 존재할 때
**When** 사용자가 `forensic search "위협" --speaker 신동식`을 실행하면
**Then** "신동식" 화자의 결과만 반환되어야 하고
**And** 모든 결과의 화자 열이 "신동식"이어야 한다

---

### TC-010: forensic search 날짜 범위 필터

**Given** 2025년 6월부터 12월까지의 데이터가 존재할 때
**When** 사용자가 `forensic search "키워드" --date 2025-07-01:2025-08-31`을 실행하면
**Then** 해당 기간 내의 결과만 반환되어야 하고
**And** 결과의 날짜가 모두 지정 범위 내에 있어야 한다

---

### TC-011: forensic search 복합 필터

**Given** 다양한 화자, 날짜, 중요도의 데이터가 존재할 때
**When** 사용자가 `forensic search "키워드" --speaker 신동식 --date 2025-07-01:2025-08-31 --importance HIGH`을 실행하면
**Then** 모든 필터 조건을 만족하는 결과만 반환되어야 하고
**And** 필터 적용 여부가 출력에 표시되어야 한다

---

### TC-012: forensic search 결과 내보내기

**Given** 검색 결과가 존재할 때
**When** 사용자가 `forensic search "키워드" -o results.json --format json`을 실행하면
**Then** 결과가 JSON 파일로 저장되어야 하고
**And** 파일이 유효한 JSON 형식이어야 하고
**And** 모든 결과 데이터가 포함되어야 한다

---

### TC-013: forensic search 결과 없음

**Given** 검색 인덱스가 존재하는 상태일 때
**When** 사용자가 존재하지 않는 키워드로 검색하면
**Then** "검색 결과가 없습니다" 메시지가 표시되어야 하고
**And** 검색어 제안이 표시될 수 있다

---

### TC-014: forensic report legal 보고서 생성

**Given** 분석이 완료되어 증거 데이터가 존재할 때
**When** 사용자가 `forensic report --type legal -o legal_report.md`를 실행하면
**Then** 법적 증거 보고서가 Markdown 형식으로 생성되어야 하고
**And** 보고서에 증거 목록, 시계열, 분석 결과가 포함되어야 하고
**And** 법정 제출에 적합한 형식이어야 한다

---

### TC-015: forensic report timeline 보고서 생성

**Given** 시계열 분석이 완료된 상태일 때
**When** 사용자가 `forensic report --type timeline -o timeline.html -f html`을 실행하면
**Then** HTML 형식의 타임라인 보고서가 생성되어야 하고
**And** 시각적 타임라인이 포함되어야 하고
**And** 브라우저에서 열 수 있어야 한다

---

### TC-016: forensic report 다양한 형식 지원

**Given** 분석이 완료된 상태일 때
**When** 사용자가 각각 `--format markdown`, `--format html`, `--format json` 옵션으로 보고서를 생성하면
**Then** 각 형식에 맞는 파일이 생성되어야 하고
**And** 각 파일이 해당 형식의 유효한 구문을 가져야 한다

---

### TC-017: forensic timeline 기본 표시

**Given** 시계열 데이터가 존재할 때
**When** 사용자가 `forensic timeline`을 실행하면
**Then** 텍스트 기반 타임라인이 표시되어야 하고
**And** 날짜별 이벤트가 시간순으로 정렬되어야 하고
**And** 주요 패턴이 표시되어야 한다

---

### TC-018: forensic timeline 날짜 범위 필터

**Given** 6개월 분량의 시계열 데이터가 존재할 때
**When** 사용자가 `forensic timeline --start 2025-07-01 --end 2025-08-31`을 실행하면
**Then** 지정된 날짜 범위의 이벤트만 표시되어야 하고
**And** 범위 외 데이터가 포함되지 않아야 한다

---

### TC-019: forensic timeline 패턴 필터

**Given** 다양한 패턴 유형의 이벤트가 존재할 때
**When** 사용자가 `forensic timeline --pattern GASLIGHTING --pattern THREAT`을 실행하면
**Then** 지정된 패턴의 이벤트만 표시되어야 하고
**And** 다른 패턴 유형은 제외되어야 한다

---

### TC-020: forensic timeline HTML 내보내기

**Given** 시계열 데이터가 존재할 때
**When** 사용자가 `forensic timeline -o timeline.html -f html`을 실행하면
**Then** HTML 파일이 생성되어야 하고
**And** 인터랙티브 타임라인이 포함되어야 하고
**And** 브라우저에서 정상적으로 표시되어야 한다

---

### TC-021: forensic config 현재 설정 표시

**Given** 설정 파일이 존재할 때
**When** 사용자가 `forensic config --show`를 실행하면
**Then** 현재 설정이 테이블 형식으로 표시되어야 하고
**And** 모든 설정 항목과 값이 표시되어야 한다

---

### TC-022: forensic config 설정 값 조회

**Given** 설정 파일이 존재할 때
**When** 사용자가 `forensic config --get search.timeout`을 실행하면
**Then** 해당 설정 값만 출력되어야 한다

---

### TC-023: forensic config 설정 값 변경

**Given** 설정 파일이 존재할 때
**When** 사용자가 `forensic config --set search.timeout 60`을 실행하면
**Then** 설정이 변경되어야 하고
**And** 변경 확인 메시지가 표시되어야 하고
**And** 설정 파일이 업데이트되어야 한다

---

### TC-024: forensic config 시스템 정보 표시

**Given** DGX Spark 환경에서 실행 중일 때
**When** 사용자가 `forensic config --system-info`를 실행하면
**Then** 시스템 정보가 패널 형식으로 표시되어야 하고
**And** CPU, GPU, 메모리, CUDA 버전 정보가 포함되어야 하고
**And** 현재 메모리 사용량이 표시되어야 한다

---

### TC-025: forensic config 기본값 초기화

**Given** 설정이 변경된 상태일 때
**When** 사용자가 `forensic config --reset`을 실행하면
**Then** 확인 프롬프트가 표시되어야 하고
**And** 확인 후 모든 설정이 기본값으로 초기화되어야 하고
**And** 백업 파일이 생성되어야 한다

---

### TC-026: 설정 파일 자동 생성

**Given** 설정 파일이 존재하지 않는 상태일 때
**When** 사용자가 임의의 forensic 명령을 실행하면
**Then** 기본 설정 파일이 `~/.forensic/config.yaml`에 생성되어야 하고
**And** 기본 설정으로 명령이 실행되어야 한다

---

### TC-027: 상세 로그 출력

**Given** forensic CLI가 정상 동작할 때
**When** 사용자가 `forensic --verbose analyze -i ./data -o ./output`을 실행하면
**Then** 상세 로그가 출력되어야 하고
**And** 각 처리 단계의 정보가 표시되어야 하고
**And** 디버깅에 유용한 정보가 포함되어야 한다

---

### TC-028: 최소 출력 모드

**Given** forensic CLI가 정상 동작할 때
**When** 사용자가 `forensic --quiet analyze -i ./data -o ./output`을 실행하면
**Then** 필수 출력만 표시되어야 하고
**And** 진행률 표시줄이 표시되지 않아야 하고
**And** 최종 결과만 출력되어야 한다

---

### TC-029: 오류 메시지 표시

**Given** 존재하지 않는 입력 디렉토리가 지정되었을 때
**When** 사용자가 `forensic analyze -i /nonexistent -o ./output`을 실행하면
**Then** 한국어 오류 메시지가 표시되어야 하고
**And** 오류 원인이 명확히 설명되어야 하고
**And** 해결 방법이 제안되어야 한다

---

### TC-030: 파일 덮어쓰기 확인

**Given** 출력 파일이 이미 존재할 때
**When** 사용자가 동일한 경로로 출력을 요청하면
**Then** 덮어쓰기 확인 프롬프트가 표시되어야 하고
**And** 사용자가 거부하면 작업이 취소되어야 한다

---

## 2. 품질 게이트

### 2.1 코드 품질

| 항목 | 기준 | 측정 방법 |
|------|------|-----------|
| 테스트 커버리지 | >= 85% | pytest --cov |
| 린트 오류 | 0개 | ruff check |
| 타입 검사 오류 | 0개 | pyright |
| 코드 복잡도 | <= 15 (함수당) | ruff --select=C901 |

### 2.2 성능 기준

| 항목 | 기준 | 측정 방법 |
|------|------|-----------|
| CLI 시작 시간 | < 1초 | 벤치마크 |
| 분석 처리량 | > 10 파일/분 | 벤치마크 |
| 검색 응답 시간 | < 500ms | 벤치마크 |
| 메모리 사용량 | < 2GB | memory_profiler |
| 진행률 업데이트 | > 10Hz | 측정 |

### 2.3 사용성 기준

| 항목 | 기준 |
|------|------|
| 도움말 완성도 | 모든 명령/옵션에 설명 존재 |
| 오류 메시지 품질 | 원인 + 해결 방법 포함 |
| 진행률 표시 | 모든 장시간 작업에 표시 |
| 취소 지원 | Ctrl+C 안전 중단 |

### 2.4 호환성 기준

| 항목 | 기준 |
|------|------|
| Python 버전 | 3.10, 3.11, 3.12 지원 |
| 플랫폼 | Linux ARM64, macOS ARM64 |
| 터미널 | TTY, 파이프 모드 지원 |

---

## 3. 완료 체크리스트

### 3.1 기능 완료

- [ ] `forensic` 메인 명령 그룹 구현 완료
- [ ] `forensic analyze` 명령 구현 완료
- [ ] `forensic search` 명령 구현 완료
- [ ] `forensic report` 명령 구현 완료
- [ ] `forensic timeline` 명령 구현 완료
- [ ] `forensic config` 명령 구현 완료
- [ ] 설정 파일 시스템 구현 완료
- [ ] 캐시 시스템 구현 완료
- [ ] 시그널 핸들링 구현 완료
- [ ] Rich 출력 시스템 구현 완료

### 3.2 SPEC 통합 완료

- [ ] SPEC-CORE-001 통합 완료
- [ ] SPEC-IO-001 통합 완료
- [ ] SPEC-TIMELINE-001 통합 완료
- [ ] SPEC-EVIDENCE-001 통합 완료
- [ ] SPEC-REPORT-001 통합 완료
- [ ] SPEC-SEARCH-001 통합 완료

### 3.3 테스트 완료

- [ ] 모든 테스트 시나리오 (TC-001 ~ TC-030) 통과
- [ ] 단위 테스트 작성 및 통과
- [ ] 통합 테스트 작성 및 통과
- [ ] 성능 테스트 기준 충족
- [ ] 엔드투엔드 테스트 통과

### 3.4 문서화 완료

- [ ] CLI 사용 가이드 작성
- [ ] 명령별 상세 문서 작성
- [ ] 설정 파일 레퍼런스 작성
- [ ] 예제 스크립트 작성

### 3.5 품질 완료

- [ ] 코드 리뷰 완료
- [ ] 린트/타입 검사 통과
- [ ] 테스트 커버리지 85% 이상
- [ ] ARM64 호환성 검증 완료

---

## 4. 검증 방법

### 4.1 자동화 테스트

```bash
# 전체 테스트 실행
pytest tests/cli/ -v --cov=forensic.cli --cov-report=html

# 통합 테스트
pytest tests/cli/test_integration.py -v

# 성능 테스트
pytest tests/cli/test_performance.py -v --benchmark-enable
```

### 4.2 수동 검증

1. **도움말 검증**
   ```bash
   forensic --help
   forensic analyze --help
   forensic search --help
   forensic report --help
   forensic timeline --help
   forensic config --help
   ```

2. **기본 워크플로우 검증**
   ```bash
   # 분석
   forensic analyze -i ./test_data -o ./output

   # 검색
   forensic search "가스라이팅" --speaker 신동식

   # 보고서
   forensic report --type legal -o report.md

   # 타임라인
   forensic timeline --start 2025-07-01 --end 2025-08-31

   # 설정
   forensic config --show
   forensic config --system-info
   ```

3. **오류 시나리오 검증**
   ```bash
   # 존재하지 않는 디렉토리
   forensic analyze -i /nonexistent -o ./output

   # 잘못된 옵션
   forensic search --invalid-option

   # 권한 없는 디렉토리
   forensic analyze -i ./data -o /root/output
   ```

### 4.3 회귀 테스트

- 기존 SPEC 기능에 영향 없음 확인
- 모든 SPEC 모듈 통합 후 기능 검증
- 캐시 시스템 무결성 확인

---

## 5. 엔드투엔드 워크플로우 테스트

### TC-E2E-001: 전체 분석 워크플로우

**Given** 183개의 원본 녹취 파일이 존재할 때

**When** 다음 워크플로우를 실행하면:
1. `forensic analyze -i ./data/recordings -o ./data/output`
2. `forensic search "가스라이팅" --importance HIGH`
3. `forensic report --type legal -o ./reports/evidence.md`
4. `forensic timeline -o ./reports/timeline.html -f html`

**Then** 각 단계가 순차적으로 성공해야 하고
**And** 최종 보고서와 타임라인 파일이 생성되어야 하고
**And** 전체 워크플로우가 오류 없이 완료되어야 한다

---

### TC-E2E-002: 중단 및 재개 워크플로우

**Given** 분석이 50% 진행된 상태에서 Ctrl+C로 중단되었을 때

**When** 사용자가 동일한 분석 명령을 재실행하면

**Then** 중단 지점부터 분석이 재개되어야 하고
**And** 이미 처리된 파일은 건너뛰어야 하고
**And** 최종 결과는 완전한 분석 결과와 동일해야 한다

---

Version: 1.0.0
Last Updated: 2026-01-19
