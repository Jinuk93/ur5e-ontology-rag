"""
데이터 수집 모듈의 데이터 모델

문서 및 청크 데이터 구조를 정의합니다.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


@dataclass
class ChunkMetadata:
    """청크 메타데이터"""

    source: str  # 원본 파일명
    page: int  # 페이지 번호
    doc_type: str  # 문서 타입 (user_manual, service_manual, error_codes)
    section: Optional[str] = None  # 섹션명
    chapter: Optional[str] = None  # 챕터명
    error_code: Optional[str] = None  # 에러 코드 (error_codes 문서용)
    extra: Dict[str, Any] = field(default_factory=dict)  # 추가 필드

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = {k: v for k, v in asdict(self).items() if v is not None and k != "extra"}
        if self.extra:
            result.update(self.extra)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkMetadata":
        """딕셔너리에서 생성 (알 수 없는 필드는 extra에 저장)"""
        known_fields = {"source", "page", "doc_type", "section", "chapter", "error_code"}
        known = {k: v for k, v in data.items() if k in known_fields}
        extra = {k: v for k, v in data.items() if k not in known_fields}
        return cls(**known, extra=extra)


@dataclass
class Chunk:
    """문서 청크"""

    id: str  # 청크 ID (예: user_manual_000)
    content: str  # 청크 텍스트
    metadata: ChunkMetadata  # 메타데이터

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (JSON 저장용)"""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """딕셔너리에서 생성"""
        metadata = ChunkMetadata.from_dict(data["metadata"])
        return cls(id=data["id"], content=data["content"], metadata=metadata)


@dataclass
class DocumentMetadata:
    """문서 메타데이터"""

    source: str  # 원본 파일명
    doc_type: str  # 문서 타입
    total_pages: int  # 총 페이지 수
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )  # 처리 시간
    topics: List[str] = field(default_factory=list)  # 주제 태그

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)


@dataclass
class Document:
    """처리된 문서"""

    id: str  # 문서 ID
    metadata: DocumentMetadata  # 문서 메타데이터
    chunks: List[Chunk] = field(default_factory=list)  # 청크 목록

    @property
    def chunk_count(self) -> int:
        """청크 수 반환"""
        return len(self.chunks)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "metadata": self.metadata.to_dict(),
            "chunk_count": self.chunk_count,
        }


@dataclass
class Manifest:
    """문서 메타데이터 매니페스트"""

    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    documents: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    totals: Dict[str, int] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)

    def add_document(self, doc_id: str, doc_info: Dict[str, Any]) -> None:
        """문서 정보 추가"""
        self.documents[doc_id] = doc_info

    def update_totals(self) -> None:
        """총계 업데이트"""
        total_chunks = sum(
            doc.get("chunk_count", 0) for doc in self.documents.values()
        )
        self.totals = {"documents": len(self.documents), "chunks": total_chunks}

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "documents": self.documents,
            "totals": self.totals,
            "settings": self.settings,
        }

    def to_json(self, indent: int = 2) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Manifest":
        """딕셔너리에서 생성"""
        return cls(
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            documents=data.get("documents", {}),
            totals=data.get("totals", {}),
            settings=data.get("settings", {}),
        )
