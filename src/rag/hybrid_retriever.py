"""
하이브리드 검색기 (Hybrid Retriever)

VectorStore + Reranker + Ontology를 통합하여
질문 유형에 따라 최적의 검색 전략을 적용합니다.

2026-01-26 신규 구현:
- VectorStore + CrossEncoderReranker 통합
- QueryType에 따른 검색 경로 분기
- DocumentReference 변환

사용 예시:
    from src.rag import HybridRetriever, QueryType

    retriever = HybridRetriever()

    # RAG 질문: 문서 검색 + 리랭킹
    docs = retriever.retrieve("C153 에러 해결 방법", QueryType.RAG)

    # HYBRID 질문: 온톨로지 + 문서 병합
    docs = retriever.retrieve("Fz 과부하 원인", QueryType.HYBRID)
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from src.config import get_settings
from src.embedding import VectorStore, SearchResult
from .evidence_schema import DocumentReference, QueryType

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """검색 결과"""
    document_refs: List[DocumentReference]  # 문서 참조 리스트
    total_candidates: int  # 1단계 후보 수
    reranked: bool  # 리랭킹 수행 여부
    search_time_ms: float  # 검색 소요 시간 (ms)
    metadata: Dict[str, Any]  # 추가 메타데이터


class HybridRetriever:
    """하이브리드 검색기

    질문 유형에 따라 다른 검색 전략을 적용:
    - RAG: VectorStore + Reranker (문서만)
    - HYBRID: VectorStore + Reranker (문서) + 온톨로지 컨텍스트
    - ONTOLOGY: 온톨로지 전용 (문서 검색 스킵 가능)

    파이프라인:
    ┌─────────────────────────────────────────────────────────────┐
    │  Query                                                      │
    │    │                                                        │
    │    ▼                                                        │
    │  ┌─────────────┐                                            │
    │  │ VectorStore │  Stage 1: Bi-encoder (Top-K=20)           │
    │  └─────────────┘                                            │
    │    │                                                        │
    │    ▼ (20개 후보)                                            │
    │  ┌─────────────┐                                            │
    │  │  Reranker   │  Stage 2: Cross-encoder (Top-N=5)         │
    │  └─────────────┘                                            │
    │    │                                                        │
    │    ▼ (5개 최종)                                             │
    │  DocumentReference[]                                        │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        use_reranker: Optional[bool] = None,
    ):
        """초기화

        Args:
            vector_store: VectorStore 인스턴스 (없으면 자동 생성)
            use_reranker: 리랭커 사용 여부 (None이면 설정에서 로드)
        """
        self.settings = get_settings()

        # VectorStore 초기화 (지연 로딩)
        self._vector_store = vector_store
        self._vs_initialized = vector_store is not None

        # 리랭커 설정
        if use_reranker is None:
            self.use_reranker = self.settings.rerank.enabled
        else:
            self.use_reranker = use_reranker

        # 검색 설정
        self.initial_top_k = self.settings.rerank.initial_top_k  # 20
        self.final_top_n = self.settings.rerank.final_top_n  # 5
        self.similarity_threshold = self.settings.retrieval.similarity_threshold  # 0.7

        logger.info(
            f"HybridRetriever 초기화: reranker={self.use_reranker}, "
            f"top_k={self.initial_top_k}, top_n={self.final_top_n}"
        )

    def preload(self) -> "HybridRetriever":
        """모델 사전 로딩 (서버 시작 시 호출)

        VectorStore와 Reranker를 미리 초기화하여
        첫 요청의 지연을 방지합니다.

        Returns:
            self (체이닝용)
        """
        import time
        start = time.time()

        # VectorStore 초기화
        logger.info("HybridRetriever 사전 로딩: VectorStore 초기화...")
        _ = self.vector_store

        # Reranker 사전 로딩
        if self.use_reranker:
            logger.info("HybridRetriever 사전 로딩: Reranker 모델 로딩...")
            from src.embedding import get_reranker
            reranker = get_reranker()
            reranker.preload()

        elapsed = time.time() - start
        logger.info(f"HybridRetriever 사전 로딩 완료: {elapsed:.1f}초 소요")
        return self

    @property
    def vector_store(self) -> VectorStore:
        """VectorStore 지연 초기화"""
        if not self._vs_initialized:
            self._vector_store = VectorStore()
            self._vs_initialized = True
        return self._vector_store

    def retrieve(
        self,
        query: str,
        query_type: QueryType,
        filter_metadata: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RetrievalResult:
        """질문 유형에 따른 문서 검색

        Args:
            query: 검색 쿼리
            query_type: 질문 유형 (ONTOLOGY/HYBRID/RAG)
            filter_metadata: 메타데이터 필터 (예: {"doc_type": "user_manual"})
            context: 추가 컨텍스트

        Returns:
            RetrievalResult: 검색 결과
        """
        import time
        start_time = time.time()

        # ONTOLOGY 질문은 문서 검색 최소화 (선택적)
        if query_type == QueryType.ONTOLOGY:
            # 온톨로지 질문도 관련 문서가 있으면 도움됨
            # 단, 더 적은 결과 반환
            top_n = min(3, self.final_top_n)
        else:
            top_n = self.final_top_n

        # 검색 수행
        if self.use_reranker:
            # 2단계 검색: Bi-encoder + Cross-encoder
            document_refs, total_candidates, reranked = self._search_with_rerank(
                query, filter_metadata, top_n
            )
            # 폴백 발생 시 reranked=False로 반환됨
        else:
            # 1단계 검색: Bi-encoder only
            document_refs, total_candidates, reranked = self._search_basic(
                query, filter_metadata, top_n
            )

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"HybridRetriever 검색 완료: query_type={query_type.value}, "
            f"results={len(document_refs)}, reranked={reranked}, time={elapsed_ms:.1f}ms"
        )

        return RetrievalResult(
            document_refs=document_refs,
            total_candidates=total_candidates,
            reranked=reranked,
            search_time_ms=elapsed_ms,
            metadata={
                "query_type": query_type.value,
                "filter_metadata": filter_metadata,
                "use_reranker": self.use_reranker,
            }
        )

    def _search_with_rerank(
        self,
        query: str,
        filter_metadata: Optional[Dict[str, str]],
        top_n: int,
    ) -> tuple[List[DocumentReference], int, bool]:
        """2단계 검색 (Bi-encoder + Cross-encoder)

        Args:
            query: 검색 쿼리
            filter_metadata: 메타데이터 필터
            top_n: 최종 반환 개수

        Returns:
            (DocumentReference 리스트, 1단계 후보 수, 실제 리랭킹 수행 여부)
        """
        try:
            # VectorStore의 search_with_rerank 사용
            search_results = self.vector_store.search_with_rerank(
                query=query,
                initial_top_k=self.initial_top_k,
                final_top_n=top_n,
                filter_metadata=filter_metadata,
            )

            # SearchResult → DocumentReference 변환
            document_refs = self._convert_to_document_refs(search_results)

            return document_refs, self.initial_top_k, True  # 리랭킹 성공

        except Exception as e:
            logger.error(f"2단계 검색 실패, 기본 검색으로 폴백: {e}")
            docs, count, _ = self._search_basic(query, filter_metadata, top_n)
            return docs, count, False  # 리랭킹 실패, 폴백함

    def _search_basic(
        self,
        query: str,
        filter_metadata: Optional[Dict[str, str]],
        top_n: int,
    ) -> tuple[List[DocumentReference], int, bool]:
        """1단계 검색 (Bi-encoder only)

        Args:
            query: 검색 쿼리
            filter_metadata: 메타데이터 필터
            top_n: 반환 개수

        Returns:
            (DocumentReference 리스트, 후보 수, 리랭킹 수행 여부 - 항상 False)
        """
        try:
            search_results = self.vector_store.search(
                query=query,
                top_k=top_n,
                filter_metadata=filter_metadata,
            )

            # SearchResult → DocumentReference 변환
            document_refs = self._convert_to_document_refs(search_results)

            return document_refs, top_n, False  # 기본 검색은 리랭킹 없음

        except Exception as e:
            logger.error(f"기본 검색 실패: {e}")
            return [], 0, False

    def _convert_to_document_refs(
        self,
        search_results: List[SearchResult],
    ) -> List[DocumentReference]:
        """SearchResult → DocumentReference 변환

        Args:
            search_results: VectorStore 검색 결과

        Returns:
            DocumentReference 리스트
        """
        document_refs = []

        for result in search_results:
            # 임계값 필터링
            if result.score < self.similarity_threshold:
                continue

            # 메타데이터에서 정보 추출
            metadata = result.metadata or {}

            doc_ref = DocumentReference(
                doc_id=metadata.get("source", "unknown"),
                page=metadata.get("page"),
                chunk_id=result.chunk_id,
                relevance=result.score,
                snippet=self._truncate_snippet(result.content, max_len=200),
            )
            document_refs.append(doc_ref)

        return document_refs

    def _truncate_snippet(self, text: str, max_len: int = 200) -> str:
        """스니펫 잘라내기"""
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."

    def search_for_entity(
        self,
        entity_id: str,
        entity_type: str,
        top_k: int = 5,
    ) -> List[DocumentReference]:
        """특정 엔티티 관련 문서 검색

        온톨로지 엔티티(ErrorCode, Pattern 등)에 대한
        관련 문서를 검색합니다.

        Args:
            entity_id: 엔티티 ID (예: "C153", "PAT_OVERLOAD")
            entity_type: 엔티티 타입 (예: "ErrorCode", "Pattern")
            top_k: 검색 개수

        Returns:
            DocumentReference 리스트
        """
        # 엔티티 타입에 따른 검색 쿼리 구성
        if entity_type == "ErrorCode":
            query = f"{entity_id} 에러 코드 해결 방법"
        elif entity_type == "Pattern":
            query = f"{entity_id} 패턴 원인 대처"
        else:
            query = f"{entity_id} 관련 정보"

        # 검색 수행
        if self.use_reranker:
            docs, _, _ = self._search_with_rerank(query, None, top_k)
        else:
            docs, _, _ = self._search_basic(query, None, top_k)

        return docs


# 팩토리 함수
def create_hybrid_retriever(
    use_reranker: Optional[bool] = None,
) -> HybridRetriever:
    """HybridRetriever 인스턴스 생성

    Args:
        use_reranker: 리랭커 사용 여부 (None이면 설정에서 로드)

    Returns:
        HybridRetriever 인스턴스
    """
    return HybridRetriever(use_reranker=use_reranker)
