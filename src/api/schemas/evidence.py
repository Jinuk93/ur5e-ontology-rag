# ============================================================
# src/api/schemas/evidence.py - Evidence 스키마
# ============================================================
# /evidence/{trace_id} 엔드포인트 응답 스키마
#
# Main-F2에서 구현
# ============================================================

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================
# [1] 세부 스키마
# ============================================================

class LinkedEntityDetail(BaseModel):
    """엔티티 링킹 상세"""
    entity: str = Field(..., description="원본 텍스트")
    canonical: str = Field(..., description="정규화된 이름")
    node_id: str = Field(default="", description="온톨로지 노드 ID")
    entity_type: str = Field(default="", description="엔티티 타입 (error_code/component)")
    confidence: float = Field(default=1.0, description="신뢰도 (0.0-1.0)")
    matched_by: str = Field(default="", description="매칭 방식 (lexicon/regex/embedding)")


class EvidenceItem(BaseModel):
    """문서 근거 항목"""
    doc_id: str = Field(..., description="문서 ID")
    page: int = Field(default=0, description="페이지 번호")
    chunk_id: str = Field(default="", description="청크 ID")
    score: float = Field(default=0.0, description="관련성 점수")
    preview: Optional[str] = Field(None, description="내용 미리보기")


class GraphPathInfo(BaseModel):
    """그래프 경로 정보"""
    paths: List[str] = Field(default_factory=list, description="추론 경로 목록")
    expansion_terms: List[str] = Field(default_factory=list, description="확장 검색어")
    node_count: int = Field(default=0, description="사용된 노드 수")
    edge_count: int = Field(default=0, description="사용된 엣지 수")


class VerifierInfo(BaseModel):
    """검증 정보"""
    status: str = Field(..., description="PASS/PARTIAL/ABSTAIN/FAIL")
    doc_verified: bool = Field(default=False, description="문서 근거 확인 여부")
    sensor_verified: Optional[bool] = Field(None, description="센서 근거 확인 여부")
    decision_reason: str = Field(default="", description="판정 사유")


class LatencyInfo(BaseModel):
    """처리 시간 정보"""
    total_ms: int = Field(default=0, description="전체 처리 시간 (ms)")
    analysis_ms: Optional[int] = Field(None, description="질문 분석 시간")
    linking_ms: Optional[int] = Field(None, description="엔티티 링킹 시간")
    graph_ms: Optional[int] = Field(None, description="그래프 검색 시간")
    vector_ms: Optional[int] = Field(None, description="벡터 검색 시간")
    verifier_ms: Optional[int] = Field(None, description="검증 시간")
    generation_ms: Optional[int] = Field(None, description="답변 생성 시간")


# ============================================================
# [2] 메인 응답 스키마
# ============================================================

class EvidenceResponse(BaseModel):
    """
    근거 상세 응답

    /evidence/{trace_id} 엔드포인트의 응답 스키마입니다.
    특정 요청의 전체 파이프라인 정보를 반환합니다.
    """
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
    def from_audit_entry(cls, entry: "AuditEntry") -> "EvidenceResponse":
        """
        AuditEntry에서 EvidenceResponse 생성

        Args:
            entry: AuditEntry 객체

        Returns:
            EvidenceResponse 객체
        """
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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2024-01-21T10:30:00.123Z",
                    "user_query": "C4A15 에러가 발생했어요. 어떻게 해결하나요?",
                    "evidence": [
                        {
                            "doc_id": "error_codes",
                            "page": 15,
                            "chunk_id": "error_codes_C4_004",
                            "score": 0.89,
                            "preview": "C4A15: Communication with joint 3 lost..."
                        }
                    ],
                    "graph_paths": {
                        "paths": [
                            "(ERR_C4A15)-[RESOLVED_BY]->(RES_COMPLETE_REBOOT)"
                        ],
                        "expansion_terms": ["Joint 3", "communication", "reboot"],
                        "node_count": 3,
                        "edge_count": 2
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
                    "verifier": {
                        "status": "PASS",
                        "doc_verified": True,
                        "sensor_verified": None,
                        "decision_reason": "Action citation satisfied"
                    },
                    "latency": {
                        "total_ms": 564,
                        "analysis_ms": 23,
                        "linking_ms": 15,
                        "graph_ms": 89,
                        "vector_ms": 156,
                        "verifier_ms": 12,
                        "generation_ms": 269
                    },
                    "answer": "C4A15 에러는 'Joint 3 통신 손실'을 의미합니다...",
                    "error": None
                }
            ]
        }
    }


# TYPE_CHECKING import for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.api.services.audit_logger import AuditEntry
