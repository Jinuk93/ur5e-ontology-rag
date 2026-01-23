"""API 합격 기준(런타임) 검증 스크립트

- 목적: 문서(백엔드 가이드)와 실제 구현이 "실행 기준"으로 일치하는지 확인
- 범위: /health 포함, 주요 API 8개 엔드포인트 런타임 호출 + 핵심 스키마 키 체크
"""

import argparse
import time
from typing import Any, Dict, Optional

import requests


def _print_result(passed: bool):
    print(f"    Result: {'PASS' if passed else 'FAIL'}")


def _safe_json(resp: requests.Response) -> Dict[str, Any]:
    try:
        data = resp.json()
        if isinstance(data, dict):
            return data
        return {"_non_dict_json": data}
    except Exception as e:
        return {"_json_error": str(e), "_text": resp.text[:500]}


def _check_status_200(resp: requests.Response) -> bool:
    return resp.status_code == 200


def _check_has_keys(obj: Dict[str, Any], keys) -> bool:
    return all(k in obj for k in keys)


def _sse_smoke_check(url: str, timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """SSE에서 최소 1개 data 이벤트를 수신하는지 확인."""
    # timeout은 (connect, read)
    with requests.get(
        url,
        stream=True,
        headers={"Accept": "text/event-stream"},
        timeout=(2.0, timeout_seconds),
    ) as resp:
        if resp.status_code != 200:
            return {"ok": False, "status_code": resp.status_code, "headers": dict(resp.headers)}

        content_type = (resp.headers.get("Content-Type") or "").lower()
        x_accel = resp.headers.get("X-Accel-Buffering")

        got_data_line: Optional[str] = None
        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("data:"):
                got_data_line = line
                break

        return {
            "ok": got_data_line is not None,
            "content_type": content_type,
            "x_accel_buffering": x_accel,
            "sample": got_data_line,
        }

def main():
    parser = argparse.ArgumentParser(description="API acceptance validation")
    parser.add_argument("--base-url", default="http://localhost:8002", help="Base URL, e.g. http://127.0.0.1:8002")
    parser.add_argument("--wait-seconds", type=int, default=5, help="Seconds to wait before running checks")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    time.sleep(args.wait_seconds)  # 서버 시작 대기

    print("=" * 60)
    print("  API 합격 기준 검증 (런타임)")
    print("=" * 60)

    all_passed = True

    # 0. /health 접근 가능
    print("\n[0] /health 접근 가능")
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        passed = _check_status_200(r)
        data = _safe_json(r)
        print(f"    Status Code: {r.status_code}")
        print(f"    status: {data.get('status')}")
        print(f"    version: {data.get('version')}")
        _print_result(passed)
        all_passed = all_passed and passed
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False

    # 1. /docs 접근 가능
    print("\n[1] /docs 접근 가능")
    try:
        r = requests.get(f"{base_url}/docs", timeout=5)
        passed = _check_status_200(r)
        print(f"    Status Code: {r.status_code}")
        _print_result(passed)
        all_passed = all_passed and passed
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False

    # 2. /api/chat - 정상 응답에 trace_id 존재 (query 필드 사용)
    print("\n[2] /api/chat 정상 응답 → trace_id 존재 (query 필드)")
    try:
        r = requests.post(
            f"{base_url}/api/chat",
            json={"query": "Fz가 -350N인데 이게 뭐야?"}  # UI 명세서 기준: query
        )
        resp = _safe_json(r)
        has_trace_id = "trace_id" in resp and resp["trace_id"] is not None
        print(f"    trace_id: {resp.get('trace_id')}")
        print(f"    query_type: {resp.get('query_type')}")
        print(f"    abstain: {resp.get('abstain')}")

        # 스키마 필드 존재 확인 (값이 비어도 키가 존재하면 OK)
        evidence = resp.get("evidence", {}) or {}
        graph = resp.get("graph", {}) or {}
        nodes = graph.get("nodes", []) or []
        has_similar_events_key = "similar_events" in evidence
        has_node_state_key = (len(nodes) == 0) or ("state" in (nodes[0] or {}))
        print(f"    evidence.similar_events key: {'OK' if has_similar_events_key else 'MISSING'}")
        print(f"    graph.nodes[0].state key: {'OK' if has_node_state_key else 'MISSING'}")
        _print_result(has_trace_id)
        all_passed = all_passed and has_trace_id and has_similar_events_key and has_node_state_key
        normal_trace_id = resp.get("trace_id")
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False
        normal_trace_id = None

    # 2b. message 필드 하위호환 테스트
    print("\n[2b] /api/chat message 필드 하위호환")
    try:
        r = requests.post(
            f"{base_url}/api/chat",
            json={"message": "Fz가 -350N인데 이게 뭐야?"}  # 하위호환: message
        )
        resp = _safe_json(r)
        compat_ok = "trace_id" in resp and resp["trace_id"] is not None
        print(f"    trace_id: {resp.get('trace_id')}")
        print(f"    Result: {'PASS' if compat_ok else 'FAIL'} (message 필드 호환)")
        all_passed = all_passed and compat_ok
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False

    # 3. ABSTAIN 케이스 검증
    print("\n[3] ABSTAIN 케이스 → abstain + abstain_reason + trace_id")
    try:
        r = requests.post(
            f"{base_url}/api/chat",
            json={"query": "hello"}  # 엔티티 없는 질문
        )
        resp = _safe_json(r)
        has_all = all([
            "trace_id" in resp and resp["trace_id"],
            "abstain" in resp,
            "abstain_reason" in resp
        ])
        print(f"    trace_id: {resp.get('trace_id')}")
        print(f"    abstain: {resp.get('abstain')}")
        print(f"    abstain_reason: {resp.get('abstain_reason')}")
        _print_result(has_all)
        all_passed = all_passed and has_all
        abstain_trace_id = resp.get("trace_id")
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False
        abstain_trace_id = None

    # 4. /api/evidence/{trace_id} 조회 가능
    print("\n[4] /api/evidence/{trace_id} 조회 가능")
    test4_passed = True

    # 정상 케이스
    if normal_trace_id:
        r = requests.get(f"{base_url}/api/evidence/{normal_trace_id}")
        resp = _safe_json(r)
        found = resp.get("found", False)
        print(f"    Normal trace ({normal_trace_id[:8]}...): found={found}")
        test4_passed = test4_passed and found

    # ABSTAIN 케이스
    if abstain_trace_id:
        r = requests.get(f"{base_url}/api/evidence/{abstain_trace_id}")
        resp = _safe_json(r)
        found = resp.get("found", False)
        print(f"    ABSTAIN trace ({abstain_trace_id[:8]}...): found={found}")
        test4_passed = test4_passed and found

    # 없는 ID (found=False 여야 함)
    r = requests.get(f"{base_url}/api/evidence/nonexistent-id-12345")
    resp = _safe_json(r)
    not_found = resp.get("found") == False
    print(f"    Nonexistent trace: found={resp.get('found')} (expected: False)")
    test4_passed = test4_passed and not_found

    _print_result(test4_passed)
    all_passed = all_passed and test4_passed

    # 5. /api/ontology/summary
    print("\n[5] /api/ontology/summary 접근 가능")
    try:
        r = requests.get(f"{base_url}/api/ontology/summary", timeout=10)
        passed = _check_status_200(r)
        data = _safe_json(r)
        print(f"    Status Code: {r.status_code}")
        print(f"    status: {data.get('status')}")
        has_summary_key = "summary" in data
        print(f"    summary key: {'OK' if has_summary_key else 'MISSING'}")
        passed = passed and has_summary_key
        _print_result(passed)
        all_passed = all_passed and passed
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False

    # 6. /api/sensors/readings
    print("\n[6] /api/sensors/readings 기본 응답")
    try:
        r = requests.get(f"{base_url}/api/sensors/readings?limit=5&offset=0", timeout=10)
        passed = _check_status_200(r)
        data = _safe_json(r)
        print(f"    Status Code: {r.status_code}")
        passed = passed and _check_has_keys(data, ["readings", "total", "time_range"])
        readings = data.get("readings") or []
        print(f"    readings count: {len(readings) if isinstance(readings, list) else 'N/A'}")
        if isinstance(readings, list) and readings:
            first = readings[0] if isinstance(readings[0], dict) else {}
            required = ["timestamp", "Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]
            has_fields = isinstance(first, dict) and all(k in first for k in required)
            print(f"    first reading fields: {'OK' if has_fields else 'MISSING'}")
            passed = passed and has_fields
        _print_result(passed)
        all_passed = all_passed and passed
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False

    # 7. /api/sensors/patterns
    print("\n[7] /api/sensors/patterns 기본 응답")
    try:
        r = requests.get(f"{base_url}/api/sensors/patterns?limit=3", timeout=10)
        passed = _check_status_200(r)
        data = _safe_json(r)
        print(f"    Status Code: {r.status_code}")
        passed = passed and _check_has_keys(data, ["patterns", "total"])
        patterns = data.get("patterns") or []
        print(f"    patterns count: {len(patterns) if isinstance(patterns, list) else 'N/A'}")
        _print_result(passed)
        all_passed = all_passed and passed
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False

    # 8. /api/sensors/events
    print("\n[8] /api/sensors/events 기본 응답")
    try:
        r = requests.get(f"{base_url}/api/sensors/events?limit=3", timeout=10)
        passed = _check_status_200(r)
        data = _safe_json(r)
        print(f"    Status Code: {r.status_code}")
        passed = passed and _check_has_keys(data, ["events", "total"])
        events = data.get("events") or []
        print(f"    events count: {len(events) if isinstance(events, list) else 'N/A'}")
        _print_result(passed)
        all_passed = all_passed and passed
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False

    # 9. /api/sensors/stream (SSE)
    print("\n[9] /api/sensors/stream SSE 스모크")
    try:
        sse = _sse_smoke_check(f"{base_url}/api/sensors/stream?interval=0.2", timeout_seconds=5.0)
        ok = bool(sse.get("ok"))
        print(f"    ok: {ok}")
        print(f"    content_type: {sse.get('content_type')}")
        print(f"    X-Accel-Buffering: {sse.get('x_accel_buffering')}")
        if sse.get("sample"):
            print(f"    sample: {str(sse.get('sample'))[:120]}")
        # 헤더는 환경에 따라 charset이 붙을 수 있어 포함 여부로 체크
        content_type = str(sse.get("content_type") or "")
        has_event_stream = "text/event-stream" in content_type
        has_x_accel = str(sse.get("x_accel_buffering") or "").lower() == "no"
        passed = ok and has_event_stream and has_x_accel
        _print_result(passed)
        all_passed = all_passed and passed
    except Exception as e:
        print(f"    Error: {e}")
        _print_result(False)
        all_passed = False

    # 최종 결과
    print("\n" + "=" * 60)
    if all_passed:
        print("  PASS: 모든 합격 기준 통과!")
    else:
        print("  FAIL: 일부 기준 미통과")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
