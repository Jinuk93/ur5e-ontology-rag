"""
RAG (Retrieval-Augmented Generation) 모듈

질문 분류, 엔티티 추출, 근거 추적 기능을 제공합니다.

사용 예시:
    from src.rag import QueryClassifier, EntityExtractor, QueryType

    # 질문 분류
    classifier = QueryClassifier()
    result = classifier.classify("Fz가 -350N인데 이게 뭐야?")
    print(result.query_type)  # QueryType.ONTOLOGY
    print(result.entities)    # [ExtractedEntity(Fz), ExtractedEntity(-350N)]

    # 엔티티 추출
    extractor = EntityExtractor()
    entities = extractor.extract("C153 에러가 발생했어")
    print(entities)  # [ExtractedEntity(C153)]
"""

from .evidence_schema import (
    QueryType,
    DocumentReference,
    OntologyPath,
    Evidence,
    ExtractedEntity,
    ClassificationResult,
)
from .entity_extractor import (
    EntityExtractor,
    create_entity_extractor,
)
from .query_classifier import (
    QueryClassifier,
    create_query_classifier,
)

__all__ = [
    # Evidence Schema
    "QueryType",
    "DocumentReference",
    "OntologyPath",
    "Evidence",
    "ExtractedEntity",
    "ClassificationResult",
    # Entity Extractor
    "EntityExtractor",
    "create_entity_extractor",
    # Query Classifier
    "QueryClassifier",
    "create_query_classifier",
]
