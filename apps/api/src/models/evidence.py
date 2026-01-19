"""
근거(Evidence) 관련 모델
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ChunkMetadata(BaseModel):
    """청크 메타데이터"""
    source_id: str
    filename: str
    page_num: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    created_at: Optional[datetime] = None


class EvidenceChunk(BaseModel):
    """근거 청크 상세 정보"""
    chunk_id: str = Field(..., description="청크 고유 ID")
    text: str = Field(..., description="청크 텍스트")
    similarity_score: float = Field(..., description="유사도 점수", ge=0.0, le=1.0)
    metadata: ChunkMetadata = Field(..., description="청크 메타데이터")
    highlighted_text: Optional[str] = Field(None, description="하이라이트된 텍스트")


class EvidenceResponse(BaseModel):
    """근거 조회 응답"""
    query_id: str
    chunks: List[EvidenceChunk]
    total_count: int
    timestamp: datetime = Field(default_factory=datetime.now)


class PDFPreview(BaseModel):
    """PDF 미리보기 정보"""
    source_id: str
    filename: str
    page_num: int
    total_pages: int
    pdf_url: Optional[str] = Field(None, description="PDF 뷰어 URL")
    chunk_highlights: Optional[List[Dict[str, Any]]] = Field(None, description="청크 하이라이트 좌표")
