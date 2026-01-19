---
id: SPEC-TIMELINE-001
type: acceptance
version: "1.0.0"
created: "2026-01-18"
updated: "2026-01-18"
author: "지니"
---

# SPEC-TIMELINE-001 인수 조건

## 1. 시계열 분석 (TimelineBuilder)

### 1.1 시나리오: 녹취 파일 시간순 정렬

```gherkin
Feature: 녹취 파일 시간순 정렬
  녹취 파일을 날짜 기준으로 시간순 정렬하여 타임라인을 구축한다

  Background:
    Given 분석 대상 디렉토리에 183개의 녹취 파일이 존재한다
    And 파일명 형식은 "YYYYMMDD_HHMMSS.txt" 또는 "YYYY-MM-DD_description.txt"이다
    And 분석 기간은 2025년 6월부터 2025년 12월까지이다

  Scenario: 전체 파일 시간순 정렬
    When TimelineBuilder.build()를 호출한다
    Then 반환된 Timeline의 transcripts는 날짜 오름차순으로 정렬되어야 한다
    And 첫 번째 녹취의 날짜는 2025년 6월 이후여야 한다
    And 마지막 녹취의 날짜는 2025년 12월 이전이어야 한다

  Scenario: 특정 날짜 조회
    Given "2025-07-15" 날짜에 3개의 녹취 파일이 존재한다
    When TimelineBuilder.get_by_date(date(2025, 7, 15))를 호출한다
    Then 3개의 Transcript가 반환되어야 한다
    And 모든 Transcript의 날짜는 2025-07-15여야 한다

  Scenario: 날짜 범위 조회
    Given 2025년 8월에 25개의 녹취 파일이 존재한다
    When TimelineBuilder.get_by_range(date(2025, 8, 1), date(2025, 8, 31))를 호출한다
    Then 25개의 Transcript가 반환되어야 한다
    And 모든 Transcript의 날짜는 2025년 8월 내여야 한다
```

### 1.2 시나리오: 기간별 그룹화

```gherkin
Feature: 기간별 그룹화
  녹취 파일을 일별/주별/월별로 그룹화한다

  Scenario: 월별 그룹화
    Given 2025년 6월부터 12월까지 녹취 파일이 분포되어 있다
    When TimelineBuilder.group_by_period("month")를 호출한다
    Then 최소 6개의 그룹이 반환되어야 한다
    And 각 그룹의 키는 "2025-06", "2025-07" 형식이어야 한다
    And 모든 Transcript는 해당 월에 속해야 한다

  Scenario: 주별 그룹화
    Given 2025년 7월에 15개의 녹취 파일이 존재한다
    When TimelineBuilder.group_by_period("week")를 호출한다
    Then 4~5개의 그룹이 반환되어야 한다
    And 각 그룹의 Transcript 날짜는 같은 주에 속해야 한다

  Scenario: 일별 그룹화
    Given 2025년 7월 15일에 3개의 녹취 파일이 존재한다
    When TimelineBuilder.group_by_period("day")를 호출한다
    Then "2025-07-15" 그룹에 3개의 Transcript가 있어야 한다
```

### 1.3 시나리오: 이벤트 마커 추출

```gherkin
Feature: 이벤트 마커 추출
  시계열에서 주요 이벤트를 자동으로 추출한다

  Scenario: 주요 이벤트 추출
    Given 타임라인이 구축되어 있다
    When TimelineBuilder.extract_events()를 호출한다
    Then TimelineEvent 목록이 반환되어야 한다
    And 각 이벤트는 id, date, event_type, description을 포함해야 한다
    And 이벤트는 중요도(HIGH/MEDIUM/LOW)가 할당되어야 한다
```

---

## 2. 화자 분리 (SpeakerAnalyzer)

### 2.1 시나리오: 화자 식별

```gherkin
Feature: 화자 식별
  세그먼트에서 화자를 식별하고 정규화한다

  Background:
    Given 등록된 화자는 "신동식"과 "신기연"이다
    And "신동식"의 별칭은 ["동식", "신씨", "아버지"]이다
    And "신기연"의 별칭은 ["기연", "신기연씨"]이다

  Scenario: 정규 이름으로 화자 식별
    Given 세그먼트의 speaker 필드가 "신동식"이다
    When SpeakerAnalyzer.identify_speaker(segment)를 호출한다
    Then "신동식"이 반환되어야 한다

  Scenario: 별칭으로 화자 식별
    Given 세그먼트의 speaker 필드가 "동식"이다
    When SpeakerAnalyzer.identify_speaker(segment)를 호출한다
    Then "신동식"이 반환되어야 한다

  Scenario: 별칭 정규화
    When SpeakerAnalyzer.normalize_alias("기연")를 호출한다
    Then "신기연"이 반환되어야 한다

  Scenario: 미등록 화자 처리
    Given 세그먼트의 speaker 필드가 "홍길동"이다
    When SpeakerAnalyzer.identify_speaker(segment)를 호출한다
    Then "UNKNOWN"이 반환되어야 한다
```

### 2.2 시나리오: 화자 통계

```gherkin
Feature: 화자 통계
  화자별 발언 통계를 계산한다

  Scenario: 개별 화자 통계 조회
    Given 100개의 세그먼트가 분석되었다
    When SpeakerAnalyzer.get_statistics("신동식")를 호출한다
    Then SpeakerStatistics가 반환되어야 한다
    And total_segments는 0보다 커야 한다
    And total_duration_seconds는 0보다 커야 한다
    And speaking_ratio는 0.0 ~ 1.0 사이여야 한다

  Scenario: 전체 화자 통계 조회
    Given 100개의 세그먼트가 분석되었다
    When SpeakerAnalyzer.get_all_statistics()를 호출한다
    Then 최소 2명의 화자 통계가 반환되어야 한다
    And 모든 화자의 speaking_ratio 합은 1.0이어야 한다

  Scenario: 발언 비율 계산
    Given "신동식"이 60분, "신기연"이 40분 발언했다
    When SpeakerAnalyzer.get_speaking_ratio()를 호출한다
    Then "신동식"의 비율은 약 0.6이어야 한다
    Then "신기연"의 비율은 약 0.4여야 한다
```

### 2.3 시나리오: 화자 전환 분석

```gherkin
Feature: 화자 전환 분석
  화자 전환 패턴을 분석한다

  Scenario: 화자 전환 이벤트 기록
    Given 연속된 세그먼트에서 화자가 "신동식" -> "신기연"으로 변경되었다
    When SpeakerAnalyzer.analyze_turn_taking(segments)를 호출한다
    Then TurnTakingEvent가 기록되어야 한다
    And from_speaker는 "신동식"이어야 한다
    And to_speaker는 "신기연"이어야 한다

  Scenario: 끼어들기 감지
    Given "신동식" 세그먼트가 끝나기 전에 "신기연" 세그먼트가 시작되었다
    When SpeakerAnalyzer.analyze_turn_taking(segments)를 호출한다
    Then TurnTakingEvent의 interruption은 True여야 한다
    And overlap_seconds는 0보다 커야 한다
```

---

## 3. 패턴 인식 (PatternDetector)

### 3.1 시나리오: 가스라이팅 탐지

```gherkin
Feature: 가스라이팅 탐지
  가스라이팅 패턴을 탐지한다

  Scenario: 부정(DENIAL) 패턴 탐지
    Given 세그먼트 내용이 "내가 그런 적 없어. 무슨 소리야."이다
    When PatternDetector.detect_gaslighting(segments)를 호출한다
    Then GaslightingPattern이 반환되어야 한다
    And pattern_type은 "DENIAL"이어야 한다
    And confidence는 0.7 이상이어야 한다

  Scenario: 기억 왜곡(COUNTERING) 패턴 탐지
    Given 세그먼트 내용이 "네가 잘못 기억하는 거야. 착각하고 있어."이다
    When PatternDetector.detect_gaslighting(segments)를 호출한다
    Then GaslightingPattern이 반환되어야 한다
    And pattern_type은 "COUNTERING"이어야 한다

  Scenario: 축소(TRIVIALIZING) 패턴 탐지
    Given 세그먼트 내용이 "별거 아니야. 너무 예민해."이다
    When PatternDetector.detect_gaslighting(segments)를 호출한다
    Then GaslightingPattern이 반환되어야 한다
    And pattern_type은 "TRIVIALIZING"이어야 한다

  Scenario: 맥락 정보 포함
    Given 가스라이팅 패턴이 탐지되었다
    Then context_before에 이전 맥락이 포함되어야 한다
    And context_after에 이후 맥락이 포함되어야 한다
```

### 3.2 시나리오: 반복 발언 추적

```gherkin
Feature: 반복 발언 추적
  반복되는 발언 패턴을 추적한다

  Scenario: 반복 발언 탐지
    Given 동일 화자가 "다 네 잘못이야"를 5회 발언했다
    When PatternDetector.detect_repeated_statements(segments, threshold=3)를 호출한다
    Then RepeatedStatement가 반환되어야 한다
    And total_count는 5여야 한다
    And speaker는 해당 화자여야 한다

  Scenario: 유사 표현 그룹화
    Given "다 네 잘못이야", "네가 잘못했어", "네 탓이야"가 발언되었다
    When PatternDetector.detect_repeated_statements(segments)를 호출한다
    Then 유사 표현이 같은 RepeatedStatement로 그룹화되어야 한다

  Scenario: 반복 기간 계산
    Given 첫 발언이 2025-07-01, 마지막 발언이 2025-09-30이다
    When 반복 발언이 탐지되었다
    Then time_span_days는 약 91일이어야 한다
```

### 3.3 시나리오: 감정적 조작 탐지

```gherkin
Feature: 감정적 조작 탐지
  감정적 조작 패턴을 탐지한다

  Scenario: 죄책감 유발(GUILT_TRIPPING) 탐지
    Given 세그먼트 내용이 "네가 이렇게 해서 내가 얼마나 힘든지 알아?"이다
    When PatternDetector.detect_emotional_manipulation(segments)를 호출한다
    Then EmotionalManipulation이 반환되어야 한다
    And manipulation_type은 "GUILT_TRIPPING"이어야 한다

  Scenario: 수치심 유발(SHAMING) 탐지
    Given 세그먼트 내용이 "창피하지도 않아? 사람이 어떻게 그래?"이다
    When PatternDetector.detect_emotional_manipulation(segments)를 호출한다
    Then manipulation_type은 "SHAMING"이어야 한다
```

### 3.4 시나리오: 위협/압박 탐지

```gherkin
Feature: 위협/압박 탐지
  위협 및 압박 표현을 탐지한다

  Scenario: 명시적 위협 탐지
    Given 세그먼트 내용이 "두고 봐. 가만 안 둬."이다
    When PatternDetector.detect_threats(segments)를 호출한다
    Then ThreatPattern이 반환되어야 한다
    And threat_type은 "EXPLICIT_THREAT"이어야 한다

  Scenario: 경제적 압박 탐지
    Given 세그먼트 내용이 "한 푼도 안 줄 거야. 상속에서 빼버릴 테니까."이다
    When PatternDetector.detect_threats(segments)를 호출한다
    Then threat_type은 "FINANCIAL_THREAT"이어야 한다
    And severity는 "HIGH" 이상이어야 한다

  Scenario: 사회적 위협 탐지
    Given 세그먼트 내용이 "아는 사람한테 다 말할 거야. 망하게 해줄게."이다
    When PatternDetector.detect_threats(segments)를 호출한다
    Then threat_type은 "SOCIAL_THREAT"이어야 한다
```

### 3.5 시나리오: 통합 탐지 및 Evidence 변환

```gherkin
Feature: 통합 탐지 및 Evidence 변환
  모든 패턴을 탐지하고 Evidence로 변환한다

  Scenario: 통합 탐지
    Given 다양한 패턴이 포함된 세그먼트 목록이 있다
    When PatternDetector.detect_all(segments)를 호출한다
    Then Evidence 목록이 반환되어야 한다
    And 각 Evidence는 category, importance, segment_ids를 포함해야 한다

  Scenario: 중요도 자동 상향
    Given 가스라이팅 패턴이 3회 이상 반복되었다
    When 패턴이 탐지되었다
    Then importance는 "HIGH"로 설정되어야 한다
```

---

## 4. 커스텀 패턴

### 4.1 시나리오: 사용자 정의 패턴

```gherkin
Feature: 사용자 정의 패턴
  사용자가 정의한 패턴을 탐지한다

  Scenario: 커스텀 패턴 추가
    Given 키워드 ["특정 표현", "다른 표현"]으로 커스텀 패턴을 정의했다
    When PatternDetector.add_custom_pattern("custom_1", keywords, rules)를 호출한다
    Then 패턴이 등록되어야 한다

  Scenario: 커스텀 패턴 탐지
    Given "특정 표현"을 포함하는 세그먼트가 있다
    And 해당 키워드로 커스텀 패턴이 등록되어 있다
    When PatternDetector.detect_all(segments)를 호출한다
    Then 커스텀 패턴 결과가 Evidence에 포함되어야 한다
```

---

## 5. 성능 요구사항

### 5.1 시나리오: 대용량 처리

```gherkin
Feature: 대용량 처리 성능
  183개 파일의 전체 분석 성능을 검증한다

  Scenario: 전체 분석 시간
    Given DGX Spark 환경에서 실행한다
    And 183개 녹취 파일이 준비되어 있다
    When 전체 분석을 수행한다
    Then 총 소요 시간은 30분 이내여야 한다

  Scenario: GPU 가속 효과
    Given GPU 가속이 활성화되어 있다
    When 패턴 인식을 수행한다
    Then 처리량은 1000 segments/second 이상이어야 한다

  Scenario: 메모리 안정성
    Given 메모리 모니터링이 활성화되어 있다
    When 전체 분석을 수행한다
    Then 최대 메모리 사용량은 100GB를 초과하지 않아야 한다
```

---

## 6. 품질 게이트

### 6.1 테스트 커버리지

- [ ] 단위 테스트 커버리지 > 85%
- [ ] 통합 테스트 시나리오 전체 통과
- [ ] 성능 테스트 기준 충족

### 6.2 정확도 기준

- [ ] 화자 식별 정확도 > 95%
- [ ] 화자 별칭 인식률 > 98%
- [ ] 가스라이팅 탐지 정밀도 > 85%
- [ ] 가스라이팅 탐지 재현율 > 80%

### 6.3 성능 기준

- [ ] 183개 파일 전체 분석 < 30분
- [ ] 단일 파일 처리 < 5초
- [ ] GPU 가속 시 처리량 > 1000 segments/s

---

## 7. 완료 체크리스트

### 7.1 기능 완료

- [ ] TimelineBuilder 구현 완료
- [ ] SpeakerAnalyzer 구현 완료
- [ ] PatternDetector 구현 완료
- [ ] 모든 데이터 모델 정의 완료
- [ ] 설정 파일 확장 완료

### 7.2 테스트 완료

- [ ] 모든 단위 테스트 통과
- [ ] 모든 통합 테스트 통과
- [ ] 성능 테스트 통과
- [ ] 실제 데이터 검증 완료

### 7.3 문서화 완료

- [ ] API 문서 작성
- [ ] 사용 가이드 작성
- [ ] 패턴 사전 문서화

---

Version: 1.0.0
Last Updated: 2026-01-18
