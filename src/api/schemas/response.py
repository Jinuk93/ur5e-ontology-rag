# ============================================================
# src/api/schemas/response.py - 응답 스키마
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class VerificationStatusEnum(str, Enum):
    """검증 상태"""
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    INSUFFICIENT = "insufficient"


class SourceInfo(BaseModel):
    """출처 정보"""
    name: str = Field(..., description="출처 이름")
    type: str = Field(..., description="출처 타입 (graph/vector)")
    score: float = Field(..., description="관련성 점수")


class VerificationInfo(BaseModel):
    """검증 정보"""
    status: VerificationStatusEnum = Field(..., description="검증 상태")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도")
    evidence_count: int = Field(..., ge=0, description="근거 수")
    warnings: List[str] = Field(default_factory=list, description="경고 메시지")


class QueryResponse(BaseModel):
    """RAG 질의 응답"""
    answer: str = Field(..., description="생성된 답변")
    verification: VerificationInfo = Field(..., description="검증 정보")
    sources: Optional[List[SourceInfo]] = Field(None, description="출처 목록")
    query_analysis: Optional[Dict[str, Any]] = Field(None, description="질문 분석 결과")
    latency_ms: float = Field(..., description="처리 시간 (밀리초)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "C4A15 에러는 Joint 3과의 통신 손실입니다...",
                    "verification": {
                        "status": "verified",
                        "confidence": 0.85,
                        "evidence_count": 2,
                        "warnings": []
                    },
                    "sources": [
                        {"name": "C4A15", "type": "graph", "score": 1.0}
                    ],
                    "query_analysis": {
                        "error_codes": ["C4A15"],
                        "components": [],
                        "query_type": "error_resolution",
                        "search_strategy": "graph_first"
                    },
                    "latency_ms": 3500
                }
            ]
        }
    }


class AnalyzeResponse(BaseModel):
    """질문 분석 응답"""
    original_query: str = Field(..., description="원본 질문")
    error_codes: List[str] = Field(default_factory=list, description="감지된 에러 코드")
    components: List[str] = Field(default_factory=list, description="감지된 부품명")
    query_type: str = Field(..., description="쿼리 타입")
    search_strategy: str = Field(..., description="검색 전략")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "original_query": "Control Box에서 C50 에러가 발생했어요",
                    "error_codes": ["C50"],
                    "components": ["control box"],
                    "query_type": "error_resolution",
                    "search_strategy": "graph_first"
                }
            ]
        }
    }


class SearchResult(BaseModel):
    """검색 결과 항목"""
    content: str = Field(..., description="내용 (500자 미리보기)")
    source_type: str = Field(..., description="출처 타입")
    score: float = Field(..., description="관련성 점수")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")


class SearchResponse(BaseModel):
    """검색 응답"""
    results: List[SearchResult] = Field(..., description="검색 결과")
    query_analysis: AnalyzeResponse = Field(..., description="질문 분석")
    total_count: int = Field(..., description="총 결과 수")
    latency_ms: float = Field(..., description="처리 시간 (밀리초)")


class ErrorCodeInfo(BaseModel):
    """에러 코드 정보"""
    code: str = Field(..., description="에러 코드")
    description: str = Field(..., description="설명")
    causes: List[str] = Field(default_factory=list, description="원인")
    solutions: List[str] = Field(default_factory=list, description="해결 방법")
    related_components: List[str] = Field(default_factory=list, description="관련 부품")


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str = Field(..., description="서버 상태")
    version: str = Field(..., description="API 버전")
    components: Dict[str, str] = Field(..., description="컴포넌트 상태")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "version": "1.0.0",
                    "components": {
                        "vectordb": "connected",
                        "graphdb": "connected",
                        "llm": "available"
                    }
                }
            ]
        }
    }
