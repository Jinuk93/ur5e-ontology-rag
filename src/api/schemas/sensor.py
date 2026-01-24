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


# ============================================================
# UR5e + Axia80 통합 실시간 스트림 스키마 (Phase 2)
# ============================================================

class UR5eTelemetrySchema(BaseModel):
    """UR5e 텔레메트리 데이터"""
    tcp_speed: float = Field(description="TCP 속도 (m/s, 0~1.0)")
    tcp_acceleration: float = Field(description="TCP 가속도 (m/s², -5~5)")
    joint_torque_sum: float = Field(description="조인트 토크 합 (Nm, 0~150)")
    joint_current_avg: float = Field(description="조인트 평균 전류 (A, 0.5~5.0)")
    safety_mode: str = Field(description="안전 모드 (normal/reduced/protective_stop)")
    program_state: str = Field(description="프로그램 상태 (running/paused/stopped)")
    protective_stop: bool = Field(description="보호 정지 활성화 여부")


class Axia80Schema(BaseModel):
    """Axia80 힘 센서 데이터"""
    Fx: float = Field(description="X축 힘 (N)")
    Fy: float = Field(description="Y축 힘 (N)")
    Fz: float = Field(description="Z축 힘 (N)")
    Tx: float = Field(description="X축 토크 (Nm)")
    Ty: float = Field(description="Y축 토크 (Nm)")
    Tz: float = Field(description="Z축 토크 (Nm)")
    force_magnitude: float = Field(description="힘 크기 (N)")
    force_rate: float = Field(description="힘 변화율 (N/tick)")
    force_spike: bool = Field(description="힘 스파이크 감지")
    peak_axis: str = Field(description="최대 힘 축 (Fx/Fy/Fz)")


class CorrelationMetricsSchema(BaseModel):
    """UR5e-Axia80 상관 메트릭"""
    torque_force_ratio: float = Field(description="토크/힘 비율")
    speed_force_correlation: float = Field(description="속도-힘 상관계수 (-1~1)")
    anomaly_detected: bool = Field(description="이상 감지 여부")


class RiskAssessmentSchema(BaseModel):
    """위험도 평가"""
    contact_risk_score: float = Field(description="접촉 위험 점수 (0~1)")
    collision_risk_score: float = Field(description="충돌 위험 점수 (0~1)")
    risk_level: str = Field(description="위험 수준 (low/medium/high/critical)")
    recommended_action: str = Field(description="권장 조치")
    prediction_horizon_sec: int = Field(default=3, description="예측 시간 범위 (초)")


class ScenarioInfoSchema(BaseModel):
    """현재 시나리오 정보"""
    current: str = Field(description="현재 시나리오 타입")
    elapsed_sec: float = Field(description="시나리오 경과 시간")
    remaining_sec: float = Field(description="시나리오 남은 시간")


class IntegratedStreamData(BaseModel):
    """통합 실시간 스트림 데이터"""
    timestamp: str = Field(description="타임스탬프 (ISO 8601)")
    scenario: ScenarioInfoSchema = Field(description="시나리오 정보")
    axia80: Axia80Schema = Field(description="Axia80 힘 센서 데이터")
    ur5e: UR5eTelemetrySchema = Field(description="UR5e 텔레메트리 (시뮬레이션)")
    correlation: CorrelationMetricsSchema = Field(description="상관 분석 결과")
    risk: RiskAssessmentSchema = Field(description="위험도 평가")
    data_source: str = Field(default="simulated", description="데이터 소스 (simulated/live)")
