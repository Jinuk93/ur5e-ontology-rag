"""
OpenAI 임베딩 생성 모듈

텍스트를 벡터로 변환합니다.
"""

import logging
import time
from typing import List, Optional

from openai import OpenAI

from src.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """OpenAI 임베딩 생성기"""

    def __init__(
        self,
        model: Optional[str] = None,
        batch_size: Optional[int] = None,
    ):
        """
        임베딩 생성기 초기화

        Args:
            model: 임베딩 모델명 (기본: settings.embedding.model)
            batch_size: 배치 크기 (기본: settings.embedding.batch_size)
        """
        settings = get_settings()
        self.model = model or settings.embedding.model
        self.batch_size = batch_size or settings.embedding.batch_size

        # OpenAI 클라이언트 초기화
        self.client = OpenAI(api_key=settings.openai_api_key)

        logger.info(f"임베딩 생성기 초기화: model={self.model}, batch_size={self.batch_size}")

    def embed_text(self, text: str) -> List[float]:
        """
        단일 텍스트 임베딩

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (1536 차원)
        """
        if not text.strip():
            raise ValueError("빈 텍스트는 임베딩할 수 없습니다")

        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )

        return response.data[0].embedding

    def embed_texts(
        self,
        texts: List[str],
        show_progress: bool = True,
    ) -> List[List[float]]:
        """
        다중 텍스트 임베딩 (배치 처리)

        Args:
            texts: 텍스트 리스트
            show_progress: 진행률 표시 여부

        Returns:
            임베딩 벡터 리스트
        """
        if not texts:
            return []

        all_embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1

            if show_progress:
                logger.info(f"배치 {batch_num}/{total_batches} 처리 중 ({len(batch_texts)}개)")

            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch_texts,
                )

                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"배치 {batch_num} 임베딩 실패: {e}")
                # Rate limit 대응: 재시도
                if "rate_limit" in str(e).lower():
                    logger.info("Rate limit 감지, 60초 대기 후 재시도...")
                    time.sleep(60)
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=batch_texts,
                    )
                    batch_embeddings = [data.embedding for data in response.data]
                    all_embeddings.extend(batch_embeddings)
                else:
                    raise

            # Rate limit 방지를 위한 짧은 대기
            if i + self.batch_size < len(texts):
                time.sleep(0.5)

        logger.info(f"임베딩 완료: {len(all_embeddings)}개")
        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """
        검색 쿼리 임베딩

        Args:
            query: 검색 쿼리

        Returns:
            임베딩 벡터
        """
        return self.embed_text(query)

    @property
    def dimension(self) -> int:
        """임베딩 차원 반환"""
        # text-embedding-3-small: 1536
        # text-embedding-3-large: 3072
        if "small" in self.model:
            return 1536
        elif "large" in self.model:
            return 3072
        else:
            return 1536  # 기본값


def create_embeddings(
    texts: List[str],
    model: Optional[str] = None,
    batch_size: Optional[int] = None,
) -> List[List[float]]:
    """
    텍스트 리스트 임베딩 생성 (편의 함수)

    Args:
        texts: 텍스트 리스트
        model: 임베딩 모델
        batch_size: 배치 크기

    Returns:
        임베딩 벡터 리스트
    """
    embedder = OpenAIEmbedder(model=model, batch_size=batch_size)
    return embedder.embed_texts(texts)
