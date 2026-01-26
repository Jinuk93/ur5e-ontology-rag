"""
Cross-Encoder 기반 리랭커 모듈

벡터 검색 결과를 재정렬하여 검색 품질을 향상시킵니다.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    """리랭킹 결과"""
    content: str
    original_score: float
    rerank_score: float
    metadata: dict
    chunk_id: str


class CrossEncoderReranker:
    """Cross-Encoder 기반 리랭커

    Bi-encoder(임베딩)보다 정확하지만 느린 Cross-Encoder를 사용하여
    검색 결과를 재정렬합니다.

    파이프라인:
    Query → Embedding → Top-K(20) → Reranker → Top-N(5) → LLM
    """

    # 지원 모델 목록
    SUPPORTED_MODELS = {
        "ms-marco-MiniLM-L-6-v2": "cross-encoder/ms-marco-MiniLM-L-6-v2",  # 빠름, 영어
        "ms-marco-MiniLM-L-12-v2": "cross-encoder/ms-marco-MiniLM-L-12-v2",  # 균형
        "bge-reranker-base": "BAAI/bge-reranker-base",  # 다국어 지원
        "bge-reranker-large": "BAAI/bge-reranker-large",  # 고품질, 다국어
    }

    DEFAULT_MODEL = "bge-reranker-base"  # 한국어 지원

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: int = 32,
    ):
        """
        리랭커 초기화

        Args:
            model_name: 모델 이름 (기본: bge-reranker-base)
            device: 디바이스 (cuda/cpu, 기본: 자동 감지)
            batch_size: 배치 크기
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.batch_size = batch_size
        self._model = None
        self._device = device

        # 모델 경로 확인
        if self.model_name in self.SUPPORTED_MODELS:
            self._model_path = self.SUPPORTED_MODELS[self.model_name]
        else:
            self._model_path = self.model_name

        logger.info(f"리랭커 초기화: model={self.model_name}")

    @property
    def model(self):
        """모델 지연 로딩"""
        if self._model is None:
            self._load_model()
        return self._model

    def preload(self) -> "CrossEncoderReranker":
        """모델 사전 로딩 (서버 시작 시 호출)

        Returns:
            self (체이닝용)
        """
        if self._model is None:
            logger.info("리랭커 모델 사전 로딩 시작...")
            self._load_model()
            logger.info("리랭커 모델 사전 로딩 완료")
        return self

    def is_loaded(self) -> bool:
        """모델이 로드되었는지 확인"""
        return self._model is not None

    def _load_model(self):
        """모델 로드"""
        try:
            from sentence_transformers import CrossEncoder
            import torch

            # 디바이스 설정
            if self._device is None:
                self._device = "cuda" if torch.cuda.is_available() else "cpu"

            logger.info(f"Cross-Encoder 모델 로딩: {self._model_path} (device={self._device})")

            self._model = CrossEncoder(
                self._model_path,
                max_length=512,
                device=self._device,
            )

            logger.info(f"Cross-Encoder 모델 로드 완료")

        except ImportError:
            raise ImportError(
                "sentence-transformers가 필요합니다. "
                "설치: pip install sentence-transformers"
            )

    def rerank(
        self,
        query: str,
        documents: List[Tuple[str, float, dict, str]],  # (content, score, metadata, chunk_id)
        top_n: Optional[int] = None,
    ) -> List[RerankResult]:
        """
        문서 리랭킹

        Args:
            query: 검색 쿼리
            documents: (내용, 원본점수, 메타데이터, chunk_id) 튜플 리스트
            top_n: 반환할 결과 수 (기본: 전체)

        Returns:
            RerankResult 리스트 (rerank_score 기준 내림차순)
        """
        if not documents:
            return []

        # Cross-Encoder 입력 준비: (query, document) 쌍
        pairs = [(query, doc[0]) for doc in documents]

        # 점수 계산
        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )

        # 결과 생성
        results = []
        for i, (content, orig_score, metadata, chunk_id) in enumerate(documents):
            results.append(RerankResult(
                content=content,
                original_score=orig_score,
                rerank_score=float(scores[i]),
                metadata=metadata,
                chunk_id=chunk_id,
            ))

        # rerank_score 기준 정렬
        results.sort(key=lambda x: x.rerank_score, reverse=True)

        # top_n 적용
        if top_n is not None:
            results = results[:top_n]

        logger.debug(
            f"리랭킹 완료: query='{query[:30]}...', "
            f"입력={len(documents)}개, 출력={len(results)}개"
        )

        return results

    def rerank_search_results(
        self,
        query: str,
        search_results: List,  # List[SearchResult]
        top_n: Optional[int] = None,
    ) -> List:
        """
        SearchResult 리스트 리랭킹 (편의 메서드)

        Args:
            query: 검색 쿼리
            search_results: VectorStore.search() 결과
            top_n: 반환할 결과 수

        Returns:
            리랭킹된 SearchResult 리스트
        """
        from .vector_store import SearchResult

        if not search_results:
            return []

        # SearchResult → 튜플 변환
        documents = [
            (r.content, r.score, r.metadata, r.chunk_id)
            for r in search_results
        ]

        # 리랭킹
        reranked = self.rerank(query, documents, top_n)

        # RerankResult → SearchResult 변환 (점수는 rerank_score로 대체)
        return [
            SearchResult(
                chunk_id=r.chunk_id,
                content=r.content,
                metadata=r.metadata,
                score=r.rerank_score,  # rerank 점수 사용
            )
            for r in reranked
        ]


# 전역 인스턴스 (싱글톤 패턴)
_reranker_instance: Optional[CrossEncoderReranker] = None


def get_reranker(
    model_name: Optional[str] = None,
    force_new: bool = False,
) -> CrossEncoderReranker:
    """
    리랭커 인스턴스 반환 (싱글톤)

    Args:
        model_name: 모델 이름
        force_new: 새 인스턴스 강제 생성

    Returns:
        CrossEncoderReranker 인스턴스
    """
    global _reranker_instance

    if _reranker_instance is None or force_new:
        _reranker_instance = CrossEncoderReranker(model_name=model_name)

    return _reranker_instance
