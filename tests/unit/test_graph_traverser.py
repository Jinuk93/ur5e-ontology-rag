"""GraphTraverser 단위 테스트"""

import pytest
from src.ontology.graph_traverser import (
    PathStep,
    OntologyPath,
    TraversalResult,
)


class TestPathStep:
    """PathStep 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        step = PathStep(
            entity_id="Fz",
            entity_type="MeasurementAxis",
            entity_name="Force Z",
            relation="HAS_STATE",
            direction="outgoing",
        )
        assert step.entity_id == "Fz"
        assert step.entity_type == "MeasurementAxis"
        assert step.relation == "HAS_STATE"

    def test_to_dict(self):
        """to_dict 변환 테스트"""
        step = PathStep(
            entity_id="Fz",
            entity_type="MeasurementAxis",
            entity_name="Force Z",
        )
        d = step.to_dict()

        assert d["entity_id"] == "Fz"
        assert d["entity_type"] == "MeasurementAxis"
        assert d["direction"] == "outgoing"  # 기본값


class TestOntologyPath:
    """OntologyPath 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        path = OntologyPath()
        assert path.steps == []
        assert path.total_confidence == 1.0

    def test_add_step(self):
        """경로에 단계 추가 테스트"""
        path = OntologyPath()
        step1 = PathStep(
            entity_id="Fz",
            entity_type="MeasurementAxis",
            entity_name="Force Z",
        )
        step2 = PathStep(
            entity_id="State_Warning",
            entity_type="State",
            entity_name="Warning State",
            relation="HAS_STATE",
            direction="outgoing",
        )

        path.add_step(step1, confidence=1.0)
        path.add_step(step2, confidence=0.9)

        assert len(path.steps) == 2
        assert path.total_confidence == 0.9  # 1.0 * 0.9

    def test_to_string(self):
        """경로 문자열 변환 테스트"""
        path = OntologyPath()
        path.add_step(PathStep(
            entity_id="Fz",
            entity_type="MeasurementAxis",
            entity_name="Force Z",
        ))
        path.add_step(PathStep(
            entity_id="State_Warning",
            entity_type="State",
            entity_name="Warning",
            relation="HAS_STATE",
            direction="outgoing",
        ))

        path_str = path.to_string()

        assert "Fz" in path_str
        assert "HAS_STATE" in path_str
        assert "State_Warning" in path_str

    def test_empty_path_to_string(self):
        """빈 경로 문자열 변환 테스트"""
        path = OntologyPath()
        assert path.to_string() == ""

    def test_length_property(self):
        """경로 길이 속성 테스트"""
        path = OntologyPath()
        assert path.length == 0

        path.add_step(PathStep(
            entity_id="A",
            entity_type="Test",
            entity_name="A",
        ))
        assert path.length == 1

    def test_start_end_entity(self):
        """시작/종료 엔티티 속성 테스트"""
        path = OntologyPath()
        assert path.start_entity is None
        assert path.end_entity is None

        path.add_step(PathStep(
            entity_id="Start",
            entity_type="Test",
            entity_name="Start",
        ))
        path.add_step(PathStep(
            entity_id="Middle",
            entity_type="Test",
            entity_name="Middle",
            relation="REL",
        ))
        path.add_step(PathStep(
            entity_id="End",
            entity_type="Test",
            entity_name="End",
            relation="REL2",
        ))

        assert path.start_entity == "Start"
        assert path.end_entity == "End"

    def test_to_dict(self):
        """to_dict 변환 테스트"""
        path = OntologyPath()
        path.add_step(PathStep(
            entity_id="A",
            entity_type="Test",
            entity_name="A",
        ))
        d = path.to_dict()

        assert "steps" in d
        assert "total_confidence" in d
        assert "path_string" in d
        assert len(d["steps"]) == 1


class TestTraversalResult:
    """TraversalResult 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        result = TraversalResult()
        assert result.paths == []
        assert result.visited_entities == set()
        assert result.related_entities == {}
        assert result.relationships_found == []

    def test_to_dict(self):
        """to_dict 변환 테스트"""
        result = TraversalResult()
        result.visited_entities.add("A")
        result.visited_entities.add("B")

        d = result.to_dict()

        assert d["visited_count"] == 2
        assert d["paths"] == []
        assert d["relationships_count"] == 0


class TestOntologyPathConfidence:
    """OntologyPath 신뢰도 계산 테스트"""

    def test_confidence_multiplication(self):
        """신뢰도 곱셈 테스트"""
        path = OntologyPath()

        # 각 단계 신뢰도: 0.9, 0.8, 0.7
        path.add_step(PathStep(
            entity_id="A", entity_type="T", entity_name="A"
        ), confidence=0.9)
        path.add_step(PathStep(
            entity_id="B", entity_type="T", entity_name="B", relation="R"
        ), confidence=0.8)
        path.add_step(PathStep(
            entity_id="C", entity_type="T", entity_name="C", relation="R2"
        ), confidence=0.7)

        # 예상: 1.0 * 0.9 * 0.8 * 0.7 = 0.504
        assert abs(path.total_confidence - 0.504) < 0.001

    def test_initial_confidence(self):
        """초기 신뢰도 테스트"""
        path = OntologyPath(total_confidence=0.5)
        path.add_step(PathStep(
            entity_id="A", entity_type="T", entity_name="A"
        ), confidence=0.8)

        # 예상: 0.5 * 0.8 = 0.4
        assert abs(path.total_confidence - 0.4) < 0.001
