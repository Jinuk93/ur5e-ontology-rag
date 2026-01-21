"""
Unit tests for Extended Verifier

Main-S5: Verifier 확장 테스트
"""

import pytest
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.rag.verifier import (
    VerificationStatus,
    VerificationResult,
    Verifier,
)
from src.rag.sensor_verifier import SensorVerifier, SensorVerificationResult
from src.rag.ontology_verifier import OntologyVerifier, OntologyVerificationResult


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def sensor_verifier():
    """SensorVerifier 인스턴스"""
    return SensorVerifier()


@pytest.fixture
def ontology_verifier():
    """OntologyVerifier 인스턴스 (no graph_retriever)"""
    return OntologyVerifier()


@pytest.fixture
def verifier():
    """Verifier 인스턴스 (센서 검증 활성화)"""
    return Verifier(use_sensor_verification=True)


@pytest.fixture
def sample_sensor_evidence():
    """샘플 센서 증거"""
    @dataclass
    class MockSensorEvidence:
        patterns: List[Dict]
        time_range: tuple = None
        has_anomaly: bool = True

    return MockSensorEvidence(
        patterns=[
            {"pattern_type": "collision", "confidence": 0.95},
            {"pattern_type": "vibration", "confidence": 0.60},
        ]
    )


@pytest.fixture
def sample_enriched_context(sample_sensor_evidence):
    """샘플 EnrichedContext"""
    @dataclass
    class MockDocEvidence:
        chunk_id: str
        content: str
        score: float
        source: str

    @dataclass
    class MockCorrelation:
        level: str
        confidence: float

    @dataclass
    class MockEnrichedContext:
        doc_evidence: List
        sensor_evidence: Any
        correlation: Any
        error_code: str = None

    doc_evidence = [
        MockDocEvidence("ec_001", "C153 충돌 에러", 0.9, "error_codes"),
        MockDocEvidence("sm_002", "Safety Reset 수행", 0.85, "service_manual"),
    ]

    return MockEnrichedContext(
        doc_evidence=doc_evidence,
        sensor_evidence=sample_sensor_evidence,
        correlation=MockCorrelation(level="STRONG", confidence=0.85),
        error_code="C153"
    )


# ============================================================
# VerificationStatus 테스트
# ============================================================

class TestVerificationStatus:
    """VerificationStatus Enum 테스트"""

    def test_new_partial_statuses_exist(self):
        """Main-S5 새 상태 존재 확인"""
        assert hasattr(VerificationStatus, "PARTIAL_BOTH")
        assert hasattr(VerificationStatus, "PARTIAL_DOC_ONLY")
        assert hasattr(VerificationStatus, "PARTIAL_SENSOR_ONLY")

    def test_status_values(self):
        """상태 값 확인"""
        assert VerificationStatus.PARTIAL_BOTH.value == "partial_both"
        assert VerificationStatus.PARTIAL_DOC_ONLY.value == "partial_doc"
        assert VerificationStatus.PARTIAL_SENSOR_ONLY.value == "partial_sensor"


# ============================================================
# VerificationResult 테스트
# ============================================================

class TestVerificationResult:
    """VerificationResult 확장 테스트"""

    def test_sensor_fields_exist(self):
        """센서 관련 필드 존재 확인"""
        result = VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.9,
            evidence_count=2,
        )

        assert hasattr(result, "sensor_evidence_count")
        assert hasattr(result, "sensor_patterns")
        assert hasattr(result, "ontology_match")
        assert hasattr(result, "correlation_level")

    def test_has_sensor_support(self):
        """has_sensor_support 속성 테스트"""
        result_with_sensor = VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.9,
            evidence_count=2,
            sensor_evidence_count=1
        )
        assert result_with_sensor.has_sensor_support

        result_without_sensor = VerificationResult(
            status=VerificationStatus.PARTIAL_DOC_ONLY,
            confidence=0.7,
            evidence_count=2,
            sensor_evidence_count=0
        )
        assert not result_without_sensor.has_sensor_support

    def test_has_dual_evidence(self):
        """has_dual_evidence 속성 테스트"""
        result_dual = VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.9,
            evidence_count=2,
            sensor_evidence_count=1
        )
        assert result_dual.has_dual_evidence

        result_doc_only = VerificationResult(
            status=VerificationStatus.PARTIAL_DOC_ONLY,
            confidence=0.7,
            evidence_count=2,
            sensor_evidence_count=0
        )
        assert not result_doc_only.has_dual_evidence

    def test_is_safe_to_answer_includes_new_statuses(self):
        """is_safe_to_answer가 새 상태 포함"""
        safe_statuses = [
            VerificationStatus.VERIFIED,
            VerificationStatus.PARTIAL,
            VerificationStatus.PARTIAL_BOTH,
            VerificationStatus.PARTIAL_DOC_ONLY,
            VerificationStatus.PARTIAL_SENSOR_ONLY,
        ]

        for status in safe_statuses:
            result = VerificationResult(
                status=status,
                confidence=0.6,
                evidence_count=1
            )
            assert result.is_safe_to_answer, f"{status} should be safe"


# ============================================================
# SensorVerifier 테스트
# ============================================================

class TestSensorVerifier:
    """SensorVerifier 테스트"""

    def test_verify_no_evidence(self, sensor_verifier):
        """센서 증거 없는 경우"""
        result = sensor_verifier.verify(sensor_evidence=None)

        assert not result.is_valid
        assert result.score == 0.0
        assert "센서 증거 없음" in result.warnings

    def test_verify_valid_patterns(self, sensor_verifier, sample_sensor_evidence):
        """유효한 패턴 검증"""
        result = sensor_verifier.verify(
            sensor_evidence=sample_sensor_evidence,
            error_code="C153"
        )

        assert result.is_valid
        assert result.score > 0.5
        assert "collision" in result.pattern_types

    def test_verify_error_match(self, sensor_verifier, sample_sensor_evidence):
        """에러-패턴 매칭 테스트"""
        result = sensor_verifier.verify(
            sensor_evidence=sample_sensor_evidence,
            error_code="C153"
        )

        # C153 → collision 매칭 확인
        assert "error_match" in result.details
        assert result.details["error_match"]["error_code"] == "C153"

    def test_verify_low_confidence_warning(self, sensor_verifier):
        """저신뢰 패턴 경고 테스트"""
        @dataclass
        class LowConfidenceEvidence:
            patterns: List[Dict]

        evidence = LowConfidenceEvidence(patterns=[
            {"pattern_type": "collision", "confidence": 0.3}  # 낮은 신뢰도
        ])

        result = sensor_verifier.verify(sensor_evidence=evidence)

        assert any("저신뢰" in w for w in result.warnings)

    def test_get_expected_patterns(self, sensor_verifier):
        """예상 패턴 조회 테스트"""
        patterns = sensor_verifier.get_expected_patterns("C153")
        assert "collision" in patterns

        patterns = sensor_verifier.get_expected_patterns("C189")
        assert "overload" in patterns


# ============================================================
# OntologyVerifier 테스트
# ============================================================

class TestOntologyVerifier:
    """OntologyVerifier 테스트"""

    def test_verify_pattern_error_relation(self, ontology_verifier):
        """패턴-에러 관계 검증"""
        is_match, prob = ontology_verifier.verify_pattern_error_relation(
            pattern_type="collision",
            error_code="C153"
        )

        assert is_match
        assert prob >= 0.9

    def test_verify_pattern_error_no_match(self, ontology_verifier):
        """패턴-에러 불일치 검증"""
        is_match, prob = ontology_verifier.verify_pattern_error_relation(
            pattern_type="drift",  # drift는 직접 에러 유발 안함
            error_code="C153"
        )

        assert not is_match
        assert prob == 0.0

    def test_get_expected_patterns_for_error(self, ontology_verifier):
        """에러에 대한 예상 패턴 조회"""
        patterns = ontology_verifier.get_expected_patterns_for_error("C153")

        assert len(patterns) >= 1
        pattern_types = [p["type"] for p in patterns]
        assert "collision" in pattern_types

    def test_get_causes_for_pattern(self, ontology_verifier):
        """패턴에 대한 원인 조회"""
        causes = ontology_verifier.get_causes_for_pattern("collision")

        assert len(causes) >= 1
        cause_ids = [c["cause_id"] for c in causes]
        assert "CAUSE_PHYSICAL_CONTACT" in cause_ids

    def test_verify_full_result(self, ontology_verifier):
        """전체 검증 결과 테스트"""
        result = ontology_verifier.verify(
            pattern_type="collision",
            error_code="C153"
        )

        assert isinstance(result, OntologyVerificationResult)
        assert result.is_match
        assert result.probability >= 0.9
        assert len(result.expected_causes) >= 1


# ============================================================
# Verifier 확장 테스트
# ============================================================

class TestVerifierExtended:
    """Verifier 확장 기능 테스트"""

    def test_init_with_sensor_verification(self):
        """센서 검증 활성화 초기화"""
        verifier = Verifier(use_sensor_verification=True)

        assert verifier.use_sensor_verification
        assert verifier.sensor_verifier is not None
        assert verifier.ontology_verifier is not None

    def test_init_without_sensor_verification(self):
        """센서 검증 비활성화 초기화"""
        verifier = Verifier(use_sensor_verification=False)

        assert not verifier.use_sensor_verification
        assert verifier.sensor_verifier is None

    def test_verify_enriched_context(self, verifier, sample_enriched_context):
        """EnrichedContext 검증"""
        result = verifier.verify_enriched_context(sample_enriched_context)

        assert isinstance(result, VerificationResult)
        assert result.evidence_count >= 1
        assert result.sensor_evidence_count >= 1
        assert result.correlation_level == "STRONG"

    def test_verify_enriched_context_doc_only(self, verifier):
        """문서만 있는 EnrichedContext 검증"""
        @dataclass
        class DocOnlyContext:
            doc_evidence: List
            sensor_evidence: None = None
            correlation: None = None
            error_code: str = None

        @dataclass
        class MockDoc:
            chunk_id: str
            score: float
            source: str

        context = DocOnlyContext(
            doc_evidence=[MockDoc("ec_001", 0.9, "error_codes")]
        )

        result = verifier.verify_enriched_context(context)

        assert result.status == VerificationStatus.PARTIAL_DOC_ONLY
        assert result.evidence_count >= 1
        assert result.sensor_evidence_count == 0

    def test_calculate_dual_confidence(self, verifier):
        """이중 신뢰도 계산 테스트"""
        # 문서 + 센서 + 온톨로지 + STRONG
        confidence = verifier._calculate_dual_confidence(
            doc_score=0.9,
            sensor_score=0.8,
            ontology_match=True,
            correlation_level="STRONG"
        )
        assert confidence >= 0.85

        # 문서만
        confidence = verifier._calculate_dual_confidence(
            doc_score=0.9,
            sensor_score=0.0,
            ontology_match=False,
            correlation_level="NONE"
        )
        assert 0.4 <= confidence <= 0.5

    def test_determine_verification_status(self, verifier):
        """검증 상태 판정 테스트"""
        # VERIFIED: 완전 검증
        status = verifier._determine_verification_status(
            has_doc=True,
            has_sensor=True,
            ontology_match=True,
            confidence=0.9
        )
        assert status == VerificationStatus.VERIFIED

        # PARTIAL_DOC_ONLY
        status = verifier._determine_verification_status(
            has_doc=True,
            has_sensor=False,
            ontology_match=False,
            confidence=0.6
        )
        assert status == VerificationStatus.PARTIAL_DOC_ONLY

        # PARTIAL_SENSOR_ONLY
        status = verifier._determine_verification_status(
            has_doc=False,
            has_sensor=True,
            ontology_match=True,
            confidence=0.6
        )
        assert status == VerificationStatus.PARTIAL_SENSOR_ONLY

        # PARTIAL_BOTH
        status = verifier._determine_verification_status(
            has_doc=True,
            has_sensor=True,
            ontology_match=False,
            confidence=0.6
        )
        assert status == VerificationStatus.PARTIAL_BOTH

    def test_add_enriched_citation(self, verifier):
        """이중 검증 정보 추가 테스트"""
        result = VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.9,
            evidence_count=2,
            evidence_sources=["error_codes:ec_001", "service_manual:sm_001"],
            sensor_evidence_count=1,
            sensor_patterns=["collision"],
            ontology_match=True,
            correlation_level="STRONG"
        )

        answer = "C153 에러 해결: Safety Reset 수행"
        enriched_answer = verifier.add_enriched_citation(answer, result)

        assert "검증 정보:" in enriched_answer
        assert "문서 근거" in enriched_answer
        assert "센서 분석" in enriched_answer
        assert "collision" in enriched_answer
        assert "온톨로지" in enriched_answer
        assert "90%" in enriched_answer


# ============================================================
# 통합 테스트
# ============================================================

class TestVerifierIntegration:
    """통합 테스트"""

    def test_full_verification_flow(self, verifier, sample_enriched_context):
        """전체 검증 흐름 테스트"""
        # 1. EnrichedContext 검증
        result = verifier.verify_enriched_context(sample_enriched_context)

        # 2. 안전 여부 확인
        assert result.is_safe_to_answer

        # 3. 이중 증거 확인
        assert result.has_dual_evidence

        # 4. 출처 추가
        answer = "C153 에러는 충돌로 인해 발생합니다."
        final_answer = verifier.add_enriched_citation(answer, result)

        assert "센서 분석" in final_answer
        assert "collision" in final_answer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
