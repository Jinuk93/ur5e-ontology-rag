"""
시스템 라우트

헬스체크, 온톨로지 요약 등 시스템 관련 엔드포인트
"""

import logging
from fastapi import APIRouter, HTTPException

from src.config import get_settings
from src.api.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System"])

# 컴포넌트 getter 함수 (main.py에서 주입)
_get_classifier = None
_get_engine = None
_get_generator = None


def configure(get_classifier, get_engine, get_generator):
    """컴포넌트 getter 함수 주입"""
    global _get_classifier, _get_engine, _get_generator
    _get_classifier = get_classifier
    _get_engine = get_engine
    _get_generator = get_generator


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스체크"""
    settings = get_settings()

    components = {}
    try:
        _get_classifier()
        components["classifier"] = "ok"
    except Exception as e:
        components["classifier"] = f"error: {str(e)}"

    try:
        _get_engine()
        components["engine"] = "ok"
    except Exception as e:
        components["engine"] = f"error: {str(e)}"

    try:
        _get_generator()
        components["generator"] = "ok"
    except Exception as e:
        components["generator"] = f"error: {str(e)}"

    return HealthResponse(
        status="healthy" if all(v == "ok" for v in components.values()) else "degraded",
        version="1.0.0",
        components=components,
    )


@router.get("/api/ontology/summary")
async def get_ontology_summary():
    """온톨로지 요약 정보"""
    try:
        engine = _get_engine()
        summary = engine.get_summary()
        return {
            "status": "ok",
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
