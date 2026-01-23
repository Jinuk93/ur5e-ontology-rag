"""
채팅 API 스키마

Chat 및 Evidence 관련 스키마 정의
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    """채팅 요청

    UI 명세서 기준: query 필드 사용
    하위 호환: message 필드도 허용 (query 우선)
    """
    query: Optional[str] = Field(None, description="사용자 질문 (권장)")
    message: Optional[str] = Field(None, description="사용자 질문 (하위 호환)")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추가 컨텍스트 (shift, product 등)"
    )

    @model_validator(mode='after')
    def validate_query_or_message(self):
        """query 또는 message 중 하나는 필수"""
        if not self.query and not self.message:
            raise ValueError("query 또는 message 중 하나는 필수입니다")
        # query 우선, 없으면 message 사용
        if not self.query:
            self.query = self.message
        return self


class AnalysisInfo(BaseModel):
    """분석 정보"""
    entity: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    state: Optional[str] = None
    normal_range: Optional[List[float]] = None
    deviation: Optional[str] = None


class ReasoningInfo(BaseModel):
    """추론 정보"""
    confidence: float
    pattern: Optional[str] = None
    pattern_confidence: Optional[float] = None
    cause: Optional[str] = None
    cause_confidence: Optional[float] = None


class PredictionInfo(BaseModel):
    """예측 정보"""
    error_code: Optional[str] = None
    probability: Optional[float] = None
    timeframe: Optional[str] = None


class RecommendationInfo(BaseModel):
    """권장사항"""
    immediate: Optional[str] = None
    reference: Optional[str] = None


class EvidenceInfo(BaseModel):
    """근거 정보"""
    ontology_paths: List[Dict[str, Any]] = Field(default_factory=list)
    document_refs: List[Dict[str, Any]] = Field(default_factory=list)
    similar_events: List[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    """그래프 노드"""
    id: str
    type: str
    label: str
    state: Optional[str] = None


class GraphEdge(BaseModel):
    """그래프 엣지"""
    source: str
    target: str
    relation: str


class GraphData(BaseModel):
    """그래프 데이터"""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """채팅 응답 (Phase12 스키마)"""
    trace_id: str = Field(..., description="추적 ID (근거 조회용)")
    query_type: str = Field(..., description="질문 유형 (ontology/hybrid/rag)")
    answer: str = Field(..., description="자연어 응답")
    analysis: Optional[AnalysisInfo] = None
    reasoning: Optional[ReasoningInfo] = None
    prediction: Optional[PredictionInfo] = None
    recommendation: Optional[RecommendationInfo] = None
    evidence: EvidenceInfo = Field(default_factory=EvidenceInfo)
    graph: GraphData = Field(default_factory=GraphData)
    abstain: bool = Field(default=False, description="ABSTAIN 여부")
    abstain_reason: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class EvidenceResponse(BaseModel):
    """근거 상세 응답"""
    trace_id: str
    found: bool
    evidence: Optional[Dict[str, Any]] = None
    full_response: Optional[Dict[str, Any]] = None
