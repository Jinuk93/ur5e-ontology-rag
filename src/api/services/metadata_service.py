# ============================================================
# src/api/services/metadata_service.py - 메타데이터 관리 서비스
# ============================================================
# sources.yaml과 chunk_manifest.jsonl을 로드하고 조회하는 서비스
#
# Main-F3에서 구현
# ============================================================

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import yaml


# ============================================================
# [1] 데이터 클래스
# ============================================================

@dataclass
class DocumentInfo:
    """문서 정보"""
    doc_id: str
    title: str
    version: str
    date: str
    pages: int
    source_file: str
    chunk_count: int
    language: str = "en"
    publisher: str = ""
    url: Optional[str] = None
    sections: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "version": self.version,
            "date": self.date,
            "pages": self.pages,
            "source_file": self.source_file,
            "chunk_count": self.chunk_count,
            "language": self.language,
            "publisher": self.publisher,
            "url": self.url,
            "sections": self.sections
        }


@dataclass
class ChunkMapping:
    """청크 매핑 정보"""
    chunk_id: str
    doc_id: str
    page: int
    section: str
    doc_type: str
    tokens: int = 0
    content_length: int = 0
    error_code: Optional[str] = None
    chapter: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "page": self.page,
            "section": self.section,
            "doc_type": self.doc_type,
            "tokens": self.tokens,
            "content_length": self.content_length
        }
        if self.error_code:
            result["error_code"] = self.error_code
        if self.chapter:
            result["chapter"] = self.chapter
        return result


# ============================================================
# [2] MetadataService 클래스
# ============================================================

class MetadataService:
    """
    메타데이터 관리 서비스

    sources.yaml과 chunk_manifest.jsonl을 로드하고
    청크 ID로 citation 정보를 조회합니다.

    사용 예시:
        service = MetadataService()
        service.load()
        citation = service.get_citation("error_codes_C4_004")
    """

    def __init__(
        self,
        sources_path: str = "data/processed/metadata/sources.yaml",
        manifest_path: str = "data/processed/metadata/chunk_manifest.jsonl"
    ):
        self.sources_path = Path(sources_path)
        self.manifest_path = Path(manifest_path)

        self._sources: Dict[str, DocumentInfo] = {}
        self._manifest: Dict[str, ChunkMapping] = {}
        self._loaded = False

    def load(self) -> bool:
        """
        메타데이터 로드

        Returns:
            로드 성공 여부
        """
        try:
            self._load_sources()
            self._load_manifest()
            self._loaded = True
            print(f"[OK] MetadataService loaded: {len(self._sources)} docs, {len(self._manifest)} chunks")
            return True
        except Exception as e:
            print(f"[ERROR] MetadataService load failed: {e}")
            return False

    def _load_sources(self):
        """sources.yaml 로드"""
        if not self.sources_path.exists():
            print(f"[WARN] sources.yaml not found: {self.sources_path}")
            return

        with open(self.sources_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        for doc_id, doc_data in data.get("documents", {}).items():
            self._sources[doc_id] = DocumentInfo(
                doc_id=doc_id,
                title=doc_data.get("title", ""),
                version=doc_data.get("version", ""),
                date=doc_data.get("date", ""),
                pages=doc_data.get("pages", 0),
                source_file=doc_data.get("source_file", ""),
                chunk_count=doc_data.get("chunk_count", 0),
                language=doc_data.get("language", "en"),
                publisher=doc_data.get("publisher", ""),
                url=doc_data.get("url"),
                sections=doc_data.get("sections", [])
            )

    def _load_manifest(self):
        """chunk_manifest.jsonl 로드"""
        if not self.manifest_path.exists():
            print(f"[WARN] chunk_manifest.jsonl not found: {self.manifest_path}")
            return

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    chunk_id = data.get("chunk_id")
                    if chunk_id:
                        self._manifest[chunk_id] = ChunkMapping(
                            chunk_id=chunk_id,
                            doc_id=data.get("doc_id", ""),
                            page=data.get("page", 0),
                            section=data.get("section", ""),
                            doc_type=data.get("doc_type", ""),
                            tokens=data.get("tokens", 0),
                            content_length=data.get("content_length", 0),
                            error_code=data.get("error_code"),
                            chapter=data.get("chapter")
                        )
                except json.JSONDecodeError:
                    continue

    # --------------------------------------------------------
    # [3] 조회 메서드
    # --------------------------------------------------------

    def get_document(self, doc_id: str) -> Optional[DocumentInfo]:
        """
        문서 정보 조회

        Args:
            doc_id: 문서 ID

        Returns:
            DocumentInfo 또는 None
        """
        return self._sources.get(doc_id)

    def get_chunk_mapping(self, chunk_id: str) -> Optional[ChunkMapping]:
        """
        청크 매핑 조회

        Args:
            chunk_id: 청크 ID

        Returns:
            ChunkMapping 또는 None
        """
        return self._manifest.get(chunk_id)

    def get_citation(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        청크 ID로 완전한 citation 정보 반환

        Args:
            chunk_id: 청크 ID

        Returns:
            Citation 정보 딕셔너리:
            {
                "doc_id": "service_manual",
                "doc_title": "e-Series Service Manual",
                "version": "5.12",
                "page": 45,
                "section": "Troubleshooting",
                "citation": "e-Series Service Manual v5.12, p.45"
            }
        """
        mapping = self.get_chunk_mapping(chunk_id)
        if not mapping:
            return None

        doc = self.get_document(mapping.doc_id)
        if not doc:
            # 문서 정보 없이 기본 citation 생성
            return {
                "doc_id": mapping.doc_id,
                "doc_title": mapping.doc_id,
                "version": "",
                "page": mapping.page,
                "section": mapping.section,
                "error_code": mapping.error_code,
                "chapter": mapping.chapter,
                "citation": f"{mapping.doc_id}, p.{mapping.page}"
            }

        # citation 문자열 생성
        citation_parts = [f"{doc.title} v{doc.version}"]
        citation_parts.append(f"p.{mapping.page}")

        if mapping.section:
            # 섹션이 너무 길면 축약
            section_display = mapping.section[:50] + "..." if len(mapping.section) > 50 else mapping.section
            citation_parts.append(section_display)

        return {
            "doc_id": doc.doc_id,
            "doc_title": doc.title,
            "version": doc.version,
            "page": mapping.page,
            "section": mapping.section,
            "error_code": mapping.error_code,
            "chapter": mapping.chapter,
            "citation": ", ".join(citation_parts)
        }

    def get_all_documents(self) -> List[DocumentInfo]:
        """모든 문서 정보 반환"""
        return list(self._sources.values())

    def get_chunks_by_doc(self, doc_id: str) -> List[ChunkMapping]:
        """
        문서에 속한 모든 청크 반환

        Args:
            doc_id: 문서 ID

        Returns:
            해당 문서의 청크 매핑 리스트
        """
        return [m for m in self._manifest.values() if m.doc_id == doc_id]

    def get_chunks_by_page(self, doc_id: str, page: int) -> List[ChunkMapping]:
        """
        특정 페이지의 청크 반환

        Args:
            doc_id: 문서 ID
            page: 페이지 번호

        Returns:
            해당 페이지의 청크 매핑 리스트
        """
        return [
            m for m in self._manifest.values()
            if m.doc_id == doc_id and m.page == page
        ]

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            "total_documents": len(self._sources),
            "total_chunks": len(self._manifest),
            "documents": {
                doc_id: {
                    "title": doc.title,
                    "pages": doc.pages,
                    "chunk_count": doc.chunk_count
                }
                for doc_id, doc in self._sources.items()
            }
        }

    @property
    def is_loaded(self) -> bool:
        """로드 상태 확인"""
        return self._loaded


# ============================================================
# [4] 싱글톤 인스턴스
# ============================================================

_metadata_service: Optional[MetadataService] = None


def get_metadata_service() -> MetadataService:
    """
    MetadataService 싱글톤 반환

    Returns:
        MetadataService 인스턴스
    """
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService()
        _metadata_service.load()
    return _metadata_service


# ============================================================
# CLI 실행
# ============================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("MetadataService Test")
    print("=" * 60)

    service = MetadataService()
    if not service.load():
        print("[FAIL] Failed to load metadata")
        sys.exit(1)

    # 통계 출력
    stats = service.get_stats()
    print(f"\nDocuments: {stats['total_documents']}")
    print(f"Chunks: {stats['total_chunks']}")

    for doc_id, doc_stats in stats.get('documents', {}).items():
        print(f"  - {doc_id}: {doc_stats['chunk_count']} chunks, {doc_stats['pages']} pages")

    # Citation 테스트
    print("\nCitation test:")
    test_chunk_ids = [
        "error_codes_C4_004",
        "service_manual_000",
        "user_manual_000"
    ]

    for chunk_id in test_chunk_ids:
        citation = service.get_citation(chunk_id)
        if citation:
            print(f"  {chunk_id}: {citation['citation']}")
        else:
            print(f"  {chunk_id}: Not found")

    print("\n" + "=" * 60)
    print("[OK] MetadataService test completed!")
    print("=" * 60)
