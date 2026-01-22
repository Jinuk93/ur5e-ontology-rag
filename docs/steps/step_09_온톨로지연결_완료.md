# Step 09: 온톨로지 연결 - 완료 보고서

## 1. 완료 요약

| 항목 | 내용 |
|------|------|
| Phase | 09 - 온톨로지 연결 (Ontology Connection) |
| 상태 | ✅ 완료 |
| 완료일 | 2026-01-22 |
| 이전 단계 | Phase 08 - 패턴 감지 |
| 다음 단계 | Phase 10 - 질문 분류기 |
| Stage 완료 | ✅ Stage 3 (Sensor Integration) 완료 |

---

## 2. 구현 파일 목록

| 파일 | 라인 수 | 설명 |
|------|---------|------|
| `configs/error_pattern_mapping.yaml` | 198 | 매핑 설정 (업데이트) |
| `src/sensor/ontology_connector.py` | 480 | 온톨로지 연결 로직 |
| `src/sensor/__init__.py` | 73 | 모듈 노출 (업데이트) |
| **합계** | **751** | |

---

## 3. 구현 내용

### 3.1 매핑 설정 (error_pattern_mapping.yaml)

> **참고**: 아래 예시는 가독성을 위해 축약됨. 실제 파일은 `- code: "C153", confidence: 0.95` 형태의 객체 리스트 사용.

```yaml
# 패턴 타입 → 온톨로지 엔티티 ID
pattern_entity_mapping:
  collision: "PAT_COLLISION"
  overload: "PAT_OVERLOAD"
  drift: "PAT_DRIFT"
  vibration: "PAT_VIBRATION"

# Shift 시간대 매핑
shift_mapping:
  SHIFT_A: {start_hour: 6, end_hour: 14}   # 오전
  SHIFT_B: {start_hour: 14, end_hour: 22}  # 오후
  SHIFT_C: {start_hour: 22, end_hour: 6}   # 야간

# 패턴 → 에러코드/원인 매핑 (축약 표현)
ontology_pattern_mapping:
  collision:
    triggers: [C153, C119]          # 실제: [{code: "C153", confidence: 0.95}, ...]
    indicates: [CAUSE_PHYSICAL_CONTACT, CAUSE_PATH_OBSTRUCTION]
  overload:
    triggers: [C189]
    indicates: [CAUSE_PAYLOAD_EXCEEDED, CAUSE_GRIP_POSITION]
  # ...
```

### 3.2 OntologyConnector 클래스

```python
class OntologyConnector:
    """온톨로지 연결기"""

    def load_mapping(self) -> Dict
    def map_pattern_to_errors(self, pattern: DetectedPattern) -> List[Dict]
    def map_pattern_to_causes(self, pattern: DetectedPattern) -> List[Dict]
    def get_pattern_entity_id(self, pattern_type: PatternType) -> str
    def get_shift_for_timestamp(self, timestamp: datetime) -> str
    def create_event(self, pattern: DetectedPattern) -> Entity
    def create_relationships(self, pattern: DetectedPattern) -> List[Relationship]
    def enrich_ontology(self, patterns: List[DetectedPattern]) -> OntologySchema
    def get_pattern_context(self, pattern: DetectedPattern) -> Dict
```

---

## 4. 테스트 결과

### 4.1 기본 연결 테스트

```
=== OntologyConnector Test ===
Patterns: 17
Summary: {
    'ontology_entities': 54,
    'ontology_relationships': 62,
    'pattern_types_mapped': 4,
    'shift_mapping': ['SHIFT_A', 'SHIFT_B', 'SHIFT_C']
}
```

✅ 온톨로지 연결기 초기화 성공

### 4.2 패턴 → 에러코드 매핑 테스트

```python
Collision pattern: PAT-001
→ Errors: [
    {'code': 'C153', 'confidence': 1.0, 'source': 'mapping'},
    {'code': 'C119', 'confidence': 0.9, 'source': 'mapping'}
]
→ Causes: [
    {'cause': 'CAUSE_PHYSICAL_CONTACT', 'confidence': 0.95},
    {'cause': 'CAUSE_PATH_OBSTRUCTION', 'confidence': 0.7}
]
```

✅ 충돌 패턴 → C153, C119 에러 매핑 성공
✅ 충돌 패턴 → CAUSE_PHYSICAL_CONTACT 원인 매핑 성공

### 4.3 Shift 매핑 테스트

```
08:00 → SHIFT_A (오전 근무)
14:00 → SHIFT_B (오후 근무)
23:00 → SHIFT_C (야간 근무)
```

✅ 시간대별 Shift 매핑 정확

### 4.4 관계 생성 테스트

```
Event: EVT-001
Relationships: 6
  PAT_COLLISION --[TRIGGERS]--> C153
  PAT_COLLISION --[TRIGGERS]--> C119
  PAT_COLLISION --[INDICATES]--> CAUSE_PHYSICAL_CONTACT
  PAT_COLLISION --[INDICATES]--> CAUSE_PATH_OBSTRUCTION
  EVT-001 --[INSTANCE_OF]--> PAT_COLLISION
  EVT-001 --[OCCURS_DURING]--> SHIFT_B
```

✅ TRIGGERS, INDICATES 관계 생성 성공
✅ INSTANCE_OF, OCCURS_DURING 관계 생성 성공

---

## 5. 생성되는 관계 타입

### 5.1 패턴 관계 (TRIGGERS, INDICATES)

| 패턴 타입 | TRIGGERS | INDICATES |
|----------|----------|-----------|
| collision | C153, C119 | CAUSE_PHYSICAL_CONTACT, CAUSE_PATH_OBSTRUCTION |
| overload | C189 | CAUSE_PAYLOAD_EXCEEDED, CAUSE_GRIP_POSITION |
| drift | (없음) | CAUSE_SENSOR_DRIFT, CAUSE_CALIBRATION_NEEDED |
| vibration | (없음) | CAUSE_MECHANICAL_WEAR, CAUSE_LOOSE_MOUNTING |

### 5.2 이벤트 관계 (컨텍스트)

| 관계 타입 | 소스 | 타겟 |
|----------|------|------|
| INSTANCE_OF | EVT-001 | PAT_COLLISION |
| OCCURS_DURING | EVT-001 | SHIFT_B |
| INVOLVES | EVT-001 | PART-A (컨텍스트 있을 때) |

---

## 6. 체크리스트 완료

### 6.1 구현 항목

- [x] `configs/error_pattern_mapping.yaml` 확장
  - [x] pattern_entity_mapping 추가
  - [x] shift_mapping 추가
  - [x] ontology_pattern_mapping 추가
- [x] `src/sensor/ontology_connector.py` 구현
  - [x] 매핑 설정 로드
  - [x] 패턴 → 에러코드 매핑
  - [x] 패턴 → 원인 매핑
  - [x] Shift 매핑
  - [x] 이벤트 생성
  - [x] 관계 생성
  - [x] 온톨로지 확장
- [x] `src/sensor/__init__.py` 업데이트

### 6.2 검증 항목

- [x] 17개 패턴 → 에러코드 매핑
- [x] TRIGGERS, INDICATES 관계 생성
- [x] OCCURS_DURING 관계 생성 (Shift)
- [x] 온톨로지 통합 정상 동작

---

## 7. Stage 3 최종 폴더 구조

```
ur5e-ontology-rag/
├── configs/
│   └── error_pattern_mapping.yaml  [198줄, 확장]
│
├── data/
│   └── sensor/
│       ├── raw/
│       │   └── axia80_week_01.parquet    # 604,800 레코드
│       └── processed/
│           └── detected_patterns.json    # 17개 패턴
│
└── src/
    └── sensor/
        ├── __init__.py              [73줄]
        ├── data_loader.py           [125줄, Phase 7]
        ├── sensor_store.py          [251줄, Phase 7]
        ├── patterns.py              [92줄, Phase 8]
        ├── pattern_detector.py      [629줄, Phase 8]
        └── ontology_connector.py    [480줄, Phase 9]
```

---

## 8. Stage 3 완료 요약

### 8.1 Phase별 산출물

| Phase | 구현 | 핵심 기능 |
|-------|------|----------|
| 7 | SensorStore, DataLoader | 센서 데이터 로드, 조회, 통계, path별 캐시 |
| 8 | PatternDetector | 패턴 감지 (collision, overload, drift, vibration), 절대값 모드 fallback |
| 9 | OntologyConnector | 패턴↔온톨로지 연결, 관계 생성 |

### 8.2 총 코드량

| 파일 | 라인 수 |
|------|---------|
| Phase 7 (data_loader, sensor_store) | 403줄 |
| Phase 8 (patterns, pattern_detector) | 721줄 |
| Phase 9 (ontology_connector) | 480줄 |
| __init__.py | 73줄 |
| configs/error_pattern_mapping.yaml | 198줄 |
| **Stage 3 합계** | **1,875줄** |

---

## 9. Stage 4 연결 (Query Engine)

### Phase 10 (질문 분류기)에서의 활용

```python
from src.sensor import SensorStore, PatternDetector, OntologyConnector
from src.ontology import load_ontology

# 온톨로지 + 센서 통합
ontology = load_ontology()
store = SensorStore()
detector = PatternDetector(store)
connector = OntologyConnector(ontology)

# 패턴 기반 온톨로지 확장
patterns = detector.load_existing_patterns()
enriched_ontology = connector.enrich_ontology(patterns)

# 질문 처리 예시
# Q: "C153 에러의 원인은?"
# 온톨로지 경로: C153 ← TRIGGERS ← PAT_COLLISION → INDICATES → CAUSE_PHYSICAL_CONTACT
# 답변: "C153 에러는 충돌 패턴(PAT_COLLISION)에 의해 발생하며,
#        주요 원인은 물리적 접촉(CAUSE_PHYSICAL_CONTACT)입니다."
```

---

## 10. 문서 정보

| 항목 | 값 |
|------|------|
| 문서 버전 | v1.0 |
| 작성일 | 2026-01-22 |
| ROADMAP 섹션 | Stage 3, Phase 9 |
| Spec 섹션 | 8.4 온톨로지 연결 |
| Stage 상태 | ✅ 완료 |
