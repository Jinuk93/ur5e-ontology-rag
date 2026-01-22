#!/usr/bin/env python
# ============================================================
# scripts/run_embedding.py - 임베딩 파이프라인 실행
# ============================================================
# 실행 방법: python scripts/run_embedding.py
#
# 전체 파이프라인:
#   1. data/processed/chunks/*.json 에서 청크 로드
#   2. OpenAI API로 임베딩 생성
#   3. ChromaDB에 저장 (stores/chroma/)
#
# 예상 비용: 722 청크 × ~200 토큰 = 약 $0.003 (4원)
# ============================================================

import sys
import os
import logging
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from src.ingestion import load_all_chunks
from src.embedding import VectorStore, OpenAIEmbedder


def run_embedding(force: bool = False):
    """
    임베딩 파이프라인 실행

    Args:
        force: True면 기존 컬렉션 삭제 후 재생성

    처리 흐름:
        1. JSON에서 청크 로드
        2. ChromaDB 초기화
        3. 임베딩 생성 및 저장
        4. 결과 요약
    """
    print("=" * 60)
    print("[*] UR5e Ontology RAG - Embedding Pipeline")
    print(f"    Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # --------------------------------------------------------
    # Step 1: 청크 로드
    # --------------------------------------------------------
    print(f"\n[Step 1] Loading chunks from data/processed/chunks/")
    print("-" * 40)

    chunks = load_all_chunks()
    print(f"Total chunks loaded: {len(chunks)}")

    if not chunks:
        print("[ERROR] No chunks to process!")
        return None

    # 문서 유형별 통계
    doc_type_counts = {}
    for chunk in chunks:
        doc_type = chunk.metadata.doc_type
        doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1

    print("\n{:<25} {:>10}".format("Document Type", "Chunks"))
    print("-" * 40)
    for doc_type, count in sorted(doc_type_counts.items()):
        print("{:<25} {:>10,}".format(doc_type, count))
    print("-" * 40)
    print("{:<25} {:>10,}".format("TOTAL", len(chunks)))

    # --------------------------------------------------------
    # Step 2: VectorStore 초기화
    # --------------------------------------------------------
    print(f"\n[Step 2] Initializing VectorStore")
    print("-" * 40)

    store = VectorStore()

    # 기존 데이터 확인
    stats = store.get_collection_stats()
    existing_count = stats["count"]

    if existing_count > 0:
        print(f"    [INFO] Collection already has {existing_count} items")
        if force:
            print(f"    [INFO] Clearing collection (--force)")
            store.clear()
        else:
            print(f"    [INFO] Will update/add new chunks only")

    # --------------------------------------------------------
    # Step 3: 임베딩 생성 및 저장
    # --------------------------------------------------------
    print(f"\n[Step 3] Generating embeddings and storing")
    print("-" * 40)

    store.add_documents(chunks, show_progress=True)

    # --------------------------------------------------------
    # Step 4: 결과 요약
    # --------------------------------------------------------
    print(f"\n[Step 4] Summary")
    print("=" * 60)

    final_stats = store.get_collection_stats()

    print(f"\nCollection: {final_stats['collection_name']}")
    print(f"Total items: {final_stats['count']}")
    print(f"Persist directory: {final_stats['persist_directory']}")

    print("\nDocument type distribution:")
    for doc_type, count in final_stats["doc_type_distribution"].items():
        print(f"  - {doc_type}: {count}")

    print("\n" + "=" * 60)
    print(f"[OK] Embedding complete!")
    print(f"     Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return store


def test_search(store: VectorStore):
    """
    임베딩 후 검색 테스트

    Args:
        store: VectorStore 객체
    """
    print("\n" + "=" * 60)
    print("[*] Search Test")
    print("=" * 60)

    # 테스트 쿼리들
    test_queries = [
        ("C153 에러 해결 방법", None),
        ("UR5e 페이로드가 몇 kg?", None),
        ("조인트 토크 사양", {"doc_type": "user_manual"}),
        ("에러 코드 C189", {"doc_type": "error_codes"}),
    ]

    for query, filter_condition in test_queries:
        print(f"\n[Query] {query}")
        if filter_condition:
            print(f"        Filter: {filter_condition}")

        results = store.search(query, top_k=3, filter_metadata=filter_condition)

        print(f"[Results] Top {len(results)}:")
        for i, r in enumerate(results, 1):
            content_preview = r.content[:60].replace("\n", " ")
            print(f"    {i}. [score={r.score:.4f}] {r.chunk_id}")
            print(f"       {content_preview}...")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="UR5e Ontology RAG - Embedding Pipeline")
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 컬렉션 삭제 후 재생성",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="임베딩 없이 검색 테스트만 실행",
    )
    args = parser.parse_args()

    if args.test_only:
        store = VectorStore()
        stats = store.get_collection_stats()
        if stats["count"] == 0:
            print("[ERROR] No embeddings found. Run without --test-only first.")
            return
        test_search(store)
    else:
        store = run_embedding(force=args.force)
        if store:
            test_search(store)


if __name__ == "__main__":
    main()
