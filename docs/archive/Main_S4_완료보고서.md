# Main-S4: 온톨로지 확장 - 완료 보고서

> **Phase**: Main-S4 (센서 통합 Phase 4)
> **목표**: 센서 패턴을 온톨로지에 통합
> **상태**: 완료
> **일자**: 2026-01-21

---

## 1. 구현 요약

### 1.1 완료 항목

| 항목 | 파일 | 상태 |
|------|------|------|
| 스키마 확장 | `src/ontology/schema.py` | 완료 |
| 온톨로지 정의 | `data/processed/ontology/ontology.json` | 완료 |
| GraphRetriever 확장 | `src/rag/graph_retriever.py` | 완료 |
| Neo4j 적재 스크립트 | `scripts/run_ontology.py` | 완료 |
| 단위 테스트 | `tests/unit/test_ontology_sensor.py` | 완료 (17개 통과) |

### 1.2 파일 구조

```
src/ontology/
└── schema.py                    # [수정] EntityType.SENSOR_PATTERN, CAUSE 추가
                                 #        RelationType.INDICATES, TRIGGERS 추가
                                 #        create_sensor_pattern(), create_cause() 헬퍼

src/rag/
└── graph_retriever.py           # [수정] 센서 패턴 검색 메서드 추가

data/processed/ontology/
└── ontology.json                # [신규] SensorPattern/Cause 노드 및 관계 정의

scripts/
└── run_ontology.py              # [수정] load_sensor_ontology() 추가

tests/unit/
└── test_ontology_sensor.py      # [신규] 센서 패턴 온톨로지 테스트
```

---

## 2. 구현 세부사항

### 2.1 스키마 확장

**새로운 EntityType:**

| 타입 | 값 | 설명 |
|------|-----|------|
| `SENSOR_PATTERN` | `SensorPattern` | 센서 패턴 노드 |
| `CAUSE` | `Cause` | 원인 노드 |

**새로운 RelationType:**

| 타입 | 값 | 설명 |
|------|-----|------|
| `INDICATES` | `INDICATES` | 패턴 → 원인 관계 |
| `TRIGGERS` | `TRIGGERS` | 패턴 → 에러코드 관계 |

**헬퍼 함수:**

```python
def create_sensor_pattern(
    pattern_id: str,       # PAT_COLLISION, PAT_VIBRATION 등
    pattern_type: str,     # collision, vibration, overload, drift
    description: str,
    threshold: Dict,
    severity: str          # high, medium, low
) -> Entity

def create_cause(
    cause_id: str,         # CAUSE_PHYSICAL_CONTACT 등
    description: str,
    category: str          # physical, mechanical, sensor, software
) -> Entity
```

### 2.2 ontology.json 구조

```json
{
  "nodes": {
    "SensorPattern": [
      {"pattern_id": "PAT_COLLISION", "type": "collision", ...},
      {"pattern_id": "PAT_VIBRATION", "type": "vibration", ...},
      {"pattern_id": "PAT_OVERLOAD", "type": "overload", ...},
      {"pattern_id": "PAT_DRIFT", "type": "drift", ...}
    ],
    "Cause": [
      {"cause_id": "CAUSE_PHYSICAL_CONTACT", ...},
      {"cause_id": "CAUSE_UNEXPECTED_OBSTACLE", ...},
      // ... 총 7개 Cause 노드
    ]
  },
  "relationships": [
    {"type": "INDICATES", "source": "PAT_COLLISION", "target": "CAUSE_PHYSICAL_CONTACT", "confidence": 0.9},
    {"type": "TRIGGERS", "source": "PAT_COLLISION", "target": "C153", "probability": 0.95},
    // ... 총 11개 관계
  ]
}
```

### 2.3 GraphRetriever 확장

**새로운 메서드:**

| 메서드 | 설명 | Cypher |
|--------|------|--------|
| `search_sensor_pattern_causes(pattern_type)` | 패턴 → 원인 검색 | `(sp:SensorPattern)-[:INDICATES]->(c:Cause)` |
| `search_sensor_pattern_errors(pattern_type)` | 패턴 → 에러 검색 | `(sp:SensorPattern)-[:TRIGGERS]->(e:ErrorCode)` |
| `search_error_patterns(error_code)` | 에러 → 패턴 검색 | `(sp:SensorPattern)-[:TRIGGERS]->(e:ErrorCode)` |
| `search_integrated_path(pattern_type)` | 통합 경로 검색 | 패턴 → 원인 + 에러 → 해결책 |

**사용 예시:**

```python
from src.rag.graph_retriever import GraphRetriever

retriever = GraphRetriever()

# 충돌 패턴의 원인 조회
causes = retriever.search_sensor_pattern_causes("collision")
# → CAUSE_PHYSICAL_CONTACT (90%), CAUSE_UNEXPECTED_OBSTACLE (85%)

# 충돌 패턴이 유발하는 에러코드
errors = retriever.search_sensor_pattern_errors("collision")
# → C153 (95%), C119 (80%)

# C153 에러와 연관된 센서 패턴
patterns = retriever.search_error_patterns("C153")
# → PAT_COLLISION (collision)

# 통합 경로 검색
integrated = retriever.search_integrated_path("collision")
# → 원인 + 에러 + 해결책 전체 경로
```

---

## 3. 테스트 결과

### 3.1 단위 테스트

```
17 passed in 2.35s
```

### 3.2 테스트 카테고리

| 카테고리 | 테스트 수 | 내용 |
|----------|----------|------|
| SensorPatternSchema | 6 | EntityType, RelationType, 헬퍼 함수 |
| GraphRetrieverSensorPatterns | 5 | 패턴 검색 메서드 |
| GraphResult | 2 | 데이터클래스 |
| OntologyJsonLoad | 3 | ontology.json 검증 |
| SensorPatternIntegration | 1 | 통합 흐름 |

---

## 4. 온톨로지 그래프

### 4.1 노드 정의

**SensorPattern (4개)**

| pattern_id | type | severity | threshold |
|------------|------|----------|-----------|
| PAT_COLLISION | collision | high | Fz > 500N |
| PAT_VIBRATION | vibration | medium | Tx/Ty noise > 2x |
| PAT_OVERLOAD | overload | high | Fz > 300N, 5s+ |
| PAT_DRIFT | drift | low | 10%+ deviation |

**Cause (7개)**

| cause_id | category | description |
|----------|----------|-------------|
| CAUSE_PHYSICAL_CONTACT | physical | 물리적 접촉 (장애물 충돌) |
| CAUSE_UNEXPECTED_OBSTACLE | physical | 예상치 못한 장애물 |
| CAUSE_PAYLOAD_EXCEEDED | mechanical | 하중 초과 |
| CAUSE_JOINT_WEAR | mechanical | 조인트 마모 |
| CAUSE_LOOSE_BOLTS | mechanical | 볼트 풀림 |
| CAUSE_CALIBRATION_NEEDED | sensor | 캘리브레이션 필요 |
| CAUSE_PROGRAM_ERROR | software | 프로그램 경로 오류 |

### 4.2 관계 정의

**INDICATES (6개)**

```
PAT_COLLISION --[90%]--> CAUSE_PHYSICAL_CONTACT
PAT_COLLISION --[85%]--> CAUSE_UNEXPECTED_OBSTACLE
PAT_COLLISION --[70%]--> CAUSE_PROGRAM_ERROR
PAT_OVERLOAD  --[90%]--> CAUSE_PAYLOAD_EXCEEDED
PAT_VIBRATION --[70%]--> CAUSE_JOINT_WEAR
PAT_VIBRATION --[65%]--> CAUSE_LOOSE_BOLTS
PAT_DRIFT     --[80%]--> CAUSE_CALIBRATION_NEEDED
```

**TRIGGERS (4개)**

```
PAT_COLLISION --[95%]--> C153 (Safety Stop)
PAT_COLLISION --[80%]--> C119
PAT_OVERLOAD  --[90%]--> C189
PAT_VIBRATION --[75%]--> C204
```

---

## 5. 통합 포인트

### 5.1 ContextEnricher 연동 (Main-S3 → S4)

```python
# ContextEnricher에서 GraphRetriever 사용
graph_results = retriever.search(
    error_codes=["C153"],
    pattern_types=["collision"]
)

# 센서 패턴 기반 원인 분석
causes = retriever.search_sensor_pattern_causes("collision")
for c in causes.related_entities:
    print(f"가능한 원인: {c['description']} ({c['confidence']:.0%})")
```

### 5.2 Verifier 연동 (Main-S5)

```python
# Verifier에서 GraphRetriever로 교차 검증
# 센서 패턴이 에러코드를 유발하는지 확인
if pattern_type == "collision":
    expected_errors = retriever.search_sensor_pattern_errors("collision")
    if error_code in [e['name'] for e in expected_errors.related_entities]:
        confidence_boost = 0.15  # 온톨로지 검증 성공
```

---

## 6. Cypher 쿼리 예시

### 6.1 센서 패턴 → 원인 조회

```cypher
MATCH (sp:SensorPattern)-[r:INDICATES]->(c:Cause)
WHERE sp.type = 'collision'
RETURN sp.pattern_id, c.description, r.confidence
ORDER BY r.confidence DESC
```

### 6.2 에러코드 → 연관 패턴 조회

```cypher
MATCH (sp:SensorPattern)-[r:TRIGGERS]->(e:ErrorCode)
WHERE e.name = 'C153'
RETURN sp.type, sp.description, r.probability
```

### 6.3 통합 경로 조회

```cypher
MATCH (sp:SensorPattern {type: 'collision'})-[r1:INDICATES]->(c:Cause)
OPTIONAL MATCH (sp)-[r2:TRIGGERS]->(e:ErrorCode)
OPTIONAL MATCH (e)-[r3:RESOLVED_BY]->(p:Procedure)
RETURN sp, c, e, p
```

---

## 7. 다음 단계

- [x] Main-S1: 센서 데이터 생성 (완료)
- [x] Main-S2: 패턴 감지 (완료)
- [x] Main-S3: Context Enricher (완료)
- [x] Main-S4: 온톨로지 확장 (완료)
- [ ] Main-S5: Verifier 확장 (이중 검증, PARTIAL 상태)
- [ ] Main-S6: API/UI 확장

---

**작성**: Main-S4 온톨로지 확장
**참조**: Main_S4_온톨로지확장.md, Main_S3_완료보고서.md
