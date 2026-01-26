"""ResponseGenerator 단위 테스트"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.rag.response_generator import (
    ResponseGenerator,
    GeneratedResponse,
    create_response_generator,
)
from src.rag.evidence_schema import (
    QueryType,
    ClassificationResult,
    ExtractedEntity,
    DocumentReference,
)
from src.rag.confidence_gate import GateResult


@dataclass
class MockReasoningResult:
    """모의 추론 결과"""
    query: str = "테스트 쿼리"
    entities: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_chain: List[Dict[str, Any]] = field(default_factory=list)
    conclusions: List[Dict[str, Any]] = field(default_factory=list)
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    ontology_paths: List[str] = field(default_factory=list)
    confidence: float = 0.85
    evidence: Dict[str, Any] = field(default_factory=dict)


class TestResponseGeneratorInit:
    """ResponseGenerator 초기화 테스트"""

    def test_init_with_defaults(self):
        """기본값으로 초기화"""
        generator = ResponseGenerator()

        assert generator.confidence_gate is not None
        assert generator.prompt_builder is not None
        assert generator.llm_client is None

    def test_init_with_llm_client(self):
        """LLM 클라이언트로 초기화"""
        mock_llm = Mock()
        generator = ResponseGenerator(llm_client=mock_llm)

        assert generator.llm_client is mock_llm


class TestResponseGeneratorAbstain:
    """ResponseGenerator ABSTAIN 응답 테스트"""

    @pytest.fixture
    def generator(self):
        return ResponseGenerator()

    @pytest.fixture
    def classification_no_entities(self):
        """엔티티 없는 분류 결과"""
        return ClassificationResult(
            query="안녕하세요",
            query_type=QueryType.RAG,
            entities=[],
            confidence=0.3,
        )

    @pytest.fixture
    def classification_with_entities(self):
        """엔티티 있는 분류 결과"""
        return ClassificationResult(
            query="Fz가 -350N인데 뭐야?",
            query_type=QueryType.ONTOLOGY,
            entities=[
                ExtractedEntity(
                    entity_id="Fz",
                    entity_type="MeasurementAxis",
                    text="Fz",
                    confidence=0.95,
                ),
            ],
            confidence=0.9,
        )

    def test_abstain_no_entities(self, generator, classification_no_entities):
        """엔티티 없을 때 ABSTAIN"""
        reasoning = MockReasoningResult()

        response = generator.generate(classification_no_entities, reasoning)

        assert response.abstain is True
        assert "구체적인" in response.answer

    def test_abstain_message_no_entities(self, generator, classification_no_entities):
        """no entities ABSTAIN 메시지 확인"""
        gate_result = GateResult(
            passed=False,
            confidence=0.0,
            abstain_reason="no entities extracted",
        )

        answer, recommendation = generator._build_abstain_message(
            gate_result.abstain_reason,
            classification_no_entities
        )

        assert "구체적인 대상" in answer
        assert "examples" in recommendation

    def test_abstain_message_low_classification_confidence(self, generator, classification_with_entities):
        """낮은 분류 신뢰도 ABSTAIN 메시지"""
        answer, recommendation = generator._build_abstain_message(
            "classification confidence too low",
            classification_with_entities
        )

        assert "의도를 명확히" in answer
        assert "명확하게" in recommendation["immediate"]

    def test_abstain_message_low_entity_confidence(self, generator, classification_with_entities):
        """낮은 엔티티 신뢰도 ABSTAIN 메시지"""
        answer, recommendation = generator._build_abstain_message(
            "entity confidence too low",
            classification_with_entities
        )

        assert "신뢰도가 낮습니다" in answer

    def test_abstain_message_no_reasoning_chain(self, generator, classification_with_entities):
        """추론 경로 없음 ABSTAIN 메시지"""
        answer, recommendation = generator._build_abstain_message(
            "no reasoning chain",
            classification_with_entities
        )

        assert "추론 경로를 찾지 못했습니다" in answer
        assert "온톨로지에 등록된 항목" in recommendation.get("reference", "")

    def test_abstain_message_low_reasoning_confidence(self, generator, classification_with_entities):
        """낮은 추론 신뢰도 ABSTAIN 메시지"""
        answer, recommendation = generator._build_abstain_message(
            "reasoning confidence too low",
            classification_with_entities
        )

        assert "신뢰도가 충분하지 않습니다" in answer

    def test_abstain_message_unknown_reason(self, generator, classification_with_entities):
        """알 수 없는 사유 ABSTAIN 메시지 (기본 응답)"""
        answer, recommendation = generator._build_abstain_message(
            "some unknown reason",
            classification_with_entities
        )

        assert "충분한 근거를 찾지 못했습니다" in answer


class TestResponseGeneratorNormalResponse:
    """ResponseGenerator 정상 응답 테스트"""

    @pytest.fixture
    def generator(self):
        return ResponseGenerator()

    @pytest.fixture
    def classification(self):
        """정상 분류 결과"""
        return ClassificationResult(
            query="Fz가 -350N인데 뭐야?",
            query_type=QueryType.ONTOLOGY,
            entities=[
                ExtractedEntity(
                    entity_id="Fz",
                    entity_type="MeasurementAxis",
                    text="Fz",
                    confidence=0.95,
                ),
                ExtractedEntity(
                    entity_id="-350.0N",
                    entity_type="Value",
                    text="-350N",
                    confidence=0.9,
                ),
            ],
            confidence=0.9,
        )

    @pytest.fixture
    def reasoning_with_state(self):
        """상태 결론이 있는 추론 결과"""
        return MockReasoningResult(
            entities=[{"entity_id": "Fz", "entity_type": "MeasurementAxis"}],
            conclusions=[
                {
                    "type": "state",
                    "entity": "Fz",
                    "state": "CRITICAL",
                    "confidence": 0.95,
                },
                {
                    "type": "pattern",
                    "pattern": "PAT_COLLISION",
                    "confidence": 0.85,
                },
                {
                    "type": "cause",
                    "cause": "CAUSE_PHYSICAL_CONTACT",
                    "pattern": "PAT_COLLISION",
                    "confidence": 0.8,
                },
            ],
            recommendations=[
                {
                    "action": "장애물 제거 및 작업 영역 확인",
                    "reference": "매뉴얼 5장 참조",
                }
            ],
            ontology_paths=["Fz →[HAS_STATE]→ CRITICAL →[INDICATES]→ PAT_COLLISION"],
            confidence=0.85,
        )

    def test_generate_normal_response(self, generator, classification, reasoning_with_state):
        """정상 응답 생성"""
        # confidence_gate가 passed=True 반환하도록 설정
        mock_gate_result = Mock()
        mock_gate_result.passed = True
        mock_gate_result.confidence = 0.85
        mock_gate_result.reason = None
        generator.confidence_gate.evaluate = Mock(return_value=mock_gate_result)

        response = generator.generate(classification, reasoning_with_state)

        assert response.abstain is False
        assert response.trace_id is not None
        assert response.query_type.upper() == "ONTOLOGY"

    def test_build_analysis_extracts_entity(self, generator, classification, reasoning_with_state):
        """분석 결과에서 엔티티 추출"""
        analysis = generator._build_analysis(classification, reasoning_with_state)

        # 엔티티 또는 상태가 포함되어야 함
        assert "entity" in analysis or "state" in analysis

    def test_build_recommendation(self, generator, reasoning_with_state):
        """권장사항 구성"""
        recommendation = generator._build_recommendation(reasoning_with_state)

        assert "immediate" in recommendation
        assert recommendation["immediate"] == "장애물 제거 및 작업 영역 확인"
        assert recommendation["reference"] == "매뉴얼 5장 참조"

    def test_build_evidence_with_document_refs(self, generator, reasoning_with_state):
        """문서 참조 포함 근거 구성"""
        doc_refs = [
            DocumentReference(
                doc_id="manual.pdf",
                page=10,
                chunk_id="chunk_1",
                relevance=0.85,
                snippet="C153 에러 해결법...",
            ),
        ]

        evidence = generator._build_evidence(reasoning_with_state, doc_refs)

        assert "document_refs" in evidence
        assert len(evidence["document_refs"]) == 1


class TestResponseGeneratorGraphData:
    """ResponseGenerator 그래프 데이터 테스트"""

    @pytest.fixture
    def generator(self):
        return ResponseGenerator()

    def test_build_graph_data_from_conclusions(self, generator):
        """결론에서 그래프 데이터 추출"""
        reasoning = MockReasoningResult(
            entities=[{"entity_id": "Fz", "entity_type": "MeasurementAxis"}],
            conclusions=[
                {"type": "state", "entity": "Fz", "state": "CRITICAL"},
                {"type": "pattern", "pattern": "PAT_COLLISION"},
                {"type": "cause", "cause": "CAUSE_COLLISION", "pattern": "PAT_COLLISION"},
            ],
        )

        graph = generator._build_graph_data(reasoning)

        assert "nodes" in graph
        assert "edges" in graph
        # 노드들이 추출되었는지 확인
        node_ids = [n["id"] for n in graph["nodes"]]
        assert "Fz" in node_ids or "CRITICAL" in node_ids or "PAT_COLLISION" in node_ids

    def test_build_graph_data_triggered_error(self, generator):
        """triggered_error 결론 처리"""
        reasoning = MockReasoningResult(
            entities=[],
            conclusions=[
                {"type": "triggered_error", "error": "C153", "pattern": "PAT_OVERLOAD"},
            ],
        )

        graph = generator._build_graph_data(reasoning)

        node_ids = [n["id"] for n in graph["nodes"]]
        assert "C153" in node_ids
        assert "PAT_OVERLOAD" in node_ids

        # TRIGGERS 관계 확인
        edge_relations = [e["relation"] for e in graph["edges"]]
        assert "TRIGGERS" in edge_relations


class TestResponseGeneratorTemplateResponse:
    """ResponseGenerator 템플릿 응답 테스트"""

    @pytest.fixture
    def generator(self):
        return ResponseGenerator()

    @pytest.fixture
    def classification(self):
        return ClassificationResult(
            query="Fz가 -350N인데 뭐야?",
            query_type=QueryType.ONTOLOGY,
            entities=[
                ExtractedEntity(
                    entity_id="Fz",
                    entity_type="MeasurementAxis",
                    text="Fz",
                    confidence=0.95,
                ),
            ],
            confidence=0.9,
        )

    def test_template_response_with_definition(self, generator, classification):
        """정의 결론이 있을 때 템플릿 응답"""
        reasoning = MockReasoningResult(
            conclusions=[
                {
                    "type": "definition",
                    "entity_id": "Fz",
                    "entity_name": "Fz",
                    "description": "Fz는 Z축 힘을 측정합니다.",
                    "properties": {"normal_range": [-10, 10], "unit": "N"},
                },
            ],
        )
        analysis = {}
        prediction = None
        recommendation = {}

        response = generator._generate_template_response(
            classification, reasoning, analysis, prediction, recommendation
        )

        assert "Fz" in response
        assert "Z축" in response or "정상 범위" in response

    def test_template_response_with_string_conclusion(self, generator, classification):
        """문자열 결론 처리"""
        reasoning = MockReasoningResult(
            conclusions=["Axia80 센서가 Fz를 측정합니다."],
        )

        response = generator._generate_template_response(
            classification, reasoning, {}, None, {}
        )

        assert "Axia80" in response or "측정합니다" in response


class TestCreateResponseGenerator:
    """create_response_generator 팩토리 함수 테스트"""

    def test_create_without_llm(self):
        """LLM 없이 생성"""
        generator = create_response_generator()

        assert isinstance(generator, ResponseGenerator)
        assert generator.llm_client is None

    def test_create_with_llm(self):
        """LLM으로 생성"""
        mock_llm = Mock()
        generator = create_response_generator(llm_client=mock_llm)

        assert generator.llm_client is mock_llm


class TestGeneratedResponseDataclass:
    """GeneratedResponse 데이터클래스 테스트"""

    def test_to_dict(self):
        """to_dict 메서드"""
        response = GeneratedResponse(
            trace_id="test-trace",
            query_type="ONTOLOGY",
            answer="테스트 응답",
            abstain=False,
        )

        result = response.to_dict()

        assert result["trace_id"] == "test-trace"
        assert result["query_type"] == "ONTOLOGY"
        assert result["answer"] == "테스트 응답"
        assert result["abstain"] is False

    def test_abstain_response_to_dict(self):
        """ABSTAIN 응답 to_dict"""
        response = GeneratedResponse(
            trace_id="test-trace",
            query_type="RAG",
            answer="근거를 찾지 못했습니다.",
            abstain=True,
            abstain_reason="no entities extracted",
        )

        result = response.to_dict()

        assert result["abstain"] is True
        assert result["abstain_reason"] == "no entities extracted"
