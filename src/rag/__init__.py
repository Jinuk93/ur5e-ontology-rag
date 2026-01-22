"""
RAG (Retrieval-Augmented Generation) 모듈

질문 분류, 엔티티 추출, 응답 생성, 근거 추적 기능을 제공합니다.

사용 예시:
    from src.rag import QueryClassifier, EntityExtractor, ResponseGenerator, QueryType
    from src.ontology import OntologyEngine

    # 질문 분류
    classifier = QueryClassifier()
    result = classifier.classify("Fz가 -350N인데 이게 뭐야?")
    print(result.query_type)  # QueryType.ONTOLOGY

    # 추론
    engine = OntologyEngine()
    entities = [e.to_dict() for e in result.entities]
    reasoning = engine.reason(result.query, entities)

    # 응답 생성
    generator = ResponseGenerator()
    response = generator.generate(result, reasoning)
    print(response.answer)
    print(response.evidence)
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
from .confidence_gate import (
    ConfidenceGate,
    GateResult,
    create_confidence_gate,
)
from .prompt_builder import (
    PromptBuilder,
    create_prompt_builder,
)
from .response_generator import (
    ResponseGenerator,
    GeneratedResponse,
    create_response_generator,
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
    # Confidence Gate
    "ConfidenceGate",
    "GateResult",
    "create_confidence_gate",
    # Prompt Builder
    "PromptBuilder",
    "create_prompt_builder",
    # Response Generator
    "ResponseGenerator",
    "GeneratedResponse",
    "create_response_generator",
]
