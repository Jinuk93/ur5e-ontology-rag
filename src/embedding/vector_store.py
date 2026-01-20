# ============================================================
# src/embedding/vector_store.py - ChromaDB 벡터 저장소
# ============================================================
# ChromaDB를 사용하여 청크와 임베딩을 저장하고 검색합니다.
#
# ChromaDB란?
#   - 오픈소스 벡터 데이터베이스
#   - 로컬 파일로 저장 (stores/chroma/)
#   - 메타데이터 필터링 지원
#
# 주요 기능:
#   - 청크 저장 (add_chunks)
#   - 유사도 검색 (search)
#   - 메타데이터 필터링 (doc_type, source 등)
# ============================================================

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings

# 프로젝트 루트의 .env 파일 로드
load_dotenv()


# ============================================================
# [1] VectorStore 클래스
# ============================================================

class VectorStore:
    """
    ChromaDB 기반 벡터 저장소

    사용 예시:
        store = VectorStore(collection_name="ur5e_chunks")
        store.add_chunks(chunks)
        results = store.search("통신 에러", top_k=5)
    """

    def __init__(
        self,
        collection_name: str = "ur5e_chunks",
        persist_dir: Optional[str] = None,
    ):
        """
        VectorStore 초기화

        Args:
            collection_name: ChromaDB 컬렉션 이름
            persist_dir: 데이터 저장 경로 (기본값: .env의 CHROMA_PERSIST_DIR)
        """
        # 저장 경로 설정
        self.persist_dir = persist_dir or os.getenv(
            "CHROMA_PERSIST_DIR",
            "./stores/chroma"
        )

        # 폴더 생성
        os.makedirs(self.persist_dir, exist_ok=True)

        # ChromaDB 클라이언트 생성 (영구 저장)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        # 컬렉션 생성 또는 가져오기
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "UR5e manual chunks"}
        )

        print(f"[OK] VectorStore initialized")
        print(f"     Collection: {collection_name}")
        print(f"     Persist dir: {self.persist_dir}")
        print(f"     Existing items: {self.collection.count()}")

    # --------------------------------------------------------
    # [1.1] 청크 추가
    # --------------------------------------------------------

    def add_chunks(
        self,
        chunks: List,
        embedder=None,
    ) -> int:
        """
        청크들을 벡터DB에 추가

        처리 흐름:
            1. 청크에 임베딩이 없으면 생성
            2. ChromaDB에 저장 (id, embedding, document, metadata)

        Args:
            chunks: Chunk 객체 리스트
            embedder: Embedder 객체 (임베딩 없을 때 사용)

        Returns:
            int: 추가된 청크 수

        사용 예시:
            store.add_chunks(chunks, embedder=embedder)
        """
        if not chunks:
            print("[WARN] No chunks to add")
            return 0

        # 임베딩이 없는 청크 확인
        chunks_without_embedding = [c for c in chunks if c.embedding is None]
        if chunks_without_embedding:
            if embedder is None:
                raise ValueError(
                    f"{len(chunks_without_embedding)} chunks have no embedding. "
                    "Please provide an embedder."
                )
            print(f"[*] Generating embeddings for {len(chunks_without_embedding)} chunks...")
            embedder.embed_chunks(chunks_without_embedding)

        # ChromaDB에 추가할 데이터 준비
        ids = [chunk.id for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata.to_dict() for chunk in chunks]

        # 배치 단위로 추가 (ChromaDB 제한 고려)
        batch_size = 500
        total_added = 0

        for i in range(0, len(chunks), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]

            # 중복 ID 제거 (이미 존재하는 것은 업데이트)
            self.collection.upsert(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas,
            )

            total_added += len(batch_ids)
            print(f"    Added batch: {total_added}/{len(chunks)}")

        print(f"[OK] Added {total_added} chunks to collection")
        print(f"     Total items in collection: {self.collection.count()}")

        return total_added

    # --------------------------------------------------------
    # [1.2] 유사도 검색
    # --------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        embedder=None,
    ) -> List[Dict[str, Any]]:
        """
        유사도 검색 수행

        처리 흐름:
            1. 쿼리 텍스트를 벡터로 변환
            2. ChromaDB에서 가장 유사한 청크 검색
            3. 결과 반환 (청크 내용, 메타데이터, 유사도 점수)

        Args:
            query: 검색 쿼리 텍스트
            top_k: 반환할 결과 수
            where: 메타데이터 필터 (예: {"doc_type": "error_code"})
            embedder: Embedder 객체 (쿼리 임베딩용)

        Returns:
            List[Dict]: 검색 결과 리스트
                - id: 청크 ID
                - content: 청크 내용
                - metadata: 메타데이터
                - score: 유사도 점수 (1에 가까울수록 유사)

        사용 예시:
            # 기본 검색
            results = store.search("통신 에러", top_k=5, embedder=embedder)

            # 필터링 검색
            results = store.search(
                "통신 에러",
                top_k=5,
                where={"doc_type": "error_code"},
                embedder=embedder
            )
        """
        if embedder is None:
            # 임베더 없이 텍스트 쿼리 사용
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        else:
            # 임베더로 쿼리 벡터 생성
            query_embedding = embedder.embed_text(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )

        # 결과 정리
        search_results = []

        if results and results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                # 거리를 유사도 점수로 변환 (1 - distance)
                # ChromaDB는 기본적으로 L2 거리 사용
                distance = results['distances'][0][i] if results['distances'] else 0
                score = 1 / (1 + distance)  # 거리가 작을수록 점수 높음

                search_results.append({
                    'id': chunk_id,
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': score,
                    'distance': distance,
                })

        return search_results

    # --------------------------------------------------------
    # [1.3] 컬렉션 관리
    # --------------------------------------------------------

    def count(self) -> int:
        """컬렉션의 총 아이템 수 반환"""
        return self.collection.count()

    def delete_collection(self) -> None:
        """
        컬렉션 삭제 (주의: 모든 데이터 삭제됨)
        """
        self.client.delete_collection(self.collection_name)
        print(f"[OK] Deleted collection: {self.collection_name}")

        # 컬렉션 다시 생성
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "UR5e manual chunks"}
        )

    def get_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        ID로 청크 조회

        Args:
            chunk_id: 청크 ID

        Returns:
            Dict or None: 청크 정보
        """
        results = self.collection.get(
            ids=[chunk_id],
            include=["documents", "metadatas", "embeddings"],
        )

        if results and results['ids']:
            # embeddings는 numpy array일 수 있으므로 len()으로 체크
            embedding = None
            if results.get('embeddings') is not None and len(results['embeddings']) > 0:
                embedding = results['embeddings'][0]

            return {
                'id': results['ids'][0],
                'content': results['documents'][0] if results['documents'] else None,
                'metadata': results['metadatas'][0] if results['metadatas'] else None,
                'embedding': embedding,
            }
        return None

    def get_all_ids(self) -> List[str]:
        """모든 청크 ID 반환"""
        results = self.collection.get(include=[])
        return results['ids'] if results else []


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    from src.embedding.embedder import Embedder
    from src.ingestion.models import Chunk, ChunkMetadata

    print("=" * 50)
    print("[*] VectorStore Test")
    print("=" * 50)

    # 테스트용 컬렉션 (기존 데이터와 분리)
    store = VectorStore(collection_name="test_collection")
    embedder = Embedder()

    # 기존 데이터 삭제
    store.delete_collection()

    # 테스트 청크 생성
    test_chunks = [
        Chunk(
            id="test_001",
            content="C4 Communication error: Lost connection with Controller",
            metadata=ChunkMetadata(
                source="ErrorCodes.pdf",
                page=12,
                doc_type="error_code",
                error_code="C4"
            )
        ),
        Chunk(
            id="test_002",
            content="Check Ethernet cable between Safety Control Board and Motherboard",
            metadata=ChunkMetadata(
                source="ErrorCodes.pdf",
                page=13,
                doc_type="error_code",
                error_code="C4"
            )
        ),
        Chunk(
            id="test_003",
            content="Joint replacement procedure: Remove the screws carefully",
            metadata=ChunkMetadata(
                source="ServiceManual.pdf",
                page=55,
                doc_type="service_manual",
                section="Joint Replacement"
            )
        ),
    ]

    # 테스트 1: 청크 추가
    print("\n[Test 1] Add chunks")
    store.add_chunks(test_chunks, embedder=embedder)
    print(f"  Total items: {store.count()}")

    # 테스트 2: 유사도 검색
    print("\n[Test 2] Similarity search")
    query = "통신 연결 오류"
    results = store.search(query, top_k=3, embedder=embedder)

    print(f"  Query: '{query}'")
    print(f"  Results:")
    for i, r in enumerate(results, 1):
        print(f"    {i}. [{r['score']:.4f}] {r['id']}")
        print(f"       {r['content'][:50]}...")

    # 테스트 3: 필터링 검색
    print("\n[Test 3] Filtered search")
    results = store.search(
        "문제 해결",
        top_k=3,
        where={"doc_type": "error_code"},
        embedder=embedder
    )
    print(f"  Query: '문제 해결' (filter: error_code only)")
    print(f"  Results: {len(results)} items")

    # 테스트 4: ID로 조회
    print("\n[Test 4] Get by ID")
    chunk = store.get_by_id("test_001")
    if chunk:
        print(f"  ID: {chunk['id']}")
        print(f"  Content: {chunk['content'][:50]}...")

    # 정리: 테스트 컬렉션 삭제
    store.delete_collection()

    print("\n" + "=" * 50)
    print("[OK] All tests passed!")
    print("=" * 50)
