"""OntologyEngine 단위 테스트"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.ontology.ontology_engine import (
    OntologyEngine,
    ReasoningResult,
    EntityContext,
    _get_entity_attr,
)
from src.ontology.models import Entity
from src.ontology.schema import EntityType, RelationType


class TestGetEntityAttr:
    """_get_entity_attr 헬퍼 함수 테스트"""

    def test_get_from_dict(self):
        """딕셔너리에서 속성 가져오기"""
        entity = {"entity_id": "Fz", "entity_type": "MeasurementAxis"}

        assert _get_entity_attr(entity, "entity_id") == "Fz"
        assert _get_entity_attr(entity, "entity_type") == "MeasurementAxis"

    def test_get_from_object(self):
        """객체에서 속성 가져오기"""
        @dataclass
        class MockEntity:
            entity_id: str = "Fz"
            entity_type: str = "MeasurementAxis"

        entity = MockEntity()

        assert _get_entity_attr(entity, "entity_id") == "Fz"
        assert _get_entity_attr(entity, "entity_type") == "MeasurementAxis"

    def test_get_with_default(self):
        """기본값 반환"""
        entity = {"entity_id": "Fz"}

        assert _get_entity_attr(entity, "missing_key", "default") == "default"
        assert _get_entity_attr(entity, "missing_key") is None


class TestOntologyEngineInit:
    """OntologyEngine 초기화 테스트"""

    @patch("src.ontology.ontology_engine.load_ontology")
    @patch("src.ontology.ontology_engine.RuleEngine")
    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_init_with_defaults(self, mock_traverser, mock_rule_engine, mock_load):
        """기본값으로 초기화"""
        mock_ontology = Mock()
        mock_load.return_value = mock_ontology

        engine = OntologyEngine()

        assert engine.ontology is mock_ontology
        mock_rule_engine.assert_called_once()
        mock_traverser.assert_called_once_with(mock_ontology)

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_init_with_custom_ontology(self, mock_traverser):
        """커스텀 온톨로지로 초기화"""
        mock_ontology = Mock()
        mock_rule_engine = Mock()

        engine = OntologyEngine(ontology=mock_ontology, rule_engine=mock_rule_engine)

        assert engine.ontology is mock_ontology
        assert engine.rule_engine is mock_rule_engine


class TestOntologyEngineGetContext:
    """OntologyEngine get_context 메서드 테스트"""

    @pytest.fixture
    def mock_ontology(self):
        """모의 온톨로지"""
        mock = Mock()
        mock_entity = Mock()
        mock_entity.id = "Fz"
        mock_entity.type = EntityType.MEASUREMENT_AXIS
        mock_entity.name = "Fz"
        mock_entity.properties = {"normal_range": [-10, 10], "unit": "N"}
        mock.get_entity.return_value = mock_entity
        return mock

    @pytest.fixture
    def mock_traverser(self):
        """모의 그래프 탐색기"""
        mock = Mock()
        mock.get_entity_context.return_value = {
            "outgoing_relations": {
                "HAS_STATE": ["CRITICAL", "WARNING"],
                "RESOLVED_BY": ["RES_REDUCE_PAYLOAD"],
            },
            "incoming_relations": {
                "INDICATES": ["PAT_COLLISION"],
                "TRIGGERS": [],
            },
        }
        return mock

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_get_context_returns_entity_context(self, mock_gt_class, mock_ontology, mock_traverser):
        """get_context가 EntityContext 반환"""
        mock_gt_class.return_value = mock_traverser

        engine = OntologyEngine(ontology=mock_ontology)
        context = engine.get_context("Fz")

        assert isinstance(context, EntityContext)
        assert context.entity.id == "Fz"
        assert "CRITICAL" in context.states or "WARNING" in context.states

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_get_context_unknown_entity(self, mock_gt_class, mock_ontology, mock_traverser):
        """존재하지 않는 엔티티"""
        mock_gt_class.return_value = mock_traverser
        mock_ontology.get_entity.return_value = None

        engine = OntologyEngine(ontology=mock_ontology)

        with patch("src.ontology.loader.resolve_alias", return_value="unknown"):
            context = engine.get_context("unknown_entity")

        assert context is None


class TestOntologyEngineReason:
    """OntologyEngine reason 메서드 테스트"""

    @pytest.fixture
    def mock_ontology(self):
        """모의 온톨로지"""
        mock = Mock()

        # Fz 엔티티
        mock_fz = Mock()
        mock_fz.id = "Fz"
        mock_fz.type = EntityType.MEASUREMENT_AXIS
        mock_fz.name = "Fz"
        mock_fz.properties = {"normal_range": [-10, 10], "unit": "N"}

        # C153 에러 코드 엔티티
        mock_c153 = Mock()
        mock_c153.id = "C153"
        mock_c153.type = EntityType.ERROR_CODE
        mock_c153.name = "Joint position error"
        mock_c153.properties = {"severity": "critical", "description": "조인트 위치 오차"}

        def get_entity_side_effect(entity_id):
            if entity_id == "Fz":
                return mock_fz
            elif entity_id == "C153":
                return mock_c153
            return None

        mock.get_entity.side_effect = get_entity_side_effect
        mock.get_relationships_for_entity.return_value = []  # 빈 리스트 반환
        return mock

    @pytest.fixture
    def mock_rule_engine(self):
        """모의 규칙 엔진"""
        mock = Mock()
        mock.infer.return_value = Mock(
            conclusions=[
                {"type": "state", "entity": "Fz", "state": "CRITICAL", "confidence": 0.85},
                {"type": "pattern", "pattern": "PAT_COLLISION", "confidence": 0.8},
            ],
            predictions=[],
            confidence=0.85,
        )
        return mock

    @pytest.fixture
    def mock_traverser(self):
        """모의 그래프 탐색기"""
        mock = Mock()
        mock.get_entity_context.return_value = {
            "outgoing_relations": {"HAS_STATE": ["CRITICAL"]},
            "incoming_relations": {"INDICATES": ["PAT_COLLISION"]},
        }
        mock.find_path.return_value = None
        mock.follow_relation_chain.return_value = []  # 빈 리스트 반환
        return mock

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_reason_returns_reasoning_result(self, mock_gt_class, mock_ontology, mock_rule_engine, mock_traverser):
        """reason이 ReasoningResult 반환"""
        mock_gt_class.return_value = mock_traverser
        # 추가 traverser 메서드 설정
        mock_traverser.follow_relation_chain.return_value = []
        mock_traverser.bfs.return_value = Mock(entities=[], paths=[])

        engine = OntologyEngine(ontology=mock_ontology, rule_engine=mock_rule_engine)

        entities = [
            {"entity_id": "Fz", "entity_type": "MeasurementAxis", "text": "Fz"},
        ]

        result = engine.reason("Fz가 뭐야?", entities)

        assert isinstance(result, ReasoningResult)
        assert result.query == "Fz가 뭐야?"

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_reason_definition_query(self, mock_gt_class, mock_ontology, mock_rule_engine, mock_traverser):
        """정의 질문 처리"""
        mock_gt_class.return_value = mock_traverser
        mock_traverser.follow_relation_chain.return_value = []
        mock_traverser.bfs.return_value = Mock(entities=[], paths=[])

        engine = OntologyEngine(ontology=mock_ontology, rule_engine=mock_rule_engine)

        entities = [
            {"entity_id": "Fz", "entity_type": "MeasurementAxis", "text": "Fz"},
        ]

        result = engine.reason("Fz가 뭐야?", entities)

        assert isinstance(result, ReasoningResult)
        # 정의 질문이므로 conclusions에 definition 타입이 있거나 처리됨
        assert result.confidence > 0

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_reason_error_code_query(self, mock_gt_class, mock_ontology, mock_rule_engine, mock_traverser):
        """에러 코드 질문 처리"""
        mock_gt_class.return_value = mock_traverser
        mock_traverser.follow_relation_chain.return_value = []
        mock_traverser.bfs.return_value = Mock(entities=[], paths=[])

        engine = OntologyEngine(ontology=mock_ontology, rule_engine=mock_rule_engine)

        entities = [
            {"entity_id": "C153", "entity_type": "ErrorCode", "text": "C153"},
        ]

        result = engine.reason("C153 에러 원인이 뭐야?", entities)

        assert isinstance(result, ReasoningResult)


class TestOntologyEngineFindPath:
    """OntologyEngine find_path 메서드 테스트"""

    @pytest.fixture
    def mock_traverser(self):
        """모의 그래프 탐색기"""
        mock = Mock()
        mock_path = Mock()
        mock_path.nodes = ["Fz", "CRITICAL", "PAT_COLLISION"]
        mock_path.relations = ["HAS_STATE", "INDICATES"]
        mock.find_path.return_value = mock_path
        return mock

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_find_path_success(self, mock_gt_class, mock_traverser):
        """경로 탐색 성공"""
        mock_gt_class.return_value = mock_traverser
        mock_ontology = Mock()

        engine = OntologyEngine(ontology=mock_ontology)
        path = engine.find_path("Fz", "PAT_COLLISION")

        assert path is not None
        mock_traverser.find_path.assert_called_once_with("Fz", "PAT_COLLISION")

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_find_path_not_found(self, mock_gt_class):
        """경로 탐색 실패"""
        mock_traverser = Mock()
        mock_traverser.find_path.return_value = None
        mock_gt_class.return_value = mock_traverser
        mock_ontology = Mock()

        engine = OntologyEngine(ontology=mock_ontology)
        path = engine.find_path("Fz", "NonExistent")

        assert path is None


class TestOntologyEngineGetRelatedEntities:
    """OntologyEngine get_related_entities 메서드 테스트"""

    @pytest.fixture
    def mock_traverser(self):
        """모의 그래프 탐색기"""
        mock = Mock()
        mock_result = Mock()
        mock_result.entities = ["Fz", "CRITICAL", "PAT_COLLISION"]
        mock_result.paths = []
        mock.bfs.return_value = mock_result
        return mock

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_get_related_entities(self, mock_gt_class, mock_traverser):
        """관련 엔티티 탐색"""
        mock_gt_class.return_value = mock_traverser
        mock_ontology = Mock()

        engine = OntologyEngine(ontology=mock_ontology)
        result = engine.get_related_entities("Fz", depth=2)

        assert result is not None
        mock_traverser.bfs.assert_called_once()


class TestReasoningResultDataclass:
    """ReasoningResult 데이터클래스 테스트"""

    def test_to_dict(self):
        """to_dict 메서드"""
        result = ReasoningResult(
            query="테스트 질문",
            entities=[{"entity_id": "Fz"}],
            reasoning_chain=[{"step": "analysis"}],
            conclusions=[{"type": "state", "state": "CRITICAL"}],
            predictions=[],
            recommendations=[],
            ontology_paths=["Fz →[HAS_STATE]→ CRITICAL"],
            confidence=0.85,
            evidence={"processed": True},
        )

        d = result.to_dict()

        assert d["query"] == "테스트 질문"
        assert d["confidence"] == 0.85
        assert len(d["conclusions"]) == 1
        assert d["ontology_paths"][0] == "Fz →[HAS_STATE]→ CRITICAL"


class TestEntityContextDataclass:
    """EntityContext 데이터클래스 테스트"""

    def test_to_dict(self):
        """to_dict 메서드"""
        mock_entity = Mock()
        mock_entity.id = "Fz"
        mock_entity.type = Mock()
        mock_entity.type.value = "MeasurementAxis"
        mock_entity.name = "Fz"

        context = EntityContext(
            entity=mock_entity,
            properties={"normal_range": [-10, 10]},
            states=["CRITICAL"],
            related_patterns=["PAT_COLLISION"],
            related_errors=["C153"],
            related_causes=["CAUSE_COLLISION"],
            related_resolutions=["RES_CHECK_AREA"],
        )

        d = context.to_dict()

        assert d["entity_id"] == "Fz"
        assert d["entity_type"] == "MeasurementAxis"
        assert "CRITICAL" in d["states"]
        assert "PAT_COLLISION" in d["related_patterns"]


class TestOntologyEnginePatternHistory:
    """OntologyEngine 패턴 이력 테스트"""

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_build_pattern_history_no_data(self, mock_gt_class):
        """패턴 데이터 없을 때"""
        mock_gt_class.return_value = Mock()
        mock_ontology = Mock()

        engine = OntologyEngine(ontology=mock_ontology)
        engine._pattern_log_cache = []  # 빈 캐시

        history = engine._build_pattern_history("PAT_COLLISION")

        assert history["count"] == 0
        assert "없습니다" in history["description"] or "확인할 수 없습니다" in history["description"]

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_build_pattern_history_with_data(self, mock_gt_class):
        """패턴 데이터 있을 때"""
        mock_gt_class.return_value = Mock()
        mock_ontology = Mock()

        engine = OntologyEngine(ontology=mock_ontology)
        engine._pattern_log_cache = [
            {
                "pattern_id": "PAT_COLLISION",
                "pattern_type": "collision",
                "timestamp": "2026-01-25T10:00:00",
                "confidence": 0.9,
            },
            {
                "pattern_id": "PAT_COLLISION",
                "pattern_type": "collision",
                "timestamp": "2026-01-26T10:00:00",
                "confidence": 0.85,
            },
        ]

        history = engine._build_pattern_history("PAT_COLLISION")

        assert history["count"] == 2
        assert "감지되었습니다" in history["description"]
        assert history["confidence"] > 0.9


class TestOntologyEngineUnregisteredEntity:
    """미등록 엔티티 처리 테스트"""

    @patch("src.ontology.ontology_engine.GraphTraverser")
    def test_reason_with_unknown_error_code(self, mock_gt_class):
        """미등록 에러 코드 처리"""
        mock_traverser = Mock()
        mock_traverser.get_entity_context.return_value = {
            "outgoing_relations": {},
            "incoming_relations": {},
        }
        mock_gt_class.return_value = mock_traverser

        mock_ontology = Mock()
        mock_ontology.get_entity.return_value = None  # 미등록 엔티티

        engine = OntologyEngine(ontology=mock_ontology)

        entities = [
            {"entity_id": "C999", "entity_type": "ErrorCode", "text": "C999"},
        ]

        result = engine.reason("C999 에러 해결법", entities)

        # 미등록 에러 코드여도 결과를 반환해야 함
        assert isinstance(result, ReasoningResult)
