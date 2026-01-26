"""
온톨로지 스키마 정의

4-Domain 온톨로지의 타입 정의를 제공합니다.
"""

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
    TEACH_PENDANT = "TeachPendant"  # v2.0 추가
    SAFETY_BOARD = "SafetyBoard"  # v2.0 추가
    MOTHERBOARD = "Motherboard"  # v2.0 추가

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
    EVENT = "Event"  # 패턴 발생 인스턴스 (traceability)


class RelationType(str, Enum):
    """관계 타입"""
    # Equipment 관계
    HAS_COMPONENT = "HAS_COMPONENT"     # Robot → Joint, ControlBox, ToolFlange
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
    INSTANCE_OF = "INSTANCE_OF"         # Event → Pattern (발생 인스턴스 → 정의)
    OCCURS_DURING = "OCCURS_DURING"     # Event → Shift
    INVOLVES = "INVOLVES"               # Event → Product


# 도메인별 엔티티 타입 매핑
DOMAIN_ENTITY_TYPES = {
    Domain.EQUIPMENT: [
        EntityType.ROBOT,
        EntityType.JOINT,
        EntityType.CONTROL_BOX,
        EntityType.TOOL_FLANGE,
        EntityType.TEACH_PENDANT,
        EntityType.SAFETY_BOARD,
        EntityType.MOTHERBOARD,
    ],
    Domain.MEASUREMENT: [
        EntityType.SENSOR,
        EntityType.MEASUREMENT_AXIS,
        EntityType.STATE,
        EntityType.PATTERN,
    ],
    Domain.KNOWLEDGE: [
        EntityType.ERROR_CODE,
        EntityType.CAUSE,
        EntityType.RESOLUTION,
        EntityType.DOCUMENT,
    ],
    Domain.CONTEXT: [
        EntityType.SHIFT,
        EntityType.PRODUCT,
        EntityType.WORK_CYCLE,
        EntityType.EVENT,
    ],
}


# 엔티티 타입 → 도메인 역매핑
ENTITY_TYPE_TO_DOMAIN = {
    entity_type: domain
    for domain, entity_types in DOMAIN_ENTITY_TYPES.items()
    for entity_type in entity_types
}


# 관계 타입별 유효한 소스/타겟 타입
RELATIONSHIP_CONSTRAINTS = {
    RelationType.HAS_COMPONENT: {
        "source_types": [EntityType.ROBOT, EntityType.CONTROL_BOX],
        "target_types": [EntityType.JOINT, EntityType.CONTROL_BOX, EntityType.TOOL_FLANGE,
                        EntityType.TEACH_PENDANT, EntityType.SAFETY_BOARD, EntityType.MOTHERBOARD],
    },
    RelationType.MOUNTED_ON: {
        "source_types": [EntityType.SENSOR],
        "target_types": [EntityType.TOOL_FLANGE],
    },
    RelationType.MEASURES: {
        "source_types": [EntityType.SENSOR],
        "target_types": [EntityType.MEASUREMENT_AXIS],
    },
    RelationType.HAS_STATE: {
        "source_types": [EntityType.MEASUREMENT_AXIS],
        "target_types": [EntityType.STATE],
    },
    RelationType.INDICATES: {
        "source_types": [EntityType.PATTERN],
        "target_types": [EntityType.CAUSE],
    },
    RelationType.TRIGGERS: {
        "source_types": [EntityType.PATTERN],
        "target_types": [EntityType.ERROR_CODE],
    },
    RelationType.CAUSED_BY: {
        "source_types": [EntityType.ERROR_CODE],
        "target_types": [EntityType.CAUSE],
    },
    RelationType.RESOLVED_BY: {
        "source_types": [EntityType.CAUSE],
        "target_types": [EntityType.RESOLUTION],
    },
    RelationType.DOCUMENTED_IN: {
        "source_types": [EntityType.ERROR_CODE, EntityType.CAUSE, EntityType.RESOLUTION, EntityType.SENSOR],
        "target_types": [EntityType.DOCUMENT],
    },
    RelationType.PREVENTS: {
        "source_types": [EntityType.RESOLUTION],
        "target_types": [EntityType.ERROR_CODE],
    },
    RelationType.AFFECTS: {
        "source_types": [EntityType.ERROR_CODE],
        "target_types": [EntityType.JOINT],
    },
    RelationType.INSTANCE_OF: {
        "source_types": [EntityType.EVENT],
        "target_types": [EntityType.PATTERN],
    },
    RelationType.OCCURS_DURING: {
        "source_types": [EntityType.EVENT, EntityType.PATTERN],
        "target_types": [EntityType.SHIFT],
    },
    RelationType.INVOLVES: {
        "source_types": [EntityType.EVENT, EntityType.PATTERN],
        "target_types": [EntityType.PRODUCT],
    },
}


def get_domain_for_entity_type(entity_type: EntityType) -> Domain:
    """엔티티 타입의 도메인 반환"""
    return ENTITY_TYPE_TO_DOMAIN[entity_type]


def get_entity_types_for_domain(domain: Domain) -> list[EntityType]:
    """도메인의 엔티티 타입 목록 반환"""
    return DOMAIN_ENTITY_TYPES[domain]


def validate_relationship(
    relation_type: RelationType,
    source_type: EntityType,
    target_type: EntityType,
) -> bool:
    """관계의 소스/타겟 타입 유효성 검증"""
    constraints = RELATIONSHIP_CONSTRAINTS.get(relation_type)
    if not constraints:
        return True

    source_valid = source_type in constraints["source_types"]
    target_valid = target_type in constraints["target_types"]

    return source_valid and target_valid
