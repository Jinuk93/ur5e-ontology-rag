# Step 05: 엔티티/관계 구축 - 완료 보고서

## 1. 요약

| 항목 | 내용 |
|------|------|
| Phase | 05 - 엔티티/관계 구축 (Entity/Relationship Population) |
| 상태 | **완료** |
---

## 2. 완료된 작업

### 2.1 구현 파일 목록

| 파일 | 라인 수 | 상태 | 설명 |
|------|--------|------|------|
| `src/ontology/loader.py` | 204 | 신규 작성 | OntologyLoader 클래스 |
| `data/processed/ontology/ontology.json` | 501 | 업데이트 | 전체 온톨로지 인스턴스 |
| `data/processed/ontology/lexicon.yaml` | 402 | 기존 유지 | 동의어 사전 |
| `scripts/build_ontology.py` | 215 | 신규 작성 | 빌드/검증 스크립트 |
| `src/ontology/__init__.py` | 89 | 업데이트 | loader 모듈 노출 |

### 2.2 온톨로지 통계

| 항목 | 수량 |
|------|------|
| 총 엔티티 | 54개 |
| 총 관계 | 62개 |

### 2.3 도메인별 엔티티 분포

| 도메인 | 엔티티 수 | 주요 엔티티 |
|--------|----------|------------|
| Equipment | 9 | UR5e, Joint_0~5, ControlBox, ToolFlange |
| Measurement | 14 | Axia80, Fx~Fz, Tx~Tz, States, Patterns |
| Knowledge | 26 | C153, C119, C189, Causes, Resolutions, Documents |
| Context | 5 | Shift_Day/Night, Product_A/B, WorkCycle_Assembly |

### 2.4 관계 타입별 분포

| 관계 타입 | 수량 | 예시 |
|----------|------|------|
| HAS_COMPONENT | 8 | UR5e → Joint_0~5, ControlBox, ToolFlange |
| MOUNTED_ON | 1 | Axia80 → ToolFlange |
| MEASURES | 6 | Axia80 → Fx, Fy, Fz, Tx, Ty, Tz |
| HAS_STATE | 6 | 각 축 → State_Normal |
| INDICATES | 5 | PAT_COLLISION → CAUSE_COLLISION |
| TRIGGERS | 4 | PAT_COLLISION → C153, C119 |
| CAUSED_BY | 11 | C153 → CAUSE_COLLISION |
| RESOLVED_BY | 5 | CAUSE_COLLISION → RES_CLEAR_PATH |
| DOCUMENTED_IN | 4 | C153 → DOC_USER_MANUAL |
| PREVENTS | 4 | RES_CLEAR_PATH → C153 |
| AFFECTS | 6 | C50~C55 → Joint_0~5 |
| OCCURS_DURING | 1 | PAT_COLLISION → Shift_Day |
| INVOLVES | 1 | PAT_OVERLOAD → Product_B |

---

## 3. 구현 상세

### 3.1 OntologyLoader 클래스

```python
class OntologyLoader:
    """온톨로지 로더/저장"""

    DEFAULT_PATH = Path("data/processed/ontology/ontology.json")
    LEXICON_PATH = Path("data/processed/ontology/lexicon.yaml")

    @classmethod
    def load(cls, path=None, use_cache=True) -> OntologySchema:
        """온톨로지 로드 (캐시 지원)"""

    @classmethod
    def save(cls, schema, path=None) -> None:
        """온톨로지 저장"""

    @classmethod
    def load_lexicon(cls, path=None, use_cache=True) -> Dict:
        """동의어 사전 로드"""

    @classmethod
    def resolve_alias(cls, term, lexicon=None) -> Optional[str]:
        """동의어를 표준 ID로 변환"""

    @classmethod
    def get_aliases(cls, entity_id, lexicon=None) -> List[str]:
        """엔티티의 별칭 목록 반환"""

    @classmethod
    def clear_cache(cls) -> None:
        """캐시 초기화"""
```

### 3.2 ontology.json 구조

```json
{
  "version": "1.0",
  "description": "UR5e 협동로봇 온톨로지 - 4-Domain Architecture",

  "entities": [
    {
      "id": "UR5e",
      "type": "Robot",
      "domain": "equipment",
      "name": "UR5e 협동로봇",
      "properties": {"payload_kg": 5.0, "reach_mm": 850}
    }
    // ... 54 entities
  ],

  "relationships": [
    {
      "source": "UR5e",
      "relation": "HAS_COMPONENT",
      "target": "Joint_0"
    }
    // ... 62 relationships
  ]
}
```

### 3.3 Lexicon 호환성

기존 lexicon.yaml 형식을 지원하도록 loader를 수정:

```python
# 두 가지 형식 모두 지원
categories = ["entities", "error_codes", "components"]
alias_keys = ["aliases", "synonyms"]
```

### 3.4 빌드 스크립트 검증 결과

```
============================================================
[*] Build Complete
============================================================

  Total Entities: 54
  Total Relationships: 62
  Validation: PASS
```

---

## 4. 사용법

### 4.1 온톨로지 로드

```python
from src.ontology import load_ontology, load_lexicon

# 온톨로지 로드
schema = load_ontology()
print(f"Entities: {len(schema.entities)}")
print(f"Relationships: {len(schema.relationships)}")

# 엔티티 조회
ur5e = schema.get_entity("UR5e")
joints = schema.get_entities_by_type(EntityType.JOINT)
equipment = schema.get_entities_by_domain(Domain.EQUIPMENT)
```

### 4.2 관계 조회

```python
# UR5e의 모든 관계
rels = schema.get_relationships_for_entity("UR5e")

# 나가는 관계만
outgoing = schema.get_relationships_for_entity("UR5e", direction="outgoing")

# 관계 타입별
has_component = schema.get_relationships_by_type(RelationType.HAS_COMPONENT)
```

### 4.3 동의어 해석

```python
from src.ontology import resolve_alias

# 다양한 표현을 표준 ID로 변환 (ontology.json entity ID와 일치)
resolve_alias("c153")        # "C153"
resolve_alias("컨트롤 박스")   # "ControlBox"
resolve_alias("joint 0")     # "Joint_0"
resolve_alias("axia80")      # "Axia80"
```

### 4.4 빌드 스크립트 실행

```bash
python scripts/build_ontology.py
```

---

## 5. 아키텍처 정합성

### 5.1 Unified_ROADMAP.md 충족 사항

| ROADMAP 요구사항 | 구현 내용 | 상태 |
|-----------------|----------|------|
| Equipment 엔티티 생성 | 9개 엔티티 (UR5e, Joints, etc.) | O |
| Measurement 엔티티 생성 | 14개 엔티티 (Sensor, Axes, etc.) | O |
| Knowledge 엔티티 생성 | 26개 엔티티 (ErrorCodes, Causes, etc.) | O |
| Context 엔티티 생성 | 5개 엔티티 (Shifts, Products, etc.) | O |
| 관계 인스턴스 생성 | 62개 관계 | O |

### 5.2 Phase 5와 Phase 6 연결점

```
Phase 5 (엔티티/관계)              Phase 6 (동의어 사전)
─────────────────                   ─────────────────
OntologySchema.entities  →          EntityLinker 입력
lexicon.yaml            →          resolve_alias() 함수
```

---

## 6. 폴더 구조

```
ur5e-ontology-rag/
├── data/
│   └── processed/
│       └── ontology/
│           ├── ontology.json [업데이트]   # 전체 온톨로지
│           ├── lexicon.yaml [기존]        # 동의어 사전
│           └── schema.yaml                # 스키마 정의
│
├── scripts/
│   └── build_ontology.py [신규]           # 빌드/검증 스크립트
│
└── src/
    └── ontology/
        ├── __init__.py [업데이트]         # loader 노출
        ├── schema.py                      # Enum 정의
        ├── models.py                      # 데이터 모델
        └── loader.py [신규]               # OntologyLoader
```

---

## 7. 다음 단계 준비

### Phase 6 (추론 규칙)와의 연결

| Phase 5 산출물 | Phase 6 사용처 |
|---------------|---------------|
| ontology.json | RuleEngine 엔티티/관계 참조 |
| State 엔티티 | infer_state() 결과 매핑 |
| Pattern 엔티티 | detect_patterns() 결과 |
| INDICATES/TRIGGERS 관계 | cause_rules, pattern_error_mapping |

### 준비 사항

```python
# Phase 6에서 사용할 코드
from src.ontology import create_rule_engine, load_ontology

# 온톨로지 로드
schema = load_ontology()

# 규칙 엔진 초기화
engine = create_rule_engine()

# 상태 추론
state = engine.infer_state("Fz", -180.0)
print(f"State: {state.result_id}")  # State_Warning
```

---

## 8. 이슈 및 참고사항

### 8.1 해결된 이슈

1. **Lexicon 형식 호환성**: 기존 lexicon.yaml의 `synonyms` 키와 새 형식의 `aliases` 키 모두 지원하도록 수정
2. **Sensor→Document 관계 검증**: DOCUMENTED_IN 제약 조건에 Sensor를 추가하여 검증 통과

### 8.2 해결된 이슈 (v2.2)

1. **관계 검증 PASS**: OCCURS_DURING/INVOLVES 제약 수정됨
   - `schema.py`: Pattern도 source로 허용하도록 수정
   - 검증 결과: Valid 62개, Invalid 0개

2. **resolve_alias → entity ID 일치**: lexicon.yaml canonical 수정됨
   - `resolve_alias("컨트롤 박스")` → `"ControlBox"` (ontology ID와 일치)
   - `resolve_alias("joint 0")` → `"Joint_0"` (ontology ID와 일치)
   - `schema.get_entity(resolve_alias(...))` 정상 동작

### 8.3 검증 명령어

```bash
# 온톨로지 빌드 및 검증
python scripts/build_ontology.py

# Python에서 직접 테스트
python -c "
from src.ontology import load_ontology
schema = load_ontology()
print(f'Entities: {len(schema.entities)}')
print(f'Relationships: {len(schema.relationships)}')
"
```

---

## 9. 문서 업데이트 내역

### 9.1 설계서 업데이트 (v1.0 → v2.0)

| 추가/변경 섹션 | 내용 |
|---------------|------|
| 구현 상태 업데이트 | "신규 작성" → "완료됨 (X줄)" 상태 반영 |
| 체크리스트 완료 | [ ] → [x] 모든 항목 완료 표시 |
| 실제 구현 결과 | Section 10 추가 - 최종 통계 및 검증 결과 |

### 9.2 코드 리팩토링

| 파일 | 변경 내용 |
|------|----------|
| `src/ontology/schema.py` | DOCUMENTED_IN 제약 조건에 Sensor 추가 |

### 9.3 검증 결과 (v2.2)

```bash
python scripts/build_ontology.py

============================================================
[*] Build Complete
============================================================

  Total Entities: 54
  Total Relationships: 62
  Validation: PASS

  Alias Resolution Test:
    'control box' -> 'ControlBox'
    'joint 0' -> 'Joint_0'
```

---

### 9.4 코드/데이터 수정 내역 (v2.2)

| 파일 | 변경 내용 |
|------|----------|
| `src/ontology/schema.py` | OCCURS_DURING/INVOLVES에 Pattern 추가 |
| `data/processed/ontology/lexicon.yaml` | canonical을 ontology entity ID와 일치시킴 |

---

## 10. 문서 정보

| 항목 | 값 |
|------|---|
| 문서 버전 | v2.2 |
| 작성일 | 2026-01-22 |
| 최종 갱신일 | 2026-01-22 |
| 설계서 참조 | [step_05_엔티티관계구축_설계.md](step_05_엔티티관계구축_설계.md) |
| ROADMAP 섹션 | A.2 Phase 5 |
| Spec 섹션 | Section 6 |

---

*Phase 05 완료. Phase 06 (추론규칙)으로 진행합니다.*
