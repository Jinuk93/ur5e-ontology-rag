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


class PredictionItem(BaseModel):
    """단일 예측 결과"""
    error_code: str = Field(description="예측되는 에러 코드")
    probability: float = Field(description="발생 확률 (0.0 ~ 1.0)")
    pattern: str = Field(description="감지된 패턴 ID")
    cause: Optional[str] = Field(default=None, description="추정 원인")
    timeframe: Optional[str] = Field(default=None, description="예상 발생 시점")
    recommendation: Optional[str] = Field(default=None, description="권장 조치")


class RealtimePrediction(BaseModel):
    """실시간 예측 결과"""
    timestamp: str = Field(description="예측 시점")
    sensor_value: float = Field(description="현재 센서 값 (Fz)")
    state: str = Field(description="현재 상태 (normal/warning/critical)")
    pattern_detected: Optional[str] = Field(default=None, description="감지된 패턴")
    predictions: List[PredictionItem] = Field(default_factory=list, description="예측 목록")
    ontology_path: Optional[str] = Field(default=None, description="온톨로지 추론 경로")


class PredictionsResponse(BaseModel):
    """예측 응답"""
    predictions: List[RealtimePrediction]
    total_patterns: int = Field(description="감지된 패턴 수")
    high_risk_count: int = Field(description="고위험 예측 수")
