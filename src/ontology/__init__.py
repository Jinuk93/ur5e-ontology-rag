"""
온톨로지 모듈

4-Domain 온톨로지 스키마 정의 및 데이터 모델을 제공합니다.

도메인 구조:
- Equipment Domain: 물리적 장비 (Robot, Joint, ControlBox, ToolFlange)
- Measurement Domain: 센서/측정 (Sensor, MeasurementAxis, State, Pattern)
- Knowledge Domain: 문제해결 지식 (ErrorCode, Cause, Resolution, Document)
- Context Domain: 운영 컨텍스트 (Shift, Product, WorkCycle)

사용 예시:
    from src.ontology import (
        Domain, EntityType, RelationType,
        Entity, Relationship, OntologySchema,
        load_ontology, load_lexicon
    )

    # 온톨로지 로드
    schema = load_ontology()

    # 엔티티 조회
    ur5e = schema.get_entity("UR5e")

    # 관계 조회
    rels = schema.get_relationships_for_entity("UR5e")

    # 동의어 해석
    from src.ontology import resolve_alias
    entity_id = resolve_alias("컨트롤 박스")  # "Control Box"
"""

from .schema import (
    Domain,
    EntityType,
    RelationType,
    DOMAIN_ENTITY_TYPES,
    ENTITY_TYPE_TO_DOMAIN,
    RELATIONSHIP_CONSTRAINTS,
    get_domain_for_entity_type,
    get_entity_types_for_domain,
    validate_relationship,
)
from .models import (
    Entity,
    Relationship,
    OntologySchema,
)
from .loader import (
    OntologyLoader,
    load_ontology,
    save_ontology,
    load_lexicon,
    resolve_alias,
)
from .rule_engine import (
    RuleEngine,
    InferenceResult,
    create_rule_engine,
)

__all__ = [
    # Enums
    "Domain",
    "EntityType",
    "RelationType",
    # Mappings
    "DOMAIN_ENTITY_TYPES",
    "ENTITY_TYPE_TO_DOMAIN",
    "RELATIONSHIP_CONSTRAINTS",
    # Functions
    "get_domain_for_entity_type",
    "get_entity_types_for_domain",
    "validate_relationship",
    # Models
    "Entity",
    "Relationship",
    "OntologySchema",
    # Loader
    "OntologyLoader",
    "load_ontology",
    "save_ontology",
    "load_lexicon",
    "resolve_alias",
    # RuleEngine
    "RuleEngine",
    "InferenceResult",
    "create_rule_engine",
]
