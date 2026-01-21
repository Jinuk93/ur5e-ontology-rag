# ============================================================
# src/api/services/audit_logger.py - 감사 로거
# ============================================================
# 모든 API 요청의 전체 파이프라인을 기록하고
# trace_id로 조회 가능하게 합니다.
#
# Main-F2에서 구현
# ============================================================

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


# ============================================================
# [1] AuditEntry 데이터 클래스
# ============================================================

@dataclass
class AuditEntry:
    """
    감사 로그 엔트리

    하나의 API 요청에 대한 전체 파이프라인 정보를 담습니다.
    """
    trace_id: str
    timestamp: str
    user_query: str
    normalized_query: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    linked_entities: List[Dict[str, Any]] = field(default_factory=list)
    graph_results: Optional[Dict[str, Any]] = None
    retrieval_results: List[Dict[str, Any]] = field(default_factory=list)
    verifier: Optional[Dict[str, Any]] = None
    answer: Optional[str] = None
    latency: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용 dict 변환 (None 값 제외)"""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                # 빈 리스트/딕셔너리도 포함
                if isinstance(value, (list, dict)) and len(value) == 0:
                    continue
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """딕셔너리에서 AuditEntry 생성"""
        return cls(
            trace_id=data.get("trace_id", ""),
            timestamp=data.get("timestamp", ""),
            user_query=data.get("user_query", ""),
            normalized_query=data.get("normalized_query"),
            analysis=data.get("analysis"),
            linked_entities=data.get("linked_entities", []),
            graph_results=data.get("graph_results"),
            retrieval_results=data.get("retrieval_results", []),
            verifier=data.get("verifier"),
            answer=data.get("answer"),
            latency=data.get("latency", {}),
            error=data.get("error")
        )


# ============================================================
# [2] AuditLogger 클래스
# ============================================================

class AuditLogger:
    """
    요청/응답 감사 로거

    모든 API 요청의 전체 파이프라인을 기록하고
    trace_id로 조회 가능하게 합니다.

    사용 예시:
        logger = AuditLogger()
        trace_id = logger.start("C4A15 에러가 발생했어요")
        logger.log_step(trace_id, "analysis", {"error_codes": ["C4A15"]})
        logger.log_step(trace_id, "linking", [...])
        logger.end(trace_id)

        # 나중에 조회
        entry = logger.get(trace_id)
    """

    def __init__(self, audit_dir: str = "stores/audit"):
        """
        AuditLogger 초기화

        Args:
            audit_dir: 감사 로그 저장 디렉토리
        """
        self.audit_dir = Path(audit_dir)
        self.audit_file = self.audit_dir / "audit_trail.jsonl"
        self._ensure_dir()

        self._lock = threading.Lock()
        self._entries: Dict[str, AuditEntry] = {}  # in-memory cache
        self._timers: Dict[str, Dict[str, float]] = {}  # step timers

    def _ensure_dir(self):
        """디렉토리 생성"""
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # [2.1] 요청 시작/종료
    # --------------------------------------------------------

    def start(self, user_query: str, trace_id: Optional[str] = None) -> str:
        """
        새 요청 시작

        Args:
            user_query: 사용자 질문
            trace_id: 외부 제공 trace_id (없으면 자동 생성)

        Returns:
            trace_id
        """
        if trace_id is None:
            trace_id = str(uuid4())

        entry = AuditEntry(
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_query=user_query
        )

        with self._lock:
            self._entries[trace_id] = entry
            self._timers[trace_id] = {"_start": time.time()}

        return trace_id

    def end(self, trace_id: str, error: Optional[str] = None) -> Optional[AuditEntry]:
        """
        요청 종료 및 저장

        Args:
            trace_id: 요청 식별자
            error: 에러 메시지 (있는 경우)

        Returns:
            저장된 AuditEntry
        """
        with self._lock:
            if trace_id not in self._entries:
                return None

            entry = self._entries[trace_id]
            entry.error = error

            # total latency 계산
            if trace_id in self._timers:
                start = self._timers[trace_id].get("_start", 0)
                entry.latency["total_ms"] = int((time.time() - start) * 1000)
                del self._timers[trace_id]

            # 파일에 저장
            self._write_entry(entry)

            return entry

    # --------------------------------------------------------
    # [2.2] 단계별 로깅
    # --------------------------------------------------------

    def log_step(
        self,
        trace_id: str,
        step: str,
        data: Any,
        start_time: Optional[float] = None
    ):
        """
        파이프라인 단계 로깅

        Args:
            trace_id: 요청 식별자
            step: 단계 이름 (analysis, linking, graph, vector, verifier, generation)
            data: 해당 단계 결과 데이터
            start_time: 단계 시작 시간 (latency 계산용)
        """
        with self._lock:
            if trace_id not in self._entries:
                return

            entry = self._entries[trace_id]

            # 단계별 데이터 저장
            if step == "analysis":
                entry.analysis = data
            elif step == "linking":
                entry.linked_entities = data if isinstance(data, list) else [data]
            elif step == "graph":
                entry.graph_results = data
            elif step == "vector":
                entry.retrieval_results = data if isinstance(data, list) else [data]
            elif step == "verifier":
                entry.verifier = data
            elif step == "generation":
                entry.answer = data
            elif step == "normalized_query":
                entry.normalized_query = data

            # latency 기록
            if start_time is not None:
                entry.latency[f"{step}_ms"] = int((time.time() - start_time) * 1000)

    # --------------------------------------------------------
    # [2.3] 조회
    # --------------------------------------------------------

    def get(self, trace_id: str) -> Optional[AuditEntry]:
        """
        trace_id로 엔트리 조회

        먼저 메모리 캐시를 확인하고, 없으면 파일에서 검색합니다.

        Args:
            trace_id: 요청 식별자

        Returns:
            AuditEntry 또는 None
        """
        # 메모리 캐시 확인
        with self._lock:
            if trace_id in self._entries:
                return self._entries[trace_id]

        # 파일에서 검색
        return self._search_file(trace_id)

    def get_recent(self, limit: int = 10) -> List[AuditEntry]:
        """
        최근 엔트리 조회

        Args:
            limit: 조회할 최대 개수

        Returns:
            최근 AuditEntry 리스트
        """
        entries = []

        if not self.audit_file.exists():
            return entries

        try:
            # 파일 끝에서부터 읽기 (최근 항목)
            with open(self.audit_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in reversed(lines[-limit:]):
                try:
                    data = json.loads(line.strip())
                    entries.append(AuditEntry.from_dict(data))
                except json.JSONDecodeError:
                    continue

        except Exception:
            pass

        return entries

    # --------------------------------------------------------
    # [2.4] 파일 I/O
    # --------------------------------------------------------

    def _write_entry(self, entry: AuditEntry):
        """파일에 엔트리 추가"""
        try:
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            # 로깅 실패는 요청 처리에 영향을 주지 않음
            print(f"[WARN] AuditLogger write failed: {e}")

    def _search_file(self, trace_id: str) -> Optional[AuditEntry]:
        """파일에서 trace_id로 검색"""
        if not self.audit_file.exists():
            return None

        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get("trace_id") == trace_id:
                            return AuditEntry.from_dict(data)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        return None

    # --------------------------------------------------------
    # [2.5] 유틸리티
    # --------------------------------------------------------

    def clear_memory_cache(self):
        """메모리 캐시 정리"""
        with self._lock:
            self._entries.clear()
            self._timers.clear()

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        count = 0
        if self.audit_file.exists():
            with open(self.audit_file, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)

        return {
            "total_entries": count,
            "memory_cache_size": len(self._entries),
            "audit_file": str(self.audit_file)
        }


# ============================================================
# [3] 싱글톤 인스턴스
# ============================================================

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    AuditLogger 싱글톤 반환

    Returns:
        AuditLogger 인스턴스
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# ============================================================
# CLI 실행
# ============================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("AuditLogger Test")
    print("=" * 60)

    logger = AuditLogger()

    # 테스트 1: 기본 로깅
    print("\n[1] Basic logging test")
    trace_id = logger.start("C4A15 에러가 발생했어요")
    print(f"    trace_id: {trace_id}")

    # 단계별 로깅
    t0 = time.time()
    time.sleep(0.01)
    logger.log_step(trace_id, "analysis", {
        "error_codes": ["C4A15"],
        "components": [],
        "query_type": "error_resolution"
    }, t0)

    t0 = time.time()
    time.sleep(0.01)
    logger.log_step(trace_id, "linking", [
        {"entity": "C4A15", "canonical": "C4A15", "node_id": "ERR_C4A15"}
    ], t0)

    logger.log_step(trace_id, "generation", "C4A15 에러는 Joint 3 통신 오류입니다...")

    entry = logger.end(trace_id)
    print(f"    latency: {entry.latency}")

    # 테스트 2: 조회
    print("\n[2] Retrieval test")
    retrieved = logger.get(trace_id)
    if retrieved:
        print(f"    Found: {retrieved.user_query[:30]}...")
        print(f"    Analysis: {retrieved.analysis}")
    else:
        print("    Not found!")

    # 테스트 3: 통계
    print("\n[3] Stats")
    stats = logger.get_stats()
    print(f"    Total entries: {stats['total_entries']}")
    print(f"    Memory cache: {stats['memory_cache_size']}")

    print("\n" + "=" * 60)
    print("[OK] AuditLogger test completed!")
    print("=" * 60)
