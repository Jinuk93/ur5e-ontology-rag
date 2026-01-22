"""
PDF 파서 모듈

PyMuPDF (fitz)를 사용하여 PDF에서 텍스트를 추출합니다.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import fitz  # PyMuPDF

from .models import DocumentMetadata

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF 텍스트 추출기"""

    # 문서 타입 매핑
    DOC_TYPE_MAP = {
        "user_manual": ["user_manual", "user manual", "710-965"],
        "service_manual": ["service_manual", "service manual", "e-series"],
        "error_codes": ["error_codes", "errorcodes", "error codes"],
    }

    # 문서별 토픽 매핑
    TOPICS_MAP = {
        "user_manual": ["safety", "operation", "installation"],
        "service_manual": ["maintenance", "repair", "troubleshooting"],
        "error_codes": ["error_codes", "diagnostics"],
    }

    def __init__(self, pdf_path: Path):
        """
        PDF 파서 초기화

        Args:
            pdf_path: PDF 파일 경로
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

        self.doc = fitz.open(str(self.pdf_path))
        self.doc_type = self._detect_doc_type()

    def _detect_doc_type(self) -> str:
        """파일명에서 문서 타입 감지"""
        filename = self.pdf_path.name.lower()

        for doc_type, patterns in self.DOC_TYPE_MAP.items():
            for pattern in patterns:
                if pattern in filename:
                    return doc_type

        # 기본값
        return "unknown"

    def get_metadata(self) -> DocumentMetadata:
        """문서 메타데이터 추출"""
        return DocumentMetadata(
            source=self.pdf_path.name,
            doc_type=self.doc_type,
            total_pages=len(self.doc),
            topics=self.TOPICS_MAP.get(self.doc_type, []),
        )

    def extract_page_text(self, page_num: int) -> str:
        """
        특정 페이지의 텍스트 추출

        Args:
            page_num: 페이지 번호 (0-indexed)

        Returns:
            페이지 텍스트
        """
        if page_num < 0 or page_num >= len(self.doc):
            raise ValueError(f"유효하지 않은 페이지 번호: {page_num}")

        page = self.doc[page_num]
        return page.get_text()

    def extract_all_text(self) -> List[Tuple[int, str]]:
        """
        모든 페이지의 텍스트 추출

        Returns:
            (페이지 번호, 텍스트) 튜플 리스트
        """
        pages = []
        for page_num in range(len(self.doc)):
            text = self.extract_page_text(page_num)
            if text.strip():  # 빈 페이지 제외
                pages.append((page_num + 1, text))  # 1-indexed 반환

        logger.info(f"추출 완료: {self.pdf_path.name}, {len(pages)} 페이지")
        return pages

    def extract_text_with_sections(self) -> List[Dict[str, Any]]:
        """
        섹션 정보를 포함한 텍스트 추출

        Returns:
            페이지 정보 딕셔너리 리스트
        """
        pages = []
        current_section = None
        current_chapter = None

        for page_num in range(len(self.doc)):
            text = self.extract_page_text(page_num)
            if not text.strip():
                continue

            # 섹션/챕터 감지 (간단한 휴리스틱)
            section, chapter = self._detect_section_chapter(text, current_section)
            if section:
                current_section = section
            if chapter:
                current_chapter = chapter

            pages.append(
                {
                    "page": page_num + 1,  # 1-indexed
                    "text": text,
                    "section": current_section,
                    "chapter": current_chapter,
                }
            )

        return pages

    def _detect_section_chapter(
        self, text: str, current_section: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """텍스트에서 섹션/챕터 감지"""
        lines = text.split("\n")[:5]  # 첫 5줄에서 검색

        section = None
        chapter = None

        for line in lines:
            line = line.strip()

            # 챕터 패턴 (예: "1.", "2.1", "Chapter 1")
            if line and (line[0].isdigit() or line.lower().startswith("chapter")):
                parts = line.split()
                if parts:
                    chapter = parts[0].rstrip(".")

            # 섹션 패턴 (대문자로 시작하는 짧은 제목)
            if line and len(line) < 50 and line[0].isupper():
                if not any(c.isdigit() for c in line[:3]):
                    section = line

        return section, chapter

    def close(self):
        """리소스 정리"""
        if self.doc:
            self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def parse_pdf(pdf_path: Path) -> Tuple[DocumentMetadata, List[Dict[str, Any]]]:
    """
    PDF 파일을 파싱하여 메타데이터와 페이지 텍스트 반환

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        (메타데이터, 페이지 정보 리스트)
    """
    with PDFParser(pdf_path) as parser:
        metadata = parser.get_metadata()
        pages = parser.extract_text_with_sections()
        return metadata, pages
