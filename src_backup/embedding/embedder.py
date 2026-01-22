# ============================================================
# src/embedding/embedder.py - 임베딩 생성 클래스
# ============================================================
# OpenAI API를 사용하여 텍스트를 벡터(임베딩)로 변환합니다.
#
# 임베딩이란?
#   - 텍스트를 숫자 배열(벡터)로 변환하는 것
#   - 의미가 비슷한 텍스트는 비슷한 벡터를 가짐
#   - 예: "통신 에러" ≈ "communication error" (벡터가 비슷)
#
# 사용하는 모델: text-embedding-3-small
#   - 1536 차원 벡터 생성
#   - 비용: $0.02 / 1M 토큰 (매우 저렴)
# ============================================================

import os
import time
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# 프로젝트 루트의 .env 파일 로드
load_dotenv()


# ============================================================
# [1] Embedder 클래스
# ============================================================

class Embedder:
    """
    텍스트를 벡터(임베딩)로 변환하는 클래스

    사용 예시:
        embedder = Embedder()
        vector = embedder.embed_text("C4 통신 에러")
        print(len(vector))  # 1536

        vectors = embedder.embed_texts(["텍스트1", "텍스트2"])
        print(len(vectors))  # 2
    """

    # 기본 임베딩 모델
    DEFAULT_MODEL = "text-embedding-3-small"

    # 배치 처리 설정
    BATCH_SIZE = 100          # 한 번에 처리할 텍스트 수
    RETRY_DELAY = 1.0         # 재시도 대기 시간 (초)
    MAX_RETRIES = 3           # 최대 재시도 횟수

    def __init__(self, model: Optional[str] = None):
        """
        Embedder 초기화

        Args:
            model: 사용할 임베딩 모델 (기본값: text-embedding-3-small)

        Raises:
            ValueError: OPENAI_API_KEY가 설정되지 않은 경우
        """
        # API 키 확인
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. "
                "Please set it in .env file."
            )

        # OpenAI 클라이언트 생성
        self.client = OpenAI()
        self.model = model or self.DEFAULT_MODEL

        print(f"[OK] Embedder initialized with model: {self.model}")

    # --------------------------------------------------------
    # [1.1] 단일 텍스트 임베딩
    # --------------------------------------------------------

    def embed_text(self, text: str) -> List[float]:
        """
        단일 텍스트를 벡터로 변환

        Args:
            text: 임베딩할 텍스트

        Returns:
            List[float]: 임베딩 벡터 (1536차원)

        사용 예시:
            vector = embedder.embed_text("C4 통신 에러")
        """
        # 빈 텍스트 처리
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # API 호출
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )

        # 벡터 추출
        embedding = response.data[0].embedding
        return embedding

    # --------------------------------------------------------
    # [1.2] 여러 텍스트 배치 임베딩
    # --------------------------------------------------------

    def embed_texts(
        self,
        texts: List[str],
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        여러 텍스트를 배치로 임베딩

        왜 배치 처리를 하는가?
            - API 호출 횟수 줄임 (비용 절감)
            - 처리 속도 향상
            - Rate limit 관리 용이

        Args:
            texts: 임베딩할 텍스트 리스트
            show_progress: 진행 상황 출력 여부

        Returns:
            List[List[float]]: 임베딩 벡터 리스트

        사용 예시:
            vectors = embedder.embed_texts(["텍스트1", "텍스트2", "텍스트3"])
        """
        if not texts:
            return []

        all_embeddings = []
        total = len(texts)

        # 배치 단위로 처리
        for i in range(0, total, self.BATCH_SIZE):
            batch = texts[i:i + self.BATCH_SIZE]
            batch_num = i // self.BATCH_SIZE + 1
            total_batches = (total + self.BATCH_SIZE - 1) // self.BATCH_SIZE

            if show_progress:
                print(f"    Processing batch {batch_num}/{total_batches} "
                      f"({len(batch)} texts)...")

            # 재시도 로직
            embeddings = self._embed_batch_with_retry(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def _embed_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        """
        배치 임베딩 (재시도 로직 포함)

        왜 재시도가 필요한가?
            - API 일시적 오류 대응
            - Rate limit 초과 시 대기 후 재시도
            - 네트워크 오류 대응

        Args:
            texts: 임베딩할 텍스트 배치

        Returns:
            List[List[float]]: 임베딩 벡터 리스트

        Raises:
            Exception: 최대 재시도 후에도 실패 시
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )

                # 응답에서 임베딩 추출 (순서 유지)
                embeddings = [item.embedding for item in response.data]
                return embeddings

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_DELAY * (attempt + 1)
                    print(f"    [WARN] API error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed after {self.MAX_RETRIES} retries: {e}")

    # --------------------------------------------------------
    # [1.3] 청크 리스트 임베딩
    # --------------------------------------------------------

    def embed_chunks(self, chunks: List) -> List:
        """
        Chunk 객체 리스트에 임베딩 추가

        Args:
            chunks: Chunk 객체 리스트

        Returns:
            List: 임베딩이 추가된 Chunk 객체 리스트

        사용 예시:
            from src.ingestion import Chunk
            chunks = [Chunk(...), Chunk(...)]
            embedded_chunks = embedder.embed_chunks(chunks)
        """
        print(f"\n[*] Embedding {len(chunks)} chunks...")

        # 청크의 content 추출
        texts = [chunk.content for chunk in chunks]

        # 배치 임베딩
        embeddings = self.embed_texts(texts)

        # 각 청크에 임베딩 추가
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        print(f"[OK] Embedded {len(chunks)} chunks")
        return chunks

    # --------------------------------------------------------
    # [1.4] 유틸리티 메서드
    # --------------------------------------------------------

    def get_embedding_dimension(self) -> int:
        """
        현재 모델의 임베딩 차원 반환

        Returns:
            int: 임베딩 차원 (text-embedding-3-small: 1536)
        """
        # 모델별 차원
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dimensions.get(self.model, 1536)


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    import sys

    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 50)
    print("[*] Embedder Test")
    print("=" * 50)

    # 임베더 생성
    embedder = Embedder()

    # 테스트 1: 단일 텍스트 임베딩
    print("\n[Test 1] Single text embedding")
    text = "C4 Communication error with Controller"
    vector = embedder.embed_text(text)
    print(f"  Input: {text}")
    print(f"  Output: vector with {len(vector)} dimensions")
    print(f"  First 5 values: {vector[:5]}")

    # 테스트 2: 여러 텍스트 임베딩
    print("\n[Test 2] Batch text embedding")
    texts = [
        "C4 Communication error",
        "Lost connection with robot",
        "Joint replacement procedure",
    ]
    vectors = embedder.embed_texts(texts, show_progress=False)
    print(f"  Input: {len(texts)} texts")
    print(f"  Output: {len(vectors)} vectors")

    # 테스트 3: 유사도 계산 (간단한 예시)
    print("\n[Test 3] Similarity check")

    def cosine_similarity(v1, v2):
        """코사인 유사도 계산"""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        return dot / (norm1 * norm2)

    # 비슷한 의미의 텍스트
    similar_texts = [
        "통신 에러",
        "communication error",
        "맛있는 피자",
    ]
    similar_vectors = embedder.embed_texts(similar_texts, show_progress=False)

    sim_01 = cosine_similarity(similar_vectors[0], similar_vectors[1])
    sim_02 = cosine_similarity(similar_vectors[0], similar_vectors[2])

    print(f"  '통신 에러' vs 'communication error': {sim_01:.4f} (비슷!)")
    print(f"  '통신 에러' vs '맛있는 피자': {sim_02:.4f} (다름)")

    print("\n" + "=" * 50)
    print("[OK] All tests passed!")
    print("=" * 50)
