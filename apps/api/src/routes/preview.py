"""
PDF 미리보기 및 청크 하이라이트 라우트
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from ..models.request import PreviewRequest
from ..models.evidence import PDFPreview

router = APIRouter(prefix="/preview", tags=["preview"])


@router.get("/{source_id}")
async def get_pdf_preview(
    source_id: str,
    page_num: Optional[int] = 1,
    chunk_id: Optional[str] = None
) -> PDFPreview:
    """
    PDF 미리보기 정보 조회
    
    Args:
        source_id: 문서 소스 ID
        page_num: 페이지 번호
        chunk_id: 하이라이트할 청크 ID (선택)
    
    Returns:
        PDF 미리보기 정보
    """
    # TODO: 실제 구현
    return PDFPreview(
        source_id=source_id,
        filename="sample.pdf",
        page_num=page_num,
        total_pages=100,
        pdf_url=f"/static/pdf/{source_id}",
        chunk_highlights=[]
    )


@router.post("/")
async def preview_with_chunks(request: PreviewRequest) -> PDFPreview:
    """
    청크 정보를 포함한 PDF 미리보기
    
    Args:
        request: 미리보기 요청
    
    Returns:
        PDF 미리보기 정보
    """
    # TODO: 실제 구현
    return PDFPreview(
        source_id=request.source_id,
        filename="sample.pdf",
        page_num=request.page_num,
        total_pages=100,
        pdf_url=f"/static/pdf/{request.source_id}",
        chunk_highlights=[]
    )
