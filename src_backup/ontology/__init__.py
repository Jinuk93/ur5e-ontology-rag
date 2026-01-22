# ============================================================
# src/ontology/__init__.py - 온톨로지 모듈
# ============================================================
# 지식 구조(온톨로지)를 설계하고 Neo4j에 저장합니다.
#
# 주요 클래스:
#   - Entity: 엔티티 (Component, ErrorCode, Procedure)
#   - Relation: 관계 (HAS_ERROR, RESOLVED_BY 등)
#   - GraphStore: Neo4j 연동
#   - EntityExtractor: LLM으로 엔티티 추출
# ============================================================

from .schema import (
    Entity,
    EntityType,
    Relation,
    RelationType,
)
from .graph_store import GraphStore
from .entity_extractor import EntityExtractor

__all__ = [
    "Entity",
    "EntityType",
    "Relation",
    "RelationType",
    "GraphStore",
    "EntityExtractor",
]
