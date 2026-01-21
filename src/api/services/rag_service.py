# ============================================================
# src/api/services/rag_service.py - RAG 서비스
# ============================================================
# API에서 RAG 파이프라인을 사용하기 위한 서비스 래퍼
# ============================================================

import os
import sys
import time
from typing import Optional, Dict, Any, List

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.rag.hybrid_retriever import HybridRetriever
from src.rag.verifier import Verifier, VerificationStatus
from src.rag.prompt_builder import PromptBuilder
from src.rag.generator import Generator
from src.rag.retriever import RetrievalResult
from src.api.schemas.response import (
    QueryResponse,
    AnalyzeResponse,
    SearchResponse,
    VerificationInfo,
    SourceInfo,
    SearchResult,
    VerificationStatusEnum,
)


class RAGService:
    """
    RAG 서비스 (Singleton)

    API에서 RAG 파이프라인을 사용하기 위한 서비스 클래스.
    Phase 7 RAG 파이프라인을 래핑하여 API 친화적인 인터페이스 제공.

    사용 예시:
        service = RAGService()
        response = service.query("C4A15 에러 해결법")
        print(response.answer)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        print("[*] Initializing RAG Service...")

        self.hybrid_retriever = HybridRetriever(verbose=False)
        self.verifier = Verifier()
        self.prompt_builder = PromptBuilder()
        self.generator = Generator()

        self._initialized = True
        print("[OK] RAG Service initialized")

    # --------------------------------------------------------
    # [1] RAG 질의
    # --------------------------------------------------------

    def query(
        self,
        question: str,
        top_k: int = 5,
        include_sources: bool = True,
        include_citation: bool = True,
    ) -> QueryResponse:
        """
        RAG 질의 실행

        Args:
            question: 사용자 질문
            top_k: 검색 결과 수
            include_sources: 출처 정보 포함 여부
            include_citation: 인용 정보 포함 여부

        Returns:
            QueryResponse: 질의 응답
        """
        start_time = time.time()

        # 1. 하이브리드 검색
        hybrid_results, analysis = self.hybrid_retriever.retrieve(
            question, top_k=top_k
        )

        # 2. 사전 검증
        pre_verification = self.verifier.verify_before_generation(
            analysis, hybrid_results
        )

        # 검증 실패 시 안전 응답
        if not pre_verification.is_safe_to_answer:
            safe_response = self.verifier.get_safe_response(
                pre_verification, analysis
            )
            return QueryResponse(
                answer=safe_response,
                verification=VerificationInfo(
                    status=VerificationStatusEnum(pre_verification.status.value),
                    confidence=pre_verification.confidence,
                    evidence_count=pre_verification.evidence_count,
                    warnings=pre_verification.warnings
                ),
                sources=None,
                query_analysis=self._to_analysis_dict(analysis),
                latency_ms=(time.time() - start_time) * 1000
            )

        # 3. 컨텍스트 변환
        contexts = self._convert_contexts(hybrid_results)

        # 4. LLM 생성
        messages = self.prompt_builder.build(question, contexts)
        result = self.generator.generate(messages)
        answer = result.answer

        # 5. 사후 검증
        post_verification = self.verifier.verify_after_generation(
            answer, hybrid_results, analysis
        )

        # 6. 경고/출처 추가
        if post_verification.status == VerificationStatus.PARTIAL:
            if post_verification.warnings:
                answer = self.verifier.add_warning(answer, post_verification)

        if include_citation:
            answer = self.verifier.add_citation(answer, post_verification)

        # 출처 정보 구성
        sources = None
        if include_sources:
            sources = [
                SourceInfo(
                    name=hr.metadata.get("entity_name", hr.metadata.get("chunk_id", "unknown")),
                    type=hr.source_type,
                    score=hr.score
                )
                for hr in hybrid_results[:5]
            ]

        return QueryResponse(
            answer=answer,
            verification=VerificationInfo(
                status=VerificationStatusEnum(post_verification.status.value),
                confidence=post_verification.confidence,
                evidence_count=post_verification.evidence_count,
                warnings=post_verification.warnings
            ),
            sources=sources,
            query_analysis=self._to_analysis_dict(analysis),
            latency_ms=(time.time() - start_time) * 1000
        )

    # --------------------------------------------------------
    # [2] 질문 분석
    # --------------------------------------------------------

    def analyze(self, question: str) -> AnalyzeResponse:
        """
        질문 분석만 수행

        Args:
            question: 분석할 질문

        Returns:
            AnalyzeResponse: 분석 결과
        """
        analysis = self.hybrid_retriever.query_analyzer.analyze(question)
        return AnalyzeResponse(
            original_query=analysis.original_query,
            error_codes=analysis.error_codes,
            components=analysis.components,
            query_type=analysis.query_type,
            search_strategy=analysis.search_strategy
        )

    # --------------------------------------------------------
    # [3] 검색
    # --------------------------------------------------------

    def search(
        self,
        question: str,
        top_k: int = 5,
        strategy: Optional[str] = None,
    ) -> SearchResponse:
        """
        검색만 수행 (LLM 생성 없이)

        Args:
            question: 검색 질문
            top_k: 검색 결과 수
            strategy: 검색 전략 (옵션)

        Returns:
            SearchResponse: 검색 결과
        """
        start_time = time.time()

        hybrid_results, analysis = self.hybrid_retriever.retrieve(
            question, top_k=top_k, strategy=strategy
        )

        results = [
            SearchResult(
                content=hr.content[:500],  # 미리보기용 500자
                source_type=hr.source_type,
                score=hr.score,
                metadata=hr.metadata
            )
            for hr in hybrid_results
        ]

        return SearchResponse(
            results=results,
            query_analysis=AnalyzeResponse(
                original_query=analysis.original_query,
                error_codes=analysis.error_codes,
                components=analysis.components,
                query_type=analysis.query_type,
                search_strategy=analysis.search_strategy
            ),
            total_count=len(results),
            latency_ms=(time.time() - start_time) * 1000
        )

    # --------------------------------------------------------
    # [4] 유틸리티
    # --------------------------------------------------------

    def _convert_contexts(self, hybrid_results) -> List[RetrievalResult]:
        """HybridResult를 RetrievalResult로 변환"""
        contexts = []
        for hr in hybrid_results:
            metadata = hr.metadata.copy()
            if hr.source_type == "graph":
                metadata["doc_type"] = "graph_result"
                metadata["source"] = "GraphDB (Neo4j)"
            else:
                metadata.setdefault("doc_type", "vector_result")
                metadata.setdefault("source", "VectorDB (ChromaDB)")

            contexts.append(RetrievalResult(
                chunk_id=metadata.get("chunk_id", f"graph_{hr.metadata.get('entity_name', 'unknown')}"),
                content=hr.content,
                metadata=metadata,
                score=hr.score,
            ))
        return contexts

    def _to_analysis_dict(self, analysis) -> Dict[str, Any]:
        """QueryAnalysis를 dict로 변환"""
        return {
            "error_codes": analysis.error_codes,
            "components": analysis.components,
            "query_type": analysis.query_type,
            "search_strategy": analysis.search_strategy
        }

    def close(self):
        """리소스 정리"""
        if hasattr(self, 'hybrid_retriever'):
            self.hybrid_retriever.close()
        print("[OK] RAG Service closed")

    def get_health_status(self) -> Dict[str, str]:
        """컴포넌트 상태 확인"""
        status = {}

        # VectorDB 상태
        try:
            if self.hybrid_retriever.vector_retriever:
                status["vectordb"] = "connected"
            else:
                status["vectordb"] = "disconnected"
        except Exception:
            status["vectordb"] = "error"

        # GraphDB 상태
        try:
            if self.hybrid_retriever.graph_retriever:
                status["graphdb"] = "connected"
            else:
                status["graphdb"] = "disconnected"
        except Exception:
            status["graphdb"] = "error"

        # LLM 상태
        try:
            if self.generator:
                status["llm"] = "available"
            else:
                status["llm"] = "unavailable"
        except Exception:
            status["llm"] = "error"

        return status
