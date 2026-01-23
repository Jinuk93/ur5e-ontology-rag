"""통합 테스트: API 쿼리 엔드포인트

Step 16 통합 테스트의 일부로, /api/chat 및 관련 엔드포인트를 pytest 환경에서 검증한다.

Note:
    - 서버가 실행 중이어야 함 (python scripts/run_api.py --port 8002)
    - 또는 pytest-xprocess 등으로 서버를 자동 시작하도록 구성
    - E2E 검증은 scripts/e2e_validate.ps1 사용 권장
"""

import os

import pytest
import requests

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8002")


def _get(endpoint: str, **kwargs):
    return requests.get(f"{BASE_URL}{endpoint}", timeout=10, **kwargs)


def _post(endpoint: str, json_data: dict, **kwargs):
    return requests.post(f"{BASE_URL}{endpoint}", json=json_data, timeout=10, **kwargs)


@pytest.fixture(scope="module")
def server_available():
    """서버 접근 가능 여부 확인."""
    try:
        resp = _get("/health")
        if resp.status_code != 200:
            pytest.skip("API 서버가 실행 중이 아님 (서버 시작 후 재시도)")
        return True
    except requests.exceptions.ConnectionError:
        pytest.skip("API 서버에 연결할 수 없음 (서버 시작 후 재시도)")


class TestHealthEndpoint:
    """헬스 체크 엔드포인트 테스트."""

    def test_health_returns_200(self, server_available):
        resp = _get("/health")
        assert resp.status_code == 200

    def test_health_returns_status_ok(self, server_available):
        resp = _get("/health")
        data = resp.json()
        assert data.get("status") == "healthy"


class TestChatEndpoint:
    """채팅 API 엔드포인트 테스트."""

    def test_chat_returns_200(self, server_available):
        resp = _post("/api/chat", {"query": "Fz가 -350N인데 이게 뭐야?"})
        assert resp.status_code == 200

    def test_chat_returns_trace_id(self, server_available):
        resp = _post("/api/chat", {"query": "Fz가 -350N인데 이게 뭐야?"})
        data = resp.json()
        assert "trace_id" in data
        assert data["trace_id"] is not None

    def test_chat_returns_query_type(self, server_available):
        resp = _post("/api/chat", {"query": "Fz가 -350N인데 이게 뭐야?"})
        data = resp.json()
        assert "query_type" in data
        assert data["query_type"] in ["ontology", "hybrid", "rag"]

    def test_chat_returns_answer(self, server_available):
        resp = _post("/api/chat", {"query": "Fz가 -350N인데 이게 뭐야?"})
        data = resp.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_chat_backward_compat_message(self, server_available):
        """message 파라미터 하위호환 테스트."""
        resp = _post("/api/chat", {"message": "테스트 질문"})
        assert resp.status_code == 200


class TestEvidenceEndpoint:
    """근거 조회 엔드포인트 테스트."""

    def test_evidence_with_valid_trace_id(self, server_available):
        # 먼저 chat으로 trace_id 획득
        chat_resp = _post("/api/chat", {"query": "Fz가 -350N"})
        trace_id = chat_resp.json().get("trace_id")

        # evidence 조회
        resp = _get(f"/api/evidence/{trace_id}")
        assert resp.status_code == 200

    def test_evidence_returns_expected_keys(self, server_available):
        chat_resp = _post("/api/chat", {"query": "Fz가 -350N"})
        trace_id = chat_resp.json().get("trace_id")

        resp = _get(f"/api/evidence/{trace_id}")
        data = resp.json()
        # evidence에 ontology_paths, document_refs 등이 있어야 함
        assert "ontology_paths" in data or "reasoning" in data


class TestOntologyEndpoint:
    """온톨로지 API 테스트."""

    def test_ontology_summary_returns_200(self, server_available):
        resp = _get("/api/ontology/summary")
        assert resp.status_code == 200

    def test_ontology_summary_has_counts(self, server_available):
        resp = _get("/api/ontology/summary")
        data = resp.json()
        assert "entity_count" in data or "entities" in data


class TestSensorEndpoints:
    """센서 API 테스트 (degrade 허용)."""

    def test_sensor_readings_returns_200_or_empty(self, server_available):
        resp = _get("/api/sensors/readings")
        # 200이거나 데이터 없음 (degrade)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_sensor_patterns_returns_200(self, server_available):
        resp = _get("/api/sensors/patterns")
        assert resp.status_code == 200

    def test_sensor_events_returns_200(self, server_available):
        resp = _get("/api/sensors/events")
        assert resp.status_code == 200
