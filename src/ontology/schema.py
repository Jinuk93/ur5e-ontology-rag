# ============================================================
# src/ontology/schema.py - 온톨로지 스키마 정의
# ============================================================
# UR5e 로봇 매뉴얼의 지식 구조를 정의합니다.
#
# Entity Types (노드 유형):
#   - Component: 부품 (Control Box, Joint, Cable...)
#   - ErrorCode: 에러 코드 (C4, C10, C17...)
#   - Procedure: 절차 (케이블 점검, 조인트 교체...)
#
# Relation Types (관계 유형):
#   - HAS_ERROR: 부품 → 에러코드
#   - RESOLVED_BY: 에러코드 → 절차
#   - CONTAINS: 부품 → 부품
#   - DESCRIBES: 청크 → 엔티티
# ============================================================

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


# ============================================================
# [1] Entity Types (노드 유형)
# ============================================================

class EntityType(str, Enum):
    """
    엔티티 유형 정의

    예시:
        EntityType.COMPONENT  # 부품
        EntityType.ERROR_CODE  # 에러 코드
    """
    COMPONENT = "Component"      # 부품
    ERROR_CODE = "ErrorCode"     # 에러 코드
    PROCEDURE = "Procedure"      # 절차/해결책
    DOCUMENT = "Document"        # 문서
    CHUNK = "Chunk"              # 청크 (VectorDB 연결)


# ============================================================
# [2] Relation Types (관계 유형)
# ============================================================

class RelationType(str, Enum):
    """
    관계 유형 정의

    예시:
        RelationType.HAS_ERROR  # 부품 → 에러코드
        RelationType.RESOLVED_BY  # 에러코드 → 절차
    """
    # Component 관련
    HAS_ERROR = "HAS_ERROR"          # Component → ErrorCode
    CONTAINS = "CONTAINS"            # Component → Component
    CONNECTED_TO = "CONNECTED_TO"    # Component → Component

    # ErrorCode 관련
    CAUSED_BY = "CAUSED_BY"          # ErrorCode → Component
    RESOLVED_BY = "RESOLVED_BY"      # ErrorCode → Procedure

    # Document/Chunk 관련
    MENTIONED_IN = "MENTIONED_IN"    # Entity → Document
    HAS_CHUNK = "HAS_CHUNK"          # Document → Chunk
    DESCRIBES = "DESCRIBES"          # Chunk → Entity


# ============================================================
# [3] Entity 클래스
# ============================================================

@dataclass
class Entity:
    """
    엔티티 (그래프의 노드)

    Attributes:
        id: 고유 식별자
        type: 엔티티 유형 (Component, ErrorCode, Procedure...)
        name: 이름
        properties: 추가 속성

    사용 예시:
        entity = Entity(
            id="component_control_box",
            type=EntityType.COMPONENT,
            name="Control Box",
            properties={"location": "base"}
        )
    """
    id: str
    type: EntityType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            **self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """딕셔너리에서 생성"""
        entity_type = data.pop("type")
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type)

        return cls(
            id=data.pop("id"),
            type=entity_type,
            name=data.pop("name"),
            properties=data,
        )


# ============================================================
# [4] Relation 클래스
# ============================================================

@dataclass
class Relation:
    """
    관계 (그래프의 엣지)

    Attributes:
        source_id: 시작 노드 ID
        target_id: 끝 노드 ID
        type: 관계 유형
        properties: 추가 속성

    사용 예시:
        relation = Relation(
            source_id="component_control_box",
            target_id="error_code_c4",
            type=RelationType.HAS_ERROR,
            properties={"severity": "high"}
        )
    """
    source_id: str
    target_id: str
    type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.value,
            **self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relation":
        """딕셔너리에서 생성"""
        relation_type = data.pop("type")
        if isinstance(relation_type, str):
            relation_type = RelationType(relation_type)

        return cls(
            source_id=data.pop("source_id"),
            target_id=data.pop("target_id"),
            type=relation_type,
            properties=data,
        )


# ============================================================
# [5] 스키마 검증 함수
# ============================================================

# 유효한 관계 정의 (source_type → relation → target_type)
VALID_RELATIONS = {
    RelationType.HAS_ERROR: (EntityType.COMPONENT, EntityType.ERROR_CODE),
    RelationType.RESOLVED_BY: (EntityType.ERROR_CODE, EntityType.PROCEDURE),
    RelationType.CAUSED_BY: (EntityType.ERROR_CODE, EntityType.COMPONENT),
    RelationType.CONTAINS: (EntityType.COMPONENT, EntityType.COMPONENT),
    RelationType.CONNECTED_TO: (EntityType.COMPONENT, EntityType.COMPONENT),
    RelationType.MENTIONED_IN: (None, EntityType.DOCUMENT),  # Any → Document
    RelationType.HAS_CHUNK: (EntityType.DOCUMENT, EntityType.CHUNK),
    RelationType.DESCRIBES: (EntityType.CHUNK, None),  # Chunk → Any
}


def validate_relation(
    relation: Relation,
    source_entity: Entity,
    target_entity: Entity,
) -> bool:
    """
    관계가 유효한지 검증

    Args:
        relation: 검증할 관계
        source_entity: 시작 노드 엔티티
        target_entity: 끝 노드 엔티티

    Returns:
        bool: 유효하면 True

    Raises:
        ValueError: 유효하지 않은 관계
    """
    if relation.type not in VALID_RELATIONS:
        raise ValueError(f"Unknown relation type: {relation.type}")

    valid_source, valid_target = VALID_RELATIONS[relation.type]

    # None은 모든 타입 허용
    if valid_source is not None and source_entity.type != valid_source:
        raise ValueError(
            f"Invalid source type for {relation.type}: "
            f"expected {valid_source}, got {source_entity.type}"
        )

    if valid_target is not None and target_entity.type != valid_target:
        raise ValueError(
            f"Invalid target type for {relation.type}: "
            f"expected {valid_target}, got {target_entity.type}"
        )

    return True


# ============================================================
# [6] 헬퍼 함수
# ============================================================

def create_component(
    name: str,
    component_type: str = "general",
    location: str = "",
    **kwargs
) -> Entity:
    """Component 엔티티 생성 헬퍼"""
    entity_id = f"component_{name.lower().replace(' ', '_')}"
    return Entity(
        id=entity_id,
        type=EntityType.COMPONENT,
        name=name,
        properties={
            "component_type": component_type,
            "location": location,
            **kwargs,
        }
    )


def create_error_code(
    code: str,
    title: str = "",
    severity: str = "unknown",
    description: str = "",
    **kwargs
) -> Entity:
    """ErrorCode 엔티티 생성 헬퍼"""
    entity_id = f"error_{code.lower()}"
    return Entity(
        id=entity_id,
        type=EntityType.ERROR_CODE,
        name=code,
        properties={
            "code": code,
            "title": title,
            "severity": severity,
            "description": description,
            **kwargs,
        }
    )


def create_procedure(
    name: str,
    steps: List[str] = None,
    tools_required: List[str] = None,
    **kwargs
) -> Entity:
    """Procedure 엔티티 생성 헬퍼"""
    entity_id = f"procedure_{name.lower().replace(' ', '_')}"
    return Entity(
        id=entity_id,
        type=EntityType.PROCEDURE,
        name=name,
        properties={
            "steps": steps or [],
            "tools_required": tools_required or [],
            **kwargs,
        }
    )


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("[*] Schema Test")
    print("=" * 50)

    # 엔티티 생성 테스트
    control_box = create_component("Control Box", component_type="main", location="base")
    error_c4 = create_error_code("C4", title="Communication error", severity="high")
    check_cable = create_procedure("Check Cable", steps=["Step 1", "Step 2"])

    print(f"\n[Entity] {control_box.name}")
    print(f"  Type: {control_box.type.value}")
    print(f"  ID: {control_box.id}")
    print(f"  Properties: {control_box.properties}")

    print(f"\n[Entity] {error_c4.name}")
    print(f"  Type: {error_c4.type.value}")
    print(f"  ID: {error_c4.id}")

    # 관계 생성 테스트
    relation = Relation(
        source_id=control_box.id,
        target_id=error_c4.id,
        type=RelationType.HAS_ERROR,
    )
    print(f"\n[Relation] {relation.source_id} -[{relation.type.value}]-> {relation.target_id}")

    # 검증 테스트
    is_valid = validate_relation(relation, control_box, error_c4)
    print(f"  Valid: {is_valid}")

    print("\n" + "=" * 50)
    print("[OK] Schema test passed!")
    print("=" * 50)
