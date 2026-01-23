"""
API 스키마 모듈

Pydantic 모델 정의
"""

from .common import HealthResponse
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
)

__all__ = [
    # Common
    "HealthResponse",
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
]
