# ============================================================
# src/rag/hybrid_retriever.py - 하이브리드 검색기
# ============================================================
# VectorDB + GraphDB를 결합한 하이브리드 검색을 수행합니다.
#
# 검색 전략:
#   - graph_first: GraphDB 우선 → VectorDB 보충
#   - vector_first: VectorDB 우선 → GraphDB 보충
#   - hybrid: 둘 다 동시에 검색 후 병합
# ============================================================

import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.rag.retriever import Retriever, RetrievalResult
from src.rag.graph_retriever import GraphRetriever, GraphResult
from src.rag.query_analyzer import QueryAnalyzer, QueryAnalysis


# ============================================================
# [1] HybridResult 데이터 클래스
# ============================================================

@dataclass
class HybridResult:
    """
    하이브리드 검색 결과

    Attributes:
        content: 텍스트 내용
        source_type: 출처 타입 ("graph" or "vector")
        score: 관련성 점수
        metadata: 추가 메타데이터
    """
    content: str
    source_type: str  # "graph" or "vector"
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"HybridResult(source={self.source_type}, score={self.score:.3f}, content='{preview}')"


# ============================================================
# [2] HybridRetriever 클래스
# ============================================================

class HybridRetriever:
    """
    하이브리드 검색기

    VectorDB + GraphDB를 결합하여 최적의 검색 결과를 반환합니다.

    사용 예시:
        retriever = HybridRetriever()
        results = retriever.retrieve("C4A15 에러 해결법", top_k=5)
        for r in results:
            print(f"[{r.source_type}] {r.content[:100]}")
    """

    def __init__(self, verbose: bool = True):
        """
        HybridRetriever 초기화

        Args:
            verbose: 상세 로그 출력 여부
        """
        self.verbose = verbose
        self.query_analyzer = QueryAnalyzer()
        self.vector_retriever = Retriever()
        self.graph_retriever = GraphRetriever()

        if self.verbose:
            print("[OK] HybridRetriever initialized")

    def close(self):
        """연결 종료"""
        self.graph_retriever.close()

    # --------------------------------------------------------
    # [2.1] 메인 검색 메서드
    # --------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        strategy: Optional[str] = None,
    ) -> tuple[List[HybridResult], QueryAnalysis]:
        """
        하이브리드 검색 수행

        Args:
            query: 사용자 질문
            top_k: 반환할 결과 수
            strategy: 검색 전략 (None이면 자동 결정)

        Returns:
            tuple[List[HybridResult], QueryAnalysis]: 검색 결과와 분석 정보
        """
        # 1. 질문 분석
        analysis = self.query_analyzer.analyze(query)

        if self.verbose:
            print(f"\n[Analysis]")
            print(f"  Error codes: {analysis.error_codes}")
            print(f"  Components: {analysis.components}")
            print(f"  Query type: {analysis.query_type}")
            print(f"  Strategy: {analysis.search_strategy}")

        # 2. 검색 전략 결정
        search_strategy = strategy or analysis.search_strategy

        # 3. 전략에 따른 검색 실행
        if search_strategy == "graph_first":
            results = self._search_graph_first(query, analysis, top_k)
        elif search_strategy == "vector_first":
            results = self._search_vector_first(query, analysis, top_k)
        else:  # hybrid
            results = self._search_hybrid(query, analysis, top_k)

        return results, analysis

    # --------------------------------------------------------
    # [2.2] Graph 우선 검색
    # --------------------------------------------------------

    def _search_graph_first(
        self,
        query: str,
        analysis: QueryAnalysis,
        top_k: int,
    ) -> List[HybridResult]:
        """
        GraphDB 우선 검색

        1. GraphDB에서 에러 코드/부품 관련 검색
        2. 결과가 부족하면 VectorDB로 보충
        """
        results = []

        if self.verbose:
            print(f"\n[Strategy] Graph First")

        # 1. GraphDB 검색
        graph_results = self.graph_retriever.search(
            error_codes=analysis.error_codes,
            components=analysis.components,
        )

        if self.verbose:
            print(f"  Graph results: {len(graph_results)}")

        # Graph 결과 변환
        for gr in graph_results:
            results.append(HybridResult(
                content=gr.content,
                source_type="graph",
                score=gr.score,
                metadata={
                    **gr.metadata,
                    "entity_type": gr.entity_type,
                    "entity_name": gr.entity_name,
                    "relation_type": gr.relation_type,
                },
            ))

        # 2. VectorDB로 보충 (결과가 부족할 때)
        remaining = top_k - len(results)
        if remaining > 0:
            vector_results = self.vector_retriever.retrieve(query, top_k=remaining)

            if self.verbose:
                print(f"  Vector supplement: {len(vector_results)}")

            for vr in vector_results:
                # 중복 체크 (내용이 비슷한지)
                if not self._is_duplicate(vr.content, results):
                    results.append(HybridResult(
                        content=vr.content,
                        source_type="vector",
                        score=vr.score,
                        metadata={
                            "chunk_id": vr.chunk_id,
                            **vr.metadata,
                        },
                    ))

        # 점수순 정렬
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]

    # --------------------------------------------------------
    # [2.3] Vector 우선 검색
    # --------------------------------------------------------

    def _search_vector_first(
        self,
        query: str,
        analysis: QueryAnalysis,
        top_k: int,
    ) -> List[HybridResult]:
        """
        VectorDB 우선 검색

        1. VectorDB에서 의미 기반 검색
        2. 에러 코드가 있으면 GraphDB로 보충
        """
        results = []

        if self.verbose:
            print(f"\n[Strategy] Vector First")

        # 1. VectorDB 검색
        vector_results = self.vector_retriever.retrieve(query, top_k=top_k)

        if self.verbose:
            print(f"  Vector results: {len(vector_results)}")

        for vr in vector_results:
            results.append(HybridResult(
                content=vr.content,
                source_type="vector",
                score=vr.score,
                metadata={
                    "chunk_id": vr.chunk_id,
                    **vr.metadata,
                },
            ))

        # 2. GraphDB로 보충 (에러 코드가 있으면)
        if analysis.error_codes:
            graph_results = self.graph_retriever.search(
                error_codes=analysis.error_codes,
            )

            if self.verbose:
                print(f"  Graph supplement: {len(graph_results)}")

            for gr in graph_results:
                if not self._is_duplicate(gr.content, results):
                    # Graph 결과는 상단에 추가 (높은 점수)
                    results.insert(0, HybridResult(
                        content=gr.content,
                        source_type="graph",
                        score=gr.score,
                        metadata={
                            **gr.metadata,
                            "entity_type": gr.entity_type,
                            "entity_name": gr.entity_name,
                        },
                    ))

        return results[:top_k]

    # --------------------------------------------------------
    # [2.4] 하이브리드 검색
    # --------------------------------------------------------

    def _search_hybrid(
        self,
        query: str,
        analysis: QueryAnalysis,
        top_k: int,
    ) -> List[HybridResult]:
        """
        하이브리드 검색 (둘 다 동시에)

        1. GraphDB와 VectorDB 동시 검색
        2. 결과 병합 및 점수 기반 정렬
        """
        results = []

        if self.verbose:
            print(f"\n[Strategy] Hybrid")

        # 1. GraphDB 검색
        graph_results = self.graph_retriever.search(
            error_codes=analysis.error_codes,
            components=analysis.components,
        )

        if self.verbose:
            print(f"  Graph results: {len(graph_results)}")

        for gr in graph_results:
            results.append(HybridResult(
                content=gr.content,
                source_type="graph",
                score=gr.score * 1.2,  # Graph 결과에 약간의 가중치
                metadata={
                    **gr.metadata,
                    "entity_type": gr.entity_type,
                    "entity_name": gr.entity_name,
                },
            ))

        # 2. VectorDB 검색
        vector_results = self.vector_retriever.retrieve(query, top_k=top_k)

        if self.verbose:
            print(f"  Vector results: {len(vector_results)}")

        for vr in vector_results:
            if not self._is_duplicate(vr.content, results):
                results.append(HybridResult(
                    content=vr.content,
                    source_type="vector",
                    score=vr.score,
                    metadata={
                        "chunk_id": vr.chunk_id,
                        **vr.metadata,
                    },
                ))

        # 3. 점수순 정렬
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]

    # --------------------------------------------------------
    # [2.5] 중복 체크
    # --------------------------------------------------------

    def _is_duplicate(
        self,
        content: str,
        existing_results: List[HybridResult],
        threshold: float = 0.8,
    ) -> bool:
        """
        중복 결과인지 확인

        Args:
            content: 확인할 내용
            existing_results: 기존 결과 리스트
            threshold: 유사도 임계값

        Returns:
            bool: 중복이면 True
        """
        content_lower = content.lower()

        for result in existing_results:
            existing_lower = result.content.lower()

            # 간단한 중복 체크: 내용의 시작 부분이 같으면
            if content_lower[:100] == existing_lower[:100]:
                return True

            # 또는 한쪽이 다른 쪽을 포함하면
            if content_lower in existing_lower or existing_lower in content_lower:
                return True

        return False


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("[*] HybridRetriever Test")
    print("=" * 60)

    retriever = HybridRetriever(verbose=True)

    # 테스트 케이스
    test_queries = [
        ("C4A15 에러 해결법", "graph_first 예상"),
        ("Safety Control Board 에러 목록", "graph_first 예상"),
        ("로봇이 갑자기 멈췄어요", "vector_first 예상"),
    ]

    for query, description in test_queries:
        print(f"\n{'═' * 60}")
        print(f"[Query] {query}")
        print(f"[Expected] {description}")
        print(f"{'═' * 60}")

        results, analysis = retriever.retrieve(query, top_k=5)

        print(f"\n[Results] {len(results)} items")
        print("-" * 40)

        for i, r in enumerate(results[:3], 1):
            print(f"\n{i}. [{r.source_type.upper()}] score={r.score:.3f}")
            print(f"   {r.content[:150]}...")

    retriever.close()

    print("\n" + "=" * 60)
    print("[OK] HybridRetriever test completed!")
    print("=" * 60)
