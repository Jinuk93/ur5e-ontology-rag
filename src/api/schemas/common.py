"""
공통 API 스키마

시스템 관련 스키마 정의
"""

from typing import Dict
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    version: str
    components: Dict[str, str]


class SupervisorTargetsResponse(BaseModel):
    """관리 감독자 대시보드 목표치(운영 기준)"""
    normal_rate_min: float
    force_magnitude_p95_max: float
    force_magnitude_mean_max: float
    fz_p95_max_abs: float
    events_daily_max: float
    collision_daily_max: float
    overload_daily_max: float
    drift_daily_max: float
    mtbe_min_minutes: float
    unresolved_events_max: int
