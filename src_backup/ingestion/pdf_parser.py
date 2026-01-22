# ============================================================
# src/ingestion/pdf_parser.py - PDF 파싱 클래스
# ============================================================
# PyMuPDF(fitz)를 사용하여 PDF에서 텍스트를 추출합니다.
#
# 주요 기능:
#   - PDF 파일 열기 및 텍스트 추출
#   - 페이지별 텍스트 분리
#   - TOC(목차) 추출
#   - PDF 메타데이터 추출
#
# 왜 PyMuPDF(fitz)를 사용하는가?
#   - 빠른 처리 속도
#   - 레이아웃 보존 옵션
#   - TOC 추출 기능 내장
#   - 다양한 PDF 형식 지원
# ============================================================

import fitz  # PyMuPDF
import os
import re
from typing import List, Dict, Any, Optional, Tuple

from .models import Document


# ============================================================
# [1] PDFParser 클래스
# ============================================================

class PDFParser:
    """
    PDF 파일을 파싱하여 Document 객체로 변환하는 클래스

    사용 예시:
        parser = PDFParser()
        doc = parser.parse("data/raw/pdf/ErrorCodes.pdf")
        print(doc.page_count)
        print(doc.toc)
    """

    # --------------------------------------------------------
    # 문서 유형 판별을 위한 키워드
    # --------------------------------------------------------
    DOC_TYPE_PATTERNS = {
        "error_code": ["ErrorCodes", "Error Codes Directory"],
        "service_manual": ["Service Manual", "Service Handbook"],
        "user_manual": ["User Manual"],
    }

    def __init__(self, clean_text: bool = True):
        """
        PDFParser 초기화

        Args:
            clean_text: 텍스트 정제 여부 (기본값: True)
                        True면 불필요한 공백, 특수문자 등을 정리
        """
        self.clean_text = clean_text

    # --------------------------------------------------------
    # [1.1] 메인 파싱 메서드
    # --------------------------------------------------------

    def parse(self, pdf_path: str) -> Document:
        """
        PDF 파일을 파싱하여 Document 객체 반환

        처리 흐름:
            1. PDF 파일 열기
            2. 메타데이터 추출
            3. TOC(목차) 추출
            4. 페이지별 텍스트 추출
            5. 문서 유형 판별
            6. Document 객체 생성 및 반환

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            Document: 파싱된 문서 객체

        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            Exception: PDF 파싱 실패 시
        """
        # 파일 존재 확인
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # PDF 열기
        doc = fitz.open(pdf_path)

        try:
            # 메타데이터 추출
            metadata = self._extract_metadata(doc)

            # TOC 추출
            toc = self._extract_toc(doc)

            # 페이지별 텍스트 추출
            pages = self._extract_pages(doc)

            # 문서 유형 판별
            filename = os.path.basename(pdf_path)
            doc_type = self._detect_doc_type(filename, pages)

            # Document 객체 생성
            document = Document(
                filename=filename,
                filepath=pdf_path,
                pages=pages,
                toc=toc,
                metadata=metadata,
                doc_type=doc_type,
            )

            print(f"[OK] Parsed: {filename}")
            print(f"     - Pages: {document.page_count}")
            print(f"     - TOC entries: {len(toc)}")
            print(f"     - Doc type: {doc_type}")

            return document

        finally:
            doc.close()

    # --------------------------------------------------------
    # [1.2] 메타데이터 추출
    # --------------------------------------------------------

    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """
        PDF 메타데이터 추출

        PDF 메타데이터란?
            - 제목, 저자, 생성일 등 문서 정보
            - PDF 파일 내부에 저장되어 있음

        Args:
            doc: fitz.Document 객체

        Returns:
            dict: 메타데이터 딕셔너리
        """
        metadata = doc.metadata

        # None 값 제거 및 정리
        cleaned = {}
        for key, value in metadata.items():
            if value:
                # 특수 문자 제거 (인코딩 문제 방지)
                if isinstance(value, str):
                    value = value.encode('ascii', 'ignore').decode('ascii')
                cleaned[key] = value

        return cleaned

    # --------------------------------------------------------
    # [1.3] TOC(목차) 추출
    # --------------------------------------------------------

    def _extract_toc(self, doc: fitz.Document) -> List[Tuple[int, str, int]]:
        """
        PDF의 TOC(Table of Contents) 추출

        TOC 구조:
            [(level, title, page), ...]
            - level: 목차 깊이 (1=최상위)
            - title: 목차 제목
            - page: 페이지 번호

        Args:
            doc: fitz.Document 객체

        Returns:
            list: TOC 항목 리스트
        """
        toc = doc.get_toc()

        # 제목에서 특수문자 제거
        cleaned_toc = []
        for level, title, page in toc:
            clean_title = title.encode('ascii', 'ignore').decode('ascii').strip()
            cleaned_toc.append((level, clean_title, page))

        return cleaned_toc

    # --------------------------------------------------------
    # [1.4] 페이지별 텍스트 추출
    # --------------------------------------------------------

    def _extract_pages(self, doc: fitz.Document) -> List[str]:
        """
        모든 페이지의 텍스트 추출

        Args:
            doc: fitz.Document 객체

        Returns:
            list: 페이지별 텍스트 리스트 (인덱스 = 페이지번호 - 1)
        """
        pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            # 텍스트 정제
            if self.clean_text:
                text = self._clean_text(text)

            pages.append(text)

        return pages

    # --------------------------------------------------------
    # [1.5] 텍스트 정제
    # --------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """
        텍스트 정제 (불필요한 문자 제거)

        처리 내용:
            1. 여러 개의 공백을 하나로
            2. 여러 개의 줄바꿈을 최대 2개로
            3. 앞뒤 공백 제거

        Args:
            text: 원본 텍스트

        Returns:
            str: 정제된 텍스트
        """
        # 여러 공백 → 하나의 공백
        text = re.sub(r'[ \t]+', ' ', text)

        # 여러 줄바꿈 → 최대 2개
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 각 줄의 앞뒤 공백 제거
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # 전체 앞뒤 공백 제거
        text = text.strip()

        return text

    # --------------------------------------------------------
    # [1.6] 문서 유형 판별
    # --------------------------------------------------------

    def _detect_doc_type(self, filename: str, pages: List[str]) -> str:
        """
        문서 유형 자동 판별

        판별 순서:
            1. 파일명으로 판별 시도
            2. 첫 페이지 내용으로 판별 시도

        Args:
            filename: 파일명
            pages: 페이지 텍스트 리스트

        Returns:
            str: 문서 유형 ("error_code", "service_manual", "user_manual", "unknown")
        """
        # 파일명 + 첫 3페이지 내용을 합쳐서 검사
        search_text = filename.lower()
        if pages:
            search_text += " " + " ".join(pages[:3]).lower()

        # 패턴 매칭
        for doc_type, patterns in self.DOC_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in search_text:
                    return doc_type

        return "unknown"


# ============================================================
# [2] 유틸리티 함수
# ============================================================

def parse_all_pdfs(pdf_dir: str) -> List[Document]:
    """
    폴더 내 모든 PDF 파일 파싱

    Args:
        pdf_dir: PDF 파일이 있는 폴더 경로

    Returns:
        list: Document 객체 리스트

    사용 예시:
        documents = parse_all_pdfs("data/raw/pdf")
        for doc in documents:
            print(f"{doc.filename}: {doc.page_count} pages")
    """
    parser = PDFParser()
    documents = []

    # PDF 파일 목록
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]

    print(f"\n[*] Parsing {len(pdf_files)} PDF files from {pdf_dir}")
    print("=" * 50)

    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        try:
            doc = parser.parse(pdf_path)
            documents.append(doc)
        except Exception as e:
            print(f"[ERROR] Failed to parse {pdf_file}: {e}")

    print("=" * 50)
    print(f"[OK] Parsed {len(documents)} documents\n")

    return documents


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    import sys

    # Windows 콘솔 인코딩
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    # 테스트: 모든 PDF 파싱
    pdf_dir = "data/raw/pdf"
    documents = parse_all_pdfs(pdf_dir)

    # 결과 출력
    print("\n[Summary]")
    print("-" * 50)
    for doc in documents:
        print(f"\n{doc.filename}:")
        print(f"  - Type: {doc.doc_type}")
        print(f"  - Pages: {doc.page_count}")
        print(f"  - Total chars: {doc.total_chars:,}")
        print(f"  - TOC entries: {len(doc.toc)}")

        # 첫 번째 페이지 미리보기
        if doc.pages:
            preview = doc.pages[0][:200].replace('\n', ' ')
            print(f"  - Page 1 preview: {preview}...")
