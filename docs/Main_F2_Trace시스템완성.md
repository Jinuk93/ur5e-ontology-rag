# Main-F2: Trace 시스템 완성 상세 설계서

> **Phase**: Main-F2 (Foundation 개선 Phase 2)
> **목표**: 모든 요청/응답을 추적 가능하게 audit_trail.jsonl 구현
> **선행 조건**: Main-F1 (Entity Linker 개선) 완료
> **참조**: Main__Spec.md Section 5, 7 / Foundation_Spec.md Section 4.4.5, 7.4

---

## 1. 개요

### 1.1 배경 (Foundation의 문제점)

Foundation 단계에서 계획되었으나 미구현된 Trace 시스템:

```python
# apps/api/src/services/audit_logger.py 현재 상태
# TODO: Phase 8에서 구현 예정
```

**문제점**:
1. `audit_trail.jsonl` 미구현 - 요청/응답 기록 없음
2. `trace_id`가 로그에만 남고 저장/조회 불가
3. `/evidence/{trace_id}` 엔드포인트 미구현
4. 디버깅 시 파이프라인 재현 어려움
5. 답변 품질 평가를 위한 이력 추적 불가

### 1.2 목표

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Main-F2 목표                                      │
├─────────────────────────────────────────────────────────────────────┤
│ 1. 모든 API 요청에 trace_id 발급 및 저장                             │
│ 2. 파이프라인 각 단계 정보를 audit_trail.jsonl에 기록                │
│ 3. trace_id로 전체 파이프라인 재현 가능                              │
│ 4. /evidence/{trace_id} 엔드포인트로 근거 상세 조회                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 핵심 가치

| 가치 | 설명 |
|------|------|
| **재현 가능성** | trace_id로 동일 질문에 대한 전체 파이프라인 재현 |
| **디버깅** | 문제 발생 시 어느 단계에서 실패했는지 추적 |
| **평가** | 답변 품질 평가를 위한 이력 데이터 축적 |
| **감사** | 시스템 동작 이력 보관 (compliance) |

---

## 2. 아키텍처

### 2.1 전체 흐름

```
사용자 질문
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ API Layer (trace_id 발급)                                            │
│   trace_id = uuid4()                                                │
│   audit_logger.start(trace_id, user_query)                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌─────────┐         ┌─────────┐           ┌─────────┐
│ Query   │   →     │ Entity  │    →      │ Graph   │
│ Analyzer│         │ Linker  │           │Retriever│
└────┬────┘         └────┬────┘           └────┬────┘
     │                   │                     │
     │  audit_logger     │  audit_logger       │  audit_logger
     │  .log_step()      │  .log_step()        │  .log_step()
     │                   │                     │
    ┌┴───────────────────┴─────────────────────┴┐
    │                                           │
    ▼                                           ▼
┌─────────┐         ┌─────────┐           ┌─────────┐
│ Vector  │   →     │ Verifier│    →      │Generator│
│Retriever│         │         │           │         │
└────┬────┘         └────┬────┘           └────┬────┘
     │                   │                     │
     │  audit_logger     │  audit_logger       │  audit_logger
     │  .log_step()      │  .log_step()        │  .log_step()
     │                   │                     │
     └───────────────────┴─────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ API Layer (응답 반환)                                                │
│   audit_logger.end(trace_id, response)                              │
│   → stores/audit/audit_trail.jsonl에 저장                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 파일 구조

```
ur5e-ontology-rag/
├── stores/
│   └── audit/
│       └── audit_trail.jsonl        # [Main-F2] 감사 로그 저장
│
├── src/
│   └── api/
│       ├── routes/
│       │   └── evidence.py          # [Main-F2] 신규 생성
│       │
│       ├── schemas/
│       │   └── evidence.py          # [Main-F2] 신규 생성
│       │
│       └── services/
│           └── audit_logger.py      # [Main-F2] 구현
│
└── tests/
    └── unit/
        └── test_audit_logger.py     # [Main-F2] 테스트
```

---

## 3. 상세 설계

### 3.1 audit_trail.jsonl 스키마

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-21T10:30:00.123Z",
  "user_query": "C4A15 에러가 발생했어요. 어떻게 해결하나요?",
  "normalized_query": "C4A15 에러가 발생했어요. 어떻게 해결하나요?",

  "analysis": {
    "error_codes": ["C4A15"],
    "components": [],
    "query_type": "error_resolution",
    "search_strategy": "graph_first"
  },

  "linked_entities": [
    {
      "entity": "C4A15",
      "canonical": "C4A15",
      "node_id": "ERR_C4A15",
      "entity_type": "error_code",
      "confidence": 1.0,
      "matched_by": "lexicon"
    }
  ],

  "graph_results": {
    "paths": [
      "(ERR_C4A15)-[RESOLVED_BY]->(RES_COMPLETE_REBOOT)",
      "(ERR_C4A15)-[CAUSED_BY]->(CAUSE_JOINT_COMM_LOST)"
    ],
    "expansion_terms": ["Joint 3", "communication", "reboot"],
    "node_count": 3,
    "edge_count": 2
  },

  "retrieval_results": [
    {
      "chunk_id": "error_codes_15_001",
      "doc_id": "error_codes",
      "page": 15,
      "score": 0.89,
      "preview": "C4A15: Communication with joint 3 lost..."
    }
  ],

  "verifier": {
    "status": "PASS",
    "doc_verified": true,
    "sensor_verified": null,
    "decision_reason": "Action citation satisfied"
  },

  "answer": "C4A15 에러는 'Joint 3 통신 손실'을 의미합니다...",

  "latency": {
    "total_ms": 564,
    "analysis_ms": 23,
    "linking_ms": 15,
    "graph_ms": 89,
    "vector_ms": 156,
    "verifier_ms": 12,
    "generation_ms": 269
  },

  "error": null
}
```

### 3.2 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `trace_id` | string (UUID) | ✓ | 요청 고유 식별자 |
| `timestamp` | string (ISO8601) | ✓ | 요청 시작 시간 (UTC) |
| `user_query` | string | ✓ | 원본 사용자 질문 |
| `normalized_query` | string | | 정규화된 질문 |
| `analysis` | object | ✓ | QueryAnalyzer 결과 |
| `linked_entities` | array | ✓ | EntityLinker 결과 |
| `graph_results` | object | | GraphRetriever 결과 |
| `retrieval_results` | array | ✓ | VectorRetriever 결과 (top-k) |
| `verifier` | object | ✓ | Verifier 판정 결과 |
| `answer` | string | ✓ | 최종 답변 |
| `latency` | object | ✓ | 각 단계별 처리 시간 |
| `error` | string | | 에러 발생 시 메시지 |

### 3.3 AuditLogger 클래스 설계

```python
# src/api/services/audit_logger.py

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


@dataclass
class AuditEntry:
    """감사 로그 엔트리"""
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
        """JSON 직렬화용 dict 변환"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class AuditLogger:
    """
    요청/응답 감사 로거

    모든 API 요청의 전체 파이프라인을 기록하고
    trace_id로 조회 가능하게 합니다.
    """

    def __init__(self, audit_dir: str = "stores/audit"):
        self.audit_dir = Path(audit_dir)
        self.audit_file = self.audit_dir / "audit_trail.jsonl"
        self._ensure_dir()
        self._lock = threading.Lock()
        self._entries: Dict[str, AuditEntry] = {}  # in-memory cache
        self._timers: Dict[str, Dict[str, float]] = {}  # step timers

    def _ensure_dir(self):
        """디렉토리 생성"""
        self.audit_dir.mkdir(parents=True, exist_ok=True)

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
            self._timers[trace_id] = {"_start": self._now()}

        return trace_id

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
                entry.linked_entities = data
            elif step == "graph":
                entry.graph_results = data
            elif step == "vector":
                entry.retrieval_results = data
            elif step == "verifier":
                entry.verifier = data
            elif step == "generation":
                entry.answer = data
            elif step == "normalized_query":
                entry.normalized_query = data

            # latency 기록
            if start_time is not None:
                entry.latency[f"{step}_ms"] = int((self._now() - start_time) * 1000)

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
                entry.latency["total_ms"] = int((self._now() - start) * 1000)
                del self._timers[trace_id]

            # 파일에 저장
            self._write_entry(entry)

            # 메모리에서 제거 (선택적)
            # del self._entries[trace_id]

            return entry

    def get(self, trace_id: str) -> Optional[AuditEntry]:
        """
        trace_id로 엔트리 조회

        먼저 메모리 캐시를 확인하고, 없으면 파일에서 검색합니다.
        """
        # 메모리 캐시 확인
        with self._lock:
            if trace_id in self._entries:
                return self._entries[trace_id]

        # 파일에서 검색
        return self._search_file(trace_id)

    def _write_entry(self, entry: AuditEntry):
        """파일에 엔트리 추가"""
        try:
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            # 로깅 실패는 요청 처리에 영향을 주지 않음
            print(f"[AuditLogger] Write failed: {e}")

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
                            return AuditEntry(**data)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        return None

    def _now(self) -> float:
        """현재 시간 (초)"""
        import time
        return time.time()


# 싱글톤 인스턴스
_audit_logger: Optional[AuditLogger] = None

def get_audit_logger() -> AuditLogger:
    """AuditLogger 싱글톤 반환"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
```

### 3.4 /evidence/{trace_id} 엔드포인트

#### 3.4.1 라우터 (src/api/routes/evidence.py)

```python
# src/api/routes/evidence.py

from fastapi import APIRouter, HTTPException
from src.api.schemas.evidence import EvidenceResponse
from src.api.services.audit_logger import get_audit_logger

router = APIRouter()


@router.get("/evidence/{trace_id}", response_model=EvidenceResponse)
async def get_evidence(trace_id: str):
    """
    trace_id로 근거/경로 상세 조회

    특정 요청의 전체 파이프라인 정보를 반환합니다.

    - **trace_id**: 요청 식별자 (UUID)

    ## 응답

    - **trace_id**: 요청 식별자
    - **timestamp**: 요청 시간
    - **user_query**: 원본 질문
    - **evidence**: 문서 근거 목록
    - **graph_paths**: 그래프 추론 경로
    - **linked_entities**: 엔티티 링킹 결과
    - **retrieval_debug**: 검색 디버그 정보
    - **verifier**: 검증 결과
    - **latency**: 처리 시간 상세

    ## 예시 요청

    ```
    GET /api/v1/evidence/550e8400-e29b-41d4-a716-446655440000
    ```
    """
    audit_logger = get_audit_logger()
    entry = audit_logger.get(trace_id)

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trace not found: {trace_id}"
        )

    return EvidenceResponse.from_audit_entry(entry)
```

#### 3.4.2 스키마 (src/api/schemas/evidence.py)

```python
# src/api/schemas/evidence.py

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LinkedEntityDetail(BaseModel):
    """엔티티 링킹 상세"""
    entity: str = Field(..., description="원본 텍스트")
    canonical: str = Field(..., description="정규화된 이름")
    node_id: str = Field(..., description="온톨로지 노드 ID")
    entity_type: str = Field(..., description="엔티티 타입 (error_code/component)")
    confidence: float = Field(..., description="신뢰도 (0.0-1.0)")
    matched_by: str = Field(..., description="매칭 방식 (lexicon/regex/embedding)")


class EvidenceItem(BaseModel):
    """문서 근거 항목"""
    doc_id: str = Field(..., description="문서 ID")
    page: int = Field(..., description="페이지 번호")
    chunk_id: str = Field(..., description="청크 ID")
    score: float = Field(..., description="관련성 점수")
    preview: Optional[str] = Field(None, description="내용 미리보기")


class GraphPathInfo(BaseModel):
    """그래프 경로 정보"""
    paths: List[str] = Field(default_factory=list, description="추론 경로 목록")
    expansion_terms: List[str] = Field(default_factory=list, description="확장 검색어")
    node_count: int = Field(0, description="사용된 노드 수")
    edge_count: int = Field(0, description="사용된 엣지 수")


class VerifierInfo(BaseModel):
    """검증 정보"""
    status: str = Field(..., description="PASS/PARTIAL/ABSTAIN/FAIL")
    doc_verified: bool = Field(..., description="문서 근거 확인 여부")
    sensor_verified: Optional[bool] = Field(None, description="센서 근거 확인 여부")
    decision_reason: str = Field(..., description="판정 사유")


class LatencyInfo(BaseModel):
    """처리 시간 정보"""
    total_ms: int = Field(0, description="전체 처리 시간 (ms)")
    analysis_ms: Optional[int] = Field(None, description="질문 분석 시간")
    linking_ms: Optional[int] = Field(None, description="엔티티 링킹 시간")
    graph_ms: Optional[int] = Field(None, description="그래프 검색 시간")
    vector_ms: Optional[int] = Field(None, description="벡터 검색 시간")
    verifier_ms: Optional[int] = Field(None, description="검증 시간")
    generation_ms: Optional[int] = Field(None, description="답변 생성 시간")


class EvidenceResponse(BaseModel):
    """근거 상세 응답"""
    trace_id: str = Field(..., description="요청 식별자")
    timestamp: str = Field(..., description="요청 시간 (ISO8601)")
    user_query: str = Field(..., description="원본 질문")

    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="문서 근거 목록"
    )
    graph_paths: GraphPathInfo = Field(
        default_factory=GraphPathInfo,
        description="그래프 추론 경로"
    )
    linked_entities: List[LinkedEntityDetail] = Field(
        default_factory=list,
        description="엔티티 링킹 결과"
    )
    verifier: Optional[VerifierInfo] = Field(
        None,
        description="검증 결과"
    )
    latency: LatencyInfo = Field(
        default_factory=LatencyInfo,
        description="처리 시간 상세"
    )
    answer: Optional[str] = Field(None, description="최종 답변")
    error: Optional[str] = Field(None, description="에러 메시지")

    @classmethod
    def from_audit_entry(cls, entry) -> "EvidenceResponse":
        """AuditEntry에서 변환"""
        # evidence 변환
        evidence = []
        for r in entry.retrieval_results or []:
            evidence.append(EvidenceItem(
                doc_id=r.get("doc_id", ""),
                page=r.get("page", 0),
                chunk_id=r.get("chunk_id", ""),
                score=r.get("score", 0.0),
                preview=r.get("preview")
            ))

        # graph_paths 변환
        graph = entry.graph_results or {}
        graph_paths = GraphPathInfo(
            paths=graph.get("paths", []),
            expansion_terms=graph.get("expansion_terms", []),
            node_count=graph.get("node_count", 0),
            edge_count=graph.get("edge_count", 0)
        )

        # linked_entities 변환
        linked = []
        for e in entry.linked_entities or []:
            linked.append(LinkedEntityDetail(
                entity=e.get("entity", ""),
                canonical=e.get("canonical", ""),
                node_id=e.get("node_id", ""),
                entity_type=e.get("entity_type", ""),
                confidence=e.get("confidence", 0.0),
                matched_by=e.get("matched_by", "")
            ))

        # verifier 변환
        verifier = None
        if entry.verifier:
            verifier = VerifierInfo(
                status=entry.verifier.get("status", "FAIL"),
                doc_verified=entry.verifier.get("doc_verified", False),
                sensor_verified=entry.verifier.get("sensor_verified"),
                decision_reason=entry.verifier.get("decision_reason", "")
            )

        # latency 변환
        lat = entry.latency or {}
        latency = LatencyInfo(
            total_ms=lat.get("total_ms", 0),
            analysis_ms=lat.get("analysis_ms"),
            linking_ms=lat.get("linking_ms"),
            graph_ms=lat.get("graph_ms"),
            vector_ms=lat.get("vector_ms"),
            verifier_ms=lat.get("verifier_ms"),
            generation_ms=lat.get("generation_ms")
        )

        return cls(
            trace_id=entry.trace_id,
            timestamp=entry.timestamp,
            user_query=entry.user_query,
            evidence=evidence,
            graph_paths=graph_paths,
            linked_entities=linked,
            verifier=verifier,
            latency=latency,
            answer=entry.answer,
            error=entry.error
        )
```

---

## 4. 구현 태스크

### 4.1 태스크 목록

```
Main-F2-1: audit_trail.jsonl 구조 정의
├── stores/audit/ 디렉토리 확인
├── 스키마 정의 (본 문서 Section 3.1)
├── 필수/선택 필드 명세
└── 검증: 샘플 JSON 생성 및 파싱 테스트

Main-F2-2: AuditLogger 클래스 구현
├── src/api/services/audit_logger.py 작성
├── AuditEntry 데이터클래스 정의
├── start(), log_step(), end(), get() 메서드 구현
├── 스레드 안전성 (Lock) 적용
├── 파일 I/O 에러 핸들링
└── 검증: 단위 테스트 10개 이상

Main-F2-3: RAGService 통합
├── src/api/services/rag_service.py 수정
├── 각 파이프라인 단계에 audit_logger.log_step() 삽입
├── latency 측정 로직 추가
└── 검증: 실제 쿼리로 audit_trail.jsonl 생성 확인

Main-F2-4: /evidence/{trace_id} 엔드포인트 구현
├── src/api/routes/evidence.py 작성
├── src/api/schemas/evidence.py 작성
├── main.py에 라우터 등록
└── 검증: API 테스트

Main-F2-5: 단위 테스트 작성
├── tests/unit/test_audit_logger.py 작성
├── 정상 케이스 테스트
├── 에지 케이스 테스트
└── 검증: 테스트 커버리지 > 80%
```

### 4.2 RAGService 통합 예시

```python
# src/api/services/rag_service.py (수정 부분)

from src.api.services.audit_logger import get_audit_logger
import time

class RAGService:
    def query(self, question: str, ...) -> QueryResponse:
        audit_logger = get_audit_logger()

        # Step 0: 시작
        trace_id = audit_logger.start(question)

        try:
            # Step 1: Query Analysis
            t0 = time.time()
            analysis = self.query_analyzer.analyze(question)
            audit_logger.log_step(trace_id, "analysis", analysis.to_dict(), t0)

            # Step 2: Entity Linking
            t0 = time.time()
            linked = self.entity_linker.link_from_text(question)
            audit_logger.log_step(
                trace_id, "linking",
                [e.to_dict() for e in linked],
                t0
            )

            # Step 3: Graph Retrieval
            t0 = time.time()
            graph_results = self.graph_retriever.search(linked)
            audit_logger.log_step(trace_id, "graph", graph_results.to_dict(), t0)

            # Step 4: Vector Retrieval
            t0 = time.time()
            vector_results = self.retriever.search(question, top_k=5)
            audit_logger.log_step(
                trace_id, "vector",
                [r.to_dict() for r in vector_results],
                t0
            )

            # Step 5: Verification
            t0 = time.time()
            verifier_result = self.verifier.verify(...)
            audit_logger.log_step(trace_id, "verifier", verifier_result.to_dict(), t0)

            # Step 6: Generation
            t0 = time.time()
            answer = self.generator.generate(...)
            audit_logger.log_step(trace_id, "generation", answer, t0)

            # 종료
            audit_logger.end(trace_id)

            return QueryResponse(
                trace_id=trace_id,
                answer=answer,
                ...
            )

        except Exception as e:
            audit_logger.end(trace_id, error=str(e))
            raise
```

---

## 5. 테스트 계획

### 5.1 단위 테스트

```python
# tests/unit/test_audit_logger.py

import os
import sys
import json
import pytest
import tempfile
from pathlib import Path

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

    def test_end_writes_to_file(self, audit_logger, temp_audit_dir):
        """end()가 파일에 기록하는지"""
        trace_id = audit_logger.start("테스트")
        audit_logger.end(trace_id)

        audit_file = Path(temp_audit_dir) / "audit_trail.jsonl"
        assert audit_file.exists()

        with open(audit_file, "r") as f:
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


# ============================================================
# [3] Latency 측정 테스트
# ============================================================

class TestLatencyMeasurement:
    """Latency 측정 테스트"""

    def test_total_latency(self, audit_logger):
        """전체 latency 측정"""
        import time
        trace_id = audit_logger.start("latency 테스트")
        time.sleep(0.1)
        entry = audit_logger.end(trace_id)
        assert entry.latency["total_ms"] >= 100

    def test_step_latency(self, audit_logger):
        """단계별 latency 측정"""
        import time
        trace_id = audit_logger.start("단계별 테스트")

        t0 = time.time()
        time.sleep(0.05)
        audit_logger.log_step(trace_id, "analysis", {}, t0)

        entry = audit_logger.get(trace_id)
        assert entry.latency.get("analysis_ms", 0) >= 50


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

    def test_from_dict(self):
        """dict에서 생성"""
        data = {
            "trace_id": "test-id",
            "timestamp": "2024-01-21T10:00:00Z",
            "user_query": "테스트",
            "analysis": {"error_codes": ["C4A15"]}
        }
        entry = AuditEntry(**data)
        assert entry.analysis["error_codes"] == ["C4A15"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 5.2 통합 테스트

```python
# tests/integration/test_evidence_endpoint.py

import pytest
from fastapi.testclient import TestClient

# API 클라이언트로 테스트
def test_evidence_endpoint_success(client, sample_trace_id):
    """정상 조회"""
    response = client.get(f"/api/v1/evidence/{sample_trace_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == sample_trace_id

def test_evidence_endpoint_not_found(client):
    """존재하지 않는 trace_id"""
    response = client.get("/api/v1/evidence/nonexistent-id")
    assert response.status_code == 404
```

---

## 6. 코드 리뷰 체크포인트

### 6.1 기능 완전성

| 항목 | 확인 내용 |
|------|----------|
| ☐ | 모든 API 요청에서 trace_id가 발급되는가? |
| ☐ | 모든 파이프라인 단계가 로깅되는가? |
| ☐ | audit_trail.jsonl에 정상적으로 기록되는가? |
| ☐ | /evidence/{trace_id}로 조회 가능한가? |

### 6.2 성능

| 항목 | 확인 내용 |
|------|----------|
| ☐ | 로깅이 응답 지연에 영향을 주지 않는가? (<10ms 추가) |
| ☐ | trace_id로 조회 시 성능이 적절한가? (<100ms) |
| ☐ | 파일 I/O가 비동기적으로 처리되는가? |

### 6.3 안정성

| 항목 | 확인 내용 |
|------|----------|
| ☐ | 스레드 안전성이 확보되었는가? (Lock 사용) |
| ☐ | 파일 I/O 실패가 요청 처리에 영향을 주지 않는가? |
| ☐ | 메모리 누수가 없는가? |

### 6.4 보안

| 항목 | 확인 내용 |
|------|----------|
| ☐ | 민감 정보(API 키 등)가 로깅되지 않는가? |
| ☐ | audit_trail.jsonl 접근 권한이 적절한가? |

---

## 7. 완료 기준

### 7.1 필수 항목

- [ ] audit_trail.jsonl 스키마 확정 및 문서화
- [ ] AuditLogger 클래스 구현 완료
- [ ] 모든 API 요청에서 로깅 동작
- [ ] /evidence/{trace_id} 엔드포인트 동작
- [ ] 단위 테스트 10개 이상, 통과율 100%

### 7.2 품질 항목

- [ ] 로그 조회 성능 < 100ms
- [ ] 로깅으로 인한 응답 지연 < 10ms
- [ ] 기존 벤치마크 성능 저하 없음
- [ ] 코드 리뷰 체크리스트 통과

---

## 8. 다음 단계

### 8.1 Main-F3: 메타데이터 정비

Main-F2 완료 후 진행:
- `data/processed/metadata/sources.yaml` 작성
- `data/processed/metadata/chunk_manifest.jsonl` 생성
- 청크 → 문서/페이지 역추적 기능

### 8.2 센서 통합 시 확장

Main-S 단계에서 audit_trail에 추가될 필드:
- `sensor_context`: 센서 맥락 정보
- `correlation`: 문서-센서 상관관계
- `verifier.sensor_verified`: 센서 검증 결과

---

## 9. 참조

### 9.1 관련 문서
- [Main__Spec.md](Main__Spec.md) - Section 5.2 (폴더 구조), Section 7 (API Contract)
- [Main__ROADMAP.md](Main__ROADMAP.md) - Main-F2
- [Foundation_Spec.md](Foundation_Spec.md) - Section 4.4.5 (Audit Store), Section 7.4 (/evidence)

### 9.2 생성/수정 파일 경로
```
stores/audit/audit_trail.jsonl          (생성)
src/api/services/audit_logger.py        (구현)
src/api/routes/evidence.py              (생성)
src/api/schemas/evidence.py             (생성)
src/api/services/rag_service.py         (수정)
src/api/main.py                         (수정 - 라우터 등록)
tests/unit/test_audit_logger.py         (생성)
```

---

**작성일**: 2024-01-21
**참조**: Main__Spec.md, Main__ROADMAP.md, Foundation_Spec.md
