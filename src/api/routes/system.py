"""
시스템 라우트

헬스체크, 온톨로지 요약 등 시스템 관련 엔드포인트
"""

import logging
from fastapi import APIRouter, HTTPException

from src.config import get_settings
from src.api.schemas import HealthResponse, SupervisorTargetsResponse

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


@router.get("/api/config/supervisor-targets", response_model=SupervisorTargetsResponse)
async def get_supervisor_targets():
    """관리 감독자 대시보드 목표치(운영 기준) 반환"""
    settings = get_settings()
    t = settings.supervisor_targets
    return SupervisorTargetsResponse(
        normal_rate_min=float(t.normal_rate_min),
        force_magnitude_p95_max=float(t.force_magnitude_p95_max),
        force_magnitude_mean_max=float(t.force_magnitude_mean_max),
        fz_p95_max_abs=float(t.fz_p95_max_abs),
        events_daily_max=float(t.events_daily_max),
        collision_daily_max=float(t.collision_daily_max),
        overload_daily_max=float(t.overload_daily_max),
        drift_daily_max=float(t.drift_daily_max),
        mtbe_min_minutes=float(t.mtbe_min_minutes),
        unresolved_events_max=int(t.unresolved_events_max),
    )
