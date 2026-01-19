"""
API 요청 Pydantic 모델
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class QueryRequest(BaseModel):
    """질의 요청 모델"""
    question: str = Field(..., description="사용자 질문", min_length=1)
    top_k: Optional[int] = Field(5, description="검색할 상위 K개 문서", ge=1, le=20)
    include_evidence: Optional[bool] = Field(True, description="근거 포함 여부")
    session_id: Optional[str] = Field(None, description="세션 ID (대화 추적용)")


class EvidenceRequest(BaseModel):
    """근거 조회 요청 모델"""
    query_id: str = Field(..., description="질의 ID")
    chunk_ids: Optional[List[str]] = Field(None, description="특정 청크 ID 목록")


class PreviewRequest(BaseModel):
    """PDF 미리보기 요청 모델"""
    source_id: str = Field(..., description="문서 소스 ID")
    page_num: Optional[int] = Field(1, description="페이지 번호", ge=1)
    chunk_id: Optional[str] = Field(None, description="특정 청크 ID")
