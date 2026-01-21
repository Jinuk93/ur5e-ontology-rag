# ============================================================
# tests/unit/test_audit_logger.py - AuditLogger 단위 테스트
# ============================================================
# pytest -v tests/unit/test_audit_logger.py
# ============================================================

import os
import sys
import json
import pytest
import tempfile
import time
from pathlib import Path

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.api.services.audit_logger import AuditLogger, AuditEntry


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_audit_dir():
    """임시 audit 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def audit_logger(temp_audit_dir):
    """테스트용 AuditLogger"""
    return AuditLogger(audit_dir=temp_audit_dir)


# ============================================================
# [1] 기본 기능 테스트
# ============================================================

class TestBasicFunctionality:
    """기본 기능 테스트"""

    def test_start_creates_entry(self, audit_logger):
        """start()가 엔트리를 생성하는지"""
        trace_id = audit_logger.start("테스트 질문")
        assert trace_id is not None
        assert len(trace_id) == 36  # UUID 형식

    def test_start_with_custom_trace_id(self, audit_logger):
        """커스텀 trace_id 지정"""
        custom_id = "custom-trace-123"
        trace_id = audit_logger.start("테스트", trace_id=custom_id)
        assert trace_id == custom_id

    def test_log_step_analysis(self, audit_logger):
        """analysis 단계 로깅"""
        trace_id = audit_logger.start("C4A15 에러")
        audit_logger.log_step(trace_id, "analysis", {
            "error_codes": ["C4A15"],
            "components": [],
            "query_type": "error_resolution"
        })
        entry = audit_logger.get(trace_id)
        assert entry.analysis["error_codes"] == ["C4A15"]

    def test_log_step_linking(self, audit_logger):
        """linking 단계 로깅"""
        trace_id = audit_logger.start("C4A15 에러")
        audit_logger.log_step(trace_id, "linking", [
            {"entity": "C4A15", "canonical": "C4A15", "node_id": "ERR_C4A15"}
        ])
        entry = audit_logger.get(trace_id)
        assert len(entry.linked_entities) == 1
        assert entry.linked_entities[0]["entity"] == "C4A15"

    def test_log_step_graph(self, audit_logger):
        """graph 단계 로깅"""
        trace_id = audit_logger.start("C4A15 에러")
        audit_logger.log_step(trace_id, "graph", {
            "paths": ["(ERR_C4A15)-[RESOLVED_BY]->(RES_001)"],
            "node_count": 2,
            "edge_count": 1
        })
        entry = audit_logger.get(trace_id)
        assert entry.graph_results["node_count"] == 2

    def test_log_step_vector(self, audit_logger):
        """vector 단계 로깅"""
        trace_id = audit_logger.start("에러 해결")
        audit_logger.log_step(trace_id, "vector", [
            {"chunk_id": "chunk_001", "score": 0.95}
        ])
        entry = audit_logger.get(trace_id)
        assert len(entry.retrieval_results) == 1

    def test_log_step_verifier(self, audit_logger):
        """verifier 단계 로깅"""
        trace_id = audit_logger.start("에러 해결")
        audit_logger.log_step(trace_id, "verifier", {
            "status": "PASS",
            "doc_verified": True
        })
        entry = audit_logger.get(trace_id)
        assert entry.verifier["status"] == "PASS"

    def test_log_step_generation(self, audit_logger):
        """generation 단계 로깅"""
        trace_id = audit_logger.start("에러 해결")
        audit_logger.log_step(trace_id, "generation", "C4A15는 Joint 3 통신 오류입니다.")
        entry = audit_logger.get(trace_id)
        assert "C4A15" in entry.answer

    def test_end_writes_to_file(self, audit_logger, temp_audit_dir):
        """end()가 파일에 기록하는지"""
        trace_id = audit_logger.start("테스트")
        audit_logger.end(trace_id)

        audit_file = Path(temp_audit_dir) / "audit_trail.jsonl"
        assert audit_file.exists()

        with open(audit_file, "r", encoding="utf-8") as f:
            data = json.loads(f.readline())
            assert data["trace_id"] == trace_id


# ============================================================
# [2] 엔트리 조회 테스트
# ============================================================

class TestEntryRetrieval:
    """엔트리 조회 테스트"""

    def test_get_from_memory(self, audit_logger):
        """메모리에서 조회"""
        trace_id = audit_logger.start("테스트")
        entry = audit_logger.get(trace_id)
        assert entry is not None
        assert entry.user_query == "테스트"

    def test_get_from_file(self, audit_logger, temp_audit_dir):
        """파일에서 조회"""
        trace_id = audit_logger.start("파일 조회 테스트")
        audit_logger.end(trace_id)

        # 새 인스턴스로 파일에서 조회
        new_logger = AuditLogger(audit_dir=temp_audit_dir)
        entry = new_logger.get(trace_id)
        assert entry is not None
        assert entry.user_query == "파일 조회 테스트"

    def test_get_nonexistent(self, audit_logger):
        """존재하지 않는 trace_id"""
        entry = audit_logger.get("nonexistent-id")
        assert entry is None

    def test_get_recent(self, audit_logger):
        """최근 엔트리 조회"""
        # 여러 엔트리 생성
        for i in range(5):
            trace_id = audit_logger.start(f"질문 {i}")
            audit_logger.end(trace_id)

        entries = audit_logger.get_recent(limit=3)
        assert len(entries) == 3


# ============================================================
# [3] Latency 측정 테스트
# ============================================================

class TestLatencyMeasurement:
    """Latency 측정 테스트"""

    def test_total_latency(self, audit_logger):
        """전체 latency 측정"""
        trace_id = audit_logger.start("latency 테스트")
        time.sleep(0.05)  # 50ms
        entry = audit_logger.end(trace_id)
        assert entry.latency["total_ms"] >= 50

    def test_step_latency(self, audit_logger):
        """단계별 latency 측정"""
        trace_id = audit_logger.start("단계별 테스트")

        t0 = time.time()
        time.sleep(0.03)  # 30ms
        audit_logger.log_step(trace_id, "analysis", {}, t0)

        entry = audit_logger.get(trace_id)
        assert entry.latency.get("analysis_ms", 0) >= 30


# ============================================================
# [4] 에러 핸들링 테스트
# ============================================================

class TestErrorHandling:
    """에러 핸들링 테스트"""

    def test_end_with_error(self, audit_logger):
        """에러 메시지 기록"""
        trace_id = audit_logger.start("에러 테스트")
        entry = audit_logger.end(trace_id, error="테스트 에러")
        assert entry.error == "테스트 에러"

    def test_log_step_invalid_trace_id(self, audit_logger):
        """존재하지 않는 trace_id에 log_step"""
        # 에러 발생하지 않고 무시됨
        audit_logger.log_step("invalid-id", "analysis", {})
        # 에러 없이 완료되면 성공

    def test_end_invalid_trace_id(self, audit_logger):
        """존재하지 않는 trace_id에 end"""
        result = audit_logger.end("invalid-id")
        assert result is None


# ============================================================
# [5] AuditEntry 테스트
# ============================================================

class TestAuditEntry:
    """AuditEntry 데이터클래스 테스트"""

    def test_to_dict(self):
        """to_dict() 메서드"""
        entry = AuditEntry(
            trace_id="test-id",
            timestamp="2024-01-21T10:00:00Z",
            user_query="테스트"
        )
        d = entry.to_dict()
        assert d["trace_id"] == "test-id"
        assert "error" not in d  # None은 제외됨

    def test_to_dict_excludes_empty_lists(self):
        """to_dict()가 빈 리스트를 제외하는지"""
        entry = AuditEntry(
            trace_id="test-id",
            timestamp="2024-01-21T10:00:00Z",
            user_query="테스트",
            linked_entities=[],
            retrieval_results=[]
        )
        d = entry.to_dict()
        assert "linked_entities" not in d
        assert "retrieval_results" not in d

    def test_from_dict(self):
        """from_dict() 메서드"""
        data = {
            "trace_id": "test-id",
            "timestamp": "2024-01-21T10:00:00Z",
            "user_query": "테스트",
            "analysis": {"error_codes": ["C4A15"]}
        }
        entry = AuditEntry.from_dict(data)
        assert entry.trace_id == "test-id"
        assert entry.analysis["error_codes"] == ["C4A15"]


# ============================================================
# [6] 통계 테스트
# ============================================================

class TestStats:
    """통계 정보 테스트"""

    def test_get_stats(self, audit_logger, temp_audit_dir):
        """통계 정보 조회"""
        # 엔트리 생성
        for i in range(3):
            trace_id = audit_logger.start(f"질문 {i}")
            audit_logger.end(trace_id)

        stats = audit_logger.get_stats()
        assert stats["total_entries"] == 3
        assert "memory_cache_size" in stats
        assert "audit_file" in stats

    def test_clear_memory_cache(self, audit_logger):
        """메모리 캐시 정리"""
        trace_id = audit_logger.start("테스트")
        audit_logger.clear_memory_cache()

        # 메모리에서는 찾을 수 없음
        stats = audit_logger.get_stats()
        assert stats["memory_cache_size"] == 0


# ============================================================
# 메인 실행
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
