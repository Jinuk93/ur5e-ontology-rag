"""
Unit tests for ContextEnricher

Main-S3: 컨텍스트 인리처 테스트
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.rag.context_enricher import ContextEnricher, get_context_enricher
from src.rag.schemas.enriched_context import (
    EnrichedContext,
    DocEvidence,
    SensorEvidence,
    AxisStats,
    CorrelationResult,
    CorrelationLevel,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def enricher():
    """ContextEnricher 인스턴스 (mock sensor store)"""
    with patch('src.rag.context_enricher.SensorStore') as MockStore:
        with patch('src.rag.context_enricher.PatternDetector') as MockDetector:
            mock_store = MockStore.return_value
            mock_store.load_data.return_value = None
            mock_store.get_data.return_value = None
            mock_store.load_patterns.return_value = []
            mock_store.get_patterns.return_value = []

            enricher = ContextEnricher(
                sensor_store=mock_store,
                pattern_detector=MockDetector.return_value
            )
            return enricher


@pytest.fixture
def sample_doc_chunks():
    """샘플 문서 청크"""
    return [
        {
            "chunk_id": "ec_15_001",
            "content": "C153: Safety Stop - 충돌 감지로 인한 정지. 원인: 물리적 접촉으로 인해 발생",
            "score": 0.92,
            "source": "error_codes",
            "page": 15
        },
        {
            "chunk_id": "sm_45_002",
            "content": "충돌 발생 시 Safety Reset을 수행하십시오.",
            "score": 0.85,
            "source": "service_manual",
            "page": 45
        }
    ]


@pytest.fixture
def sample_patterns():
    """샘플 센서 패턴"""
    return [
        {
            "pattern_id": "PAT-001",
            "pattern_type": "collision",
            "timestamp": "2024-01-17T14:00:00",
            "duration_ms": 1000,
            "confidence": 0.95,
            "metrics": {"peak_value": -800},
            "related_error_codes": ["C153"]
        }
    ]


# ============================================================
# DocEvidence 테스트
# ============================================================

class TestDocEvidence:
    """DocEvidence 데이터클래스 테스트"""

    def test_create_doc_evidence(self):
        """기본 생성 테스트"""
        evidence = DocEvidence(
            chunk_id="test_001",
            content="테스트 내용",
            score=0.9,
            source="test_doc"
        )
        assert evidence.chunk_id == "test_001"
        assert evidence.score == 0.9

    def test_to_dict(self):
        """직렬화 테스트"""
        evidence = DocEvidence(
            chunk_id="test_001",
            content="테스트",
            score=0.9,
            source="test_doc",
            page=10
        )
        d = evidence.to_dict()
        assert d["chunk_id"] == "test_001"
        assert d["page"] == 10

    def test_from_retrieval_result(self):
        """검색 결과에서 생성"""
        result = {
            "chunk_id": "ec_001",
            "content": "에러 내용",
            "score": 0.88,
            "source": "error_codes"
        }
        evidence = DocEvidence.from_retrieval_result(result)
        assert evidence.chunk_id == "ec_001"
        assert evidence.score == 0.88


# ============================================================
# SensorEvidence 테스트
# ============================================================

class TestSensorEvidence:
    """SensorEvidence 데이터클래스 테스트"""

    def test_create_sensor_evidence(self):
        """기본 생성 테스트"""
        now = datetime.now()
        evidence = SensorEvidence(
            patterns=[{"pattern_type": "collision"}],
            statistics={"Fz": AxisStats(mean=-50, std=10, min=-100, max=0)},
            time_range=(now - timedelta(hours=1), now),
            has_anomaly=True
        )
        assert evidence.has_anomaly
        assert len(evidence.patterns) == 1

    def test_to_dict(self):
        """직렬화 테스트"""
        now = datetime.now()
        evidence = SensorEvidence(
            patterns=[],
            statistics={"Fz": AxisStats(mean=-50, std=10, min=-100, max=0)},
            time_range=(now - timedelta(hours=1), now),
            has_anomaly=False
        )
        d = evidence.to_dict()
        assert "time_range" in d
        assert "statistics" in d


# ============================================================
# CorrelationResult 테스트
# ============================================================

class TestCorrelationResult:
    """CorrelationResult 데이터클래스 테스트"""

    def test_create_strong_correlation(self):
        """STRONG 상관관계 생성"""
        result = CorrelationResult(
            level=CorrelationLevel.STRONG,
            confidence=0.95,
            reason="문서 + 센서 모두 확인",
            supporting_evidence=["문서 1건", "센서 패턴 1건"]
        )
        assert result.is_strong
        assert result.has_sensor_support

    def test_create_moderate_correlation(self):
        """MODERATE 상관관계 생성"""
        result = CorrelationResult(
            level=CorrelationLevel.MODERATE,
            confidence=0.75,
            reason="문서만 확인"
        )
        assert not result.is_strong
        assert result.has_sensor_support

    def test_create_none_correlation(self):
        """NONE 상관관계 생성"""
        result = CorrelationResult(
            level=CorrelationLevel.NONE,
            confidence=0.0,
            reason="데이터 없음"
        )
        assert not result.is_strong
        assert not result.has_sensor_support


# ============================================================
# EnrichedContext 테스트
# ============================================================

class TestEnrichedContext:
    """EnrichedContext 데이터클래스 테스트"""

    def test_create_enriched_context(self):
        """기본 생성 테스트"""
        doc_evidence = [DocEvidence("id1", "content", 0.9, "doc")]
        correlation = CorrelationResult(
            level=CorrelationLevel.MODERATE,
            confidence=0.7,
            reason="test"
        )

        context = EnrichedContext(
            doc_evidence=doc_evidence,
            sensor_evidence=None,
            correlation=correlation,
            error_code="C153",
            query="테스트 쿼리"
        )

        assert context.has_doc_evidence
        assert not context.has_sensor_evidence
        assert context.error_code == "C153"

    def test_evidence_summary(self):
        """증거 요약 테스트"""
        doc_evidence = [
            DocEvidence("id1", "content", 0.9, "doc"),
            DocEvidence("id2", "content", 0.8, "doc")
        ]
        correlation = CorrelationResult(
            level=CorrelationLevel.MODERATE,
            confidence=0.7,
            reason="test"
        )

        context = EnrichedContext(
            doc_evidence=doc_evidence,
            sensor_evidence=None,
            correlation=correlation
        )

        assert "문서 2건" in context.evidence_summary


# ============================================================
# ContextEnricher - 상관관계 분석 테스트
# ============================================================

class TestCorrelationAnalysis:
    """상관관계 분석 테스트"""

    def test_strong_correlation_doc_and_sensor(self, enricher, sample_patterns):
        """STRONG: 문서 + 센서 모두 일치"""
        result = enricher.analyze_correlation(
            error_code="C153",
            patterns=sample_patterns,
            doc_causes=["물리적 접촉으로 인한 충돌"]
        )
        assert result.level == CorrelationLevel.STRONG
        assert result.confidence >= 0.85

    def test_moderate_correlation_sensor_only(self, enricher, sample_patterns):
        """MODERATE: 센서만 일치"""
        result = enricher.analyze_correlation(
            error_code="C153",
            patterns=sample_patterns,
            doc_causes=[]  # 문서 원인 없음
        )
        assert result.level == CorrelationLevel.MODERATE
        assert result.confidence >= 0.70

    def test_moderate_correlation_doc_only(self, enricher):
        """MODERATE: 문서만 일치"""
        result = enricher.analyze_correlation(
            error_code="C153",
            patterns=[],  # 센서 패턴 없음
            doc_causes=["물리적 접촉"]
        )
        assert result.level == CorrelationLevel.MODERATE
        assert result.confidence >= 0.70

    def test_weak_correlation_wrong_pattern(self, enricher):
        """WEAK: 예상 외 패턴"""
        wrong_pattern = [{
            "pattern_type": "vibration",  # C153은 collision 예상
            "confidence": 0.8
        }]
        result = enricher.analyze_correlation(
            error_code="C153",
            patterns=wrong_pattern,
            doc_causes=[]
        )
        assert result.level == CorrelationLevel.WEAK

    def test_none_correlation_no_data(self, enricher):
        """NONE: 센서 데이터 없음"""
        result = enricher.analyze_correlation(
            error_code="C153",
            patterns=[],
            doc_causes=[]
        )
        # 센서 없고 문서도 없으면 NONE
        assert result.level == CorrelationLevel.NONE


# ============================================================
# ContextEnricher - Enrich 테스트
# ============================================================

class TestContextEnricherEnrich:
    """enrich() 메서드 테스트"""

    def test_enrich_with_doc_only(self, enricher, sample_doc_chunks):
        """문서만 있는 경우"""
        result = enricher.enrich(
            query="C153 에러 원인",
            doc_chunks=sample_doc_chunks,
            error_code="C153"
        )

        assert isinstance(result, EnrichedContext)
        assert len(result.doc_evidence) == 2
        assert result.error_code == "C153"

    def test_enrich_without_error_code(self, enricher):
        """에러코드 없는 일반 질문"""
        # 원인 키워드가 없는 문서 사용
        simple_chunks = [{
            "chunk_id": "um_001",
            "content": "UR5e의 작업반경은 850mm입니다.",
            "score": 0.85,
            "source": "user_manual"
        }]

        result = enricher.enrich(
            query="로봇 작업 반경",
            doc_chunks=simple_chunks,
            error_code=None
        )

        # 원인 없고 센서 없으면 NONE
        assert result.correlation.level == CorrelationLevel.NONE

    def test_enrich_converts_doc_chunks(self, enricher, sample_doc_chunks):
        """문서 청크 변환 확인"""
        result = enricher.enrich(
            query="테스트",
            doc_chunks=sample_doc_chunks,
            error_code=None
        )

        assert all(isinstance(d, DocEvidence) for d in result.doc_evidence)
        assert result.doc_evidence[0].source == "error_codes"


# ============================================================
# ContextEnricher - 유틸리티 테스트
# ============================================================

class TestContextEnricherUtils:
    """유틸리티 메서드 테스트"""

    def test_parse_time_window(self, enricher):
        """시간 윈도우 파싱"""
        assert enricher._parse_time_window("1h").total_seconds() == 3600
        assert enricher._parse_time_window("30m").total_seconds() == 1800
        assert enricher._parse_time_window("2d").total_seconds() == 2 * 24 * 3600

    def test_get_expected_patterns(self, enricher):
        """예상 패턴 조회"""
        patterns = enricher._get_expected_patterns("C153")
        assert "collision" in patterns

        patterns = enricher._get_expected_patterns("C189")
        assert "overload" in patterns

    def test_get_time_window_for_error(self, enricher):
        """에러별 시간 윈도우"""
        # C153 (collision) → 30m
        window = enricher._get_time_window_for_error("C153")
        assert window == "30m"

        # Unknown error → default (1h)
        window = enricher._get_time_window_for_error("C999")
        assert window == "1h"


# ============================================================
# 싱글톤 테스트
# ============================================================

class TestSingleton:
    """싱글톤 패턴 테스트"""

    def test_get_context_enricher_singleton(self):
        """싱글톤 인스턴스 확인"""
        # Note: 실제 테스트에서는 global state 초기화 필요
        enricher1 = get_context_enricher()
        enricher2 = get_context_enricher()
        assert enricher1 is enricher2


# ============================================================
# 통합 테스트 (실제 데이터 사용)
# ============================================================

class TestContextEnricherIntegration:
    """실제 데이터를 사용한 통합 테스트"""

    def test_enrich_with_real_sensor_data(self):
        """실제 센서 데이터가 있는 경우"""
        data_path = Path("data/sensor/raw/axia80_week_01.parquet")

        if not data_path.exists():
            pytest.skip("Sensor data not available")

        enricher = ContextEnricher()

        doc_chunks = [{
            "chunk_id": "ec_001",
            "content": "C153: Safety Stop 충돌 감지",
            "score": 0.9,
            "source": "error_codes"
        }]

        result = enricher.enrich(
            query="C153 에러가 발생했습니다",
            doc_chunks=doc_chunks,
            error_code="C153",
            reference_time=datetime(2024, 1, 17, 14, 30),  # EVT-001 시점
            time_window="1h"
        )

        # 실제 데이터에서 충돌 패턴이 있어야 함
        assert result.sensor_evidence is not None
        # EVT-001은 2024-01-17 14:00에 충돌이 있음


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
