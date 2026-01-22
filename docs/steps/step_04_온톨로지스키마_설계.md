# Step 04: 온톨로지 스키마 - 설계서

## 1. 개요

### 1.1 Phase 정보
- **Phase 번호**: 04
- **Phase 명**: 온톨로지 스키마 설계 (Ontology Schema Design)
- **Stage**: Stage 2 - 온톨로지 핵심 (Ontology Core) ★
- **목표**: 4-Domain 온톨로지 스키마 정의

### 1.2 Phase 목표 (Unified_ROADMAP.md 기준)
- Equipment Domain 정의 (UR5e, Joints, ControlBox)
- Measurement Domain 정의 (Axia80, Axes, States, Patterns)
- Knowledge Domain 정의 (ErrorCodes, Causes, Resolutions)
- Context Domain 정의 (Shifts, Products, WorkCycles)
- 관계 타입 정의 (13개)

### 1.3 핵심 산출물
- `data/processed/ontology/schema.yaml` (스키마 정의)
- `src/ontology/__init__.py` (패키지 초기화)
- `src/ontology/schema.py` (EntityType, RelationType 정의)
- `src/ontology/models.py` (Entity, Relationship 데이터 모델)

---

## 2. 다룰 파일

### 2.1 핵심 구현 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `src/ontology/__init__.py` | 패키지 초기화 | 완료됨 (60줄) |
| `src/ontology/schema.py` | 타입 정의 (Enum) | 완료됨 (130줄) |
| `src/ontology/models.py` | 데이터 모델 | 완료됨 (180줄) |

### 2.2 데이터 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `data/processed/ontology/schema.yaml` | 스키마 정의 | 완료됨 (280줄) |

### 2.3 참조 문서 (기존)

| 파일 경로 | 설명 | 상태 |
|-----------|------|------|
| `docs/온톨로지_스키마_설계.md` | 온톨로지 상세 설계 | 존재 |

---

## 3. 설계 상세

### 3.1 4-Domain 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        UR5e Ontology Domains                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │                   │  │                   │  │                   │   │
│  │    Equipment      │  │   Measurement     │  │    Knowledge      │   │
│  │    Domain         │◀─▶    Domain         │◀─▶    Domain         │   │
│  │                   │  │                   │  │                   │   │
│  │   물리적 장비     │  │   센서/측정       │  │   문제해결 지식   │   │
│  │                   │  │                   │  │                   │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘   │
│           │                     │                     │                 │
│           ▼                     ▼                     ▼                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │ • Robot           │  │ • Sensor          │  │ • ErrorCode       │   │
│  │ • Joint           │  │ • MeasurementAxis │  │ • Cause           │   │
│  │ • ControlBox      │  │ • State           │  │ • Resolution      │   │
│  │ • ToolFlange      │  │ • Pattern         │  │ • Document        │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘   │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Context Domain (운영 컨텍스트)                  │  │
│  │                                                                   │  │
│  │   • Shift (A/B/C조)  • Product (PART-A/B/C)  • WorkCycle         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Entity Type 정의

```python
from enum import Enum

class Domain(str, Enum):
    """온톨로지 도메인"""
    EQUIPMENT = "equipment"
    MEASUREMENT = "measurement"
    KNOWLEDGE = "knowledge"
    CONTEXT = "context"

class EntityType(str, Enum):
    """엔티티 타입"""
    # Equipment Domain
    ROBOT = "Robot"
    JOINT = "Joint"
    CONTROL_BOX = "ControlBox"
    TOOL_FLANGE = "ToolFlange"

    # Measurement Domain
    SENSOR = "Sensor"
    MEASUREMENT_AXIS = "MeasurementAxis"
    STATE = "State"
    PATTERN = "Pattern"

    # Knowledge Domain
    ERROR_CODE = "ErrorCode"
    CAUSE = "Cause"
    RESOLUTION = "Resolution"
    DOCUMENT = "Document"

    # Context Domain
    SHIFT = "Shift"
    PRODUCT = "Product"
    WORK_CYCLE = "WorkCycle"
```

### 3.3 Relationship Type 정의

```python
class RelationType(str, Enum):
    """관계 타입"""
    # Equipment 관계
    HAS_COMPONENT = "HAS_COMPONENT"     # Robot → Joint
    MOUNTED_ON = "MOUNTED_ON"           # Sensor → ToolFlange

    # Measurement 관계
    MEASURES = "MEASURES"               # Sensor → Axis
    HAS_STATE = "HAS_STATE"             # Axis → State
    INDICATES = "INDICATES"             # Pattern → Cause
    TRIGGERS = "TRIGGERS"               # Pattern → ErrorCode

    # Knowledge 관계
    CAUSED_BY = "CAUSED_BY"             # ErrorCode → Cause
    RESOLVED_BY = "RESOLVED_BY"         # Cause → Resolution
    DOCUMENTED_IN = "DOCUMENTED_IN"     # ErrorCode → Document
    PREVENTS = "PREVENTS"               # Resolution → ErrorCode
    AFFECTS = "AFFECTS"                 # ErrorCode → Joint

    # Context 관계
    OCCURS_DURING = "OCCURS_DURING"     # Event → Shift
    INVOLVES = "INVOLVES"               # Event → Product
```

### 3.4 Entity 데이터 모델

```python
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class Entity:
    """온톨로지 엔티티"""
    id: str                     # 엔티티 ID (예: "UR5e", "Fz", "C153")
    type: EntityType            # 엔티티 타입
    domain: Domain              # 소속 도메인
    name: str                   # 표시 이름
    properties: Dict[str, Any] = field(default_factory=dict)  # 속성

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "type": self.type.value,
            "domain": self.domain.value,
            "name": self.name,
            "properties": self.properties,
        }

@dataclass
class Relationship:
    """온톨로지 관계"""
    source: str                 # 소스 엔티티 ID
    relation: RelationType      # 관계 타입
    target: str                 # 타겟 엔티티 ID
    properties: Dict[str, Any] = field(default_factory=dict)  # 속성 (confidence 등)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "source": self.source,
            "relation": self.relation.value,
            "target": self.target,
            "properties": self.properties,
        }
```

### 3.5 schema.yaml 구조

```yaml
# data/processed/ontology/schema.yaml
version: "1.0"
created_at: "2026-01-22"
description: "UR5e 온톨로지 스키마 정의"

domains:
  equipment:
    description: "물리적 장비 도메인"
    entities:
      - Robot
      - Joint
      - ControlBox
      - ToolFlange

  measurement:
    description: "센서/측정 도메인"
    entities:
      - Sensor
      - MeasurementAxis
      - State
      - Pattern

  knowledge:
    description: "문제해결 지식 도메인"
    entities:
      - ErrorCode
      - Cause
      - Resolution
      - Document

  context:
    description: "운영 컨텍스트 도메인"
    entities:
      - Shift
      - Product
      - WorkCycle

entity_types:
  Robot:
    domain: equipment
    description: "협동로봇"
    properties:
      - payload_kg: float
      - reach_mm: float
      - dof: int

  Joint:
    domain: equipment
    description: "로봇 관절"
    properties:
      - index: int
      - max_torque_nm: float
      - max_speed_deg_s: float

  Sensor:
    domain: measurement
    description: "센서"
    properties:
      - type: string
      - sampling_rate_hz: int

  MeasurementAxis:
    domain: measurement
    description: "측정축"
    properties:
      - direction: string
      - unit: string
      - range: [float, float]
      - normal_range: [float, float]

  State:
    domain: measurement
    description: "센서 상태"
    properties:
      - severity: string
      - range: [float, float]

  Pattern:
    domain: measurement
    description: "이상 패턴"
    properties:
      - severity: string
      - detection_condition: string

  ErrorCode:
    domain: knowledge
    description: "에러 코드"
    properties:
      - category: string
      - severity: string

  Cause:
    domain: knowledge
    description: "에러 원인"
    properties:
      - category: string

  Resolution:
    domain: knowledge
    description: "해결책"
    properties:
      - steps: [string]

  Document:
    domain: knowledge
    description: "문서"
    properties:
      - doc_type: string
      - topics: [string]

  Shift:
    domain: context
    description: "근무조"
    properties:
      - hours: string

  Product:
    domain: context
    description: "제품"
    properties:
      - payload_kg: float
      - class: string

  WorkCycle:
    domain: context
    description: "작업 단계"
    properties:
      - phases: [string]

relationship_types:
  HAS_COMPONENT:
    source_types: [Robot]
    target_types: [Joint, ControlBox, ToolFlange]
    description: "장비 계층 관계"

  MOUNTED_ON:
    source_types: [Sensor]
    target_types: [ToolFlange]
    description: "센서 장착 관계"

  MEASURES:
    source_types: [Sensor]
    target_types: [MeasurementAxis]
    description: "측정 대상 관계"

  HAS_STATE:
    source_types: [MeasurementAxis]
    target_types: [State]
    description: "상태 보유 관계"

  INDICATES:
    source_types: [Pattern]
    target_types: [Cause]
    description: "패턴 → 원인 관계"
    properties:
      - confidence: float

  TRIGGERS:
    source_types: [Pattern]
    target_types: [ErrorCode]
    description: "패턴 → 에러 관계"
    properties:
      - confidence: float

  CAUSED_BY:
    source_types: [ErrorCode]
    target_types: [Cause]
    description: "에러 → 원인 관계"

  RESOLVED_BY:
    source_types: [Cause]
    target_types: [Resolution]
    description: "원인 → 해결 관계"

  DOCUMENTED_IN:
    source_types: [ErrorCode, Cause, Resolution]
    target_types: [Document]
    description: "문서 참조 관계"
    properties:
      - page: int

  PREVENTS:
    source_types: [Resolution]
    target_types: [ErrorCode]
    description: "해결 → 예방 관계"

  AFFECTS:
    source_types: [ErrorCode]
    target_types: [Joint]
    description: "영향 컴포넌트 관계"

  OCCURS_DURING:
    source_types: [Pattern]
    target_types: [Shift]
    description: "발생 시간 관계"

  INVOLVES:
    source_types: [Pattern]
    target_types: [Product]
    description: "관련 제품 관계"
```

---

## 4. 온톨로지 연결

### 4.1 Phase 5 (엔티티/관계 구축)과의 연결

Phase 4에서 정의된 스키마가 Phase 5에서 인스턴스화됩니다.

```
Phase 4 (스키마)                    Phase 5 (인스턴스)
─────────────────                   ─────────────────
EntityType.ROBOT         →         Entity("UR5e", ROBOT, ...)
EntityType.JOINT         →         Entity("Joint_0", JOINT, ...)
RelationType.HAS_COMPONENT →       Relationship("UR5e", HAS_COMPONENT, "Joint_0")
```

### 4.2 Phase 10-12 (RAG)와의 연결

| Phase 4 산출물 | RAG 사용처 |
|---------------|------------|
| EntityType | 엔티티 인식 시 타입 분류 |
| RelationType | 관계 탐색 시 경로 타입 |
| schema.yaml | 질문 분류 시 도메인 판단 |

---

## 5. Unified_Spec.md 정합성 검증

### 5.1 온톨로지 구조 요구사항

| Spec 요구사항 | Phase 4 구현 내용 | 충족 여부 |
|--------------|------------------|----------|
| 4-Domain 아키텍처 | Domain Enum 정의 | O |
| Equipment 엔티티 | Robot, Joint, ControlBox, ToolFlange | O |
| Measurement 엔티티 | Sensor, MeasurementAxis, State, Pattern | O |
| Knowledge 엔티티 | ErrorCode, Cause, Resolution, Document | O |
| Context 엔티티 | Shift, Product, WorkCycle | O |
| 13개 관계 타입 | RelationType Enum 정의 | O |

### 5.2 API 명세 연결

| Spec API | Phase 4 지원 |
|----------|-------------|
| GET /api/v1/ontology/entity/{id} | Entity 모델 반환 |
| GET /api/v1/ontology/relations/{id} | Relationship 목록 반환 |

---

## 6. 구현 체크리스트

### 6.1 스키마 정의

- [x] `data/processed/ontology/schema.yaml` 작성

### 6.2 코드 구현

- [x] `src/ontology/__init__.py` - 패키지 초기화
- [x] `src/ontology/schema.py` - Domain, EntityType, RelationType Enum
- [x] `src/ontology/models.py` - Entity, Relationship 데이터클래스

### 6.3 검증 명령어

```python
# 스키마 검증
from src.ontology import Domain, EntityType, RelationType, Entity, Relationship

# 도메인 확인
print(list(Domain))
# [Domain.EQUIPMENT, Domain.MEASUREMENT, Domain.KNOWLEDGE, Domain.CONTEXT]

# 엔티티 타입 확인
equipment_types = [e for e in EntityType if e.value in ["Robot", "Joint", "ControlBox", "ToolFlange"]]
print(f"Equipment 타입: {len(equipment_types)}개")

# 관계 타입 확인
print(f"관계 타입: {len(RelationType)}개")

# Entity 생성 테스트
ur5e = Entity(
    id="UR5e",
    type=EntityType.ROBOT,
    domain=Domain.EQUIPMENT,
    name="UR5e 협동로봇",
    properties={"payload_kg": 5.0, "reach_mm": 850}
)
print(ur5e.to_dict())
```

---

## 7. 설계 결정 사항

### 7.1 YAML vs JSON 선택

**결정**: schema.yaml (YAML 형식) 사용

**근거**:
1. 가독성: 계층 구조가 명확
2. 주석: 인라인 주석 지원
3. 편집: 수동 편집 용이
4. 호환성: Python pyyaml로 쉽게 로딩

### 7.2 Enum 기반 타입 정의

**결정**: str Enum으로 타입 정의

**근거**:
1. 타입 안정성: IDE 자동완성 지원
2. 검증: 잘못된 타입 사용 방지
3. 직렬화: str 상속으로 JSON 직렬화 용이

### 7.3 DataClass 기반 모델

**결정**: @dataclass로 Entity, Relationship 정의

**근거**:
1. 간결성: 보일러플레이트 최소화
2. 불변성: frozen=True 옵션 가능
3. 호환성: Pydantic 마이그레이션 용이

---

## 8. 다음 Phase 연결

### Phase 5 (엔티티/관계 구축)와의 연결

| Phase 4 산출물 | Phase 5 사용처 |
|---------------|---------------|
| EntityType | 인스턴스 타입 지정 |
| RelationType | 관계 타입 지정 |
| schema.yaml | 유효성 검증 기준 |
| Entity 모델 | 인스턴스 데이터 구조 |
| Relationship 모델 | 관계 데이터 구조 |

### Phase 6 (추론 규칙)와의 연결

| Phase 4 산출물 | Phase 6 사용처 |
|---------------|---------------|
| State 엔티티 타입 | 상태 추론 규칙 |
| Pattern 엔티티 타입 | 패턴 매칭 규칙 |
| INDICATES, TRIGGERS 관계 | 원인/에러 추론 |

---

*작성일: 2026-01-22*
*리팩토링일: 2026-01-22*
*Phase: 04 - 온톨로지 스키마*
*문서 버전: v2.0*
