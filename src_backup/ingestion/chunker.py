# ============================================================
# src/ingestion/chunker.py - 청킹 클래스
# ============================================================
# Document 객체를 Chunk 리스트로 분할합니다.
#
# 청킹 전략:
#   - ErrorCodes.pdf: TOC 기반 (에러 코드별 분할)
#   - Service Manual: 섹션 기반 (절차별 분할)
#   - User Manual: 섹션 기반 (기능별 분할)
#
# 왜 청킹이 필요한가?
#   1. LLM 컨텍스트 제한: 한 번에 처리할 수 있는 토큰 수 제한
#   2. 검색 정확도: 작은 단위가 더 정확한 검색 결과
#   3. 비용 효율: 필요한 부분만 LLM에 전달
# ============================================================

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .models import Document, Chunk, ChunkMetadata


# ============================================================
# [1] 청킹 설정
# ============================================================

@dataclass
class ChunkingConfig:
    """
    청킹 설정값

    Attributes:
        chunk_size: 기본 청크 크기 (문자 수)
        chunk_overlap: 청크 간 오버랩 크기
        min_chunk_size: 최소 청크 크기 (이보다 작으면 이전 청크에 병합)
    """
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100


# ============================================================
# [2] Chunker 클래스
# ============================================================

class Chunker:
    """
    Document를 Chunk 리스트로 분할하는 클래스

    사용 예시:
        chunker = Chunker()
        chunks = chunker.chunk_document(document)
    """

    # 섹션 제목 패턴 (예: "1.2. Title" 또는 "1.2 Title")
    SECTION_PATTERN = re.compile(r'^(\d+(?:\.\d+)*\.?\s+)(.+)', re.MULTILINE)

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Chunker 초기화

        Args:
            config: 청킹 설정 (기본값 사용 시 None)
        """
        self.config = config or ChunkingConfig()

    # --------------------------------------------------------
    # [2.1] 메인 청킹 메서드
    # --------------------------------------------------------

    def chunk_document(self, document: Document) -> List[Chunk]:
        """
        Document를 적절한 전략으로 청킹

        문서 유형에 따라 다른 전략 적용:
            - error_code: TOC 기반 청킹
            - service_manual, user_manual: 섹션 기반 청킹
            - unknown: 고정 크기 청킹

        Args:
            document: 청킹할 Document 객체

        Returns:
            List[Chunk]: 청크 리스트
        """
        print(f"\n[*] Chunking: {document.filename} (type: {document.doc_type})")

        if document.doc_type == "error_code":
            # ErrorCodes.pdf는 TOC 기반
            chunks = self._chunk_by_toc(document)
        elif document.doc_type in ["service_manual", "user_manual"]:
            # 매뉴얼은 섹션 기반
            chunks = self._chunk_by_section(document)
        else:
            # 알 수 없는 유형은 고정 크기
            chunks = self._chunk_by_size(document)

        print(f"    Created {len(chunks)} chunks")
        return chunks

    # --------------------------------------------------------
    # [2.2] TOC 기반 청킹 (ErrorCodes.pdf용)
    # --------------------------------------------------------

    def _chunk_by_toc(self, document: Document) -> List[Chunk]:
        """
        TOC(목차) 기반 청킹

        ErrorCodes.pdf의 TOC 구조:
            [(1, "Introduction", 12), (2, "C0", 12), (2, "C1", 12), ...]
            Level 2 항목이 각 에러 코드

        처리 흐름:
            1. TOC에서 Level 2 항목(에러 코드) 추출
            2. 각 에러 코드의 시작/끝 페이지 계산
            3. 해당 범위의 텍스트 추출
            4. Chunk 객체 생성

        Args:
            document: Document 객체

        Returns:
            List[Chunk]: 청크 리스트
        """
        chunks = []

        if not document.toc:
            # TOC가 없으면 섹션 기반으로 폴백
            print("    [WARN] No TOC found, falling back to section-based chunking")
            return self._chunk_by_section(document)

        # Level 2 항목 (에러 코드들) 필터링
        error_codes = [(title, page) for level, title, page in document.toc if level == 2]

        if not error_codes:
            print("    [WARN] No Level 2 TOC entries, falling back to section-based")
            return self._chunk_by_section(document)

        # 전체 텍스트
        full_text = document.get_full_text()

        # 각 에러 코드별로 청크 생성
        for i, (title, start_page) in enumerate(error_codes):
            # 다음 에러 코드의 시작 페이지 (끝 범위 계산용)
            if i + 1 < len(error_codes):
                _, end_page = error_codes[i + 1]
            else:
                end_page = document.page_count

            # 에러 코드 추출 (예: "C1" from "C1 Outbuffer overflow")
            error_code = self._extract_error_code(title)

            # 해당 페이지 범위의 텍스트 추출
            content = self._extract_page_range(document, start_page, end_page)

            # 내용이 너무 짧으면 스킵
            if len(content) < self.config.min_chunk_size:
                continue

            # 청크 ID 생성
            chunk_id = f"error_codes_{error_code}_{i:03d}"

            # 메타데이터 생성
            metadata = ChunkMetadata(
                source=document.filename,
                page=start_page,
                doc_type="error_code",
                section=title,
                error_code=error_code,
            )

            # Chunk 객체 생성
            chunk = Chunk(
                id=chunk_id,
                content=content,
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def _extract_error_code(self, title: str) -> str:
        """
        제목에서 에러 코드 추출

        예시:
            "C1 Outbuffer overflow" → "C1"
            "C10A2 Some error" → "C10A2"

        Args:
            title: TOC 제목

        Returns:
            str: 에러 코드
        """
        # "C숫자" 또는 "C숫자A숫자" 패턴 찾기
        match = re.match(r'^(C\d+[A-Z]?\d*)', title)
        if match:
            return match.group(1)
        return title.split()[0] if title else "unknown"

    def _extract_page_range(self, document: Document, start_page: int, end_page: int) -> str:
        """
        페이지 범위의 텍스트 추출

        Args:
            document: Document 객체
            start_page: 시작 페이지 (1부터 시작)
            end_page: 끝 페이지 (포함하지 않음)

        Returns:
            str: 해당 범위의 텍스트
        """
        # 페이지 인덱스 변환 (1-based → 0-based)
        start_idx = max(0, start_page - 1)
        end_idx = min(len(document.pages), end_page - 1)

        # 페이지 텍스트 합치기
        pages_text = "\n\n".join(document.pages[start_idx:end_idx])
        return pages_text.strip()

    # --------------------------------------------------------
    # [2.3] 섹션 기반 청킹 (Manual용)
    # --------------------------------------------------------

    def _chunk_by_section(self, document: Document) -> List[Chunk]:
        """
        섹션(제목) 기반 청킹

        섹션 패턴:
            "1.2. Title" 또는 "1.2 Title"

        처리 흐름:
            1. 전체 텍스트에서 섹션 제목 위치 찾기
            2. 섹션별로 텍스트 분할
            3. 큰 섹션은 추가로 크기 기반 분할

        Args:
            document: Document 객체

        Returns:
            List[Chunk]: 청크 리스트
        """
        chunks = []
        full_text = document.get_full_text()

        # 섹션 제목 찾기
        sections = self._find_sections(full_text)

        if not sections:
            # 섹션을 찾지 못하면 크기 기반으로 폴백
            print("    [WARN] No sections found, falling back to size-based chunking")
            return self._chunk_by_size(document)

        # 각 섹션별로 청크 생성
        for i, (chapter, title, start_pos) in enumerate(sections):
            # 다음 섹션의 시작 위치 (끝 범위 계산용)
            if i + 1 < len(sections):
                end_pos = sections[i + 1][2]
            else:
                end_pos = len(full_text)

            # 섹션 내용 추출
            content = full_text[start_pos:end_pos].strip()

            # 내용이 너무 짧으면 스킵
            if len(content) < self.config.min_chunk_size:
                continue

            # 내용이 너무 크면 추가 분할
            if len(content) > self.config.chunk_size * 2:
                sub_chunks = self._split_large_content(
                    content=content,
                    document=document,
                    chapter=chapter,
                    title=title,
                    base_index=len(chunks),
                )
                chunks.extend(sub_chunks)
            else:
                # 단일 청크 생성
                chunk_id = f"{document.doc_type}_{len(chunks):03d}"

                metadata = ChunkMetadata(
                    source=document.filename,
                    page=self._estimate_page(document, start_pos),
                    doc_type=document.doc_type,
                    section=title,
                    chapter=chapter,
                )

                chunk = Chunk(
                    id=chunk_id,
                    content=content,
                    metadata=metadata,
                )
                chunks.append(chunk)

        return chunks

    def _find_sections(self, text: str) -> List[Tuple[str, str, int]]:
        """
        텍스트에서 섹션 찾기

        Args:
            text: 전체 텍스트

        Returns:
            list: [(chapter, title, position), ...]
        """
        sections = []

        for match in self.SECTION_PATTERN.finditer(text):
            chapter = match.group(1).strip()  # "1.2."
            title = match.group(2).strip()    # "Title"
            position = match.start()

            # 제목이 너무 짧거나 숫자만 있으면 스킵
            if len(title) < 3 or title.isdigit():
                continue

            sections.append((chapter, title, position))

        return sections

    def _split_large_content(
        self,
        content: str,
        document: Document,
        chapter: str,
        title: str,
        base_index: int,
    ) -> List[Chunk]:
        """
        큰 내용을 작은 청크로 분할

        Args:
            content: 분할할 텍스트
            document: Document 객체
            chapter: 챕터 번호
            title: 섹션 제목
            base_index: 청크 ID 시작 인덱스

        Returns:
            List[Chunk]: 분할된 청크 리스트
        """
        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        # 문단 단위로 분할 시도
        paragraphs = content.split('\n\n')
        current_chunk = ""
        chunk_count = 0

        for para in paragraphs:
            # 현재 청크 + 새 문단이 크기 제한 내인지 확인
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                # 현재 청크 저장
                if current_chunk:
                    chunk_id = f"{document.doc_type}_{base_index + chunk_count:03d}"

                    metadata = ChunkMetadata(
                        source=document.filename,
                        page=1,  # 정확한 페이지 추정 어려움
                        doc_type=document.doc_type,
                        section=title,
                        chapter=chapter,
                    )

                    chunk = Chunk(
                        id=chunk_id,
                        content=current_chunk,
                        metadata=metadata,
                    )
                    chunks.append(chunk)
                    chunk_count += 1

                    # 오버랩 적용
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else ""
                    current_chunk = overlap_text + para
                else:
                    current_chunk = para

        # 마지막 청크 저장
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunk_id = f"{document.doc_type}_{base_index + chunk_count:03d}"

            metadata = ChunkMetadata(
                source=document.filename,
                page=1,
                doc_type=document.doc_type,
                section=title,
                chapter=chapter,
            )

            chunk = Chunk(
                id=chunk_id,
                content=current_chunk,
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def _estimate_page(self, document: Document, position: int) -> int:
        """
        텍스트 위치에서 페이지 번호 추정

        Args:
            document: Document 객체
            position: 전체 텍스트에서의 위치

        Returns:
            int: 추정된 페이지 번호
        """
        current_pos = 0
        for i, page_text in enumerate(document.pages):
            current_pos += len(page_text) + 2  # +2 for "\n\n"
            if current_pos > position:
                return i + 1  # 1-based
        return document.page_count

    # --------------------------------------------------------
    # [2.4] 크기 기반 청킹 (폴백용)
    # --------------------------------------------------------

    def _chunk_by_size(self, document: Document) -> List[Chunk]:
        """
        고정 크기 기반 청킹 (폴백)

        다른 전략이 실패했을 때 사용

        Args:
            document: Document 객체

        Returns:
            List[Chunk]: 청크 리스트
        """
        chunks = []
        full_text = document.get_full_text()
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        start = 0
        chunk_count = 0

        while start < len(full_text):
            # 끝 위치 계산
            end = start + chunk_size

            # 문장 경계에서 자르기 시도
            if end < len(full_text):
                # 마지막 마침표 또는 줄바꿈 찾기
                last_break = max(
                    full_text.rfind('.', start, end),
                    full_text.rfind('\n', start, end),
                )
                if last_break > start + chunk_size // 2:
                    end = last_break + 1

            content = full_text[start:end].strip()

            if len(content) >= self.config.min_chunk_size:
                chunk_id = f"{document.doc_type}_{chunk_count:03d}"

                # 페이지 추정
                page = self._estimate_page(document, start)

                metadata = ChunkMetadata(
                    source=document.filename,
                    page=page,
                    doc_type=document.doc_type,
                )

                chunk = Chunk(
                    id=chunk_id,
                    content=content,
                    metadata=metadata,
                )
                chunks.append(chunk)
                chunk_count += 1

            # 다음 청크 시작 위치 (오버랩 적용)
            start = end - overlap

        return chunks


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    import sys

    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    from .pdf_parser import parse_all_pdfs

    # 모든 PDF 파싱
    documents = parse_all_pdfs("data/raw/pdf")

    # 청커 생성
    chunker = Chunker()

    # 각 문서 청킹
    all_chunks = {}
    for doc in documents:
        chunks = chunker.chunk_document(doc)
        all_chunks[doc.doc_type] = chunks

        # 샘플 청크 출력
        print(f"\n[Sample chunks from {doc.filename}]")
        for chunk in chunks[:3]:
            print(f"\n  ID: {chunk.id}")
            print(f"  Length: {len(chunk)} chars")
            print(f"  Metadata: {chunk.metadata.to_dict()}")
            preview = chunk.content[:100].replace('\n', ' ')
            print(f"  Preview: {preview}...")

    # 요약
    print("\n" + "=" * 50)
    print("[Summary]")
    for doc_type, chunks in all_chunks.items():
        total_chars = sum(len(c) for c in chunks)
        print(f"  {doc_type}: {len(chunks)} chunks, {total_chars:,} chars")
