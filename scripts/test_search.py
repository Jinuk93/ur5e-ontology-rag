# 검색 테스트 스크립트
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.embedding.embedder import Embedder
from src.embedding.vector_store import VectorStore

store = VectorStore(collection_name='ur5e_chunks')
embedder = Embedder()

# 여러 쿼리 테스트
queries = [
    "C4 에러 해결법",
    "로봇 설치 방법",
    "조인트 교체",
]

for query in queries:
    print("=" * 60)
    print(f"[Query] '{query}' - 필터 없이 전체 검색")
    print("=" * 60)

    results = store.search(query, top_k=3, embedder=embedder)

    for i, r in enumerate(results, 1):
        doc_type = r['metadata'].get('doc_type', 'unknown')
        score = r['score']
        chunk_id = r['id']
        content = r['content'][:60].replace('\n', ' ')

        print(f"{i}. [{score:.4f}] [{doc_type}] {chunk_id}")
        print(f"   {content}...")
    print()
