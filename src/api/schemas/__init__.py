"""
API 스키마 모듈

Pydantic 모델 정의
"""

from .common import HealthResponse, SupervisorTargetsResponse
from .chat import (
    ChatRequest,
    ChatResponse,
    AnalysisInfo,
    ReasoningInfo,
    PredictionInfo,
    RecommendationInfo,
    EvidenceInfo,
    EvidenceResponse,
    GraphNode,
    GraphEdge,
    GraphData,
)
from .sensor import (
    SensorReading,
    SensorReadingsResponse,
    PatternInfo,
    PatternsResponse,
    EventInfo,
    EventsResponse,
    PredictionItem,
    RealtimePrediction,
    PredictionsResponse,
    # Phase 2: 통합 실시간 스트림
    UR5eTelemetrySchema,
    Axia80Schema,
    CorrelationMetricsSchema,
    RiskAssessmentSchema,
    ScenarioInfoSchema,
    IntegratedStreamData,
)

__all__ = [
    # Common
    "HealthResponse",
    "SupervisorTargetsResponse",
    # Chat
    "ChatRequest",
    "ChatResponse",
    "AnalysisInfo",
    "ReasoningInfo",
    "PredictionInfo",
    "RecommendationInfo",
    "EvidenceInfo",
    "EvidenceResponse",
    "GraphNode",
    "GraphEdge",
    "GraphData",
    # Sensor
    "SensorReading",
    "SensorReadingsResponse",
    "PatternInfo",
    "PatternsResponse",
    "EventInfo",
    "EventsResponse",
    "PredictionItem",
    "RealtimePrediction",
    "PredictionsResponse",
    # Phase 2: 통합 실시간 스트림
    "UR5eTelemetrySchema",
    "Axia80Schema",
    "CorrelationMetricsSchema",
    "RiskAssessmentSchema",
    "ScenarioInfoSchema",
    "IntegratedStreamData",
]
