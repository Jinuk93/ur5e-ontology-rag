# Main-S4: 온톨로지 확장

> **Phase**: Main-S4 (센서 통합 Phase 4)
> **목표**: 센서 패턴을 온톨로지에 통합
> **선행 조건**: Main-S2 (패턴 감지) 완료
> **상태**: 설계

---

## 1. 개요

### 1.1 목적

센서 패턴을 온톨로지에 통합하여 그래프 기반 추론을 지원합니다.

```
[기존]
(Component) --[HAS_ERROR]--> (ErrorCode)
(ErrorCode) --[RESOLVED_BY]--> (Resolution)
(ErrorCode) --[CAUSED_BY]--> (Cause)

[추가]
(SensorPattern) --[INDICATES]--> (Cause)
(SensorPattern) --[TRIGGERS]--> (ErrorCode)
```

### 1.2 핵심 변경사항

1. **SensorPattern 노드 추가**: 충돌, 진동, 과부하, 드리프트 패턴 노드
2. **INDICATES 관계**: 센서 패턴 → 원인 관계
3. **TRIGGERS 관계**: 센서 패턴 → 에러코드 관계
4. **GraphRetriever 확장**: 센서 패턴 기반 추론 지원

---

## 2. 온톨로지 스키마

### 2.1 SensorPattern 노드

```json
{
  "SensorPattern": {
    "pattern_id": "string (PK)",
    "type": "string (collision|vibration|overload|drift)",
    "description": "string",
    "threshold": {
      "axis": "string",
      "value": "number",
      "duration_ms": "number (optional)"
    },
    "severity": "string (high|medium|low)"
  }
}
```

### 2.2 노드 정의

| pattern_id | type | 설명 | 임계값 |
|------------|------|------|--------|
| PAT_COLLISION | collision | Z축 충돌 패턴 | Fz > 500N |
| PAT_VIBRATION | vibration | 토크 진동 패턴 | Tx/Ty noise > 2x |
| PAT_OVERLOAD | overload | 지속 과부하 | Fz > 300N, 5s+ |
| PAT_DRIFT | drift | baseline 드리프트 | 10%+ deviation |

### 2.3 관계 정의

**INDICATES (SensorPattern → Cause)**
```json
{
  "type": "INDICATES",
  "properties": {
    "confidence": "float (0.0~1.0)",
    "evidence_type": "string (sensor)"
  }
}
```

**TRIGGERS (SensorPattern → ErrorCode)**
```json
{
  "type": "TRIGGERS",
  "properties": {
    "probability": "float",
    "typical_delay_ms": "number"
  }
}
```

---

## 3. ontology.json 확장

### 3.1 추가할 노드

```json
{
  "nodes": {
    "SensorPattern": [
      {
        "pattern_id": "PAT_COLLISION",
        "type": "collision",
        "description": "Z축 급격한 힘 증가 (충돌)",
        "threshold": {
          "axis": "Fz",
          "value": 500,
          "rise_time_ms": 100
        },
        "severity": "high"
      },
      {
        "pattern_id": "PAT_VIBRATION",
        "type": "vibration",
        "description": "토크 축 고주파 진동",
        "threshold": {
          "axis": "Tx,Ty",
          "multiplier": 2.0,
          "min_duration_s": 10
        },
        "severity": "medium"
      },
      {
        "pattern_id": "PAT_OVERLOAD",
        "type": "overload",
        "description": "지속적 과부하",
        "threshold": {
          "axis": "Fz",
          "value": 300,
          "duration_s": 5
        },
        "severity": "high"
      },
      {
        "pattern_id": "PAT_DRIFT",
        "type": "drift",
        "description": "Baseline 점진적 이동",
        "threshold": {
          "deviation_pct": 10,
          "min_duration_h": 0.5
        },
        "severity": "low"
      }
    ]
  }
}
```

### 3.2 추가할 관계

```json
{
  "relationships": [
    {
      "type": "INDICATES",
      "source": "PAT_COLLISION",
      "target": "CAUSE_PHYSICAL_CONTACT",
      "confidence": 0.9
    },
    {
      "type": "INDICATES",
      "source": "PAT_COLLISION",
      "target": "CAUSE_UNEXPECTED_OBSTACLE",
      "confidence": 0.85
    },
    {
      "type": "TRIGGERS",
      "source": "PAT_COLLISION",
      "target": "C153",
      "probability": 0.95
    },
    {
      "type": "TRIGGERS",
      "source": "PAT_COLLISION",
      "target": "C119",
      "probability": 0.8
    },
    {
      "type": "INDICATES",
      "source": "PAT_OVERLOAD",
      "target": "CAUSE_PAYLOAD_EXCEEDED",
      "confidence": 0.9
    },
    {
      "type": "TRIGGERS",
      "source": "PAT_OVERLOAD",
      "target": "C189",
      "probability": 0.9
    },
    {
      "type": "INDICATES",
      "source": "PAT_VIBRATION",
      "target": "CAUSE_JOINT_WEAR",
      "confidence": 0.7
    },
    {
      "type": "INDICATES",
      "source": "PAT_VIBRATION",
      "target": "CAUSE_LOOSE_BOLTS",
      "confidence": 0.65
    },
    {
      "type": "TRIGGERS",
      "source": "PAT_VIBRATION",
      "target": "C204",
      "probability": 0.75
    },
    {
      "type": "INDICATES",
      "source": "PAT_DRIFT",
      "target": "CAUSE_CALIBRATION_NEEDED",
      "confidence": 0.8
    }
  ]
}
```

---

## 4. Cypher 쿼리

### 4.1 패턴 → 원인 조회

```cypher
// 센서 패턴에서 가능한 원인 조회
MATCH (sp:SensorPattern {type: $pattern_type})-[r:INDICATES]->(c:Cause)
RETURN sp.pattern_id, c.description, r.confidence
ORDER BY r.confidence DESC
```

### 4.2 에러코드 → 연관 패턴 조회

```cypher
// 에러코드와 연관된 센서 패턴 조회
MATCH (sp:SensorPattern)-[r:TRIGGERS]->(e:ErrorCode {code: $error_code})
RETURN sp.type, sp.description, r.probability
```

### 4.3 통합 경로 조회

```cypher
// 센서 패턴 → 원인 → 에러코드 → 조치 경로
MATCH path = (sp:SensorPattern)-[:INDICATES]->(c:Cause)<-[:CAUSED_BY]-(e:ErrorCode)-[:RESOLVED_BY]->(r:Resolution)
WHERE sp.type = $pattern_type
RETURN path
```

---

## 5. GraphRetriever 확장

### 5.1 수정 사항

```python
class GraphRetriever:
    def retrieve_by_sensor_pattern(
        self,
        pattern_type: str,
        include_causes: bool = True,
        include_errors: bool = True
    ) -> List[GraphResult]:
        """
        센서 패턴 기반 그래프 검색

        Args:
            pattern_type: 패턴 유형 (collision, vibration, overload, drift)
            include_causes: 원인 포함 여부
            include_errors: 에러코드 포함 여부

        Returns:
            관련 노드/관계 목록
        """
```

### 5.2 통합 검색 메서드

```python
def retrieve_integrated(
    self,
    error_code: Optional[str] = None,
    pattern_type: Optional[str] = None,
    entity_ids: Optional[List[str]] = None
) -> HybridResult:
    """
    통합 검색 (에러코드 + 센서 패턴 + 엔티티)
    """
```

---

## 6. 구현 태스크

```
Main-S4-1: ontology.json 확장
├── data/processed/ontology/ontology.json 수정
├── SensorPattern 노드 4개 추가
├── INDICATES 관계 추가
├── TRIGGERS 관계 추가
└── 검증: JSON 스키마 검증

Main-S4-2: Neo4j 적재 스크립트 수정
├── scripts/run_ontology.py 수정
├── SensorPattern 노드 생성 쿼리
├── 새 관계 타입 처리
└── 검증: Neo4j 적재 확인

Main-S4-3: GraphRetriever 확장
├── src/rag/graph_retriever.py 수정
├── retrieve_by_sensor_pattern() 메서드 추가
├── retrieve_integrated() 메서드 추가
└── 검증: 단위 테스트

Main-S4-4: 단위 테스트
├── tests/unit/test_ontology_sensor.py 작성
├── 노드/관계 조회 테스트
└── 검증: 테스트 통과
```

---

## 7. 완료 기준

- [ ] ontology.json에 SensorPattern 노드 4개 추가
- [ ] INDICATES 관계 8개 이상 정의
- [ ] TRIGGERS 관계 4개 이상 정의
- [ ] Neo4j 적재 완료
- [ ] GraphRetriever 확장 완료
- [ ] Cypher 쿼리 테스트 통과
- [ ] 단위 테스트 100% 통과

---

## 8. 다음 단계

Main-S4 완료 후:
- Main-S5: Verifier 확장 (이중 검증, PARTIAL 상태)
- Main-S6: API/UI 확장

---

**참조**: Main__ROADMAP.md, Main_S2_패턴감지.md
