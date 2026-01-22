"""
ChromaDB 기반 벡터 저장소 모듈

문서 벡터를 저장하고 검색합니다.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import get_settings
from src.ingestion.models import Chunk
from .embedder import OpenAIEmbedder

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """검색 결과"""

    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    score: float  # 유사도 점수 (0~1, 높을수록 유사)


class VectorStore:
    """ChromaDB 기반 벡터 저장소"""

    DEFAULT_COLLECTION_NAME = "ur5e_documents"

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
    ):
        """
        벡터 저장소 초기화

        Args:
            collection_name: 컬렉션 이름 (기본: ur5e_documents)
            persist_directory: 영속 저장 디렉토리 (기본: stores/chroma)
        """
        settings = get_settings()

        self.collection_name = collection_name or self.DEFAULT_COLLECTION_NAME

        if persist_directory:
            self.persist_directory = Path(persist_directory)
        else:
            self.persist_directory = settings.paths.project_root / "stores" / "chroma"

        # 디렉토리 생성
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # ChromaDB 클라이언트 초기화 (영속 모드)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # 컬렉션 가져오기 또는 생성
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "description": "UR5e 문서 벡터 인덱스",
                "embedding_model": settings.embedding.model,
                # Step03 설계서/완료보고서의 가정과 일치: cosine distance
                # (Chroma의 HNSW 공간 설정)
                "hnsw:space": "cosine",
            },
        )

        # 임베딩 생성기
        self._embedder: Optional[OpenAIEmbedder] = None

        logger.info(
            f"벡터 저장소 초기화: collection={self.collection_name}, "
            f"path={self.persist_directory}, count={self.collection.count()}"
        )

    @property
    def embedder(self) -> OpenAIEmbedder:
        """임베딩 생성기 (지연 초기화)"""
        if self._embedder is None:
            self._embedder = OpenAIEmbedder()
        return self._embedder

    def add_documents(
        self,
        chunks: List[Chunk],
        embeddings: Optional[List[List[float]]] = None,
        show_progress: bool = True,
    ) -> None:
        """
        문서 청크 추가

        Args:
            chunks: Chunk 리스트
            embeddings: 미리 생성된 임베딩 (없으면 자동 생성)
            show_progress: 진행률 표시 여부
        """
        if not chunks:
            logger.warning("추가할 청크가 없습니다")
            return

        # 이미 존재하는 ID 확인
        existing_ids = set(self.collection.get()["ids"])
        new_chunks = [c for c in chunks if c.id not in existing_ids]

        if not new_chunks:
            logger.info("모든 청크가 이미 존재합니다")
            return

        logger.info(f"새 청크 추가: {len(new_chunks)}개 (기존: {len(existing_ids)}개)")

        # 임베딩 생성 (필요한 경우)
        if embeddings is None:
            texts = [chunk.content for chunk in new_chunks]
            embeddings = self.embedder.embed_texts(texts, show_progress=show_progress)

        # ChromaDB에 추가
        ids = [chunk.id for chunk in new_chunks]
        documents = [chunk.content for chunk in new_chunks]
        metadatas = [chunk.metadata.to_dict() for chunk in new_chunks]

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(f"청크 추가 완료: {len(new_chunks)}개 (총: {self.collection.count()}개)")

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        유사 문서 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수 (기본: settings.retrieval.top_k)
            filter_metadata: 메타데이터 필터 (예: {"doc_type": "user_manual"})

        Returns:
            SearchResult 리스트
        """
        settings = get_settings()
        top_k = top_k or settings.retrieval.top_k

        # 쿼리 임베딩
        query_embedding = self.embedder.embed_query(query)

        # ChromaDB 검색
        where = self._normalize_where(filter_metadata)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # 결과 변환
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                # ChromaDB의 distance를 유사도 점수로 변환 (cosine의 경우)
                # distance = 1 - similarity, so similarity = 1 - distance
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance

                search_results.append(
                    SearchResult(
                        chunk_id=chunk_id,
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        score=score,
                    )
                )

        logger.debug(f"검색 완료: query='{query[:50]}...', results={len(search_results)}")
        return search_results

    def search_by_embedding(
        self,
        embedding: List[float],
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        임베딩으로 직접 검색

        Args:
            embedding: 쿼리 임베딩
            top_k: 반환할 결과 수
            filter_metadata: 메타데이터 필터

        Returns:
            SearchResult 리스트
        """
        settings = get_settings()
        top_k = top_k or settings.retrieval.top_k

        where = self._normalize_where(filter_metadata)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance

                search_results.append(
                    SearchResult(
                        chunk_id=chunk_id,
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        score=score,
                    )
                )

        return search_results

    def get_by_id(self, chunk_id: str) -> Optional[SearchResult]:
        """
        ID로 청크 조회

        Args:
            chunk_id: 청크 ID

        Returns:
            SearchResult 또는 None
        """
        result = self.collection.get(ids=[chunk_id], include=["documents", "metadatas"])

        if result["ids"]:
            return SearchResult(
                chunk_id=result["ids"][0],
                content=result["documents"][0],
                metadata=result["metadatas"][0] if result["metadatas"] else {},
                score=1.0,
            )
        return None

    def get_by_ids(self, chunk_ids: List[str]) -> List[SearchResult]:
        """
        여러 ID로 청크 조회

        Args:
            chunk_ids: 청크 ID 리스트

        Returns:
            SearchResult 리스트
        """
        result = self.collection.get(ids=chunk_ids, include=["documents", "metadatas"])

        search_results = []
        for i, chunk_id in enumerate(result["ids"]):
            search_results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    content=result["documents"][i],
                    metadata=result["metadatas"][i] if result["metadatas"] else {},
                    score=1.0,
                )
            )
        return search_results

    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 반환"""
        count = self.collection.count()

        # 메타데이터 분포 계산
        all_data = self.collection.get(include=["metadatas"])
        doc_type_counts = {}

        for metadata in all_data["metadatas"] or []:
            doc_type = metadata.get("doc_type", "unknown")
            doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1

        return {
            "collection_name": self.collection_name,
            "count": count,
            "persist_directory": str(self.persist_directory),
            "doc_type_distribution": doc_type_counts,
        }

    def delete_collection(self) -> None:
        """컬렉션 삭제 (재색인용)"""
        self.client.delete_collection(self.collection_name)
        logger.info(f"컬렉션 삭제됨: {self.collection_name}")

        # 새 컬렉션 생성
        settings = get_settings()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "description": "UR5e 문서 벡터 인덱스",
                "embedding_model": settings.embedding.model,
                "hnsw:space": "cosine",
            },
        )

    @staticmethod
    def _normalize_where(filter_metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Chroma where 문법으로 정규화.

        - 값이 리스트/튜플/셋이면 {"$in": [...]}로 변환
        - None이면 None 반환
        """
        if not filter_metadata:
            return None

        normalized: Dict[str, Any] = {}
        for key, value in filter_metadata.items():
            if isinstance(value, (list, tuple, set)):
                normalized[key] = {"$in": list(value)}
            else:
                normalized[key] = value

        return normalized

    def clear(self) -> None:
        """컬렉션 내용 비우기"""
        self.delete_collection()
        logger.info(f"컬렉션 초기화됨: {self.collection_name}")
