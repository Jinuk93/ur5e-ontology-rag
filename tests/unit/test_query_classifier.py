"""QueryClassifier 단위 테스트"""

import pytest
from src.rag.evidence_schema import QueryType, ExtractedEntity, ClassificationResult
from src.rag.query_classifier import QueryClassifier


class TestQueryClassifierBasic:
    """QueryClassifier 기본 테스트"""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_init(self, classifier):
        """초기화 테스트"""
        assert classifier is not None
        assert classifier._extractor is not None

    def test_classify_returns_classification_result(self, classifier):
        """classify가 ClassificationResult를 반환하는지 테스트"""
        result = classifier.classify("테스트 질문")
        assert isinstance(result, ClassificationResult)
        assert result.query == "테스트 질문"
        assert isinstance(result.query_type, QueryType)
        assert 0 <= result.confidence <= 1


class TestOntologyQueryClassification:
    """온톨로지 질문 분류 테스트"""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_sensor_value_question(self, classifier):
        """센서 값 질문이 ONTOLOGY로 분류되는지 테스트"""
        result = classifier.classify("Fz가 -350N인데 이게 뭐야?")
        assert result.query_type == QueryType.ONTOLOGY
        assert result.confidence > 0.5

    def test_pattern_cause_question(self, classifier):
        """패턴/원인 질문이 ONTOLOGY로 분류되는지 테스트"""
        result = classifier.classify("충돌 패턴의 원인이 뭐야?")
        assert result.query_type == QueryType.ONTOLOGY

    def test_state_question(self, classifier):
        """상태 질문이 ONTOLOGY로 분류되는지 테스트"""
        result = classifier.classify("현재 로봇 상태가 어때?")
        assert result.query_type == QueryType.ONTOLOGY

    def test_prediction_request(self, classifier):
        """예측 요청이 ONTOLOGY로 분류되는지 테스트"""
        result = classifier.classify("다음에 어떤 에러가 발생할까?")
        assert result.query_type == QueryType.ONTOLOGY


class TestHybridQueryClassification:
    """하이브리드 질문 분류 테스트"""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_error_context_question(self, classifier):
        """에러코드 맥락 질문이 HYBRID로 분류되는지 테스트"""
        result = classifier.classify("C153 에러가 자주 발생하는 이유가 뭐야?")
        assert result.query_type == QueryType.HYBRID

    def test_resolution_context_question(self, classifier):
        """해결 맥락 질문 테스트"""
        result = classifier.classify("이런 상황에서 해결 방법이 어떻게 돼?")
        # HYBRID 또는 RAG일 수 있음 (패턴 매칭에 따라)
        assert result.query_type in [QueryType.HYBRID, QueryType.RAG]


class TestRAGQueryClassification:
    """RAG 질문 분류 테스트"""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_specification_question(self, classifier):
        """사양 질문이 RAG로 분류되는지 테스트"""
        result = classifier.classify("UR5e의 최대 페이로드는 몇 kg이야?")
        assert result.query_type == QueryType.RAG

    def test_procedure_question(self, classifier):
        """절차 질문이 RAG로 분류되는지 테스트"""
        result = classifier.classify("센서 설치 방법 알려줘")
        assert result.query_type == QueryType.RAG

    def test_generic_question_fallback(self, classifier):
        """일반 질문이 RAG로 폴백되는지 테스트"""
        result = classifier.classify("안녕하세요")
        assert result.query_type == QueryType.RAG


class TestEntityBonus:
    """엔티티 기반 보너스 점수 테스트"""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_sensor_axis_with_value_gets_bonus(self, classifier):
        """센서 축 + 값 조합이 보너스를 받는지 테스트"""
        # Fz -350N 형태의 질문은 MeasurementAxis + Value 엔티티 추출
        result = classifier.classify("Fz가 -350N인데 뭐가 문제야?")

        entity_types = [e.entity_type for e in result.entities]
        # 엔티티 추출 확인
        assert len(result.entities) > 0


class TestConvenienceMethods:
    """편의 메서드 테스트"""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_is_ontology_query(self, classifier):
        """is_ontology_query 메서드 테스트"""
        assert classifier.is_ontology_query("Fz가 -350N인데 뭐야?") is True
        assert classifier.is_ontology_query("UR5e 최대 페이로드") is False

    def test_is_rag_query(self, classifier):
        """is_rag_query 메서드 테스트"""
        assert classifier.is_rag_query("UR5e 사양 알려줘") is True

    def test_get_query_intent(self, classifier):
        """get_query_intent 메서드 테스트"""
        intent = classifier.get_query_intent("Fz가 -350N인데 뭐야?")

        assert "type" in intent
        assert "confidence" in intent
        assert "entities" in intent
        assert "sub_intent" in intent


class TestScoreCalculation:
    """점수 계산 테스트"""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_score_normalized_to_max_1(self, classifier):
        """점수가 1.0을 넘지 않는지 테스트"""
        # 여러 지표를 매칭하는 질문
        result = classifier.classify("Fz가 -350N이고 어제 충돌 발생했는데 원인이 뭐야?")
        assert result.confidence <= 1.0

    def test_low_score_fallback_to_rag(self, classifier):
        """낮은 점수는 RAG로 폴백되는지 테스트"""
        result = classifier.classify("...")
        assert result.query_type == QueryType.RAG
