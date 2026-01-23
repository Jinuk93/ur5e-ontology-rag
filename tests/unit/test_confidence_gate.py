"""ConfidenceGate 단위 테스트"""

import pytest
from dataclasses import dataclass, field
from typing import List, Optional, Any

from src.rag.confidence_gate import ConfidenceGate, GateResult
from src.rag.evidence_schema import (
    ClassificationResult,
    QueryType,
    ExtractedEntity,
    OntologyPath,
)


# Mock ReasoningResult (실제 import 대신 테스트용 mock)
@dataclass
class MockReasoningResult:
    """테스트용 ReasoningResult mock"""
    confidence: float = 0.8
    reasoning_chain: List[str] = field(default_factory=list)
    conclusions: List[Any] = field(default_factory=list)
    predictions: List[Any] = field(default_factory=list)
    recommendations: List[Any] = field(default_factory=list)
    ontology_paths: List[Any] = field(default_factory=list)


class TestGateResultDataclass:
    """GateResult 데이터클래스 테스트"""

    def test_gate_result_creation(self):
        """GateResult 생성 테스트"""
        result = GateResult(
            passed=True,
            confidence=0.85,
            abstain_reason=None,
            warnings=["warning1"],
        )
        assert result.passed is True
        assert result.confidence == 0.85
        assert result.abstain_reason is None
        assert len(result.warnings) == 1

    def test_gate_result_to_dict(self):
        """GateResult.to_dict 테스트"""
        result = GateResult(
            passed=False,
            confidence=0.3,
            abstain_reason="test reason",
            warnings=["w1", "w2"],
        )
        d = result.to_dict()

        assert d["passed"] is False
        assert d["confidence"] == 0.3
        assert d["abstain_reason"] == "test reason"
        assert len(d["warnings"]) == 2


class TestConfidenceGateInit:
    """ConfidenceGate 초기화 테스트"""

    def test_default_thresholds(self):
        """기본 임계값 테스트"""
        gate = ConfidenceGate()
        assert gate.min_confidence == 0.5
        assert gate.min_entity_confidence == 0.6
        assert gate.min_classification_confidence == 0.4

    def test_custom_thresholds(self):
        """커스텀 임계값 테스트"""
        gate = ConfidenceGate(
            min_confidence=0.7,
            min_entity_confidence=0.8,
            min_classification_confidence=0.5,
        )
        assert gate.min_confidence == 0.7
        assert gate.min_entity_confidence == 0.8
        assert gate.min_classification_confidence == 0.5


class TestClassificationQualityCheck:
    """분류 품질 검사 테스트"""

    @pytest.fixture
    def gate(self):
        return ConfidenceGate()

    def test_low_classification_confidence_abstain(self, gate):
        """분류 신뢰도가 낮으면 ABSTAIN"""
        classification = ClassificationResult(
            query="test",
            query_type=QueryType.ONTOLOGY,
            confidence=0.2,  # 임계값 0.4 미만
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.9
                )
            ],
        )
        reasoning = MockReasoningResult(confidence=0.8)

        result = gate.evaluate(classification, reasoning)

        assert result.passed is False
        assert "classification confidence too low" in result.abstain_reason

    def test_high_classification_confidence_pass(self, gate):
        """분류 신뢰도가 충분하면 통과"""
        classification = ClassificationResult(
            query="test",
            query_type=QueryType.ONTOLOGY,
            confidence=0.8,
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.9
                )
            ],
        )
        reasoning = MockReasoningResult(
            confidence=0.8,
            reasoning_chain=["step1"],
            conclusions=["conclusion1"],
        )

        result = gate.evaluate(classification, reasoning)

        assert result.passed is True


class TestEntityQualityCheck:
    """엔티티 품질 검사 테스트"""

    @pytest.fixture
    def gate(self):
        return ConfidenceGate()

    def test_no_entities_abstain(self, gate):
        """엔티티가 없으면 ABSTAIN"""
        classification = ClassificationResult(
            query="test",
            query_type=QueryType.ONTOLOGY,
            confidence=0.8,
            entities=[],  # 빈 엔티티
        )
        reasoning = MockReasoningResult(confidence=0.8)

        result = gate.evaluate(classification, reasoning)

        assert result.passed is False
        assert "no entities extracted" in result.abstain_reason

    def test_low_entity_confidence_abstain(self, gate):
        """엔티티 신뢰도가 낮으면 ABSTAIN"""
        classification = ClassificationResult(
            query="test",
            query_type=QueryType.ONTOLOGY,
            confidence=0.8,
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.3  # 낮음
                ),
                ExtractedEntity(
                    text="-350", entity_id="Value",
                    entity_type="Value", confidence=0.4  # 낮음
                ),
            ],
        )
        reasoning = MockReasoningResult(confidence=0.8)

        result = gate.evaluate(classification, reasoning)

        assert result.passed is False
        assert "entity confidence too low" in result.abstain_reason


class TestReasoningQualityCheck:
    """추론 품질 검사 테스트"""

    @pytest.fixture
    def gate(self):
        return ConfidenceGate()

    def test_no_reasoning_abstain(self, gate):
        """추론 결과가 없으면 ABSTAIN"""
        classification = ClassificationResult(
            query="test",
            query_type=QueryType.ONTOLOGY,
            confidence=0.8,
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.9
                )
            ],
        )

        result = gate.evaluate(classification, None)

        assert result.passed is False
        assert "no reasoning result" in result.abstain_reason

    def test_low_reasoning_confidence_abstain(self, gate):
        """추론 신뢰도가 낮으면 ABSTAIN"""
        classification = ClassificationResult(
            query="test",
            query_type=QueryType.ONTOLOGY,
            confidence=0.8,
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.9
                )
            ],
        )
        reasoning = MockReasoningResult(
            confidence=0.3,  # 낮음
            reasoning_chain=["step1"],
        )

        result = gate.evaluate(classification, reasoning)

        assert result.passed is False
        assert "reasoning confidence too low" in result.abstain_reason

    def test_no_reasoning_chain_with_conclusions_pass(self, gate):
        """추론 체인은 없지만 결론이 있으면 경고와 함께 통과"""
        classification = ClassificationResult(
            query="test",
            query_type=QueryType.ONTOLOGY,
            confidence=0.8,
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.9
                )
            ],
        )
        reasoning = MockReasoningResult(
            confidence=0.8,
            reasoning_chain=[],  # 빈 체인
            conclusions=["conclusion1"],  # 결론 있음
        )

        result = gate.evaluate(classification, reasoning)

        assert result.passed is True
        assert "no reasoning chain" in result.warnings


class TestFinalConfidenceCalculation:
    """최종 신뢰도 계산 테스트"""

    @pytest.fixture
    def gate(self):
        return ConfidenceGate()

    def test_final_confidence_weighted_average(self, gate):
        """최종 신뢰도가 가중 평균으로 계산되는지 테스트"""
        classification = ClassificationResult(
            query="test",
            query_type=QueryType.ONTOLOGY,
            confidence=0.8,
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.9
                )
            ],
        )
        reasoning = MockReasoningResult(
            confidence=0.8,
            reasoning_chain=["step1"],
            conclusions=["conclusion1"],
        )

        result = gate.evaluate(classification, reasoning)

        # 가중치: classification=0.3, reasoning=0.5, entity=0.2
        # 예상: 0.8*0.3 + 0.8*0.5 + 0.9*0.2 = 0.24 + 0.4 + 0.18 = 0.82
        assert 0.7 < result.confidence < 0.9

    def test_final_confidence_below_threshold_abstain(self, gate):
        """최종 신뢰도가 임계값 미만이면 ABSTAIN"""
        # 최종 신뢰도 임계값 테스트: 개별 검사는 통과하지만 가중 평균이 임계값 미만
        gate = ConfidenceGate(min_confidence=0.95)  # 매우 높은 임계값

        classification = ClassificationResult(
            query="test",
            query_type=QueryType.ONTOLOGY,
            confidence=0.6,
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.7
                )
            ],
        )
        # reasoning confidence는 개별 검사(0.95) 통과하도록 설정
        reasoning = MockReasoningResult(
            confidence=0.96,
            reasoning_chain=["step1"],
            conclusions=["conclusion1"],
        )

        result = gate.evaluate(classification, reasoning)

        # 가중 평균: 0.6*0.3 + 0.96*0.5 + 0.7*0.2 = 0.18 + 0.48 + 0.14 = 0.8
        # 0.8 < 0.95 이므로 ABSTAIN
        assert result.passed is False
        assert "confidence below threshold" in result.abstain_reason


class TestFullEvaluationFlow:
    """전체 평가 흐름 테스트"""

    @pytest.fixture
    def gate(self):
        return ConfidenceGate()

    def test_successful_evaluation(self, gate):
        """성공적인 평가 흐름 테스트"""
        classification = ClassificationResult(
            query="Fz가 -350N인데 뭐야?",
            query_type=QueryType.ONTOLOGY,
            confidence=0.85,
            entities=[
                ExtractedEntity(
                    text="Fz", entity_id="Fz",
                    entity_type="MeasurementAxis", confidence=0.95
                ),
                ExtractedEntity(
                    text="-350N", entity_id="-350",
                    entity_type="Value", confidence=0.9
                ),
            ],
        )
        reasoning = MockReasoningResult(
            confidence=0.8,
            reasoning_chain=["상태 분석", "패턴 감지", "원인 추론"],
            conclusions=[{"type": "state", "value": "warning"}],
            ontology_paths=[{"path": ["Fz", "State_Warning"]}],
        )

        result = gate.evaluate(classification, reasoning)

        assert result.passed is True
        assert result.abstain_reason is None
        assert result.confidence > 0.7
