# Step 09: 온톨로지 연결 - 설계서

## 1. 개요

| 항목 | 내용 |
|------|------|
| Phase | 09 - 온톨로지 연결 (Ontology Connection) |
| 목표 | 감지된 패턴을 온톨로지와 연결 |
| 이전 단계 | Phase 08 - 패턴 감지 |
| 다음 단계 | Phase 10 - 질문 분류기 |
| ROADMAP 섹션 | Stage 3: Sensor Integration (완료) |

---

## 2. 요구사항 분석

### 2.1 Unified_ROADMAP.md 요구사항

| 요구사항 | 설명 |
|----------|------|
| 패턴 → 에러코드 매핑 | TRIGGERS 관계 생성 |
| 패턴 → 원인 매핑 | INDICATES 관계 생성 |
| 이벤트 → 컨텍스트 연결 | OCCURS_DURING, INVOLVES 관계 |
| 관계 그래프 업데이트 | 온톨로지에 동적 관계 추가 |

### 2.2 기존 온톨로지 관계 타입 (schema.py)

```python
# Measurement 관계 (Phase 9 핵심)
INDICATES = "INDICATES"     # Pattern → Cause
TRIGGERS = "TRIGGERS"       # Pattern → ErrorCode

# Context 관계 (Phase 9 핵심)
INSTANCE_OF = "INSTANCE_OF"   # Event → Pattern
OCCURS_DURING = "OCCURS_DURING"  # Event → Shift
INVOLVES = "INVOLVES"          # Event → Product
```

### 2.3 기존 패턴 데이터 (17개)

| 패턴 타입 | 개수 | 관련 에러 코드 |
|----------|------|---------------|
| collision | 2 | C153, C119 |
| overload | 4 | C189 |
| drift | 11 | (없음) |
| **합계** | **17** | |

### 2.4 기존 온톨로지 엔티티

| 도메인 | 관련 엔티티 |
|--------|------------|
| Measurement | PAT_COLLISION, PAT_OVERLOAD, PAT_DRIFT, PAT_VIBRATION |
| Knowledge | C153, C119, C189, CAUSE_*, RES_* |
| Context | SHIFT_A/B/C, PART-A/B/C, EVT_* |

---

## 3. 설계

### 3.1 구현 파일 목록

| 파일 | 설명 |
|------|------|
| `configs/error_pattern_mapping.yaml` | 패턴-에러-원인 매핑 설정 |
| `src/sensor/ontology_connector.py` | 온톨로지 연결 로직 |
| `src/sensor/__init__.py` | 모듈 노출 업데이트 |

### 3.2 매핑 설정 파일 (error_pattern_mapping.yaml)

```yaml
# 패턴 타입 → 에러코드/원인 매핑 (온톨로지 관계 생성용)
ontology_pattern_mapping:

  # 충돌 패턴
  collision:
    triggers:
      - code: "C153"
        confidence: 0.95
        description: "보호 정지 (Protective Stop)"
      - code: "C119"
        confidence: 0.80
        description: "관절 위치 이탈 (Joint Position Deviation)"
    indicates:
      - cause: "CAUSE_PHYSICAL_CONTACT"
        confidence: 0.95
        description: "물리적 접촉 (장애물, 작업자)"
      - cause: "CAUSE_PATH_OBSTRUCTION"
        confidence: 0.70
        description: "경로상 장애물"

  # 과부하 패턴
  overload:
    triggers:
      - code: "C189"
        confidence: 0.90
        description: "과부하 감지 (Overload Detected)"
    indicates:
      - cause: "CAUSE_PAYLOAD_EXCEEDED"
        confidence: 0.85
        description: "페이로드 초과"
      - cause: "CAUSE_GRIP_POSITION"
        confidence: 0.70
        description: "그립 위치 불량"

  # 드리프트 패턴
  drift:
    triggers: []  # 경고 수준, 에러 없음
    indicates:
      - cause: "CAUSE_SENSOR_DRIFT"
        confidence: 0.80
        description: "센서 드리프트"
      - cause: "CAUSE_CALIBRATION_NEEDED"
        confidence: 0.60
        description: "재교정 필요"

  # 진동 패턴
  vibration:
    triggers: []  # 경고 수준, 에러 없음
    indicates:
      - cause: "CAUSE_MECHANICAL_WEAR"
        confidence: 0.70
        description: "기계적 마모"
      - cause: "CAUSE_LOOSE_MOUNTING"
        confidence: 0.60
        description: "마운팅 느슨함"
```

### 3.3 OntologyConnector 클래스 설계

```python
class OntologyConnector:
    """온톨로지 연결기

    감지된 패턴을 온톨로지와 연결합니다.
    """

    def __init__(self, ontology_schema: Optional[OntologySchema] = None):
        """초기화"""

    def load_mapping(self, path: Optional[Path] = None) -> Dict:
        """매핑 설정 로드"""

    def map_pattern_to_errors(
        self,
        pattern: DetectedPattern
    ) -> List[Dict]:
        """패턴 → 에러코드 매핑

        Returns:
            [{"code": "C153", "confidence": 0.95}, ...]
        """

    def map_pattern_to_causes(
        self,
        pattern: DetectedPattern
    ) -> List[Dict]:
        """패턴 → 원인 매핑

        Returns:
            [{"cause": "CAUSE_PHYSICAL_CONTACT", "confidence": 0.95}, ...]
        """

    def create_event(
        self,
        pattern: DetectedPattern,
        context: Optional[Dict] = None
    ) -> Entity:
        """패턴 발생 이벤트 엔티티 생성"""

    def create_relationships(
        self,
        pattern: DetectedPattern,
        event: Optional[Entity] = None
    ) -> List[Relationship]:
        """온톨로지 관계 생성

        - Pattern → ErrorCode (TRIGGERS)
        - Pattern → Cause (INDICATES)
        - Event → Pattern (INSTANCE_OF)
        - Event → Shift (OCCURS_DURING)
        - Event → Product (INVOLVES)
        """

    def get_pattern_entity_id(self, pattern_type: PatternType) -> str:
        """패턴 타입 → 온톨로지 엔티티 ID"""

    def get_shift_for_timestamp(self, timestamp: datetime) -> str:
        """시각 → Shift ID"""

    def enrich_ontology(
        self,
        patterns: List[DetectedPattern]
    ) -> OntologySchema:
        """패턴 기반 온톨로지 확장"""
```

### 3.4 관계 생성 흐름

```
DetectedPattern (PAT-001, collision)
    │
    ├─[map_pattern_to_errors]→ [C153, C119]
    │   └─ TRIGGERS 관계 생성
    │
    ├─[map_pattern_to_causes]→ [CAUSE_PHYSICAL_CONTACT, ...]
    │   └─ INDICATES 관계 생성
    │
    └─[create_event]→ Event (EVT-001)
        ├─ INSTANCE_OF → PAT_COLLISION
        ├─ OCCURS_DURING → SHIFT_B (14:00 = 오후 근무)
        └─ INVOLVES → PART-A (컨텍스트에서)
```

---

## 4. 온톨로지 확장

### 4.1 새로 추가될 관계

| 관계 타입 | 소스 | 타겟 | 예시 |
|----------|------|------|------|
| TRIGGERS | PAT_COLLISION | C153 | 충돌→보호정지 |
| TRIGGERS | PAT_OVERLOAD | C189 | 과부하→과부하에러 |
| INDICATES | PAT_COLLISION | CAUSE_PHYSICAL_CONTACT | 충돌→물리접촉 |
| INDICATES | PAT_OVERLOAD | CAUSE_PAYLOAD_EXCEEDED | 과부하→페이로드초과 |
| INSTANCE_OF | EVT-001 | PAT_COLLISION | 이벤트→패턴정의 |
| OCCURS_DURING | EVT-001 | SHIFT_B | 이벤트→근무시간 |
| INVOLVES | EVT-001 | PART-A | 이벤트→제품 |

### 4.2 Shift 매핑

```python
SHIFT_MAPPING = {
    (6, 14): "SHIFT_A",   # 06:00 ~ 14:00 (오전)
    (14, 22): "SHIFT_B",  # 14:00 ~ 22:00 (오후)
    (22, 6): "SHIFT_C",   # 22:00 ~ 06:00 (야간)
}
```

---

## 5. 컨텍스트 연결

### 5.1 SensorStore 컨텍스트 활용

```python
from src.sensor import SensorStore

store = SensorStore()

# 패턴 발생 시점의 컨텍스트
context = store.get_context_at(pattern.timestamp)
# {
#     "timestamp": "2024-01-17T14:00:00",
#     "task_mode": "ASSEMBLY",
#     "shift": "B",
#     "product_id": "PART-A",
#     "operator_id": "OP-001",
#     ...
# }
```

### 5.2 컨텍스트 → 관계 매핑

| 컨텍스트 필드 | 관계 타입 | 타겟 엔티티 |
|--------------|----------|------------|
| shift | OCCURS_DURING | SHIFT_A/B/C |
| product_id | INVOLVES | PART-A/B/C |

---

## 6. 체크리스트

### 6.1 구현 항목

- [ ] `configs/error_pattern_mapping.yaml` 작성
  - [ ] collision 매핑
  - [ ] overload 매핑
  - [ ] drift 매핑
  - [ ] vibration 매핑
- [ ] `src/sensor/ontology_connector.py` 구현
  - [ ] 매핑 설정 로드
  - [ ] 패턴 → 에러코드 매핑
  - [ ] 패턴 → 원인 매핑
  - [ ] 이벤트 생성
  - [ ] 관계 생성
  - [ ] 온톨로지 확장
- [ ] `src/sensor/__init__.py` 업데이트
- [ ] 단위 테스트

### 6.2 검증 항목

- [ ] 17개 패턴에 대한 매핑 정확성
- [ ] TRIGGERS, INDICATES 관계 생성
- [ ] 컨텍스트 연결 (OCCURS_DURING, INVOLVES)
- [ ] 온톨로지 통합 정상 동작

---

## 7. 폴더 구조 (Phase 9 완료 후)

```
ur5e-ontology-rag/
├── configs/
│   └── error_pattern_mapping.yaml  [신규]
│
├── data/
│   └── sensor/
│       └── processed/
│           └── detected_patterns.json
│
└── src/
    └── sensor/
        ├── __init__.py              [업데이트]
        ├── data_loader.py           [Phase 7]
        ├── sensor_store.py          [Phase 7]
        ├── patterns.py              [Phase 8]
        ├── pattern_detector.py      [Phase 8]
        └── ontology_connector.py    [신규]
```

---

## 8. Stage 3 완료 후 활용

### Phase 10 (질문 분류기)에서의 활용

```python
from src.sensor import OntologyConnector, PatternDetector, SensorStore
from src.ontology import load_ontology

# 온톨로지 로드
ontology = load_ontology()

# 패턴 기반 확장
store = SensorStore()
detector = PatternDetector(store)
connector = OntologyConnector(ontology)

patterns = detector.load_existing_patterns()
enriched_ontology = connector.enrich_ontology(patterns)

# 질문 처리 시 활용
# Q: "C153 에러의 원인은?"
# → 온톨로지 경로: C153 ← TRIGGERS ← PAT_COLLISION → INDICATES → CAUSE_PHYSICAL_CONTACT
```

---

## 9. 문서 정보

| 항목 | 값 |
|------|------|
| 문서 버전 | v1.0 |
| ROADMAP 섹션 | Stage 3, Phase 9 |
| Spec 섹션 | 8.4 온톨로지 연결 |
