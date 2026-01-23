"""
센서 API 스키마

센서 데이터, 패턴, 이벤트 관련 스키마 정의
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    """센서 측정값"""
    timestamp: str
    Fx: float
    Fy: float
    Fz: float
    Tx: float
    Ty: float
    Tz: float
    status: Optional[str] = "normal"
    task_mode: Optional[str] = "idle"


class SensorReadingsResponse(BaseModel):
    """센서 데이터 응답"""
    readings: List[SensorReading]
    total: int
    time_range: Dict[str, str]


class PatternInfo(BaseModel):
    """패턴 정보"""
    id: str
    type: str
    timestamp: str
    confidence: float
    metrics: Dict[str, Any]
    related_error_codes: List[str] = Field(default_factory=list)


class PatternsResponse(BaseModel):
    """패턴 목록 응답"""
    patterns: List[PatternInfo]
    total: int


class EventInfo(BaseModel):
    """이벤트 정보"""
    event_id: str
    scenario: str
    event_type: str
    start_time: str
    end_time: str
    duration_s: float
    error_code: Optional[str] = None
    description: str


class EventsResponse(BaseModel):
    """이벤트 목록 응답"""
    events: List[EventInfo]
    total: int
