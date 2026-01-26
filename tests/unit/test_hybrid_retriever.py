"""HybridRetriever 단위 테스트"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from src.rag.hybrid_retriever import (
    HybridRetriever,
    RetrievalResult,
    create_hybrid_retriever,
)
from src.rag.evidence_schema import QueryType, DocumentReference
from src.embedding import SearchResult


class TestHybridRetrieverInit:
    """HybridRetriever 초기화 테스트"""

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_init_with_defaults(self, mock_settings):
        """기본값으로 초기화"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=True, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.7),
        )

        retriever = HybridRetriever()

        assert retriever.use_reranker is True
        assert retriever.initial_top_k == 20
        assert retriever.final_top_n == 5
        assert retriever.similarity_threshold == 0.7

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_init_with_reranker_disabled(self, mock_settings):
        """리랭커 비활성화로 초기화"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=True, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.7),
        )

        retriever = HybridRetriever(use_reranker=False)

        assert retriever.use_reranker is False

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_init_with_custom_vector_store(self, mock_settings):
        """커스텀 VectorStore로 초기화"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=False, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.7),
        )
        mock_vs = Mock()

        retriever = HybridRetriever(vector_store=mock_vs)

        assert retriever._vector_store is mock_vs
        assert retriever._vs_initialized is True


class TestHybridRetrieverRetrieve:
    """HybridRetriever retrieve 메서드 테스트"""

    @pytest.fixture
    def mock_vector_store(self):
        """모의 VectorStore"""
        mock = Mock()
        mock.search.return_value = [
            SearchResult(
                chunk_id="chunk_1",
                content="C153 에러 해결 방법입니다.",
                score=0.85,
                metadata={"source": "manual.pdf", "page": 10},
            ),
            SearchResult(
                chunk_id="chunk_2",
                content="충돌 발생 시 조치 사항",
                score=0.75,
                metadata={"source": "guide.pdf", "page": 5},
            ),
        ]
        mock.search_with_rerank.return_value = [
            SearchResult(
                chunk_id="chunk_1",
                content="C153 에러 해결 방법입니다.",
                score=0.92,
                metadata={"source": "manual.pdf", "page": 10},
            ),
        ]
        return mock

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_retrieve_returns_retrieval_result(self, mock_settings, mock_vector_store):
        """retrieve가 RetrievalResult를 반환"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=True, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.3),
        )
        retriever = HybridRetriever(vector_store=mock_vector_store, use_reranker=False)
        result = retriever.retrieve("C153 에러", QueryType.RAG)

        assert isinstance(result, RetrievalResult)
        assert isinstance(result.document_refs, list)
        assert isinstance(result.total_candidates, int)
        assert isinstance(result.reranked, bool)
        assert isinstance(result.search_time_ms, float)

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_retrieve_rag_query(self, mock_settings):
        """RAG 질문 검색"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=True, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.3),
        )
        mock_vs = Mock()
        mock_vs.search.return_value = [
            SearchResult(
                chunk_id="chunk_1",
                content="C153 에러 해결 방법입니다.",
                score=0.85,
                metadata={"source": "manual.pdf", "page": 10},
            ),
        ]
        retriever = HybridRetriever(vector_store=mock_vs, use_reranker=False)
        result = retriever.retrieve("C153 에러 해결법", QueryType.RAG)

        assert len(result.document_refs) > 0
        assert result.metadata["query_type"].upper() == "RAG"

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_retrieve_ontology_query_limits_results(self, mock_settings):
        """ONTOLOGY 질문은 결과 수가 제한됨"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=True, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.3),
        )
        mock_vs = Mock()
        mock_vs.search.return_value = [
            SearchResult(
                chunk_id="chunk_1",
                content="Fz 정보입니다.",
                score=0.85,
                metadata={"source": "manual.pdf", "page": 10},
            ),
        ]
        retriever = HybridRetriever(vector_store=mock_vs, use_reranker=False)
        result = retriever.retrieve("Fz가 뭐야?", QueryType.ONTOLOGY)

        # ONTOLOGY는 top_n이 min(3, final_top_n)으로 제한됨
        assert result.metadata["query_type"].upper() == "ONTOLOGY"

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_retrieve_hybrid_query(self, mock_settings):
        """HYBRID 질문 검색"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=True, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.3),
        )
        mock_vs = Mock()
        mock_vs.search.return_value = [
            SearchResult(
                chunk_id="chunk_1",
                content="C153 원인입니다.",
                score=0.85,
                metadata={"source": "manual.pdf", "page": 10},
            ),
        ]
        retriever = HybridRetriever(vector_store=mock_vs, use_reranker=False)
        result = retriever.retrieve("C153 원인이 뭐야?", QueryType.HYBRID)

        assert result.metadata["query_type"].upper() == "HYBRID"


class TestHybridRetrieverFallback:
    """HybridRetriever 폴백 테스트"""

    @pytest.fixture
    def mock_vector_store_with_error(self):
        """리랭킹 실패하는 모의 VectorStore"""
        mock = Mock()
        mock.search_with_rerank.side_effect = Exception("Reranker error")
        mock.search.return_value = [
            SearchResult(
                chunk_id="chunk_1",
                content="기본 검색 결과",
                score=0.75,
                metadata={"source": "doc.pdf"},
            ),
        ]
        return mock

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_fallback_on_rerank_error(self, mock_settings, mock_vector_store_with_error):
        """리랭킹 실패 시 기본 검색으로 폴백"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=True, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.3),
        )

        retriever = HybridRetriever(
            vector_store=mock_vector_store_with_error,
            use_reranker=True
        )

        result = retriever.retrieve("테스트 쿼리", QueryType.RAG)

        # 폴백 발생: reranked=False
        assert result.reranked is False
        assert len(result.document_refs) > 0

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_basic_search_returns_reranked_false(self, mock_settings):
        """기본 검색은 reranked=False 반환"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=False, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.3),
        )
        mock_vs = Mock()
        mock_vs.search.return_value = [
            SearchResult(
                chunk_id="chunk_1",
                content="결과",
                score=0.8,
                metadata={"source": "doc.pdf"},
            ),
        ]

        retriever = HybridRetriever(vector_store=mock_vs, use_reranker=False)
        result = retriever.retrieve("테스트", QueryType.RAG)

        assert result.reranked is False


class TestHybridRetrieverThreshold:
    """HybridRetriever 임계값 필터링 테스트"""

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_threshold_filters_low_scores(self, mock_settings):
        """similarity_threshold 미만 결과는 필터링"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=False, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.8),  # 높은 임계값
        )
        mock_vs = Mock()
        mock_vs.search.return_value = [
            SearchResult(
                chunk_id="chunk_1",
                content="높은 점수",
                score=0.9,
                metadata={"source": "doc.pdf"},
            ),
            SearchResult(
                chunk_id="chunk_2",
                content="낮은 점수",
                score=0.7,  # 임계값 미만
                metadata={"source": "doc2.pdf"},
            ),
        ]

        retriever = HybridRetriever(vector_store=mock_vs, use_reranker=False)
        result = retriever.retrieve("테스트", QueryType.RAG)

        # 0.7 점수는 0.8 임계값 미만이므로 필터링됨
        assert len(result.document_refs) == 1
        assert result.document_refs[0].relevance == 0.9


class TestHybridRetrieverSearchForEntity:
    """HybridRetriever search_for_entity 테스트"""

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_search_for_error_code(self, mock_settings):
        """에러 코드 엔티티 검색"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=False, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.3),
        )
        mock_vs = Mock()
        mock_vs.search.return_value = [
            SearchResult(
                chunk_id="chunk_1",
                content="C153 해결 방법",
                score=0.85,
                metadata={"source": "manual.pdf"},
            ),
        ]

        retriever = HybridRetriever(vector_store=mock_vs, use_reranker=False)
        docs = retriever.search_for_entity("C153", "ErrorCode", top_k=3)

        assert len(docs) == 1
        # 에러 코드 쿼리 형식 확인
        mock_vs.search.assert_called_once()
        call_args = mock_vs.search.call_args
        assert "C153" in call_args.kwargs["query"]
        assert "에러" in call_args.kwargs["query"]

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_search_for_pattern(self, mock_settings):
        """패턴 엔티티 검색"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=False, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.3),
        )
        mock_vs = Mock()
        mock_vs.search.return_value = []

        retriever = HybridRetriever(vector_store=mock_vs, use_reranker=False)
        retriever.search_for_entity("PAT_COLLISION", "Pattern", top_k=5)

        call_args = mock_vs.search.call_args
        assert "PAT_COLLISION" in call_args.kwargs["query"]
        assert "패턴" in call_args.kwargs["query"]


class TestCreateHybridRetriever:
    """create_hybrid_retriever 팩토리 함수 테스트"""

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_create_with_default(self, mock_settings):
        """기본 설정으로 생성"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=True, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.7),
        )

        retriever = create_hybrid_retriever()

        assert isinstance(retriever, HybridRetriever)
        assert retriever.use_reranker is True

    @patch("src.rag.hybrid_retriever.get_settings")
    def test_create_with_reranker_false(self, mock_settings):
        """리랭커 비활성화로 생성"""
        mock_settings.return_value = Mock(
            rerank=Mock(enabled=True, initial_top_k=20, final_top_n=5),
            retrieval=Mock(similarity_threshold=0.7),
        )

        retriever = create_hybrid_retriever(use_reranker=False)

        assert retriever.use_reranker is False
