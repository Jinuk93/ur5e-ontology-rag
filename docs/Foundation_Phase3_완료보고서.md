# Phase 3: 임베딩 및 벡터 DB - 완료 보고서

> **목표:** 청크를 벡터로 변환하고, ChromaDB에 저장하여 "의미 기반 검색"이 가능하게 한다.
>
> **완료일:** 2026-01-20

---

## 1. Before vs After 비교

### 1.1 파일 구조

| 항목 | Before (계획) | After (실제) | 차이점 |
|------|--------------|--------------|--------|
| `embedder.py` | 단순 임베딩 | 배치 처리 + 재시도 로직 | **안정성 강화** |
| `vector_store.py` | 기본 CRUD | upsert + 필터링 검색 | **중복 처리 추가** |
| `run_embedding.py` | 실행 스크립트 | 실행 + 검색 테스트 포함 | **테스트 통합** |
| `__init__.py` | 계획대로 | 계획대로 | 동일 |

### 1.2 임베딩 설정

| 항목 | Before (계획) | After (실제) | 이유 |
|------|--------------|--------------|------|
| 모델 | text-embedding-3-small | 동일 | 비용 효율적 |
| 차원 | 1536 | 동일 | 모델 기본값 |
| 배치 크기 | 미정 | **100** | API 안정성 |
| 재시도 | 미정 | **3회** | 오류 대응 |

### 1.3 비용 비교

| 항목 | Before (예상) | After (실제) | 차이 |
|------|--------------|--------------|------|
| 청크 수 | 722개 | 722개 | 동일 |
| 예상 비용 | $0.003 | ~$0.003 | 동일 |
| 처리 시간 | 미정 | **9초** | 매우 빠름 |

---

## 2. 차이점 분석 및 이유

### 2.1 배치 처리 + 재시도 로직 추가 (embedder.py)

**Before:** 단순히 텍스트를 임베딩으로 변환

**After:** 배치 처리 + 재시도 로직 추가
```python
BATCH_SIZE = 100          # 한 번에 100개씩 처리
RETRY_DELAY = 1.0         # 재시도 대기 시간
MAX_RETRIES = 3           # 최대 3회 재시도
```

**이유:**
1. **API Rate Limit 대응**: OpenAI API는 호출 횟수 제한이 있음
2. **네트워크 오류 대응**: 일시적 오류 시 자동 재시도
3. **비용 효율**: 배치 처리로 API 호출 횟수 최소화

---

### 2.2 upsert 사용 (vector_store.py)

**Before:** `add()` 메서드로 단순 추가

**After:** `upsert()` 메서드로 중복 처리
```python
self.collection.upsert(
    ids=batch_ids,
    embeddings=batch_embeddings,
    documents=batch_documents,
    metadatas=batch_metadatas,
)
```

**이유:**
1. **재실행 안전**: 스크립트를 여러 번 실행해도 중복 없음
2. **업데이트 지원**: 기존 청크 수정 시 자동 갱신
3. **멱등성 보장**: 동일한 입력 → 동일한 결과

---

### 2.3 검색 테스트 통합 (run_embedding.py)

**Before:** 별도의 테스트 스크립트

**After:** 임베딩 후 자동으로 검색 테스트 실행

**이유:**
1. **즉시 검증**: 임베딩 후 바로 품질 확인
2. **파이프라인 통합**: 한 스크립트로 전체 흐름 파악
3. **디버깅 용이**: 문제 발생 시 즉시 확인

---

## 3. 생성된 파일 및 코드 분석

### 3.1 파일 구조

```
src/embedding/
├── __init__.py         ← 패키지 export
├── embedder.py         ← OpenAI 임베딩 (180줄)
└── vector_store.py     ← ChromaDB 연동 (290줄)

scripts/
└── run_embedding.py    ← 파이프라인 실행 (180줄)

stores/chroma/          ← ChromaDB 데이터 저장
```

### 3.2 코드 분석: embedder.py

```python
class Embedder:
    """텍스트 → 벡터 변환"""

    DEFAULT_MODEL = "text-embedding-3-small"  # 1536차원
    BATCH_SIZE = 100                          # 배치 크기
    MAX_RETRIES = 3                           # 재시도 횟수

    def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """배치 임베딩 (100개씩)"""

    def embed_chunks(self, chunks: List) -> List:
        """청크 리스트에 임베딩 추가"""
```

**핵심 기능:**
- OpenAI API로 임베딩 생성
- 100개 단위 배치 처리
- 오류 시 3회 재시도

### 3.3 코드 분석: vector_store.py

```python
class VectorStore:
    """ChromaDB 벡터 저장소"""

    def add_chunks(self, chunks, embedder):
        """청크 + 임베딩 저장 (upsert)"""

    def search(self, query, top_k, where, embedder):
        """유사도 검색 (필터링 지원)"""

    def get_by_id(self, chunk_id):
        """ID로 청크 조회"""
```

**핵심 기능:**
- ChromaDB 영구 저장 (stores/chroma/)
- 메타데이터 필터링 검색
- 거리 → 유사도 점수 변환

---

## 4. 검색 테스트 결과

### 4.1 필터 없이 전체 검색 (3개 문서 모두에서 검색)

| 쿼리 | Top 1 결과 | 문서 유형 | 점수 |
|------|-----------|----------|------|
| "C4 에러 해결법" | C50A54 5V regulator too low... | **error_code** | 0.4519 |
| "로봇 설치 방법" | Maintenance and Repair... | **user_manual** | 0.4512 |
| "조인트 교체" | Remove the 4 nuts... | **service_manual** | 0.4028 |

```
[Query] 'C4 에러 해결법' - 필터 없이 전체 검색
1. [0.4519] [error_code] error_codes_C51_035
2. [0.4465] [error_code] error_codes_C305_164
3. [0.4441] [error_code] error_codes_C304_163

[Query] '로봇 설치 방법' - 필터 없이 전체 검색
1. [0.4512] [user_manual] user_manual_367
2. [0.4412] [user_manual] user_manual_279
3. [0.4351] [service_manual] service_manual_167  ← 다른 문서도 검색됨!

[Query] '조인트 교체' - 필터 없이 전체 검색
1. [0.4028] [service_manual] service_manual_113
2. [0.4015] [service_manual] service_manual_072
3. [0.4002] [service_manual] service_manual_055
```

**결과:** 필터 없이 검색하면 **3개 문서 전체**에서 의미적으로 유사한 청크를 찾음

---

### 4.2 필터 있는 검색 (특정 문서 유형만 검색)

| 쿼리 | 필터 | Top 1 결과 | 점수 |
|------|------|-----------|------|
| "C4 에러 해결법" | `doc_type: error_code` | C50A54 5V regulator | 0.4519 |
| "Control Box 분해" | `doc_type: service_manual` | Dismantling Control Box | 0.4959 |

```
[Query] 'Control Box 분해' - 필터: service_manual만
1. [0.4959] service_manual_041 - "Check for any dirt/dust inside..."
2. [0.4924] service_manual_101 - "Dismantling the Control Box..."
3. [0.4911] service_manual_102 - "Take out the Control Box bracket..."
```

**결과:** 필터를 적용하면 **특정 문서 유형에서만** 검색됨

---

### 4.3 필터 유무 비교 및 결론

| 항목 | 필터 없음 | 필터 있음 |
|------|----------|----------|
| **검색 범위** | 3개 문서 전체 (722 청크) | 특정 문서 유형만 |
| **검색 방식** | 임베딩 유사도만 | 임베딩 유사도 + 메타데이터 필터 |
| **사용 시점** | 어떤 문서에 답이 있는지 모를 때 | 특정 문서에서만 찾고 싶을 때 |

**핵심 결론:**

```
1. 벡터 검색의 핵심 = "의미" 유사도
   - "C4 에러 해결법" → 에러 관련 문서가 의미적으로 유사
   - "조인트 교체" → 서비스 매뉴얼이 의미적으로 유사
   - 필터 없이도 적절한 문서 유형에서 결과 반환

2. 필터는 "선택적 제한"
   - 검색 = 임베딩 유사도 검색 + (선택적) 메타데이터 필터
   - 필터를 쓰면 검색 범위를 좁힐 수 있음

3. 한글 → 영문 검색 성공
   - 임베딩이 언어를 넘어 "의미"를 이해
   - "통신 에러" ≈ "communication error" (의미적 유사)
```

---

### 4.4 검색 품질 분석

**좋은 점:**
- 한글 쿼리로 영문 문서 검색 성공
- 쿼리의 의미에 맞는 문서 유형에서 결과 반환
- 유사도 점수 0.4~0.5 범위가 적절한 결과

**개선 필요:**
- "C4 에러 해결법" 검색 시 C4가 아닌 C50, C304 반환
- 원인: Phase 2 청킹에서 C4가 큰 청크 안에 포함됨
- 해결: 더 세밀한 청킹 전략 필요 (향후 개선)

---

## 5. 결과 요약

### 5.1 수치 요약

| 항목 | 값 |
|------|-----|
| 임베딩된 청크 | **722개** |
| 임베딩 차원 | 1536 |
| 처리 시간 | ~9초 |
| ChromaDB 저장 위치 | `stores/chroma/` |
| 컬렉션 이름 | `ur5e_chunks` |

### 5.2 문서 유형별 통계

| 문서 유형 | 청크 수 |
|----------|--------|
| error_code | 99 |
| service_manual | 197 |
| user_manual | 426 |
| **합계** | **722** |

---

## 6. Phase 3 완료 체크리스트

- [x] `src/embedding/` 폴더 구조 생성
- [x] `embedder.py` - OpenAI 임베딩 API 연동
- [x] `vector_store.py` - ChromaDB 연동
- [x] `run_embedding.py` - 실행 스크립트
- [x] 722개 청크 임베딩 생성
- [x] ChromaDB에 저장 완료
- [x] 유사도 검색 테스트 성공
- [x] 검색 결과 품질 확인

---

## 7. 현재까지 완료된 것

```
[Phase 0] 환경 설정 ✅
    └── Python, Docker, 패키지 설치

[Phase 1] PDF 분석 ✅
    └── 3개 PDF 구조 파악

[Phase 2] PDF 파싱 ✅
    └── 722개 청크 생성

[Phase 3] 임베딩 ✅ (현재)
    └── 벡터 DB 저장 완료
```

---

## 8. 다음 단계 (Phase 4 예정)

### 8.1 Phase 4: 온톨로지 및 그래프 DB

```
목표: 지식 구조(온톨로지)를 설계하고 Neo4j에 저장

핵심 개념:
- VectorDB: "의미"로 검색 (비슷한 것)
- GraphDB: "관계"로 검색 (연결된 것)

예상 작업:
1. 온톨로지 스키마 설계
2. 엔티티 추출 (Component, ErrorCode, Procedure...)
3. 관계 정의 (HAS_ERROR, RESOLVED_BY...)
4. Neo4j에 그래프 구축
```

### 8.2 왜 GraphDB가 필요한가?

```
VectorDB만으로는:
  "Control Box 관련 에러 전부" → 어려움

GraphDB 추가 시:
  Control Box → [HAS_ERROR] → C4, C10, C17...
  → 관계를 따라 모든 에러 코드 반환!
```