"""Evidence Schema 단위 테스트"""

import pytest
from src.rag.evidence_schema import (
    QueryType,
    DocumentReference,
    OntologyPath,
    Evidence,
    ExtractedEntity,
    ClassificationResult,
)


class TestQueryTypeEnum:
    """QueryType 열거형 테스트"""

    def test_query_type_values(self):
        """QueryType 값 테스트"""
        assert QueryType.ONTOLOGY.value == "ontology"
        assert QueryType.HYBRID.value == "hybrid"
        assert QueryType.RAG.value == "rag"

    def test_query_type_is_str_enum(self):
        """QueryType이 str Enum인지 테스트"""
        assert isinstance(QueryType.ONTOLOGY, str)
        assert QueryType.ONTOLOGY == "ontology"


class TestDocumentReference:
    """DocumentReference 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        ref = DocumentReference(
            doc_id="service_manual",
            page=45,
            chunk_id="SM-045-01",
            relevance=0.85,
            snippet="관련 텍스트",
        )
        assert ref.doc_id == "service_manual"
        assert ref.page == 45
        assert ref.relevance == 0.85

    def test_to_dict(self):
        """to_dict 변환 테스트"""
        ref = DocumentReference(
            doc_id="test_doc",
            relevance=0.9,
        )
        d = ref.to_dict()

        assert d["doc_id"] == "test_doc"
        assert d["relevance"] == 0.9
        assert "page" in d
        assert "chunk_id" in d


class TestOntologyPath:
    """OntologyPath 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        path = OntologyPath(
            path=["Fz", "CRITICAL", "PAT_OVERLOAD"],
            relations=["HAS_STATE", "INDICATES"],
            confidence=0.9,
        )
        assert path.path == ["Fz", "CRITICAL", "PAT_OVERLOAD"]
        assert len(path.relations) == 2

    def test_path_string_format(self):
        """경로 문자열 포맷 테스트"""
        path = OntologyPath(
            path=["Fz", "CRITICAL", "PAT_OVERLOAD"],
            relations=["HAS_STATE", "INDICATES"],
        )
        d = path.to_dict()
        path_string = d["path_string"]

        assert "Fz" in path_string
        assert "HAS_STATE" in path_string
        assert "CRITICAL" in path_string

    def test_empty_path(self):
        """빈 경로 테스트"""
        path = OntologyPath(path=[], relations=[])
        d = path.to_dict()

        assert d["path_string"] == ""


class TestEvidence:
    """Evidence 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        evidence = Evidence()
        assert evidence.ontology_paths == []
        assert evidence.document_refs == []
        assert evidence.similar_events == []

    def test_add_ontology_path(self):
        """온톨로지 경로 추가 테스트"""
        evidence = Evidence()
        path = OntologyPath(
            path=["A", "B"],
            relations=["REL"],
            confidence=0.8,
        )
        evidence.add_ontology_path(path)

        assert len(evidence.ontology_paths) == 1
        assert evidence.ontology_paths[0].confidence == 0.8

    def test_add_document_ref(self):
        """문서 참조 추가 테스트"""
        evidence = Evidence()
        ref = DocumentReference(doc_id="test", relevance=0.9)
        evidence.add_document_ref(ref)

        assert len(evidence.document_refs) == 1

    def test_has_evidence(self):
        """근거 존재 여부 테스트"""
        evidence = Evidence()
        assert evidence.has_evidence() is False

        evidence.add_ontology_path(
            OntologyPath(path=["A"], relations=[], confidence=1.0)
        )
        assert evidence.has_evidence() is True

    def test_primary_path(self):
        """주요 경로 (최고 신뢰도) 테스트"""
        evidence = Evidence()
        evidence.add_ontology_path(
            OntologyPath(path=["A"], relations=[], confidence=0.5)
        )
        evidence.add_ontology_path(
            OntologyPath(path=["B"], relations=[], confidence=0.9)
        )
        evidence.add_ontology_path(
            OntologyPath(path=["C"], relations=[], confidence=0.7)
        )

        primary = evidence.primary_path
        assert primary.path == ["B"]
        assert primary.confidence == 0.9

    def test_primary_path_empty(self):
        """빈 Evidence의 primary_path 테스트"""
        evidence = Evidence()
        assert evidence.primary_path is None

    def test_to_dict(self):
        """to_dict 변환 테스트"""
        evidence = Evidence(similar_events=["EVT001", "EVT002"])
        d = evidence.to_dict()

        assert "ontology_paths" in d
        assert "document_refs" in d
        assert d["similar_events"] == ["EVT001", "EVT002"]


class TestExtractedEntity:
    """ExtractedEntity 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        entity = ExtractedEntity(
            text="Fz",
            entity_id="Fz",
            entity_type="MeasurementAxis",
            confidence=0.95,
        )
        assert entity.text == "Fz"
        assert entity.entity_type == "MeasurementAxis"

    def test_to_dict(self):
        """to_dict 변환 테스트"""
        entity = ExtractedEntity(
            text="-350N",
            entity_id="-350",
            entity_type="Value",
            confidence=0.9,
            properties={"unit": "N"},
        )
        d = entity.to_dict()

        assert d["text"] == "-350N"
        assert d["properties"]["unit"] == "N"


class TestClassificationResult:
    """ClassificationResult 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        result = ClassificationResult(
            query="테스트 질문",
            query_type=QueryType.ONTOLOGY,
            confidence=0.85,
        )
        assert result.query == "테스트 질문"
        assert result.query_type == QueryType.ONTOLOGY

    def test_has_entities(self):
        """엔티티 존재 여부 테스트"""
        result = ClassificationResult(
            query="test",
            query_type=QueryType.RAG,
            confidence=0.5,
            entities=[],
        )
        assert result.has_entities() is False

        result.entities.append(
            ExtractedEntity(
                text="Fz", entity_id="Fz",
                entity_type="MeasurementAxis", confidence=0.9
            )
        )
        assert result.has_entities() is True

    def test_get_entities_by_type(self):
        """타입별 엔티티 조회 테스트"""
        result = ClassificationResult(
            query="Fz가 -350N이고 Tx는 10Nm",
            query_type=QueryType.ONTOLOGY,
            confidence=0.9,
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.95
                ),
                ExtractedEntity(
                    text="-350N", entity_id="-350",
                    entity_type="Value", confidence=0.9
                ),
                ExtractedEntity(
                    text="Tx", entity_id="Tx",
                    entity_type="MeasurementAxis", confidence=0.95
                ),
                ExtractedEntity(
                    text="10Nm", entity_id="10",
                    entity_type="Value", confidence=0.9
                ),
            ],
        )

        axes = result.get_entities_by_type("MeasurementAxis")
        values = result.get_entities_by_type("Value")

        assert len(axes) == 2
        assert len(values) == 2
        assert all(e.entity_type == "MeasurementAxis" for e in axes)

    def test_to_dict(self):
        """to_dict 변환 테스트"""
        result = ClassificationResult(
            query="test",
            query_type=QueryType.HYBRID,
            confidence=0.75,
            indicators=["error_context", "resolution"],
            metadata={"scores": {"ontology": 0.3}},
        )
        d = result.to_dict()

        assert d["query_type"] == "hybrid"
        assert d["confidence"] == 0.75
        assert "error_context" in d["indicators"]
        assert "scores" in d["metadata"]
