"""GPT 합격 기준 검증 스크립트"""

import argparse
import time
import requests

def main():
    parser = argparse.ArgumentParser(description="API acceptance validation")
    parser.add_argument("--base-url", default="http://localhost:8002", help="Base URL, e.g. http://127.0.0.1:8002")
    parser.add_argument("--wait-seconds", type=int, default=5, help="Seconds to wait before running checks")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    time.sleep(args.wait_seconds)  # 서버 시작 대기

    print("=" * 60)
    print("  GPT 합격 기준 검증")
    print("=" * 60)

    all_passed = True

    # 1. /docs 접근 가능
    print("\n[1] /docs 접근 가능")
    try:
        r = requests.get(f"{base_url}/docs", timeout=5)
        passed = r.status_code == 200
        print(f"    Status Code: {r.status_code}")
        print(f"    Result: {'PASS' if passed else 'FAIL'}")
        all_passed = all_passed and passed
    except Exception as e:
        print(f"    Error: {e}")
        print("    Result: FAIL")
        all_passed = False

    # 2. /api/chat - 정상 응답에 trace_id 존재 (query 필드 사용)
    print("\n[2] /api/chat 정상 응답 → trace_id 존재 (query 필드)")
    try:
        r = requests.post(
            f"{base_url}/api/chat",
            json={"query": "Fz가 -350N인데 이게 뭐야?"}  # UI 명세서 기준: query
        )
        resp = r.json()
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
        print(f"    Result: {'PASS' if has_trace_id else 'FAIL'}")
        all_passed = all_passed and has_trace_id and has_similar_events_key and has_node_state_key
        normal_trace_id = resp.get("trace_id")
    except Exception as e:
        print(f"    Error: {e}")
        print("    Result: FAIL")
        all_passed = False
        normal_trace_id = None

    # 2b. message 필드 하위호환 테스트
    print("\n[2b] /api/chat message 필드 하위호환")
    try:
        r = requests.post(
            f"{base_url}/api/chat",
            json={"message": "Fz가 -350N인데 이게 뭐야?"}  # 하위호환: message
        )
        resp = r.json()
        compat_ok = "trace_id" in resp and resp["trace_id"] is not None
        print(f"    trace_id: {resp.get('trace_id')}")
        print(f"    Result: {'PASS' if compat_ok else 'FAIL'} (message 필드 호환)")
        all_passed = all_passed and compat_ok
    except Exception as e:
        print(f"    Error: {e}")
        print("    Result: FAIL")
        all_passed = False

    # 3. ABSTAIN 케이스 검증
    print("\n[3] ABSTAIN 케이스 → abstain + abstain_reason + trace_id")
    try:
        r = requests.post(
            f"{base_url}/api/chat",
            json={"query": "hello"}  # 엔티티 없는 질문
        )
        resp = r.json()
        has_all = all([
            "trace_id" in resp and resp["trace_id"],
            "abstain" in resp,
            "abstain_reason" in resp
        ])
        print(f"    trace_id: {resp.get('trace_id')}")
        print(f"    abstain: {resp.get('abstain')}")
        print(f"    abstain_reason: {resp.get('abstain_reason')}")
        print(f"    Result: {'PASS' if has_all else 'FAIL'}")
        all_passed = all_passed and has_all
        abstain_trace_id = resp.get("trace_id")
    except Exception as e:
        print(f"    Error: {e}")
        print("    Result: FAIL")
        all_passed = False
        abstain_trace_id = None

    # 4. /api/evidence/{trace_id} 조회 가능
    print("\n[4] /api/evidence/{trace_id} 조회 가능")
    test4_passed = True

    # 정상 케이스
    if normal_trace_id:
        r = requests.get(f"{base_url}/api/evidence/{normal_trace_id}")
        resp = r.json()
        found = resp.get("found", False)
        print(f"    Normal trace ({normal_trace_id[:8]}...): found={found}")
        test4_passed = test4_passed and found

    # ABSTAIN 케이스
    if abstain_trace_id:
        r = requests.get(f"{base_url}/api/evidence/{abstain_trace_id}")
        resp = r.json()
        found = resp.get("found", False)
        print(f"    ABSTAIN trace ({abstain_trace_id[:8]}...): found={found}")
        test4_passed = test4_passed and found

    # 없는 ID (found=False 여야 함)
    r = requests.get(f"{base_url}/api/evidence/nonexistent-id-12345")
    resp = r.json()
    not_found = resp.get("found") == False
    print(f"    Nonexistent trace: found={resp.get('found')} (expected: False)")
    test4_passed = test4_passed and not_found

    print(f"    Result: {'PASS' if test4_passed else 'FAIL'}")
    all_passed = all_passed and test4_passed

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
