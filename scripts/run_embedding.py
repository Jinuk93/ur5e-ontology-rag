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
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.ingestion.models import load_chunks_from_json
from src.embedding.embedder import Embedder
from src.embedding.vector_store import VectorStore


# ============================================================
# [1] 설정
# ============================================================

# 경로 설정
CHUNKS_DIR = os.path.join(project_root, "data", "processed", "chunks")

# 청크 파일 목록
CHUNK_FILES = [
    "error_codes_chunks.json",
    "service_manual_chunks.json",
    "user_manual_chunks.json",
]

# ChromaDB 컬렉션 이름
COLLECTION_NAME = "ur5e_chunks"


# ============================================================
# [2] 메인 함수
# ============================================================

def run_embedding():
    """
    임베딩 파이프라인 실행

    처리 흐름:
        1. JSON에서 청크 로드
        2. 임베딩 생성
        3. ChromaDB에 저장
        4. 결과 요약
    """
    print("=" * 60)
    print("[*] UR5e Ontology RAG - Embedding Pipeline")
    print(f"    Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # --------------------------------------------------------
    # Step 1: 청크 로드
    # --------------------------------------------------------
    print(f"\n[Step 1] Loading chunks from: {CHUNKS_DIR}")
    print("-" * 40)

    all_chunks = []

    for filename in CHUNK_FILES:
        filepath = os.path.join(CHUNKS_DIR, filename)
        if os.path.exists(filepath):
            chunks = load_chunks_from_json(filepath)
            all_chunks.extend(chunks)
        else:
            print(f"[WARN] File not found: {filename}")

    print(f"\nTotal chunks loaded: {len(all_chunks)}")

    if not all_chunks:
        print("[ERROR] No chunks to process!")
        return

    # --------------------------------------------------------
    # Step 2: 임베더 초기화
    # --------------------------------------------------------
    print(f"\n[Step 2] Initializing Embedder")
    print("-" * 40)

    embedder = Embedder()

    # --------------------------------------------------------
    # Step 3: VectorStore 초기화
    # --------------------------------------------------------
    print(f"\n[Step 3] Initializing VectorStore")
    print("-" * 40)

    store = VectorStore(collection_name=COLLECTION_NAME)

    # 기존 데이터 확인
    existing_count = store.count()
    if existing_count > 0:
        print(f"    [INFO] Collection already has {existing_count} items")
        print(f"    [INFO] Will update/add new chunks")

    # --------------------------------------------------------
    # Step 4: 임베딩 생성 및 저장
    # --------------------------------------------------------
    print(f"\n[Step 4] Generating embeddings and storing")
    print("-" * 40)

    # 청크 추가 (임베딩 자동 생성)
    added_count = store.add_chunks(all_chunks, embedder=embedder)

    # --------------------------------------------------------
    # Step 5: 결과 요약
    # --------------------------------------------------------
    print(f"\n[Step 5] Summary")
    print("=" * 60)

    # 문서 유형별 통계
    doc_type_counts = {}
    for chunk in all_chunks:
        doc_type = chunk.metadata.doc_type
        doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1

    print("\n{:<25} {:>10}".format("Document Type", "Chunks"))
    print("-" * 40)
    for doc_type, count in sorted(doc_type_counts.items()):
        print("{:<25} {:>10,}".format(doc_type, count))
    print("-" * 40)
    print("{:<25} {:>10,}".format("TOTAL", len(all_chunks)))

    print("\n" + "=" * 60)
    print(f"[OK] Embedding complete!")
    print(f"     Collection: {COLLECTION_NAME}")
    print(f"     Total items: {store.count()}")
    print(f"     Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return store


# ============================================================
# [3] 검색 테스트 함수
# ============================================================

def test_search(store: VectorStore):
    """
    임베딩 후 검색 테스트

    Args:
        store: VectorStore 객체
    """
    print("\n" + "=" * 60)
    print("[*] Search Test")
    print("=" * 60)

    embedder = Embedder()

    # 테스트 쿼리들
    test_queries = [
        ("통신 에러가 발생했어요", None),
        ("로봇 조인트 교체 방법", None),
        ("C4 에러 해결법", {"doc_type": "error_code"}),
        ("Control Box 분해", {"doc_type": "service_manual"}),
    ]

    for query, filter_condition in test_queries:
        print(f"\n[Query] {query}")
        if filter_condition:
            print(f"        Filter: {filter_condition}")

        results = store.search(
            query,
            top_k=3,
            where=filter_condition,
            embedder=embedder
        )

        print(f"[Results] Top 3:")
        for i, r in enumerate(results, 1):
            score = r['score']
            chunk_id = r['id']
            content_preview = r['content'][:60].replace('\n', ' ')
            print(f"    {i}. [{score:.4f}] {chunk_id}")
            print(f"       {content_preview}...")


# ============================================================
# [4] 실행
# ============================================================

if __name__ == "__main__":
    # 임베딩 실행
    store = run_embedding()

    # 검색 테스트
    if store:
        test_search(store)
