# ============================================================
# src/ingestion/models.py - 데이터 모델 정의
# ============================================================
# PDF 파싱과 청킹에 사용되는 데이터 구조를 정의합니다.
#
# 주요 클래스:
#   - ChunkMetadata: 청크의 메타데이터 (출처, 페이지 등)
#   - Chunk: 청킹된 텍스트 조각
#   - Document: PDF 문서 전체를 표현
#
# 왜 dataclass를 사용하는가?
#   - 보일러플레이트 코드 감소 (__init__, __repr__ 자동 생성)
#   - 타입 힌트와 함께 사용하여 코드 가독성 향상
#   - 불변 객체(frozen=True)로 만들어 안전한 데이터 관리 가능
# ============================================================

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from datetime import datetime
import json


# ============================================================
# [1] ChunkMetadata - 청크의 메타데이터
# ============================================================
# 청크가 어디서 왔는지, 어떤 정보를 담고 있는지 기록합니다.
# 나중에 검색 결과에서 "출처"를 보여줄 때 사용됩니다.
# ============================================================

@dataclass
class ChunkMetadata:
    """
    청크의 메타데이터를 담는 클래스

    Attributes:
        source: 원본 파일명 (예: "ErrorCodes.pdf")
        page: 페이지 번호 (1부터 시작)
        doc_type: 문서 유형 ("error_code", "service_manual", "user_manual")
        section: 섹션 제목 (예: "C1 Outbuffer overflow")
        error_code: 에러 코드 (ErrorCodes.pdf용, 예: "C1")
        chapter: 챕터 번호 (예: "5.2")
    """
    source: str                              # 원본 파일명
    page: int                                # 페이지 번호
    doc_type: str                            # 문서 유형
    section: Optional[str] = None            # 섹션 제목
    error_code: Optional[str] = None         # 에러 코드 (ErrorCodes용)
    chapter: Optional[str] = None            # 챕터 번호

    def to_dict(self) -> Dict[str, Any]:
        """
        메타데이터를 딕셔너리로 변환

        왜 필요한가?
        - JSON 저장 시 딕셔너리 형태가 필요
        - None 값은 제외하여 저장 공간 절약

        Returns:
            dict: None이 아닌 값들만 포함된 딕셔너리
        """
        # asdict()는 dataclass를 딕셔너리로 변환
        # None 값은 제외
        return {k: v for k, v in asdict(self).items() if v is not None}


# ============================================================
# [2] Chunk - 청킹된 텍스트 조각
# ============================================================
# RAG 시스템에서 검색의 기본 단위입니다.
# 벡터 DB에 저장되고, 쿼리와 유사도 비교됩니다.
# ============================================================

@dataclass
class Chunk:
    """
    청킹된 텍스트 조각을 담는 클래스

    Attributes:
        id: 고유 식별자 (예: "error_codes_C1_001")
        content: 청크 텍스트 내용
        metadata: 메타데이터 객체
        embedding: 임베딩 벡터 (Phase 3에서 추가)

    사용 예시:
        chunk = Chunk(
            id="error_codes_C1_001",
            content="C1 Outbuffer overflow...",
            metadata=ChunkMetadata(
                source="ErrorCodes.pdf",
                page=12,
                doc_type="error_code",
                error_code="C1"
            )
        )
    """
    id: str                                  # 고유 ID
    content: str                             # 청크 텍스트
    metadata: ChunkMetadata                  # 메타데이터
    embedding: Optional[List[float]] = None  # 임베딩 벡터 (나중에 추가)

    def to_dict(self) -> Dict[str, Any]:
        """
        청크를 딕셔너리로 변환 (JSON 저장용)

        Returns:
            dict: 청크 데이터를 담은 딕셔너리
        """
        result = {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata.to_dict(),
        }
        # 임베딩은 있을 때만 포함
        if self.embedding is not None:
            result["embedding"] = self.embedding
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """
        딕셔너리에서 Chunk 객체 생성 (JSON 로드용)

        Args:
            data: 청크 데이터 딕셔너리

        Returns:
            Chunk: 생성된 Chunk 객체

        사용 예시:
            with open("chunks.json", "r") as f:
                data = json.load(f)
            chunk = Chunk.from_dict(data)
        """
        return cls(
            id=data["id"],
            content=data["content"],
            metadata=ChunkMetadata(**data["metadata"]),
            embedding=data.get("embedding"),
        )

    def __len__(self) -> int:
        """
        청크의 길이 (문자 수) 반환

        왜 필요한가?
        - 청크 크기 검증에 사용
        - len(chunk)로 간단히 크기 확인 가능

        Returns:
            int: content의 문자 수
        """
        return len(self.content)


# ============================================================
# [3] Document - PDF 문서 전체
# ============================================================
# PDF에서 추출한 전체 내용을 담습니다.
# 청킹 전 중간 단계로 사용됩니다.
# ============================================================

@dataclass
class Document:
    """
    PDF 문서 전체를 담는 클래스

    Attributes:
        filename: 파일명 (예: "ErrorCodes.pdf")
        filepath: 파일 경로
        pages: 페이지별 텍스트 리스트
        toc: 목차 정보 [(level, title, page), ...]
        metadata: 문서 메타데이터 (제목, 저자 등)
        doc_type: 문서 유형

    처리 흐름:
        PDF 파일 → PDFParser → Document → Chunker → List[Chunk]
    """
    filename: str                            # 파일명
    filepath: str                            # 파일 경로
    pages: List[str]                         # 페이지별 텍스트
    toc: List[tuple] = field(default_factory=list)  # 목차 [(level, title, page), ...]
    metadata: Dict[str, Any] = field(default_factory=dict)  # PDF 메타데이터
    doc_type: str = "unknown"                # 문서 유형

    @property
    def page_count(self) -> int:
        """페이지 수 반환"""
        return len(self.pages)

    @property
    def total_chars(self) -> int:
        """전체 문자 수 반환"""
        return sum(len(page) for page in self.pages)

    def get_full_text(self) -> str:
        """
        전체 텍스트를 하나의 문자열로 반환

        Returns:
            str: 모든 페이지 텍스트를 합친 문자열
        """
        return "\n\n".join(self.pages)


# ============================================================
# [4] 유틸리티 함수
# ============================================================

def save_chunks_to_json(chunks: List[Chunk], filepath: str) -> None:
    """
    청크 리스트를 JSON 파일로 저장

    Args:
        chunks: 저장할 Chunk 객체 리스트
        filepath: 저장할 파일 경로

    사용 예시:
        save_chunks_to_json(chunks, "data/processed/chunks/error_codes.json")
    """
    data = [chunk.to_dict() for chunk in chunks]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved {len(chunks)} chunks to {filepath}")


def load_chunks_from_json(filepath: str) -> List[Chunk]:
    """
    JSON 파일에서 청크 리스트 로드

    Args:
        filepath: 로드할 파일 경로

    Returns:
        List[Chunk]: 로드된 Chunk 객체 리스트

    사용 예시:
        chunks = load_chunks_from_json("data/processed/chunks/error_codes.json")
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    chunks = [Chunk.from_dict(item) for item in data]
    print(f"[OK] Loaded {len(chunks)} chunks from {filepath}")
    return chunks


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    # 테스트: ChunkMetadata 생성
    meta = ChunkMetadata(
        source="ErrorCodes.pdf",
        page=12,
        doc_type="error_code",
        section="C1 Outbuffer overflow",
        error_code="C1"
    )
    print("[1] ChunkMetadata 생성:")
    print(f"    {meta}")
    print(f"    to_dict: {meta.to_dict()}")

    # 테스트: Chunk 생성
    chunk = Chunk(
        id="error_codes_C1_001",
        content="C1 Outbuffer overflow\nC1A1 Buffer of stored warnings overflowed",
        metadata=meta
    )
    print(f"\n[2] Chunk 생성:")
    print(f"    id: {chunk.id}")
    print(f"    length: {len(chunk)} chars")
    print(f"    to_dict: {chunk.to_dict()}")

    # 테스트: Document 생성
    doc = Document(
        filename="ErrorCodes.pdf",
        filepath="data/raw/pdf/ErrorCodes.pdf",
        pages=["Page 1 content", "Page 2 content"],
        doc_type="error_code"
    )
    print(f"\n[3] Document 생성:")
    print(f"    filename: {doc.filename}")
    print(f"    page_count: {doc.page_count}")
    print(f"    total_chars: {doc.total_chars}")

    print("\n[OK] All tests passed!")
