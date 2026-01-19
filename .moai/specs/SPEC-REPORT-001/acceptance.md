---
id: SPEC-REPORT-001
type: acceptance
version: "1.0.0"
created: "2026-01-19"
updated: "2026-01-19"
author: "지니"
---

# SPEC-REPORT-001 인수 조건

## 1. 보고서 생성기 (ReportGenerator)

### 1.1 시나리오: 보고서 ID 생성

```gherkin
Feature: 보고서 ID 생성
  고유한 보고서 ID를 생성한다

  Scenario: ID 형식 준수
    When ReportGenerator.generate_id()를 호출한다
    Then 반환된 ID는 "RPT-YYYYMMDD-XXXX" 형식이어야 한다
    And 날짜 부분은 오늘 날짜여야 한다
    And 순번은 4자리 숫자여야 한다

  Scenario: 동일 날짜 내 순번 증가
    Given 오늘 날짜에 3개의 보고서가 이미 생성되었다
    When ReportGenerator.generate_id()를 호출한다
    Then 반환된 ID의 순번은 "0004"여야 한다

  Scenario: 날짜 변경 시 순번 리셋
    Given 어제 날짜에 100개의 보고서가 생성되었다
    And 현재 날짜가 오늘로 변경되었다
    When ReportGenerator.generate_id()를 호출한다
    Then 반환된 ID의 순번은 "0001"이어야 한다

  Scenario: ID 고유성 보장
    Given 1000개의 보고서를 연속 생성한다
    When 모든 ID를 수집한다
    Then 중복 ID가 없어야 한다
```

### 1.2 시나리오: 데이터 검증

```gherkin
Feature: 보고서 데이터 검증
  보고서 생성 전 데이터 유효성을 검증한다

  Scenario: 유효한 데이터 검증
    Given 모든 필수 필드가 포함된 ReportData가 있다
    And 모든 증거 참조가 유효하다
    When ReportGenerator.validate_data(data)를 호출한다
    Then ValidationResult.is_valid는 True여야 한다

  Scenario: 필수 필드 누락 검증
    Given evidence_list가 비어있는 ReportData가 있다
    When ReportGenerator.validate_data(data)를 호출한다
    Then ValidationResult.is_valid는 False여야 한다
    And errors에 "evidence_list is required"가 포함되어야 한다

  Scenario: 잘못된 참조 검증
    Given 존재하지 않는 evidence_id를 참조하는 데이터가 있다
    When ReportGenerator.validate_data(data)를 호출한다
    Then ValidationResult.is_valid는 False여야 한다
    And errors에 "Invalid evidence reference"가 포함되어야 한다
```

### 1.3 시나리오: 무결성 해시

```gherkin
Feature: 보고서 무결성 해시
  보고서의 SHA-256 해시를 계산한다

  Scenario: 해시 계산
    Given 완성된 Report 객체가 있다
    When ReportGenerator.compute_hash(report)를 호출한다
    Then 64자리 16진수 해시가 반환되어야 한다

  Scenario: 동일 데이터 동일 해시
    Given 동일한 내용의 두 보고서가 있다
    When 각각 compute_hash를 호출한다
    Then 두 해시값은 동일해야 한다

  Scenario: 데이터 변경 시 해시 변경
    Given 보고서의 해시가 계산되었다
    And 보고서 내용이 변경되었다
    When compute_hash를 다시 호출한다
    Then 새 해시값은 기존과 달라야 한다
```

---

## 2. 법적 증거 보고서 (LegalReportBuilder)

### 2.1 시나리오: 사건 정보 설정

```gherkin
Feature: 사건 정보 설정
  법적 보고서에 사건 정보를 설정한다

  Scenario: 완전한 사건 정보 설정
    Given LegalReportBuilder 인스턴스가 있다
    When set_case_info(case_number="2025가합12345", court_name="서울중앙지방법원", parties={"plaintiff": "홍길동", "defendant": "김철수"})를 호출한다
    Then 빌더가 반환되어야 한다 (fluent interface)
    And case_info가 설정되어야 한다

  Scenario: 선택적 정보만 설정
    Given LegalReportBuilder 인스턴스가 있다
    When set_case_info(case_number=None, court_name=None, parties={})를 호출한다
    Then 빌더가 반환되어야 한다
    And case_info는 기본값을 가져야 한다
```

### 2.2 시나리오: 증거 목록 추가

```gherkin
Feature: 증거 목록 추가
  법적 보고서에 증거 목록을 추가한다

  Background:
    Given 50개의 Evidence 객체가 있다
    And 중요도 분포는 HIGH 15개, MEDIUM 20개, LOW 15개이다

  Scenario: 중요도순 정렬
    When add_evidence_list(evidence_list, sort_by="importance")를 호출한다
    Then 증거는 HIGH -> MEDIUM -> LOW 순으로 정렬되어야 한다
    And 첫 번째 증거의 중요도는 "HIGH"여야 한다

  Scenario: 시간순 정렬
    When add_evidence_list(evidence_list, sort_by="timestamp")를 호출한다
    Then 증거는 오래된 것부터 최신 순으로 정렬되어야 한다

  Scenario: 카테고리별 정렬
    When add_evidence_list(evidence_list, sort_by="category")를 호출한다
    Then 증거는 카테고리 알파벳 순으로 그룹화되어야 한다
```

### 2.3 시나리오: 법적 보고서 빌드

```gherkin
Feature: 법적 보고서 빌드
  완성된 법적 증거 보고서를 생성한다

  Scenario: 완전한 법적 보고서 생성
    Given 사건 정보가 설정되었다
    And 30개의 증거가 추가되었다
    And 2개의 증거 체인이 추가되었다
    And 무결성 진술이 추가되었다
    When build()를 호출한다
    Then LegalReport 객체가 반환되어야 한다
    And report.report_type은 "LEGAL"이어야 한다
    And report.evidence_list는 30개 항목을 포함해야 한다
    And report.evidence_chains는 2개 항목을 포함해야 한다
    And report.integrity_statement가 존재해야 한다

  Scenario: 페이지 구분 자동 생성
    Given 100개 이상의 증거가 추가되었다
    When build()를 호출한다
    Then 보고서에 페이지 구분이 포함되어야 한다
    And 색인이 자동 생성되어야 한다
```

---

## 3. 타임라인 보고서 (TimelineReportBuilder)

### 3.1 시나리오: 날짜 범위 설정

```gherkin
Feature: 날짜 범위 설정
  타임라인 보고서의 분석 기간을 설정한다

  Scenario: 기간 설정
    Given TimelineReportBuilder 인스턴스가 있다
    When set_date_range(date(2025, 6, 1), date(2025, 12, 31))를 호출한다
    Then date_range가 설정되어야 한다
    And 시작일은 2025-06-01이어야 한다
    And 종료일은 2025-12-31이어야 한다

  Scenario: 잘못된 기간 설정
    Given TimelineReportBuilder 인스턴스가 있다
    When set_date_range(date(2025, 12, 31), date(2025, 6, 1))를 호출한다
    Then ValueError가 발생해야 한다
    And 에러 메시지는 "종료일이 시작일보다 빠를 수 없습니다"여야 한다
```

### 3.2 시나리오: 타임라인 이벤트 추가

```gherkin
Feature: 타임라인 이벤트 추가
  시간순 이벤트를 타임라인에 추가한다

  Background:
    Given 100개의 TimelineEvent가 있다
    And 이벤트는 2025년 6월~12월에 분포한다

  Scenario: 이벤트 시간순 정렬
    When add_timeline_events(events)를 호출한다
    Then 이벤트는 시간순으로 정렬되어야 한다
    And 첫 번째 이벤트는 가장 오래된 것이어야 한다

  Scenario: 날짜별 그룹화
    When add_timeline_events(events)를 호출한다
    And build()를 호출한다
    Then 이벤트는 날짜별로 그룹화되어야 한다
```

### 3.3 시나리오: 패턴 발생 표시

```gherkin
Feature: 패턴 발생 표시
  타임라인에 패턴 발생 시점을 표시한다

  Scenario: 패턴 발생 추가
    Given 30개의 PatternOccurrence가 있다
    And 패턴 유형은 GASLIGHTING, THREAT가 포함된다
    When add_pattern_occurrences(occurrences)를 호출한다
    Then 패턴 발생 정보가 타임라인에 추가되어야 한다
    And 각 패턴은 유형별로 구분되어야 한다

  Scenario: 반복 패턴 하이라이트
    Given 동일 패턴이 5회 이상 발생했다
    When build()를 호출한다
    Then 해당 패턴은 "반복 패턴" 섹션에 포함되어야 한다
```

### 3.4 시나리오: 월별 요약 생성

```gherkin
Feature: 월별 요약 생성
  6개월 이상 분석 시 월별 요약을 생성한다

  Scenario: 자동 월별 요약 생성
    Given 분석 기간이 2025년 6월~12월이다 (7개월)
    When build()를 호출한다
    Then 7개의 월별 요약이 생성되어야 한다
    And 각 월별 요약에 이벤트 수가 포함되어야 한다
    And 각 월별 요약에 패턴 분포가 포함되어야 한다

  Scenario: 단기간 분석 시 월별 요약 생략
    Given 분석 기간이 2025년 6월 1일~6월 15일이다 (15일)
    When build()를 호출한다
    Then 월별 요약은 생성되지 않아야 한다
```

---

## 4. 요약 보고서 (SummaryReportBuilder)

### 4.1 시나리오: 분석 개요 설정

```gherkin
Feature: 분석 개요 설정
  요약 보고서의 분석 개요를 설정한다

  Scenario: 완전한 개요 설정
    Given SummaryReportBuilder 인스턴스가 있다
    When set_analysis_overview(total_files=183, total_duration=7200.0, date_range=(date(2025, 6, 1), date(2025, 12, 31)))를 호출한다
    Then analysis_overview가 설정되어야 한다
    And total_files는 183이어야 한다
    And total_duration은 7200.0이어야 한다 (분 단위)
```

### 4.2 시나리오: 주요 발견사항 추가

```gherkin
Feature: 주요 발견사항 추가
  요약 보고서에 주요 발견사항을 추가한다

  Background:
    Given 10개의 KeyFinding이 있다
    And 심각도 분포는 CRITICAL 2개, HIGH 3개, MEDIUM 3개, LOW 2개이다

  Scenario: 발견사항 심각도순 정렬
    When add_key_findings(findings)를 호출한다
    And build()를 호출한다
    Then 발견사항은 심각도순으로 정렬되어야 한다
    And 첫 번째 발견사항의 심각도는 "CRITICAL"이어야 한다

  Scenario: 근거 증거 연결
    Given 각 발견사항에 supporting_evidence가 있다
    When build()를 호출한다
    Then 각 발견사항에 증거 참조가 포함되어야 한다
```

### 4.3 시나리오: 통계 데이터 추가

```gherkin
Feature: 통계 데이터 추가
  요약 보고서에 분석 통계를 추가한다

  Scenario: 완전한 통계 추가
    Given AnalysisStatistics 객체가 있다
    And total_files=183, total_evidence=250이다
    When add_statistics(stats)를 호출한다
    And build()를 호출한다
    Then statistics가 보고서에 포함되어야 한다
    And 카테고리별 분포가 포함되어야 한다
    And 중요도별 분포가 포함되어야 한다
    And 화자별 발언 수가 포함되어야 한다
```

### 4.4 시나리오: 권장 조치 추가

```gherkin
Feature: 권장 조치 추가
  요약 보고서에 권장 조치사항을 추가한다

  Scenario: 권장 조치 우선순위순 정렬
    Given 5개의 Recommendation이 있다
    And 우선순위는 URGENT 1개, HIGH 2개, MEDIUM 2개이다
    When add_recommendations(recommendations)를 호출한다
    And build()를 호출한다
    Then 권장 조치는 우선순위순으로 정렬되어야 한다
    And 첫 번째 권장 조치의 priority는 "URGENT"여야 한다

  Scenario: 위협 패턴 탐지 시 자동 권장
    Given 위협 패턴이 5회 이상 탐지되었다
    When build()를 호출한다
    Then "위협 관련 법적 대응 검토" 권장이 자동 추가되어야 한다
    And 해당 권장의 priority는 "URGENT"여야 한다
```

---

## 5. 보고서 내보내기 (ReportExporter)

### 5.1 시나리오: Markdown 내보내기

```gherkin
Feature: Markdown 내보내기
  보고서를 Markdown 형식으로 내보낸다

  Scenario: 기본 Markdown 내보내기
    Given 완성된 Report 객체가 있다
    When export_markdown(report, Path("./output/report.md"))를 호출한다
    Then Markdown 파일이 생성되어야 한다
    And 파일 인코딩은 UTF-8이어야 한다
    And 파일 내용에 report.title이 포함되어야 한다

  Scenario: 목차 포함
    Given ReportConfig.include_toc=True로 설정되었다
    When export_markdown(report, output_path)를 호출한다
    Then 파일에 목차(TOC)가 포함되어야 한다
    And 목차는 섹션 헤더와 연결되어야 한다
```

### 5.2 시나리오: HTML 내보내기

```gherkin
Feature: HTML 내보내기
  보고서를 HTML 형식으로 내보낸다

  Scenario: CSS 포함 HTML 내보내기
    Given 완성된 Report 객체가 있다
    When export_html(report, Path("./output/report.html"), include_css=True)를 호출한다
    Then HTML 파일이 생성되어야 한다
    And <style> 태그에 CSS가 포함되어야 한다
    And HTML은 유효한 문법이어야 한다

  Scenario: 인쇄 친화적 레이아웃
    Given ReportConfig.output_format="HTML"이다
    When export_html(report, output_path)를 호출한다
    Then @media print 스타일이 포함되어야 한다
    And 페이지 나눔 설정이 포함되어야 한다
```

### 5.3 시나리오: JSON 내보내기

```gherkin
Feature: JSON 내보내기
  보고서를 JSON 형식으로 내보낸다

  Scenario: 메타데이터 포함 JSON 내보내기
    Given 완성된 Report 객체가 있다
    When export_json(report, Path("./output/report.json"), include_metadata=True)를 호출한다
    Then JSON 파일이 생성되어야 한다
    And JSON에 "metadata" 필드가 포함되어야 한다
    And JSON은 유효한 형식이어야 한다

  Scenario: 메타데이터 제외 JSON 내보내기
    When export_json(report, output_path, include_metadata=False)를 호출한다
    Then JSON에 "metadata" 필드가 없어야 한다
```

### 5.4 시나리오: PDF 내보내기 (선택적)

```gherkin
Feature: PDF 내보내기
  보고서를 PDF 형식으로 내보낸다 (weasyprint 설치 시)

  Scenario: A4 PDF 내보내기
    Given weasyprint가 설치되어 있다
    And 완성된 Report 객체가 있다
    When export_pdf(report, Path("./output/report.pdf"), page_size="A4")를 호출한다
    Then PDF 파일이 생성되어야 한다
    And 페이지 크기는 A4여야 한다

  Scenario: weasyprint 미설치 시 대체
    Given weasyprint가 설치되어 있지 않다
    When export_pdf(report, output_path)를 호출한다
    Then ImportError가 발생해야 한다
    And 에러 메시지에 "PDF 기능을 사용하려면 weasyprint를 설치하세요"가 포함되어야 한다
```

---

## 6. PII 마스킹

### 6.1 시나리오: 개인정보 마스킹

```gherkin
Feature: 개인정보 마스킹
  보고서에서 개인 식별 정보를 마스킹한다

  Scenario: 전화번호 마스킹
    Given 텍스트에 "010-1234-5678"이 포함되어 있다
    And PII 마스킹이 활성화되어 있다
    When 보고서를 생성한다
    Then 전화번호가 "***-****-****"로 마스킹되어야 한다

  Scenario: 주민번호 마스킹
    Given 텍스트에 "850101-1234567"이 포함되어 있다
    And PII 마스킹이 활성화되어 있다
    When 보고서를 생성한다
    Then 주민번호가 "******-*******"로 마스킹되어야 한다

  Scenario: 마스킹 비활성화
    Given PII 마스킹이 비활성화되어 있다
    And 텍스트에 "010-1234-5678"이 포함되어 있다
    When 보고서를 생성한다
    Then 전화번호가 그대로 "010-1234-5678"로 표시되어야 한다
```

---

## 7. 성능 요구사항

### 7.1 시나리오: 대용량 처리

```gherkin
Feature: 대용량 보고서 생성 성능
  대량의 증거를 포함한 보고서 생성 성능을 검증한다

  Scenario: 100개 증거 보고서 생성
    Given 100개의 증거가 포함된 ReportData가 있다
    When 보고서 생성을 수행한다
    Then 처리 시간은 5초 이내여야 한다

  Scenario: 1000개 증거 보고서 생성
    Given 1000개의 증거가 포함된 ReportData가 있다
    When 보고서 생성을 수행한다
    Then 처리 시간은 30초 이내여야 한다

  Scenario: HTML 렌더링 성능
    Given 완성된 100페이지 보고서가 있다
    When export_html을 수행한다
    Then 렌더링 시간은 2초 이내여야 한다

  Scenario: PDF 생성 성능
    Given 완성된 100페이지 보고서가 있다
    And weasyprint가 설치되어 있다
    When export_pdf를 수행한다
    Then 생성 시간은 10초 이내여야 한다
```

---

## 8. 품질 게이트

### 8.1 테스트 커버리지

- [ ] 단위 테스트 커버리지 > 85%
- [ ] 통합 테스트 시나리오 전체 통과
- [ ] 성능 테스트 기준 충족

### 8.2 정확도 기준

- [ ] 타임스탬프 정확도 100%
- [ ] 증거 참조 정확도 100%
- [ ] 통계 계산 정확도 100%

### 8.3 형식 기준

- [ ] Markdown 문법 유효성 100%
- [ ] HTML W3C 유효성 검사 통과
- [ ] JSON 스키마 유효성 100%

### 8.4 보안 기준

- [ ] PII 마스킹 동작 100%
- [ ] 민감 정보 로깅 없음
- [ ] 출력 파일 권한 적절

### 8.5 성능 기준

- [ ] 100개 증거 보고서 생성 < 5초
- [ ] 1000개 증거 보고서 생성 < 30초
- [ ] HTML 렌더링 < 2초
- [ ] PDF 생성 < 10초 (100페이지)

---

## 9. 완료 체크리스트

### 9.1 기능 완료

- [ ] ReportGenerator 구현 완료
- [ ] LegalReportBuilder 구현 완료
- [ ] TimelineReportBuilder 구현 완료
- [ ] SummaryReportBuilder 구현 완료
- [ ] ReportExporter 구현 완료 (Markdown, HTML, JSON)
- [ ] PDF Exporter 구현 완료 (선택적)
- [ ] 모든 데이터 모델 정의 완료
- [ ] 템플릿 완성 (법적, 타임라인, 요약)
- [ ] PII 마스킹 구현 완료

### 9.2 테스트 완료

- [ ] 모든 단위 테스트 통과
- [ ] 모든 통합 테스트 통과
- [ ] 성능 테스트 통과
- [ ] 형식 유효성 테스트 통과

### 9.3 문서화 완료

- [ ] API 문서 작성
- [ ] 사용 가이드 작성
- [ ] 템플릿 커스터마이징 가이드

---

Version: 1.0.0
Last Updated: 2026-01-19
