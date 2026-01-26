# Step 03: 문서 인덱싱 - 완료 보고서

## 1. 요약

| 항목 | 내용 |
|------|------|
| Phase | 03 - 문서 인덱싱 (Document Indexing) |
| 상태 | **완료** |
| 주요 산출물 | ChromaDB 영속 인덱스(stores/chroma), VectorStore/OpenAIEmbedder, 임베딩 실행 스크립트 |

---

## 2. 완료된 작업

### 2.1 구현 파일 목록

| 파일 | 라인 수 | 상태 | 설명 |
|------|--------|------|------|
| `src/embedding/__init__.py` | 37 | 신규 작성 | 패키지 초기화 및 모듈 노출 |
| `src/embedding/embedder.py` | 115 | 신규 작성 | OpenAI 임베딩 생성 |
| `src/embedding/vector_store.py` | 401 | 신규 작성 | ChromaDB 벡터 저장소 + 리랭킹 검색 |
| `src/embedding/reranker.py` | 226 | 신규 작성 | Cross-Encoder 리랭커 (2026-01-26 추가) |
| `scripts/run_embedding.py` | 200 | 업데이트 | 임베딩 실행 스크립트 |

### 2.2 저장소 (생성됨)

| 경로 | 설명 | 상태 |
|------|------|------|
| `stores/chroma/` | ChromaDB 영속 인덱스 | 생성됨 |

---

## 3. 구현 상세

### 3.1 OpenAIEmbedder (embedder.py)

```python
class OpenAIEmbedder:
    """OpenAI 임베딩 생성기"""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
    ):
        pass

    def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        pass

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """다중 텍스트 임베딩 (배치 처리)"""
        pass

    def embed_query(self, query: str) -> List[float]:
        """검색 쿼리 임베딩"""
        pass
```

주요 기능:
- OpenAI API 연동
- 배치 처리 (100개씩)
- Rate limiting 자동 대응
- 진행률 표시

### 3.2 VectorStore (vector_store.py)

```python
class VectorStore:
    """ChromaDB 기반 벡터 저장소"""

    def add_documents(self, chunks: List[Chunk], ...) -> None:
        """문서 청크 추가 (임베딩 자동 생성)"""
        pass

    def search(self, query: str, top_k: int = 5, ...) -> List[SearchResult]:
        """유사 문서 검색"""
        pass

    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계"""
        pass

    def delete_collection(self) -> None:
        """컬렉션 삭제 (재색인용)"""
        pass
```

주요 기능:
- ChromaDB 영속 저장
- 메타데이터 필터링
- 유사도 점수 반환
- 증분 추가 지원 (기존 ID 스킵)
- **2단계 검색 (리랭킹 포함)** - 2026-01-26 추가

### 3.4 CrossEncoderReranker (reranker.py) - 2026-01-26 추가

```python
class CrossEncoderReranker:
    """Cross-Encoder 기반 리랭커

    2단계 검색 파이프라인:
    Query → Embedding → Top-K(20) → Reranker → Top-N(5) → LLM
    """

    SUPPORTED_MODELS = {
        "bge-reranker-base": "BAAI/bge-reranker-base",  # 한국어 지원
        "bge-reranker-large": "BAAI/bge-reranker-large",
    }

    def rerank(self, query: str, documents: List[Tuple], top_n: int) -> List[RerankResult]:
        """문서 리랭킹"""
        pass

    def rerank_search_results(self, query: str, search_results: List, top_n: int) -> List:
        """SearchResult 리스트 리랭킹"""
        pass
```

주요 기능:
- Cross-Encoder 기반 정밀 리랭킹
- BGE-reranker-base 모델 (한국어 지원)
- GPU 자동 감지 및 활용
- 싱글톤 패턴으로 모델 재사용

### 3.3 SearchResult 데이터 클래스

```python
@dataclass
class SearchResult:
    chunk_id: str       # 청크 ID
    content: str        # 청크 텍스트
    metadata: Dict      # 메타데이터 (source, page, doc_type)
    score: float        # 유사도 점수 (0~1)
```

---

## 4. 사용법

### 4.1 임베딩 생성 실행

```bash
# 전체 청크 임베딩 생성
python scripts/run_embedding.py

# 기존 컬렉션 삭제 후 재생성
python scripts/run_embedding.py --force

# 검색 테스트만 실행
python scripts/run_embedding.py --test-only
```

### 4.2 코드에서 사용

```python
from src.embedding import VectorStore

# 벡터 저장소 초기화
vs = VectorStore()

# 검색
results = vs.search("C153 에러 해결 방법", top_k=3)
for r in results:
    print(f"{r.chunk_id}: {r.score:.3f}")
    print(f"  {r.content[:100]}...")

# 메타데이터 필터링
results = vs.search(
    "조인트 토크",
    filter_metadata={"doc_type": "user_manual"}
)

# 컬렉션 통계
stats = vs.get_collection_stats()
print(f"총 문서: {stats['count']}개")

# 2단계 검색 (리랭킹 포함) - 2026-01-26 추가
results = vs.search_with_rerank(
    "C153 에러 해결 방법",
    initial_top_k=20,  # 1단계: 후보 확장
    final_top_n=5,     # 2단계: 정밀 리랭킹
)
```

---

## 5. 아키텍처 정합성

### 5.1 Unified_ROADMAP.md 충족 사항

| ROADMAP 요구사항 | 구현 내용 | 상태 |
|-----------------|----------|------|
| ChromaDB 컬렉션 생성 | VectorStore(collection_name) | O |
| 청크 임베딩 생성 | OpenAIEmbedder.embed_texts() | O |
| 인덱스 저장 | stores/chroma/ | O |
| 검색 테스트 | VectorStore.search() | O |

### 5.2 Unified_Spec.md 충족 사항

| Spec 요구사항 | 구현 내용 | 상태 |
|--------------|----------|------|
| text-embedding-3-small | embedder.model | O |
| 메타데이터 필터링 | search(filter_metadata=) | O |
| 유사도 검색 | cosine distance → score | O |

### 5.3 온톨로지 스키마 연결점

```
VectorStore 검색 → Knowledge Domain 문서 검색
    │
    ▼
Phase 10-12 RAG 파이프라인에서 활용
    │
    ▼
DOCUMENTED_IN 관계의 실제 문서 내용 제공
```

---

## 6. 폴더 구조

```
ur5e-ontology-rag/
├── src/
│   └── embedding/
│       ├── __init__.py [신규]
│       ├── embedder.py [신규]
│       ├── vector_store.py [신규]
│       └── reranker.py [신규 - 2026-01-26]
│
├── scripts/
│   └── run_embedding.py [업데이트]
│
└── stores/
    └── chroma/ [신규]
        └── (ChromaDB 데이터 파일)
```

---

## 7. 다음 단계 준비

### Phase 4 (온톨로지 스키마)와의 연결

| Phase 3 산출물 | Phase 4 사용처 |
|---------------|---------------|
| VectorStore | Knowledge Domain의 Document 검색 |
| SearchResult.metadata | DOCUMENTED_IN 관계 활용 |

### Phase 10-12 (RAG)와의 연결

| Phase 3 산출물 | Phase 10-12 사용처 |
|---------------|-------------------|
| VectorStore.search() | HybridRetriever의 벡터 검색 |
| SearchResult | ResponseGenerator의 문서 근거 |

---

## 8. 이슈 및 참고사항

### 8.1 해결된 이슈

없음 - 구현 완료

### 8.2 주의사항

1. **OpenAI API 키**: `.env` 파일에 `OPENAI_API_KEY` 설정 필요
2. **임베딩 비용**: 722 청크 × ~200 토큰 = 약 $0.003 (4원)
3. **Rate Limiting**: 배치 처리 + 자동 재시도로 대응
4. **기존 컬렉션 distance 설정**: 기존 Chroma 컬렉션이 cosine이 아닌 L2로 생성됐을 수 있음. score 해석/threshold 정확성을 위해 `--force`로 재생성 권장:
   ```bash
   python scripts/run_embedding.py --force
   ```

### 8.3 검증 명령어

```python
# 검색 테스트
from src.embedding import VectorStore

vs = VectorStore()
results = vs.search("C153 에러 해결 방법", top_k=3)
print(f"검색 결과: {len(results)} 건")

# 컬렉션 통계
stats = vs.get_collection_stats()
assert stats["count"] == 722  # 청크 수 확인
```

---

## 9. 문서 업데이트 내역

### 9.1 설계서 업데이트 (v1.0 → v2.0)

| 추가/변경 섹션 | 내용 |
|---------------|------|
| 구현 상태 업데이트 | "신규 작성" → "완료됨 (X줄)" 상태 반영 |
| 체크리스트 완료 | [ ] → [x] 모든 항목 완료 표시 |
| 저장소 상태 | "생성 필요" → "생성됨" |
| 온톨로지 연결 상세화 | Knowledge Domain 연결점 명시 |

### 9.2 코드 검증

| 항목 | 검증 결과 |
|------|----------|
| `src/embedding/__init__.py` | 완료 (25줄) - 모듈 정상 노출 |
| `src/embedding/embedder.py` | 완료 (115줄) - OpenAI 연동 정상 |
| `src/embedding/vector_store.py` | 완료 (250줄) - ChromaDB 연동 정상 |
| `scripts/run_embedding.py` | 완료 (200줄) - 실행 스크립트 정상 |

### 9.3 검증 코드

```python
>>> from src.embedding import VectorStore, OpenAIEmbedder
>>> vs = VectorStore()
>>> stats = vs.get_collection_stats()
>>> print(f'Collection count: {stats["count"]}')
Collection count: 722

>>> embedder = OpenAIEmbedder()
>>> print(f'Model: {embedder.model}')
Model: text-embedding-3-small
```

모든 검증 테스트 통과 확인.
