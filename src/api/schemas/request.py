# ============================================================
# src/api/schemas/request.py - 요청 스키마
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    """RAG 질의 요청"""
    question: str = Field(
        ...,
        description="사용자 질문",
        min_length=1,
        max_length=1000
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="검색 결과 수"
    )
    include_sources: bool = Field(
        default=True,
        description="출처 정보 포함 여부"
    )
    include_citation: bool = Field(
        default=True,
        description="인용 정보 포함 여부"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "C4A15 에러가 발생했어요. 어떻게 해결하나요?",
                    "top_k": 5,
                    "include_sources": True,
                    "include_citation": True
                }
            ]
        }
    }


class AnalyzeRequest(BaseModel):
    """질문 분석 요청"""
    question: str = Field(
        ...,
        description="분석할 질문",
        min_length=1,
        max_length=1000
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "Control Box에서 C50 에러가 발생했어요"
                }
            ]
        }
    }


class SearchRequest(BaseModel):
    """검색 요청 (답변 생성 없이)"""
    question: str = Field(
        ...,
        description="검색 질문",
        min_length=1,
        max_length=1000
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="검색 결과 수"
    )
    strategy: Optional[str] = Field(
        default=None,
        description="검색 전략 (graph_first, vector_first, hybrid)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "조인트 통신 에러",
                    "top_k": 3,
                    "strategy": "hybrid"
                }
            ]
        }
    }
