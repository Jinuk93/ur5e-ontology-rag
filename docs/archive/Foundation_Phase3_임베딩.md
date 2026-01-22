# Phase 3: 임베딩 및 벡터 DB

> **목표:** 청크를 벡터(숫자 배열)로 변환하고, ChromaDB에 저장하여 "의미 기반 검색"이 가능하게 한다.
>
> **왜 필요한가?** 사용자 질문과 "의미가 비슷한" 청크를 찾으려면 텍스트를 벡터로 변환해야 한다.

---

## 1. 이번 Phase에서 배울 것

| 개념 | 설명 | 왜 필요한가? |
|------|------|-------------|
| **임베딩(Embedding)** | 텍스트를 숫자 배열(벡터)로 변환 | 컴퓨터가 "의미"를 비교할 수 있게 함 |
| **벡터(Vector)** | 숫자들의 배열 [0.1, -0.3, 0.5, ...] | 텍스트의 의미를 수학적으로 표현 |
| **유사도(Similarity)** | 두 벡터가 얼마나 비슷한지 | 질문과 비슷한 청크 찾기 |
| **벡터DB (ChromaDB)** | 벡터를 저장하고 검색하는 DB | 빠른 유사도 검색 |

---

## 2. 핵심 개념 설명

### 2.1 임베딩이란?

```
텍스트                              벡터 (1536차원)
─────────────────────────────────────────────────────────
"C4 통신 에러"        →  [0.12, -0.34, 0.56, ..., 0.78]
"Communication error" →  [0.11, -0.35, 0.55, ..., 0.77]  ← 비슷!
"맛있는 피자"         →  [-0.89, 0.45, -0.12, ..., 0.23] ← 다름

의미가 비슷하면 → 벡터도 비슷
의미가 다르면   → 벡터도 다름
```

### 2.2 유사도 검색 원리

```
1. 사용자 질문: "통신 오류 해결법"
                    ↓
2. 질문을 벡터로 변환: [0.13, -0.32, 0.54, ...]
                    ↓
3. DB의 모든 청크 벡터와 비교
   - 청크1 벡터와의 거리: 0.05 (가까움!) ← 비슷한 의미
   - 청크2 벡터와의 거리: 0.92 (멀다)
   - 청크3 벡터와의 거리: 0.08 (가까움!)
                    ↓
4. 가장 가까운 청크들 반환 (Top-K)
```

### 2.3 왜 ChromaDB를 사용하는가?

| 옵션 | 장점 | 단점 |
|------|------|------|
| **ChromaDB** | 설치 쉬움, Python 친화적, 로컬 저장 | 대규모에 약함 |
| Pinecone | 클라우드, 확장성 | 비용 발생 |
| Milvus | 대규모 처리 | 설정 복잡 |
| FAISS | 빠름 | 메타데이터 관리 어려움 |

**우리 선택: ChromaDB** (개인 프로젝트, 학습 목적에 적합)

---

## 3. 다룰 파일들과 역할

```
ur5e-ontology-rag/
│
├── src/
│   └── embedding/                  ← [신규] 임베딩 모듈
│       ├── __init__.py             ← 패키지 초기화
│       ├── embedder.py             ← [1] 임베딩 생성 클래스
│       └── vector_store.py         ← [2] ChromaDB 연동 클래스
│
├── stores/
│   └── chroma/                     ← ChromaDB 데이터 저장 위치
│
└── scripts/
    └── run_embedding.py            ← [3] 실행 스크립트
```

### 각 파일의 역할

| 번호 | 파일 | 역할 | 왜 필요? |
|------|------|------|----------|
| **1** | `embedder.py` | OpenAI API로 임베딩 생성 | 텍스트 → 벡터 변환 |
| **2** | `vector_store.py` | ChromaDB CRUD 작업 | 벡터 저장, 검색, 삭제 |
| **3** | `run_embedding.py` | 전체 파이프라인 실행 | 청크 로드 → 임베딩 → 저장 |

---

## 4. Phase 3 진행 순서

```
Step 1: 임베더 구현 (embedder.py)
   └─▶ OpenAI 임베딩 API 연동
   └─▶ 배치 처리 (여러 청크 한번에)
   └─▶ 에러 처리 및 재시도 로직

Step 2: 벡터 스토어 구현 (vector_store.py)
   └─▶ ChromaDB 컬렉션 생성
   └─▶ 청크 + 임베딩 저장
   └─▶ 유사도 검색 메서드

Step 3: 실행 스크립트 (run_embedding.py)
   └─▶ JSON에서 청크 로드
   └─▶ 임베딩 생성
   └─▶ ChromaDB에 저장

Step 4: 검색 테스트
   └─▶ 샘플 질문으로 유사도 검색
   └─▶ 결과 품질 확인
```

---

## 5. 핵심 코드 구조 (계획)

### 5.1 embedder.py

```python
class Embedder:
    """텍스트를 벡터로 변환하는 클래스"""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = OpenAI()

    def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        pass

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트 배치 임베딩"""
        pass

    def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """청크 리스트에 임베딩 추가"""
        pass
```

### 5.2 vector_store.py

```python
class VectorStore:
    """ChromaDB를 사용한 벡터 저장소"""

    def __init__(self, collection_name: str, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(collection_name)

    def add_chunks(self, chunks: List[Chunk]) -> None:
        """청크들을 벡터DB에 추가"""
        pass

    def search(self, query: str, top_k: int = 5) -> List[Chunk]:
        """유사도 검색"""
        pass

    def delete_collection(self) -> None:
        """컬렉션 삭제"""
        pass
```

---

## 6. 사용할 임베딩 모델

### OpenAI 임베딩 모델 비교

| 모델 | 차원 | 가격 (1M 토큰) | 특징 |
|------|------|---------------|------|
| `text-embedding-3-small` | 1536 | $0.02 | 가성비 좋음, 일반 용도 |
| `text-embedding-3-large` | 3072 | $0.13 | 고품질, 복잡한 검색 |
| `text-embedding-ada-002` | 1536 | $0.10 | 레거시 |

**우리 선택: `text-embedding-3-small`**
- 이유: 비용 효율적, 우리 규모에 충분

### 비용 추정

```
총 청크: 722개
평균 청크 크기: ~850자 (약 200 토큰)
총 토큰: 722 × 200 = 144,400 토큰

비용: 144,400 / 1,000,000 × $0.02 = $0.003 (약 4원)
```

---

## 7. ChromaDB 컬렉션 설계

### 7.1 컬렉션 구조

```
Collection: "ur5e_chunks"
│
├── ids: ["error_codes_C4_004", "service_manual_000", ...]
│
├── embeddings: [[0.12, -0.34, ...], [0.56, 0.78, ...], ...]
│
├── documents: ["C4 Communication issue...", "About This Document...", ...]
│
└── metadatas: [
│     {"source": "ErrorCodes.pdf", "doc_type": "error_code", ...},
│     {"source": "e-Series_Service_Manual_en.pdf", ...},
│     ...
│   ]
```

### 7.2 메타데이터 필터링 예시

```python
# 에러 코드만 검색
results = collection.query(
    query_texts=["통신 에러"],
    where={"doc_type": "error_code"},  # 필터
    n_results=5
)

# 특정 문서에서만 검색
results = collection.query(
    query_texts=["조립 방법"],
    where={"source": "e-Series_Service_Manual_en.pdf"},
    n_results=5
)
```

---

## 8. 예상 출력

### 8.1 임베딩 후 청크 구조

```python
Chunk(
    id="error_codes_C4_004",
    content="C4A1 Lost communication with Controller...",
    metadata=ChunkMetadata(
        source="ErrorCodes.pdf",
        page=12,
        doc_type="error_code",
        error_code="C4"
    ),
    embedding=[0.12, -0.34, 0.56, ...]  # 1536차원
)
```

### 8.2 검색 결과 예시

```
질문: "로봇 통신이 끊겼어"

검색 결과 (Top 3):
1. [Score: 0.92] error_codes_C4_004
   "C4A1 Lost communication with Controller..."

2. [Score: 0.87] error_codes_C10_007
   "C10 Controller communication issue..."

3. [Score: 0.81] service_manual_045
   "Check Ethernet connection between boards..."
```

---

## 9. 완료 조건 (체크리스트)

- [ ] `src/embedding/` 폴더 구조 생성
- [ ] `embedder.py` - OpenAI 임베딩 API 연동
- [ ] `vector_store.py` - ChromaDB 연동
- [ ] `run_embedding.py` - 실행 스크립트
- [ ] 722개 청크 임베딩 생성
- [ ] ChromaDB에 저장 완료
- [ ] 유사도 검색 테스트 성공
- [ ] 검색 결과 품질 확인

---

## 10. 예상 어려움 및 해결 방안

| 예상 어려움 | 해결 방안 |
|------------|----------|
| API 호출 속도 제한 | 배치 처리 + 지연 시간 추가 |
| 임베딩 비용 | text-embedding-3-small 사용 |
| ChromaDB 저장 경로 | .env에서 CHROMA_PERSIST_DIR 사용 |
| 검색 품질 | top_k 조정, 메타데이터 필터링 |

---

## 11. 참고: Phase 3 이후

Phase 3 완료 후 할 수 있는 것:
```
"C4 에러가 뭐야?"
→ VectorDB 검색
→ 관련 청크 반환
```

Phase 4 (온톨로지/그래프DB) 완료 후 추가로 할 수 있는 것:
```
"Control Box 관련 에러 전부 알려줘"
→ GraphDB에서 관계 탐색
→ C4, C10, C17 등 연결된 에러 코드 반환
```

---

**이 계획대로 진행할까요?**
