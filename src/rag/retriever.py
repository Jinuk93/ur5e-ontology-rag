# ============================================================
# src/rag/retriever.py - VectorDB 검색기
# ============================================================
# VectorDB(ChromaDB)에서 질문과 유사한 청크를 검색합니다.
#
# 사용 예시:
#   retriever = Retriever()
#   results = retriever.retrieve("C4A15 에러 해결법", top_k=5)
# ============================================================

import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.embedding.vector_store import VectorStore
from src.embedding.embedder import Embedder


# ============================================================
# [1] RetrievalResult 데이터 클래스
# ============================================================

@dataclass
class RetrievalResult:
    """
    검색 결과를 담는 데이터 클래스

    Attributes:
        chunk_id: 청크 고유 ID
        content: 청크 텍스트 내용
        metadata: 메타데이터 (source, page, doc_type 등)
        score: 유사도 점수 (0~1, 높을수록 유사)
    """
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    score: float

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"RetrievalResult(id={self.chunk_id}, score={self.score:.4f}, content='{preview}')"


# ============================================================
# [2] Retriever 클래스
# ============================================================

class Retriever:
    """
    VectorDB 기반 검색기

    VectorDB(ChromaDB)에서 질문과 의미적으로 유사한 청크를 검색합니다.

    사용 예시:
        retriever = Retriever()
        results = retriever.retrieve("C4A15 에러가 발생했어요", top_k=5)

        for result in results:
            print(f"[{result.score:.2f}] {result.content[:100]}")
    """

    def __init__(
        self,
        collection_name: str = "ur5e_chunks",
        use_embedder: bool = True,
    ):
        """
        Retriever 초기화

        Args:
            collection_name: ChromaDB 컬렉션 이름
            use_embedder: Embedder 사용 여부 (True 권장)
        """
        self.vector_store = VectorStore(collection_name=collection_name)
        self.embedder = Embedder() if use_embedder else None

        print(f"[OK] Retriever initialized")
        print(f"     Collection: {collection_name}")
        print(f"     Total chunks: {self.vector_store.count()}")

    # --------------------------------------------------------
    # [2.1] 검색 메서드
    # --------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        doc_type_filter: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """
        질문과 유사한 청크 검색

        Args:
            query: 사용자 질문
            top_k: 반환할 결과 수 (기본값: 5)
            doc_type_filter: 문서 타입 필터 (예: "error_code", "service_manual")

        Returns:
            List[RetrievalResult]: 검색 결과 리스트 (유사도 높은 순)

        사용 예시:
            # 기본 검색
            results = retriever.retrieve("통신 에러", top_k=5)

            # 에러 코드 문서만 검색
            results = retriever.retrieve(
                "C4A15 해결법",
                top_k=5,
                doc_type_filter="error_code"
            )
        """
        # 메타데이터 필터 구성
        where_filter = None
        if doc_type_filter:
            where_filter = {"doc_type": doc_type_filter}

        # VectorDB 검색
        raw_results = self.vector_store.search(
            query=query,
            top_k=top_k,
            where=where_filter,
            embedder=self.embedder,
        )

        # RetrievalResult로 변환
        results = []
        for r in raw_results:
            result = RetrievalResult(
                chunk_id=r['id'],
                content=r['content'],
                metadata=r['metadata'],
                score=r['score'],
            )
            results.append(result)

        return results

    # --------------------------------------------------------
    # [2.2] 유틸리티 메서드
    # --------------------------------------------------------

    def get_chunk_by_id(self, chunk_id: str) -> Optional[RetrievalResult]:
        """
        ID로 특정 청크 조회

        Args:
            chunk_id: 청크 ID

        Returns:
            RetrievalResult or None
        """
        chunk = self.vector_store.get_by_id(chunk_id)
        if chunk:
            return RetrievalResult(
                chunk_id=chunk['id'],
                content=chunk['content'],
                metadata=chunk['metadata'],
                score=1.0,  # 직접 조회이므로 점수 1.0
            )
        return None

    def count(self) -> int:
        """저장된 총 청크 수 반환"""
        return self.vector_store.count()


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("[*] Retriever Test")
    print("=" * 60)

    # Retriever 초기화
    retriever = Retriever()

    # 테스트 검색
    test_queries = [
        "C4A15 에러가 발생했어요",
        "통신 에러 해결 방법",
        "조인트 캘리브레이션",
    ]

    for query in test_queries:
        print(f"\n[Query] {query}")
        print("-" * 40)

        results = retriever.retrieve(query, top_k=3)

        for i, result in enumerate(results, 1):
            print(f"  {i}. [score: {result.score:.4f}] {result.chunk_id}")
            print(f"     {result.content[:80]}...")
            print(f"     (doc_type: {result.metadata.get('doc_type', 'N/A')})")

    print("\n" + "=" * 60)
    print("[OK] Retriever test completed!")
    print("=" * 60)
