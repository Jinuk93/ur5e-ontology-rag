"""
Unit tests for Ontology Sensor Pattern Extension

Main-S4: 온톨로지 센서 패턴 확장 테스트
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ontology.schema import (
    EntityType,
    RelationType,
    create_sensor_pattern,
    create_cause,
)
from src.rag.graph_retriever import GraphRetriever, GraphResult


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_graph_store():
    """Mock GraphStore"""
    with patch('src.rag.graph_retriever.GraphStore') as MockStore:
        mock_store = MockStore.return_value
        yield mock_store


@pytest.fixture
def retriever(mock_graph_store):
    """GraphRetriever 인스턴스 (mock store)"""
    with patch('src.rag.graph_retriever.GraphStore') as MockStore:
        MockStore.return_value = mock_graph_store
        return GraphRetriever()


@pytest.fixture
def sample_ontology_json():
    """샘플 ontology.json 데이터"""
    return {
        "version": "1.0",
        "nodes": {
            "SensorPattern": [
                {
                    "pattern_id": "PAT_COLLISION",
                    "type": "collision",
                    "description": "Z축 급격한 힘 증가 (충돌)",
                    "threshold": {"axis": "Fz", "value": 500},
                    "severity": "high"
                }
            ],
            "Cause": [
                {
                    "cause_id": "CAUSE_PHYSICAL_CONTACT",
                    "description": "물리적 접촉 (장애물 충돌)",
                    "category": "physical"
                }
            ]
        },
        "relationships": [
            {
                "type": "INDICATES",
                "source": "PAT_COLLISION",
                "target": "CAUSE_PHYSICAL_CONTACT",
                "confidence": 0.9
            },
            {
                "type": "TRIGGERS",
                "source": "PAT_COLLISION",
                "target": "C153",
                "probability": 0.95
            }
        ]
    }


# ============================================================
# Schema 테스트
# ============================================================

class TestSensorPatternSchema:
    """SensorPattern 스키마 테스트"""

    def test_create_sensor_pattern(self):
        """SensorPattern 엔티티 생성"""
        entity = create_sensor_pattern(
            pattern_id="PAT_COLLISION",
            pattern_type="collision",
            description="충돌 패턴",
            threshold={"axis": "Fz", "value": 500},
            severity="high"
        )

        assert entity.id == "PAT_COLLISION"  # ID는 pattern_id 그대로
        assert entity.type == EntityType.SENSOR_PATTERN
        assert entity.name == "PAT_COLLISION"
        assert entity.properties["type"] == "collision"
        assert entity.properties["severity"] == "high"
        assert entity.properties["description"] == "충돌 패턴"

    def test_create_cause(self):
        """Cause 엔티티 생성"""
        entity = create_cause(
            cause_id="CAUSE_PHYSICAL_CONTACT",
            description="물리적 접촉",
            category="physical"
        )

        assert entity.id == "CAUSE_PHYSICAL_CONTACT"  # ID는 cause_id 그대로
        assert entity.type == EntityType.CAUSE
        assert entity.name == "물리적 접촉"  # name은 description
        assert entity.properties["description"] == "물리적 접촉"
        assert entity.properties["category"] == "physical"

    def test_sensor_pattern_entity_type(self):
        """EntityType에 SENSOR_PATTERN 존재"""
        assert hasattr(EntityType, "SENSOR_PATTERN")
        assert EntityType.SENSOR_PATTERN.value == "SensorPattern"

    def test_cause_entity_type(self):
        """EntityType에 CAUSE 존재"""
        assert hasattr(EntityType, "CAUSE")
        assert EntityType.CAUSE.value == "Cause"

    def test_indicates_relation_type(self):
        """RelationType에 INDICATES 존재"""
        assert hasattr(RelationType, "INDICATES")
        assert RelationType.INDICATES.value == "INDICATES"

    def test_triggers_relation_type(self):
        """RelationType에 TRIGGERS 존재"""
        assert hasattr(RelationType, "TRIGGERS")
        assert RelationType.TRIGGERS.value == "TRIGGERS"


# ============================================================
# GraphRetriever 센서 패턴 검색 테스트
# ============================================================

class TestGraphRetrieverSensorPatterns:
    """GraphRetriever 센서 패턴 검색 테스트"""

    def test_search_sensor_pattern_causes(self, retriever, mock_graph_store):
        """센서 패턴 → 원인 검색"""
        # Mock 쿼리 결과 설정
        mock_graph_store.query.return_value = [
            {
                'sp': {
                    'pattern_id': 'PAT_COLLISION',
                    'type': 'collision',
                    'description': '충돌 패턴'
                },
                'c': {
                    'cause_id': 'CAUSE_PHYSICAL_CONTACT',
                    'description': '물리적 접촉',
                    'category': 'physical'
                },
                'confidence': 0.9
            }
        ]

        results = retriever.search_sensor_pattern_causes("collision")

        assert len(results) == 1
        assert results[0].entity_type == "SensorPattern"
        assert results[0].entity_name == "PAT_COLLISION"
        assert results[0].relation_type == "INDICATES"
        assert len(results[0].related_entities) == 1
        assert results[0].related_entities[0]["cause_id"] == "CAUSE_PHYSICAL_CONTACT"

    def test_search_sensor_pattern_errors(self, retriever, mock_graph_store):
        """센서 패턴 → 에러코드 검색"""
        mock_graph_store.query.return_value = [
            {
                'sp': {
                    'pattern_id': 'PAT_COLLISION',
                    'type': 'collision'
                },
                'e': {
                    'name': 'C153',
                    'title': 'Safety Stop'
                },
                'probability': 0.95
            }
        ]

        results = retriever.search_sensor_pattern_errors("collision")

        assert len(results) == 1
        assert results[0].relation_type == "TRIGGERS"
        assert results[0].related_entities[0]["name"] == "C153"
        assert results[0].related_entities[0]["probability"] == 0.95

    def test_search_error_patterns(self, retriever, mock_graph_store):
        """에러코드 → 연관 센서 패턴 검색"""
        mock_graph_store.query.return_value = [
            {
                'sp': {
                    'pattern_id': 'PAT_COLLISION',
                    'type': 'collision',
                    'description': '충돌 패턴'
                },
                'e': {
                    'name': 'C153'
                },
                'probability': 0.95
            }
        ]

        results = retriever.search_error_patterns("C153")

        assert len(results) == 1
        assert results[0].entity_type == "ErrorCode"
        assert results[0].entity_name == "C153"
        assert "collision" in results[0].content

    def test_search_integrated_path(self, retriever, mock_graph_store):
        """통합 경로 검색"""
        mock_graph_store.query.return_value = [
            {
                'sp': {
                    'pattern_id': 'PAT_COLLISION',
                    'type': 'collision',
                    'description': '충돌 패턴'
                },
                'c': {
                    'cause_id': 'CAUSE_PHYSICAL_CONTACT',
                    'description': '물리적 접촉'
                },
                'e': {
                    'name': 'C153',
                    'title': 'Safety Stop'
                },
                'p': {
                    'name': 'Safety Reset 수행'
                },
                'cause_confidence': 0.9,
                'error_probability': 0.95
            }
        ]

        results = retriever.search_integrated_path("collision")

        assert len(results) == 1
        assert results[0].relation_type == "INTEGRATED"
        assert "가능한 원인" in results[0].content
        assert "연관 에러코드" in results[0].content

    def test_search_with_pattern_types(self, retriever, mock_graph_store):
        """통합 검색에 pattern_types 포함"""
        mock_graph_store.query.return_value = []

        results = retriever.search(
            error_codes=["C153"],
            pattern_types=["collision"]
        )

        # 쿼리가 호출되었는지 확인
        assert mock_graph_store.query.called


# ============================================================
# GraphResult 테스트
# ============================================================

class TestGraphResult:
    """GraphResult 데이터클래스 테스트"""

    def test_create_graph_result(self):
        """GraphResult 생성"""
        result = GraphResult(
            content="테스트 컨텐츠",
            entity_type="SensorPattern",
            entity_name="PAT_COLLISION",
            related_entities=[{"type": "Cause", "cause_id": "CAUSE_1"}],
            relation_type="INDICATES",
            metadata={"source": "GraphDB"},
            score=1.0
        )

        assert result.entity_type == "SensorPattern"
        assert result.entity_name == "PAT_COLLISION"
        assert result.score == 1.0
        assert len(result.related_entities) == 1

    def test_graph_result_repr(self):
        """GraphResult __repr__"""
        result = GraphResult(
            content="test",
            entity_type="SensorPattern",
            entity_name="PAT_COLLISION",
            related_entities=[{}, {}]
        )

        repr_str = repr(result)
        assert "PAT_COLLISION" in repr_str
        assert "SensorPattern" in repr_str


# ============================================================
# ontology.json 로드 테스트
# ============================================================

class TestOntologyJsonLoad:
    """ontology.json 로드 및 검증 테스트"""

    def test_ontology_json_exists(self):
        """ontology.json 파일 존재 확인"""
        ontology_path = Path("data/processed/ontology/ontology.json")
        assert ontology_path.exists(), "ontology.json not found"

    def test_ontology_json_structure(self):
        """ontology.json 구조 검증"""
        ontology_path = Path("data/processed/ontology/ontology.json")

        if not ontology_path.exists():
            pytest.skip("ontology.json not found")

        with open(ontology_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 필수 키 확인
        assert "nodes" in data
        assert "relationships" in data

        # SensorPattern 노드 확인
        assert "SensorPattern" in data["nodes"]
        patterns = data["nodes"]["SensorPattern"]
        assert len(patterns) >= 4  # collision, vibration, overload, drift

        # Cause 노드 확인
        assert "Cause" in data["nodes"]
        causes = data["nodes"]["Cause"]
        assert len(causes) >= 5

        # 관계 확인
        rels = data["relationships"]
        indicates_count = sum(1 for r in rels if r["type"] == "INDICATES")
        triggers_count = sum(1 for r in rels if r["type"] == "TRIGGERS")

        assert indicates_count >= 6
        assert triggers_count >= 4

    def test_sensor_pattern_fields(self):
        """SensorPattern 필드 검증"""
        ontology_path = Path("data/processed/ontology/ontology.json")

        if not ontology_path.exists():
            pytest.skip("ontology.json not found")

        with open(ontology_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for pattern in data["nodes"]["SensorPattern"]:
            assert "pattern_id" in pattern
            assert "type" in pattern
            assert "description" in pattern
            assert pattern["type"] in ["collision", "vibration", "overload", "drift"]


# ============================================================
# 통합 테스트
# ============================================================

class TestSensorPatternIntegration:
    """센서 패턴 통합 테스트"""

    def test_pattern_to_cause_to_error_flow(self, sample_ontology_json):
        """패턴 → 원인 → 에러 흐름 확인"""
        data = sample_ontology_json

        # PAT_COLLISION이 CAUSE_PHYSICAL_CONTACT를 INDICATES
        indicates_rels = [r for r in data["relationships"] if r["type"] == "INDICATES"]
        collision_causes = [
            r for r in indicates_rels
            if r["source"] == "PAT_COLLISION"
        ]
        assert len(collision_causes) >= 1

        # PAT_COLLISION이 C153을 TRIGGERS
        triggers_rels = [r for r in data["relationships"] if r["type"] == "TRIGGERS"]
        collision_errors = [
            r for r in triggers_rels
            if r["source"] == "PAT_COLLISION"
        ]
        assert len(collision_errors) >= 1
        assert collision_errors[0]["target"] == "C153"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
