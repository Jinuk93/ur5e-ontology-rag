# Step 04: 온톨로지 스키마 - 완료 보고서

## 1. 요약

| 항목 | 내용 |
|------|------|
| Phase | 04 - 온톨로지 스키마 설계 (Ontology Schema Design) |
| 상태 | **완료** |
| 시작일 | 2026-01-22 |
| 완료일 | 2026-01-22 |
| 리팩토링일 | 2026-01-22 |
| 작업자 | Claude Code |

---

## 2. 완료된 작업

### 2.1 구현 파일 목록

| 파일 | 라인 수 | 상태 | 설명 |
|------|--------|------|------|
| `src/ontology/__init__.py` | 60 | 신규 작성 | 패키지 초기화 및 모듈 노출 |
| `src/ontology/schema.py` | 130 | 신규 작성 | Domain, EntityType, RelationType 정의 |
| `src/ontology/models.py` | 180 | 신규 작성 | Entity, Relationship, OntologySchema 모델 |
| `data/processed/ontology/schema.yaml` | 280 | 신규 작성 | 스키마 정의 파일 |

### 2.2 스키마 통계

| 항목 | 수량 |
|------|------|
| 도메인 (Domain) | 4개 |
| 엔티티 타입 (EntityType) | 15개 |
| 관계 타입 (RelationType) | 13개 |

---

## 3. 구현 상세

### 3.1 4-Domain 아키텍처

```
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Equipment   │  │  Measurement  │  │   Knowledge   │  │    Context    │
│               │  │               │  │               │  │               │
│ • Robot       │  │ • Sensor      │  │ • ErrorCode   │  │ • Shift       │
│ • Joint       │  │ • Axis        │  │ • Cause       │  │ • Product     │
│ • ControlBox  │  │ • State       │  │ • Resolution  │  │ • WorkCycle   │
│ • ToolFlange  │  │ • Pattern     │  │ • Document    │  │               │
└───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘
```

### 3.2 Domain Enum

```python
class Domain(str, Enum):
    EQUIPMENT = "equipment"
    MEASUREMENT = "measurement"
    KNOWLEDGE = "knowledge"
    CONTEXT = "context"
```

### 3.3 EntityType Enum (15개)

| 도메인 | 엔티티 타입 |
|--------|------------|
| Equipment | Robot, Joint, ControlBox, ToolFlange |
| Measurement | Sensor, MeasurementAxis, State, Pattern |
| Knowledge | ErrorCode, Cause, Resolution, Document |
| Context | Shift, Product, WorkCycle |

### 3.4 RelationType Enum (13개)

| 관계 | 설명 | Source → Target |
|------|------|-----------------|
| HAS_COMPONENT | 장비 계층 | Robot → Joint |
| MOUNTED_ON | 센서 장착 | Sensor → ToolFlange |
| MEASURES | 측정 대상 | Sensor → Axis |
| HAS_STATE | 상태 보유 | Axis → State |
| INDICATES | 패턴→원인 | Pattern → Cause |
| TRIGGERS | 패턴→에러 | Pattern → ErrorCode |
| CAUSED_BY | 에러→원인 | ErrorCode → Cause |
| RESOLVED_BY | 원인→해결 | Cause → Resolution |
| DOCUMENTED_IN | 문서 참조 | ErrorCode → Document |
| PREVENTS | 해결→예방 | Resolution → ErrorCode |
| AFFECTS | 영향 컴포넌트 | ErrorCode → Joint |
| OCCURS_DURING | 발생 시간 | Pattern → Shift |
| INVOLVES | 관련 제품 | Pattern → Product |

### 3.5 데이터 모델

```python
@dataclass
class Entity:
    id: str                  # "UR5e", "Fz", "C153"
    type: EntityType         # EntityType.ROBOT
    name: str                # "UR5e 협동로봇"
    domain: Domain           # Domain.EQUIPMENT (자동 설정)
    properties: Dict         # {"payload_kg": 5.0}

@dataclass
class Relationship:
    source: str              # "UR5e"
    relation: RelationType   # RelationType.HAS_COMPONENT
    target: str              # "Joint_0"
    properties: Dict         # {"confidence": 0.95}

@dataclass
class OntologySchema:
    version: str
    description: str
    entities: List[Entity]
    relationships: List[Relationship]
```

---

## 4. 사용법

### 4.1 기본 사용

```python
from src.ontology import (
    Domain, EntityType, RelationType,
    Entity, Relationship, OntologySchema
)

# 엔티티 생성
ur5e = Entity(
    id="UR5e",
    type=EntityType.ROBOT,
    name="UR5e 협동로봇",
    properties={"payload_kg": 5.0, "reach_mm": 850}
)
print(ur5e.domain)  # Domain.EQUIPMENT (자동 설정)

# 관계 생성
rel = Relationship(
    source="UR5e",
    relation=RelationType.HAS_COMPONENT,
    target="Joint_0"
)

# 스키마 생성
schema = OntologySchema(
    version="1.0",
    description="UR5e 온톨로지"
)
schema.add_entity(ur5e)
schema.add_relationship(rel)

# 조회
print(schema.get_entity("UR5e"))
print(schema.get_entities_by_domain(Domain.EQUIPMENT))
print(schema.get_relationships_for_entity("UR5e"))
```

### 4.2 유틸리티 함수

```python
from src.ontology import (
    get_domain_for_entity_type,
    get_entity_types_for_domain,
    validate_relationship
)

# 엔티티 타입 → 도메인
domain = get_domain_for_entity_type(EntityType.ROBOT)
# Domain.EQUIPMENT

# 도메인 → 엔티티 타입 목록
types = get_entity_types_for_domain(Domain.MEASUREMENT)
# [EntityType.SENSOR, EntityType.MEASUREMENT_AXIS, ...]

# 관계 유효성 검증
valid = validate_relationship(
    RelationType.HAS_COMPONENT,
    EntityType.ROBOT,
    EntityType.JOINT
)
# True
```

---

## 5. 아키텍처 정합성

### 5.1 Unified_ROADMAP.md 충족 사항

| ROADMAP 요구사항 | 구현 내용 | 상태 |
|-----------------|----------|------|
| Equipment Domain 정의 | Robot, Joint, ControlBox, ToolFlange | O |
| Measurement Domain 정의 | Sensor, MeasurementAxis, State, Pattern | O |
| Knowledge Domain 정의 | ErrorCode, Cause, Resolution, Document | O |
| Context Domain 정의 | Shift, Product, WorkCycle | O |
| 13개 관계 타입 | RelationType Enum | O |

### 5.2 Unified_Spec.md 충족 사항

| Spec 요구사항 | 구현 내용 | 상태 |
|--------------|----------|------|
| 4-Domain 아키텍처 | Domain Enum | O |
| 엔티티 타입 정의 | EntityType Enum (15개) | O |
| 관계 타입 정의 | RelationType Enum (13개) | O |
| 관계 제약 조건 | RELATIONSHIP_CONSTRAINTS | O |

### 5.3 온톨로지 스키마 연결점

```
Phase 4 (스키마)                    Phase 5 (인스턴스)
─────────────────                   ─────────────────
EntityType.ROBOT         →         Entity("UR5e", ROBOT, ...)
EntityType.JOINT         →         Entity("Joint_0", JOINT, ...)
RelationType.HAS_COMPONENT →       Relationship("UR5e", HAS_COMPONENT, "Joint_0")
```

---

## 6. 폴더 구조

```
ur5e-ontology-rag/
├── data/
│   └── processed/
│       └── ontology/
│           └── schema.yaml [신규]
│
└── src/
    └── ontology/
        ├── __init__.py [신규]
        ├── schema.py [신규]
        └── models.py [신규]
```

---

## 7. 다음 단계 준비

### Phase 5 (엔티티/관계 구축)와의 연결

| Phase 4 산출물 | Phase 5 사용처 |
|---------------|---------------|
| EntityType | 인스턴스 타입 지정 |
| RelationType | 관계 타입 지정 |
| Entity 모델 | 인스턴스 데이터 구조 |
| Relationship 모델 | 관계 데이터 구조 |
| validate_relationship() | 관계 유효성 검증 |

### 준비 사항

```python
# Phase 5에서 사용할 코드
from src.ontology import (
    EntityType, RelationType,
    Entity, Relationship, OntologySchema
)

# 온톨로지 인스턴스 생성
schema = OntologySchema(
    version="1.0",
    description="UR5e 온톨로지 인스턴스"
)

# Equipment 엔티티 추가
ur5e = Entity(
    id="UR5e",
    type=EntityType.ROBOT,
    name="UR5e 협동로봇",
    properties={"payload_kg": 5.0}
)
schema.add_entity(ur5e)

# 관계 추가
for i in range(6):
    schema.add_relationship(Relationship(
        source="UR5e",
        relation=RelationType.HAS_COMPONENT,
        target=f"Joint_{i}"
    ))

# JSON으로 저장
import json
with open("data/processed/ontology/ontology.json", "w") as f:
    json.dump(schema.to_dict(), f, indent=2)
```

---

## 8. 이슈 및 참고사항

### 8.1 해결된 이슈

없음 - 구현 완료

### 8.2 설계 결정

1. **str Enum 사용**: JSON 직렬화 용이, IDE 자동완성 지원
2. **dataclass 사용**: 보일러플레이트 최소화, Pydantic 마이그레이션 용이
3. **도메인 자동 설정**: Entity 생성 시 타입에서 도메인 자동 추론

### 8.3 검증 명령어

```python
# 모듈 임포트 검증
from src.ontology import Domain, EntityType, RelationType

print(f"도메인: {len(Domain)}개")
print(f"엔티티 타입: {len(EntityType)}개")
print(f"관계 타입: {len(RelationType)}개")
```

---

## 9. 리팩토링 수행 내역

### 9.1 설계서 업데이트 (v1.0 → v2.0)

| 추가/변경 섹션 | 내용 |
|---------------|------|
| 구현 상태 업데이트 | "신규 작성" → "완료됨 (X줄)" 상태 반영 |
| 체크리스트 완료 | [ ] → [x] 모든 항목 완료 표시 |

### 9.2 코드 검증

| 항목 | 검증 결과 |
|------|----------|
| `src/ontology/__init__.py` | 완료 (60줄) - 모듈 정상 노출 |
| `src/ontology/schema.py` | 완료 (130줄) - Enum 정상 정의 |
| `src/ontology/models.py` | 완료 (180줄) - 데이터클래스 정상 |
| `data/processed/ontology/schema.yaml` | 완료 (280줄) - 스키마 정상 |

### 9.3 검증 코드

```python
>>> from src.ontology import Domain, EntityType, RelationType
>>> print(f'도메인: {len(Domain)}개')
도메인: 4개
>>> print(f'엔티티 타입: {len(EntityType)}개')
엔티티 타입: 15개
>>> print(f'관계 타입: {len(RelationType)}개')
관계 타입: 13개
```

모든 검증 테스트 통과 확인.

---

## 10. 문서 정보

| 항목 | 값 |
|------|---|
| 문서 버전 | v2.0 (리팩토링 완료) |
| 작성일 | 2026-01-22 |
| 리팩토링일 | 2026-01-22 |
| 설계서 참조 | [step_04_온톨로지스키마_설계.md](step_04_온톨로지스키마_설계.md) |
| ROADMAP 섹션 | A.2 Phase 4 |
| Spec 섹션 | Section 6 |

---

*Phase 04 완료. Phase 05 (엔티티/관계 구축)로 진행합니다.*
