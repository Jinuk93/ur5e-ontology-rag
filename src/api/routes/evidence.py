# ============================================================
# src/api/routes/evidence.py - Evidence 라우터
# ============================================================
# trace_id로 근거/경로 상세 조회 엔드포인트
#
# Main-F2에서 구현
# ============================================================

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from src.api.schemas.evidence import EvidenceResponse
from src.api.services.audit_logger import get_audit_logger, AuditEntry


router = APIRouter()


# ============================================================
# [1] Evidence 엔드포인트
# ============================================================

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
    - **verifier**: 검증 결과
    - **latency**: 처리 시간 상세
    - **answer**: 최종 답변
    - **error**: 에러 메시지 (있는 경우)

    ## 예시 요청

    ```
    GET /api/v1/evidence/550e8400-e29b-41d4-a716-446655440000
    ```

    ## 사용 사례

    - 답변 근거 확인
    - 디버깅 및 트러블슈팅
    - 파이프라인 성능 분석
    - 품질 평가를 위한 이력 추적
    """
    audit_logger = get_audit_logger()
    entry = audit_logger.get(trace_id)

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trace not found: {trace_id}"
        )

    return EvidenceResponse.from_audit_entry(entry)


@router.get("/evidence", response_model=List[dict])
async def get_recent_traces(limit: int = 10):
    """
    최근 trace 목록 조회

    가장 최근에 처리된 요청들의 요약 정보를 반환합니다.

    - **limit**: 조회할 최대 개수 (기본값: 10, 범위: 1-100)

    ## 응답

    각 항목은 다음 정보를 포함합니다:
    - **trace_id**: 요청 식별자
    - **timestamp**: 요청 시간
    - **user_query**: 원본 질문 (50자 제한)
    - **latency_ms**: 전체 처리 시간
    - **has_error**: 에러 발생 여부

    ## 사용 사례

    - 최근 요청 모니터링
    - 에러 발생 요청 파악
    - 성능 트렌드 파악
    """
    if limit < 1:
        limit = 1
    elif limit > 100:
        limit = 100

    audit_logger = get_audit_logger()
    entries = audit_logger.get_recent(limit=limit)

    # 요약 정보만 반환
    summaries = []
    for entry in entries:
        summaries.append({
            "trace_id": entry.trace_id,
            "timestamp": entry.timestamp,
            "user_query": entry.user_query[:50] + "..." if len(entry.user_query) > 50 else entry.user_query,
            "latency_ms": entry.latency.get("total_ms", 0),
            "has_error": entry.error is not None
        })

    return summaries


@router.get("/evidence/stats", response_model=dict)
async def get_audit_stats():
    """
    Audit 통계 정보 조회

    감사 로그의 통계 정보를 반환합니다.

    ## 응답

    - **total_entries**: 전체 로그 수
    - **memory_cache_size**: 메모리 캐시 크기
    - **audit_file**: 로그 파일 경로
    """
    audit_logger = get_audit_logger()
    return audit_logger.get_stats()
