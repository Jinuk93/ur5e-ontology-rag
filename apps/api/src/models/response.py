"""
API 응답 Pydantic 모델
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class Evidence(BaseModel):
    """근거 정보 모델"""
    chunk_id: str
    source_id: str
    text: str
    page_num: Optional[int] = None
    similarity_score: float
    metadata: Optional[Dict[str, Any]] = None


class ReasoningStep(BaseModel):
    """추론 단계 모델"""
    step: int
    description: str
    entities: List[str] = []
    relations: List[str] = []


class QueryResponse(BaseModel):
    """질의 응답 모델"""
    query_id: str = Field(..., description="질의 고유 ID")
    question: str = Field(..., description="원본 질문")
    answer: str = Field(..., description="생성된 답변")
    confidence: float = Field(..., description="답변 신뢰도 점수", ge=0.0, le=1.0)
    
    evidence: Optional[List[Evidence]] = Field(None, description="근거 청크 목록")
    reasoning_steps: Optional[List[ReasoningStep]] = Field(None, description="추론 과정")
    
    entities_extracted: Optional[List[str]] = Field(None, description="추출된 엔티티")
    graph_path: Optional[List[str]] = Field(None, description="지식 그래프 경로")
    
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 생성 시각")
    processing_time_ms: Optional[float] = Field(None, description="처리 시간(ms)")


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str = Field(..., description="서비스 상태")
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = Field(default_factory=dict, description="각 서비스 상태")


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 정보")
    timestamp: datetime = Field(default_factory=datetime.now)
