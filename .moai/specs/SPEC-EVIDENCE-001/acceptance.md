---
id: SPEC-EVIDENCE-001
type: acceptance
version: "1.0.0"
created: "2026-01-18"
updated: "2026-01-18"
author: "지니"
---

# SPEC-EVIDENCE-001 인수 조건

## 1. 증거 추출 (EvidenceExtractor)

### 1.1 시나리오: 패턴에서 증거 추출

```gherkin
Feature: 패턴에서 증거 추출
  탐지된 패턴을 법적 증거 형식으로 변환한다

  Background:
    Given SPEC-TIMELINE-001의 PatternDetector가 패턴을 탐지했다
    And 탐지된 패턴은 GaslightingPattern, ThreatPattern 등이다
    And 원본 세그먼트 목록이 존재한다

  Scenario: 가스라이팅 패턴에서 증거 추출
    Given GaslightingPattern이 탐지되었다
    And pattern_type은 "DENIAL"이다
    And segment_ids는 ["seg-001", "seg-002"]이다
    When EvidenceExtractor.extract_from_pattern(pattern, segments)를 호출한다
    Then Evidence 객체가 반환되어야 한다
    And evidence.category는 "GASLIGHTING"이어야 한다
    And evidence.source_pattern_type은 "DENIAL"이어야 한다
    And evidence.segment_ids는 ["seg-001", "seg-002"]를 포함해야 한다

  Scenario: 위협 패턴에서 증거 추출
    Given ThreatPattern이 탐지되었다
    And threat_type은 "FINANCIAL_THREAT"이다
    And severity는 "HIGH"이다
    When EvidenceExtractor.extract_from_pattern(pattern, segments)를 호출한다
    Then Evidence 객체가 반환되어야 한다
    And evidence.category는 "THREAT"이어야 한다
    And evidence.importance는 "HIGH"이어야 한다

  Scenario: 배치 증거 추출
    Given 10개의 다양한 패턴이 탐지되었다
    When EvidenceExtractor.extract_batch(patterns, segments)를 호출한다
    Then 10개의 Evidence 객체가 반환되어야 한다
    And 모든 Evidence는 고유한 ID를 가져야 한다
```

### 1.2 시나리오: 증거 ID 생성

```gherkin
Feature: 증거 ID 생성
  고유한 증거 ID를 생성한다

  Scenario: ID 형식 준수
    When EvidenceExtractor.generate_id()를 호출한다
    Then 반환된 ID는 "EVD-YYYYMMDD-XXXX" 형식이어야 한다
    And 날짜 부분은 오늘 날짜여야 한다
    And 순번은 4자리 숫자여야 한다

  Scenario: 동일 날짜 내 순번 증가
    Given 오늘 날짜에 3개의 증거가 이미 생성되었다
    When EvidenceExtractor.generate_id()를 호출한다
    Then 반환된 ID의 순번은 "0004"여야 한다

  Scenario: 날짜 변경 시 순번 리셋
    Given 어제 날짜에 100개의 증거가 생성되었다
    And 현재 날짜가 오늘로 변경되었다
    When EvidenceExtractor.generate_id()를 호출한다
    Then 반환된 ID의 순번은 "0001"이어야 한다

  Scenario: ID 고유성 보장
    Given 1000개의 증거를 연속 생성한다
    When 모든 ID를 수집한다
    Then 중복 ID가 없어야 한다
```

### 1.3 시나리오: 중요도 할당

```gherkin
Feature: 중요도 할당
  증거에 중요도를 자동으로 할당한다

  Scenario: 반복 횟수 기반 HIGH 할당
    Given 가스라이팅 패턴이 5회 반복되었다
    When EvidenceExtractor.assign_importance(evidence, 5, "GASLIGHTING")를 호출한다
    Then 반환된 중요도는 "HIGH"여야 한다

  Scenario: 위험 패턴 자동 HIGH
    Given 패턴 유형이 "EXPLICIT_THREAT"이다
    And 발생 횟수가 1회이다
    When EvidenceExtractor.assign_importance(evidence, 1, "EXPLICIT_THREAT")를 호출한다
    Then 반환된 중요도는 "HIGH"여야 한다

  Scenario: 기본 MEDIUM 할당
    Given 패턴 유형이 "DENIAL"이다
    And 발생 횟수가 2회이다
    When EvidenceExtractor.assign_importance(evidence, 2, "DENIAL")를 호출한다
    Then 반환된 중요도는 "MEDIUM"이어야 한다

  Scenario: 기본 LOW 할당
    Given 패턴 유형이 "TRIVIALIZING"이다
    And 발생 횟수가 1회이다
    When EvidenceExtractor.assign_importance(evidence, 1, "TRIVIALIZING")를 호출한다
    Then 반환된 중요도는 "LOW"이어야 한다
```

---

## 2. 맥락 보존 (ContextPreserver)

### 2.1 시나리오: 전후 맥락 추출

```gherkin
Feature: 전후 맥락 추출
  증거 세그먼트의 전후 맥락을 추출한다

  Background:
    Given 10개의 연속된 세그먼트가 존재한다
    And 대상 세그먼트는 5번째 위치이다

  Scenario: 기본 맥락 추출 (전후 3개)
    When ContextPreserver.extract_context(segment, all_segments)를 호출한다
    Then context_before에 3개의 이전 발언이 포함되어야 한다
    And context_after에 3개의 이후 발언이 포함되어야 한다

  Scenario: 커스텀 범위 맥락 추출
    When ContextPreserver.extract_context(segment, all_segments, before_count=5, after_count=2)를 호출한다
    Then context_before에 5개의 이전 발언이 포함되어야 한다
    And context_after에 2개의 이후 발언이 포함되어야 한다

  Scenario: 시작 부분 맥락 추출
    Given 대상 세그먼트가 1번째 위치이다
    When ContextPreserver.extract_context(segment, all_segments, before_count=3)를 호출한다
    Then context_before는 0개의 발언을 포함해야 한다
    And context_after는 3개의 발언을 포함해야 한다

  Scenario: 끝 부분 맥락 추출
    Given 대상 세그먼트가 10번째(마지막) 위치이다
    When ContextPreserver.extract_context(segment, all_segments, after_count=3)를 호출한다
    Then context_before는 3개의 발언을 포함해야 한다
    And context_after는 0개의 발언을 포함해야 한다
```

### 2.2 시나리오: 대화 흐름 추출

```gherkin
Feature: 대화 흐름 추출
  증거 주변의 전체 대화 흐름을 추출한다

  Scenario: 전체 대화 흐름 추출
    Given 증거가 녹취 중간에 위치한다
    When ContextPreserver.get_conversation_flow(evidence, all_segments, window_size=10)를 호출한다
    Then 10개의 세그먼트가 반환되어야 한다
    And 세그먼트는 시간순으로 정렬되어야 한다
    And 화자 정보가 포함되어야 한다

  Scenario: 화자 전환 포함
    Given 대화 흐름 내에 화자 전환이 3회 발생했다
    When ContextPreserver.get_conversation_flow(evidence, all_segments)를 호출한다
    Then 반환된 세그먼트에 화자 전환이 반영되어야 한다
```

### 2.3 시나리오: 관련 세그먼트 연결

```gherkin
Feature: 관련 세그먼트 연결
  유사한 발언 세그먼트를 연결한다

  Scenario: 유사 발언 연결
    Given 증거 발언이 "그런 적 없어"이다
    And 다른 세그먼트에 "내가 언제 그랬어"가 존재한다
    And 유사도 임계값이 0.7이다
    When ContextPreserver.link_related_segments(evidence, all_segments, 0.7)를 호출한다
    Then 유사 발언의 세그먼트 ID가 연결되어야 한다

  Scenario: 임계값 미달 시 미연결
    Given 유사도가 0.5인 세그먼트가 존재한다
    And 유사도 임계값이 0.7이다
    When ContextPreserver.link_related_segments(evidence, all_segments, 0.7)를 호출한다
    Then 해당 세그먼트는 연결되지 않아야 한다
```

### 2.4 시나리오: 위치 정보 추출

```gherkin
Feature: 위치 정보 추출
  전체 녹취 내에서의 위치 정보를 추출한다

  Scenario: 상대적 위치 계산
    Given 녹취의 총 세그먼트 수가 100개이다
    And 대상 세그먼트가 30번째이다
    When ContextPreserver.get_position_in_transcript(segment, transcript)를 호출한다
    Then 상대적 위치는 30%여야 한다
    And 위치 라벨은 "초반부"여야 한다

  Scenario: 시간 정보 포함
    Given 세그먼트의 시작 시간이 15분 30초이다
    And 녹취 총 길이가 45분이다
    When ContextPreserver.get_position_in_transcript(segment, transcript)를 호출한다
    Then 시간 위치 정보가 포함되어야 한다
    And 상대적 시간은 약 34%여야 한다
```

---

## 3. 증거 검증 (EvidenceValidator)

### 3.1 시나리오: 무결성 검증

```gherkin
Feature: 무결성 검증
  증거의 무결성을 검증한다

  Background:
    Given 증거가 생성되어 있다
    And integrity_hash가 저장되어 있다

  Scenario: 무결성 검증 성공
    Given 증거 내용이 변경되지 않았다
    When EvidenceValidator.validate_integrity(evidence)를 호출한다
    Then ValidationResult.is_valid는 True여야 한다
    And ValidationResult.hash_valid는 True여야 한다

  Scenario: 무결성 검증 실패
    Given 증거의 content_sample이 변경되었다
    When EvidenceValidator.validate_integrity(evidence)를 호출한다
    Then ValidationResult.is_valid는 False여야 한다
    And ValidationResult.hash_valid는 False여야 한다
    And ValidationResult.issues에 "Hash mismatch"가 포함되어야 한다
```

### 3.2 시나리오: 타임스탬프 검증

```gherkin
Feature: 타임스탬프 검증
  증거의 타임스탬프가 원본과 일치하는지 검증한다

  Scenario: 타임스탬프 일치
    Given 증거의 timestamp가 "2025-07-15 14:30:00"이다
    And 원본 세그먼트의 시작 시간이 동일하다
    When EvidenceValidator.verify_timestamp(evidence, original_segment)를 호출한다
    Then True가 반환되어야 한다

  Scenario: 타임스탬프 불일치
    Given 증거의 timestamp가 "2025-07-15 14:30:00"이다
    And 원본 세그먼트의 시작 시간이 "2025-07-15 15:00:00"이다
    When EvidenceValidator.verify_timestamp(evidence, original_segment)를 호출한다
    Then False가 반환되어야 한다
```

### 3.3 시나리오: 중복 탐지

```gherkin
Feature: 중복 탐지
  중복된 증거를 탐지한다

  Scenario: 완전 중복 탐지
    Given 동일한 segment_ids와 content_sample을 가진 증거가 2개 존재한다
    When EvidenceValidator.detect_duplicates(new_evidence, existing_evidence)를 호출한다
    Then 기존 증거 ID가 반환되어야 한다
    And duplicate_found는 True여야 한다

  Scenario: 부분 중복 탐지
    Given segment_ids가 70% 일치하는 증거가 존재한다
    And 중복 임계값이 0.9이다
    When EvidenceValidator.detect_duplicates(new_evidence, existing_evidence)를 호출한다
    Then 중복으로 판정되지 않아야 한다

  Scenario: 중복 병합
    Given 3개의 중복 증거가 탐지되었다
    When EvidenceValidator.merge_duplicates(evidence_list)를 호출한다
    Then 1개의 병합된 Evidence가 반환되어야 한다
    And 병합된 증거는 모든 segment_ids를 포함해야 한다
    And related_evidence_ids에 원본 ID들이 포함되어야 한다
```

### 3.4 시나리오: 검증 보고서

```gherkin
Feature: 검증 보고서
  전체 증거에 대한 검증 보고서를 생성한다

  Scenario: 검증 보고서 생성
    Given 100개의 증거가 존재한다
    And 95개는 유효하고 5개는 무효이다
    When EvidenceValidator.get_validation_report(evidence_list)를 호출한다
    Then ValidationReport가 반환되어야 한다
    And total_evidence는 100이어야 한다
    And valid_count는 95여야 한다
    And invalid_count는 5여야 한다
    And integrity_score는 0.95여야 한다
```

---

## 4. 증거 내보내기 (EvidenceExporter)

### 4.1 시나리오: JSON 내보내기

```gherkin
Feature: JSON 내보내기
  증거를 JSON 형식으로 내보낸다

  Scenario: 전체 JSON 내보내기
    Given 50개의 증거가 존재한다
    When EvidenceExporter.export_json(evidence_list, output_path, include_context=True)를 호출한다
    Then JSON 파일이 생성되어야 한다
    And 파일 인코딩은 UTF-8이어야 한다
    And 모든 증거가 포함되어야 한다
    And 각 증거에 context_before, context_after가 포함되어야 한다

  Scenario: 맥락 제외 내보내기
    Given 50개의 증거가 존재한다
    When EvidenceExporter.export_json(evidence_list, output_path, include_context=False)를 호출한다
    Then context_before, context_after가 비어있어야 한다
```

### 4.2 시나리오: 법적 문서 내보내기

```gherkin
Feature: 법적 문서 내보내기
  증거를 법적 문서 형식으로 내보낸다

  Scenario: 한국 형사소송 형식
    Given 20개의 HIGH 중요도 증거가 존재한다
    When EvidenceExporter.export_legal_format(evidence_list, output_path, template="korean_criminal")를 호출한다
    Then 마크다운 문서가 생성되어야 한다
    And 문서에 사건 개요가 포함되어야 한다
    And 증거 목록이 중요도순으로 정렬되어야 한다
    And 각 증거에 발언 내용과 맥락이 포함되어야 한다

  Scenario: 한국 민사소송 형식
    When EvidenceExporter.export_legal_format(evidence_list, output_path, template="korean_civil")를 호출한다
    Then 민사소송 형식의 문서가 생성되어야 한다
```

### 4.3 시나리오: 증거 체인 내보내기

```gherkin
Feature: 증거 체인 내보내기
  증거 체인(연속성) 문서를 생성한다

  Scenario: 시간순 체인 내보내기
    Given 동일 화자의 5개 연속 증거가 존재한다
    And 증거들이 시간순으로 연결되어 있다
    When EvidenceExporter.export_chain_of_custody(evidence_list, output_path)를 호출한다
    Then 체인 문서가 생성되어야 한다
    And 시간순 정렬된 증거 목록이 포함되어야 한다
    And 각 증거 간의 시간 간격이 표시되어야 한다
```

### 4.4 시나리오: 필터링

```gherkin
Feature: 증거 필터링
  다양한 조건으로 증거를 필터링한다

  Scenario: 중요도 필터링
    Given 100개의 증거 중 HIGH 30개, MEDIUM 40개, LOW 30개가 존재한다
    When EvidenceExporter.filter_by_importance(evidence_list, "HIGH")를 호출한다
    Then 30개의 증거가 반환되어야 한다
    And 모든 증거의 중요도는 "HIGH"여야 한다

  Scenario: 카테고리 필터링
    Given 다양한 카테고리의 증거가 존재한다
    When EvidenceExporter.filter_by_category(evidence_list, ["GASLIGHTING", "THREAT"])를 호출한다
    Then 반환된 증거는 GASLIGHTING 또는 THREAT 카테고리여야 한다

  Scenario: 날짜 범위 필터링
    Given 2025년 6월부터 12월까지의 증거가 존재한다
    When EvidenceExporter.filter_by_date_range(evidence_list, date(2025, 7, 1), date(2025, 8, 31))를 호출한다
    Then 반환된 증거는 2025년 7월~8월 범위 내여야 한다
```

---

## 5. 증거 체인 시스템

### 5.1 시나리오: 체인 자동 탐지

```gherkin
Feature: 체인 자동 탐지
  관련 증거들의 체인을 자동으로 탐지한다

  Scenario: 시간적 체인 탐지
    Given 동일 화자가 7일 내에 동일 패턴을 5회 반복했다
    When 체인 탐지를 수행한다
    Then TEMPORAL 유형의 EvidenceChain이 생성되어야 한다
    And total_occurrences는 5여야 한다

  Scenario: 패턴 체인 탐지
    Given 동일 패턴(DENIAL)이 10회 이상 탐지되었다
    When 체인 탐지를 수행한다
    Then PATTERN 유형의 EvidenceChain이 생성되어야 한다
    And pattern_type은 "DENIAL"이어야 한다

  Scenario: 심각도 자동 할당
    Given 위협 패턴이 3회 이상 연속되었다
    And 패턴 유형이 "EXPLICIT_THREAT"이다
    When 체인이 생성된다
    Then severity는 "CRITICAL"이어야 한다
```

---

## 6. 성능 요구사항

### 6.1 시나리오: 대용량 처리

```gherkin
Feature: 대용량 처리 성능
  대량의 증거 처리 성능을 검증한다

  Scenario: 증거 추출 성능
    Given 1000개의 패턴이 탐지되었다
    When EvidenceExtractor.extract_batch를 수행한다
    Then 처리 시간은 2초 이내여야 한다
    And 처리량은 500 patterns/second 이상이어야 한다

  Scenario: 맥락 추출 성능
    Given 1000개의 세그먼트에서 맥락을 추출한다
    When ContextPreserver.extract_context를 1000회 수행한다
    Then 평균 처리 시간은 10ms 이내여야 한다

  Scenario: 검증 성능
    Given 500개의 증거를 검증한다
    When EvidenceValidator.validate_integrity를 수행한다
    Then 평균 처리 시간은 50ms 이내여야 한다

  Scenario: 내보내기 성능
    Given 100개의 증거를 내보낸다
    When EvidenceExporter.export_legal_format를 수행한다
    Then 처리 시간은 5초 이내여야 한다
```

---

## 7. 품질 게이트

### 7.1 테스트 커버리지

- [ ] 단위 테스트 커버리지 > 85%
- [ ] 통합 테스트 시나리오 전체 통과
- [ ] 성능 테스트 기준 충족

### 7.2 정확도 기준

- [ ] 중복 탐지 정확도 > 95%
- [ ] 카테고리 분류 정확도 > 90%
- [ ] 타임스탬프 일치율 100%

### 7.3 무결성 기준

- [ ] 모든 증거 해시 검증 가능
- [ ] 원본 참조 100% 유지
- [ ] 내보내기 후 불변성 보장

### 7.4 성능 기준

- [ ] 증거 추출 > 500 patterns/second
- [ ] 맥락 추출 < 10ms per segment
- [ ] 검증 처리 < 50ms per evidence
- [ ] 100개 증거 내보내기 < 5초

---

## 8. 완료 체크리스트

### 8.1 기능 완료

- [ ] EvidenceExtractor 구현 완료
- [ ] ContextPreserver 구현 완료
- [ ] EvidenceValidator 구현 완료
- [ ] EvidenceExporter 구현 완료
- [ ] 모든 데이터 모델 정의 완료
- [ ] 법적 문서 템플릿 완성

### 8.2 테스트 완료

- [ ] 모든 단위 테스트 통과
- [ ] 모든 통합 테스트 통과
- [ ] 성능 테스트 통과
- [ ] 법적 형식 검증 완료

### 8.3 문서화 완료

- [ ] API 문서 작성
- [ ] 사용 가이드 작성
- [ ] 법적 문서 템플릿 가이드

---

Version: 1.0.0
Last Updated: 2026-01-18
