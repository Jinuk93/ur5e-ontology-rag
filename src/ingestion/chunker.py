"""
문서 청킹 모듈

텍스트를 의미 있는 청크로 분할합니다.
"""

import logging
from typing import List, Dict, Any, Optional

from src.config import get_settings
from .models import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)


class TextChunker:
    """텍스트 청커"""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        """
        청커 초기화

        Args:
            chunk_size: 청크 크기 (기본: settings.document.chunk_size)
            chunk_overlap: 청크 겹침 (기본: settings.document.chunk_overlap)
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.document.chunk_size
        self.chunk_overlap = chunk_overlap or settings.document.chunk_overlap

    def chunk_text(
        self,
        text: str,
        doc_id: str,
        doc_type: str,
        page: int,
        section: Optional[str] = None,
        chapter: Optional[str] = None,
        start_idx: int = 0,
    ) -> List[Chunk]:
        """
        텍스트를 청크로 분할

        Args:
            text: 분할할 텍스트
            doc_id: 문서 ID
            doc_type: 문서 타입
            page: 페이지 번호
            section: 섹션명
            chapter: 챕터명
            start_idx: 시작 인덱스 (청크 ID 생성용)

        Returns:
            Chunk 리스트
        """
        if not text.strip():
            return []

        chunks = []
        text_length = len(text)
        current_pos = 0
        chunk_idx = start_idx

        while current_pos < text_length:
            # 청크 끝 위치 계산
            end_pos = min(current_pos + self.chunk_size, text_length)

            # 문장 경계에서 끊기 (가능한 경우)
            if end_pos < text_length:
                end_pos = self._find_sentence_boundary(text, current_pos, end_pos)

            # 청크 텍스트 추출
            chunk_text = text[current_pos:end_pos].strip()

            if chunk_text:
                chunk_id = f"{doc_id}_{chunk_idx:03d}"
                metadata = ChunkMetadata(
                    source=f"{doc_id}.pdf",
                    page=page,
                    doc_type=doc_type,
                    section=section,
                    chapter=chapter,
                )
                chunk = Chunk(id=chunk_id, content=chunk_text, metadata=metadata)
                chunks.append(chunk)
                chunk_idx += 1

            # 다음 위치로 이동 (오버랩 적용)
            current_pos = end_pos - self.chunk_overlap
            if current_pos >= text_length:
                break

            # 무한 루프 방지
            if end_pos >= text_length:
                break

        return chunks

    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """
        문장 경계 찾기

        Args:
            text: 전체 텍스트
            start: 시작 위치
            end: 초기 끝 위치

        Returns:
            조정된 끝 위치
        """
        # 끝 위치에서 뒤로 탐색하며 문장 경계 찾기
        search_text = text[start:end]

        # 문장 종료 문자 목록
        sentence_endings = [".", "!", "?", "\n\n", ")\n", ":\n"]

        best_end = end
        for ending in sentence_endings:
            pos = search_text.rfind(ending)
            if pos != -1:
                candidate_end = start + pos + len(ending)
                if candidate_end > start + self.chunk_size // 2:  # 최소 절반 이상
                    best_end = candidate_end
                    break

        return best_end

    def chunk_document(
        self,
        pages: List[Dict[str, Any]],
        doc_id: str,
        doc_type: str,
    ) -> List[Chunk]:
        """
        문서 전체를 청크로 분할

        Args:
            pages: 페이지 정보 리스트 (page, text, section, chapter)
            doc_id: 문서 ID
            doc_type: 문서 타입

        Returns:
            Chunk 리스트
        """
        all_chunks = []
        chunk_idx = 0

        for page_info in pages:
            page_chunks = self.chunk_text(
                text=page_info["text"],
                doc_id=doc_id,
                doc_type=doc_type,
                page=page_info["page"],
                section=page_info.get("section"),
                chapter=page_info.get("chapter"),
                start_idx=chunk_idx,
            )
            all_chunks.extend(page_chunks)
            chunk_idx = len(all_chunks)

        logger.info(f"청킹 완료: {doc_id}, {len(all_chunks)} 청크")
        return all_chunks


def chunk_pages(
    pages: List[Dict[str, Any]],
    doc_id: str,
    doc_type: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Chunk]:
    """
    페이지 리스트를 청크로 분할 (편의 함수)

    Args:
        pages: 페이지 정보 리스트
        doc_id: 문서 ID
        doc_type: 문서 타입
        chunk_size: 청크 크기
        chunk_overlap: 청크 겹침

    Returns:
        Chunk 리스트
    """
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_document(pages, doc_id, doc_type)
