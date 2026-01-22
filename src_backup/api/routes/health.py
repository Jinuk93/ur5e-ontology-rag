# ============================================================
# src/api/routes/health.py - 헬스체크 라우터
# ============================================================

from fastapi import APIRouter, Request
from src.api.schemas.response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    서버 상태 확인

    서버와 각 컴포넌트(VectorDB, GraphDB, LLM)의 상태를 반환합니다.
    """
    rag_service = request.app.state.rag_service
    components = rag_service.get_health_status()

    # 전체 상태 판단
    all_healthy = all(v in ["connected", "available"] for v in components.values())
    status = "healthy" if all_healthy else "degraded"

    return HealthResponse(
        status=status,
        version="1.0.0",
        components=components
    )


@router.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "UR5e RAG API Server",
        "version": "1.0.0",
        "docs": "/docs"
    }
