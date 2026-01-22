"""
임베딩 모듈

OpenAI 임베딩 생성 및 ChromaDB 벡터 저장소를 제공합니다.

사용 예시:
    from src.embedding import VectorStore, OpenAIEmbedder

    # 벡터 저장소 사용
    vs = VectorStore()
    results = vs.search("C153 에러 해결 방법", top_k=3)

    # 임베딩 생성
    embedder = OpenAIEmbedder()
    embedding = embedder.embed_text("안녕하세요")
"""

from .embedder import OpenAIEmbedder, create_embeddings
from .vector_store import VectorStore, SearchResult

__all__ = [
    # 임베딩
    "OpenAIEmbedder",
    "create_embeddings",
    # 벡터 저장소
    "VectorStore",
    "SearchResult",
]
