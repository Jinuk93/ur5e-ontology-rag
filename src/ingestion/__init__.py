"""
데이터 수집 모듈

PDF 문서 파싱 및 청킹 기능을 제공합니다.

사용 예시:
    from src.ingestion import PDFParser, TextChunker, load_all_chunks

    # PDF 파싱
    with PDFParser(pdf_path) as parser:
        metadata = parser.get_metadata()
        pages = parser.extract_text_with_sections()

    # 청킹
    chunker = TextChunker()
    chunks = chunker.chunk_document(pages, doc_id, doc_type)

    # 기존 청크 로드
    chunks = load_all_chunks()
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from src.config import get_settings
from .models import Chunk, ChunkMetadata, Document, DocumentMetadata, Manifest
from .pdf_parser import PDFParser, parse_pdf
from .chunker import TextChunker, chunk_pages

logger = logging.getLogger(__name__)

__all__ = [
    # 모델
    "Chunk",
    "ChunkMetadata",
    "Document",
    "DocumentMetadata",
    "Manifest",
    # 파서
    "PDFParser",
    "parse_pdf",
    # 청커
    "TextChunker",
    "chunk_pages",
    # 유틸리티
    "load_all_chunks",
    "load_chunks_from_file",
    "save_chunks_to_file",
    "get_chunks_dir",
    "load_manifest",
    "save_manifest",
]


def get_chunks_dir() -> Path:
    """청크 저장 디렉토리 경로 반환"""
    settings = get_settings()
    return settings.paths.chunks_dir


def load_chunks_from_file(file_path: Path) -> List[Chunk]:
    """
    JSON 파일에서 청크 로드

    Args:
        file_path: JSON 파일 경로

    Returns:
        Chunk 리스트
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = [Chunk.from_dict(item) for item in data]
    logger.debug(f"로드 완료: {file_path.name}, {len(chunks)} 청크")
    return chunks


def save_chunks_to_file(chunks: List[Chunk], file_path: Path) -> None:
    """
    청크를 JSON 파일로 저장

    Args:
        chunks: Chunk 리스트
        file_path: 저장할 파일 경로
    """
    data = [chunk.to_dict() for chunk in chunks]

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"저장 완료: {file_path.name}, {len(chunks)} 청크")


def load_all_chunks() -> List[Chunk]:
    """
    모든 청크 파일 로드

    Returns:
        전체 Chunk 리스트
    """
    chunks_dir = get_chunks_dir()
    all_chunks = []

    if not chunks_dir.exists():
        logger.warning(f"청크 디렉토리가 없습니다: {chunks_dir}")
        return all_chunks

    for json_file in sorted(chunks_dir.glob("*.json")):
        chunks = load_chunks_from_file(json_file)
        all_chunks.extend(chunks)

    logger.info(f"전체 청크 로드 완료: {len(all_chunks)} 청크")
    return all_chunks


def load_manifest(manifest_path: Path = None) -> Manifest:
    """
    매니페스트 파일 로드

    Args:
        manifest_path: 매니페스트 파일 경로 (기본: metadata/manifest.json)

    Returns:
        Manifest 객체
    """
    if manifest_path is None:
        settings = get_settings()
        manifest_path = settings.paths.data_processed_dir / "metadata" / "manifest.json"

    if not manifest_path.exists():
        logger.warning(f"매니페스트 파일이 없습니다: {manifest_path}")
        return Manifest()

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Manifest.from_dict(data)


def save_manifest(manifest: Manifest, manifest_path: Path = None) -> None:
    """
    매니페스트 파일 저장

    Args:
        manifest: Manifest 객체
        manifest_path: 저장할 파일 경로
    """
    if manifest_path is None:
        settings = get_settings()
        manifest_path = settings.paths.data_processed_dir / "metadata" / "manifest.json"

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.to_json())

    logger.info(f"매니페스트 저장 완료: {manifest_path}")
