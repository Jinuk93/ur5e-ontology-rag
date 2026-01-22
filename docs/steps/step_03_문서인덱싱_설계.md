# Step 03: 문서 인덱싱 - 설계서

## 1. 개요

### 1.1 Phase 정보
- **Phase 번호**: 03
- **Phase 명**: 문서 인덱싱 (Document Indexing)
- **Stage**: Stage 1 - 데이터 기반 (Data Foundation)
- **목표**: ChromaDB에 문서 벡터 인덱싱

### 1.2 Phase 목표 (Unified_ROADMAP.md 기준)
- ChromaDB 컬렉션 생성
- 청크 임베딩 생성 (OpenAI text-embedding-3-small)
- 인덱스 저장 (`stores/chroma/`)
- 검색 테스트

### 1.3 핵심 산출물
- `stores/chroma/` (영속 인덱스)
- `src/embedding/__init__.py` (패키지 초기화)
- `src/embedding/embedder.py` (임베딩 생성기)
- `src/embedding/vector_store.py` (ChromaDB 인터페이스)
- `scripts/run_embedding.py` (임베딩 생성 스크립트)

---

## 2. 다룰 파일

### 2.1 핵심 구현 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `src/embedding/__init__.py` | 패키지 초기화 | 완료됨 (25줄) |
| `src/embedding/embedder.py` | OpenAI 임베딩 생성 | 완료됨 (115줄) |
| `src/embedding/vector_store.py` | ChromaDB 인터페이스 | 완료됨 (250줄) |
| `scripts/run_embedding.py` | 임베딩 생성 스크립트 | 완료됨 (200줄) |

### 2.2 데이터 파일 (Phase 2에서 생성됨)

| 파일 경로 | 설명 | 상태 |
|-----------|------|------|
| `data/processed/chunks/user_manual_chunks.json` | 426 chunks | 존재 |
| `data/processed/chunks/service_manual_chunks.json` | 197 chunks | 존재 |
| `data/processed/chunks/error_codes_chunks.json` | 99 chunks | 존재 |
| `data/processed/metadata/manifest.json` | 문서 메타데이터 | 존재 |

### 2.3 저장소

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `stores/chroma/` | ChromaDB 영속 인덱스 | 생성됨 |

---

## 3. 설계 상세

### 3.1 임베딩 파이프라인 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                  Embedding Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   data/processed/chunks/                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  user_manual_chunks.json (426)                       │  │
│   │  service_manual_chunks.json (197)                    │  │
│   │  error_codes_chunks.json (99)                        │  │
│   │                                                      │  │
│   │  Total: 722 chunks                                   │  │
│   └──────────────────────────┬──────────────────────────┘  │
│                              │                              │
│                              ▼                              │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              src/embedding/embedder.py               │  │
│   │                                                      │  │
│   │   OpenAI text-embedding-3-small                     │  │
│   │   - 차원: 1536                                      │  │
│   │   - 배치 처리 (100개씩)                             │  │
│   │   - Rate limiting 처리                              │  │
│   └──────────────────────────┬──────────────────────────┘  │
│                              │                              │
│                              ▼                              │
│   ┌─────────────────────────────────────────────────────┐  │
│   │            src/embedding/vector_store.py             │  │
│   │                                                      │  │
│   │   ChromaDB 컬렉션: "ur5e_documents"                  │  │
│   │   - 영속 저장: stores/chroma/                       │  │
│   │   - 메타데이터 필터링 지원                          │  │
│   │   - 유사도 검색 (top_k)                             │  │
│   └──────────────────────────┬──────────────────────────┘  │
│                              │                              │
│                              ▼                              │
│   stores/chroma/                                            │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  영속 벡터 인덱스                                    │  │
│   │  - 722 벡터                                          │  │
│   │  - 메타데이터 (source, page, doc_type)              │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 임베딩 모델 설정

| 항목 | 값 | 설명 |
|------|-----|------|
| 모델명 | text-embedding-3-small | OpenAI 임베딩 모델 |
| 차원 | 1536 | 벡터 차원 |
| 배치 크기 | 100 | 한번에 처리할 청크 수 |
| 거리 메트릭 | cosine | 유사도 측정 방식 |

### 3.3 VectorStore 인터페이스

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class SearchResult:
    """검색 결과"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    score: float  # 유사도 점수 (0~1, 높을수록 유사)

class VectorStore:
    """ChromaDB 기반 벡터 저장소"""

    def __init__(
        self,
        collection_name: str = "ur5e_documents",
        persist_directory: str = "stores/chroma"
    ):
        """벡터 저장소 초기화"""
        pass

    def add_documents(
        self,
        chunks: List[Chunk],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """
        문서 청크 추가

        Args:
            chunks: Chunk 리스트
            embeddings: 미리 생성된 임베딩 (없으면 자동 생성)
        """
        pass

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        유사 문서 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            filter_metadata: 메타데이터 필터 (예: {"doc_type": "user_manual"})

        Returns:
            SearchResult 리스트
        """
        pass

    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 반환"""
        pass

    def delete_collection(self) -> None:
        """컬렉션 삭제 (재색인용)"""
        pass
```

### 3.4 Embedder 인터페이스

```python
from typing import List

class OpenAIEmbedder:
    """OpenAI 임베딩 생성기"""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
    ):
        """임베딩 생성기 초기화"""
        pass

    def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        pass

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        다중 텍스트 임베딩 (배치 처리)

        Args:
            texts: 텍스트 리스트

        Returns:
            임베딩 벡터 리스트
        """
        pass

    def embed_query(self, query: str) -> List[float]:
        """검색 쿼리 임베딩 (embed_text와 동일)"""
        pass
```

### 3.5 ChromaDB 컬렉션 구조

```python
# ChromaDB 컬렉션 설정
collection_config = {
    "name": "ur5e_documents",
    "metadata": {
        "description": "UR5e 문서 벡터 인덱스",
        "embedding_model": "text-embedding-3-small",
        "embedding_dimension": 1536,
        "hnsw:space": "cosine",
    },
    "distance_function": "cosine"  # l2, ip, cosine
}

# 문서 추가 시 구조
document = {
    "id": "user_manual_000",  # 청크 ID
    "document": "1. Preface\nIntroduction\nCongratulations on...",  # 청크 텍스트
    "metadata": {
        "source": "710-965-00_UR5e_User_Manual_en_Global.pdf",
        "page": 1,
        "doc_type": "user_manual",
        "section": "Preface",
        "chapter": "1."
    },
    "embedding": [0.123, 0.456, ...]  # 1536차원 벡터
}
```

---

## 4. 온톨로지 연결

### 4.1 Knowledge Domain 연결

Phase 3에서 생성된 벡터 인덱스는 Knowledge Domain의 Document 엔티티와 연결됩니다.

```yaml
Document:
  instances:
    - id: "user_manual"
      vector_collection: "ur5e_documents"
      filter: {"doc_type": "user_manual"}
      chunk_count: 426

    - id: "service_manual"
      vector_collection: "ur5e_documents"
      filter: {"doc_type": "service_manual"}
      chunk_count: 197

    - id: "error_codes"
      vector_collection: "ur5e_documents"
      filter: {"doc_type": "error_codes"}
      chunk_count: 99
```

### 4.2 DOCUMENTED_IN 관계 활용

에러 코드와 문서 간의 관계를 검색에서 활용:

```
질문: "C153 에러 해결 방법"
    │
    ▼
1. 온톨로지에서 C153 정보 조회
    │
    ▼
2. DOCUMENTED_IN 관계로 관련 문서 식별
    → user_manual#p145, service_manual#p67
    │
    ▼
3. VectorStore에서 메타데이터 필터링
    → filter: {"doc_type": {"$in": ["user_manual", "service_manual"]}}
    │
    ▼
4. 관련 청크 검색 + 순위화
```

### 4.3 Phase 10-12 연결

Phase 3 벡터 인덱스가 RAG 파이프라인에서 사용되는 방식:

```
Phase 10 (질문 분류)
        │
        ▼
일반 RAG 질문 → Phase 3 VectorStore.search()
하이브리드 질문 → Phase 3 VectorStore + Phase 5 Ontology
온톨로지 질문 → Phase 5 Ontology 우선
        │
        ▼
Phase 12 (응답 생성)
        → 문서 근거로 VectorStore 결과 활용
```

---

## 5. Unified_Spec.md 정합성 검증

### 5.1 기술 스택 요구사항

| Spec 요구사항 | Phase 3 구현 내용 | 충족 여부 |
|--------------|------------------|----------|
| ChromaDB 사용 | VectorStore(ChromaDB) | O |
| OpenAI embedding | text-embedding-3-small | O |
| 영속 저장 | stores/chroma/ | O |

### 5.2 API 명세 연결

| Spec API | Phase 3 지원 |
|----------|-------------|
| POST /api/v1/query | VectorStore.search() 활용 |
| GET /api/v1/evidence/{trace_id} | 문서 청크 조회 |

---

## 6. 구현 체크리스트

### 6.1 임베딩 모듈 (완료됨)

- [x] `src/embedding/__init__.py` - 패키지 초기화
- [x] `src/embedding/embedder.py` - OpenAI 임베딩 생성
- [x] `src/embedding/vector_store.py` - ChromaDB 인터페이스

### 6.2 스크립트 (완료됨)

- [x] `scripts/run_embedding.py` - 전체 청크 임베딩 및 저장

### 6.3 검증 (스크립트 실행 시 확인)

- [x] 722개 청크 임베딩 생성 확인
- [x] ChromaDB 영속 저장 확인
- [x] 검색 테스트 (C153, 페이로드 등)

### 6.4 검증 명령어 (ROADMAP 기준)

```python
# 검색 테스트
from src.embedding import VectorStore

vs = VectorStore()
results = vs.search("C153 에러 해결 방법", top_k=3)
print(f"검색 결과: {len(results)} 건")
for r in results:
    print(f"  - {r.chunk_id}: {r.score:.3f}")

# 컬렉션 통계
stats = vs.get_collection_stats()
assert stats["count"] == 722
```

---

## 7. 설계 결정 사항

### 7.1 ChromaDB 선택

**결정**: ChromaDB를 벡터 저장소로 사용

**근거**:
1. 간편성: 설치/설정 간단, 로컬 실행
2. 영속성: 파일 기반 영속 저장 지원
3. 메타데이터: 풍부한 메타데이터 필터링
4. 성능: 소규모 데이터셋(~1000개)에 적합

### 7.2 text-embedding-3-small 선택

**결정**: OpenAI text-embedding-3-small 모델 사용

**근거**:
1. 성능: text-embedding-ada-002 대비 개선된 성능
2. 비용: 3-small이 ada 대비 5배 저렴
3. 차원: 1536 차원 (충분한 표현력)
4. 호환성: OpenAI API 기반으로 일관된 인터페이스

### 7.3 배치 처리

**결정**: 100개 단위로 배치 처리

**근거**:
1. Rate Limiting: OpenAI API 제한 대응
2. 메모리: 대량 임베딩 시 메모리 효율
3. 진행률: 배치 단위 진행률 표시 가능

---

## 8. 다음 Phase 연결

### Phase 4-5 (온톨로지)와의 연결

| Phase 3 산출물 | Phase 4-5 사용처 |
|---------------|-----------------|
| VectorStore | DOCUMENTED_IN 관계의 실제 문서 검색 |
| 메타데이터 필터 | 특정 문서 타입 검색 |

### Phase 10-12 (RAG)와의 연결

| Phase 3 산출물 | Phase 10-12 사용처 |
|---------------|-------------------|
| VectorStore.search() | HybridRetriever의 벡터 검색 |
| SearchResult | ResponseGenerator의 문서 근거 |

---

*작성일: 2026-01-22*
*리팩토링일: 2026-01-22*
*Phase: 03 - 문서 인덱싱*
*문서 버전: v2.0*
