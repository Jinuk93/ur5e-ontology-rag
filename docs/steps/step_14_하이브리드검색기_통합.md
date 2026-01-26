# Step 14: HybridRetriever 통합 - 완료 보고서

## 1. 요약

| 항목 | 내용 |
|------|------|
| Phase | 14 - HybridRetriever 통합 |
| 상태 | **완료** |
| 날짜 | 2026-01-26 |
| 주요 산출물 | HybridRetriever, chat.py 통합, settings.yaml 업데이트 |

---

## 2. 문제 정의 (보완 전)

### 2.1 발견된 GAP

```
┌─────────────────────────────────────────────────────────────────┐
│  보완 전: VectorStore/Reranker 미연결                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Query                                                          │
│    │                                                            │
│    ▼                                                            │
│  QueryClassifier ─────────────────────┐                        │
│    │                                   │                        │
│    │ (ONTOLOGY/HYBRID/RAG 분류)        │                        │
│    │                                   │                        │
│    ▼                                   ▼                        │
│  OntologyEngine                    VectorStore ← [미연결!]     │
│    │                                   │                        │
│    │                               Reranker ← [미연결!]        │
│    │                                   │                        │
│    ▼                                   │                        │
│  ResponseGenerator ←───────────────────┘ [document_refs 누락]  │
│    │                                                            │
│    ▼                                                            │
│  Response (문서 근거 없음)                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 문제점

| 구성요소 | 상태 | 문제 |
|----------|------|------|
| `VectorStore` | 구현됨 | chat.py에서 호출 안함 |
| `CrossEncoderReranker` | 구현됨 | 파이프라인 미연결 |
| `ResponseGenerator` | 구현됨 | document_refs 미전달 |
| `settings.yaml` | 존재 | rerank 설정 없음 |

---

## 3. 해결 방안 (보완 후)

### 3.1 새로운 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│  보완 후: 완전 통합 파이프라인                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Query: "C153 에러 해결 방법"                                   │
│    │                                                            │
│    ▼                                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Step 1: QueryClassifier                                │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • 질문 분류: ONTOLOGY / HYBRID / RAG                   │   │
│  │  • 엔티티 추출: C153 (ErrorCode)                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│    │                                                            │
│    │ classification.query_type = HYBRID                        │
│    │                                                            │
│    ├───────────────────────┬───────────────────────┐           │
│    │                       │                       │            │
│    ▼                       ▼                       │            │
│  ┌───────────────┐   ┌───────────────────────────┐│            │
│  │ OntologyEngine│   │ HybridRetriever [NEW!]    ││            │
│  │ ──────────────│   │ ─────────────────────────  ││            │
│  │ • 그래프 탐색 │   │ • VectorStore (Stage 1)   ││            │
│  │ • 패턴 매칭   │   │   └─ Bi-encoder Top-K=20  ││            │
│  │ • 원인 추론   │   │ • Reranker (Stage 2)      ││            │
│  │               │   │   └─ Cross-encoder Top-N=5││            │
│  └───────────────┘   └───────────────────────────┘│            │
│    │                       │                       │            │
│    │ reasoning             │ document_refs        │            │
│    │                       │                       │            │
│    ▼                       ▼                       │            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Step 4: ResponseGenerator                              │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • 온톨로지 추론 결과 + 문서 참조 병합                  │   │
│  │  • 자연어 응답 생성                                     │   │
│  │  • Evidence (ontology_paths + document_refs)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│    │                                                            │
│    ▼                                                            │
│  Response (온톨로지 근거 + 문서 근거)                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 HybridRetriever 상세

```
┌─────────────────────────────────────────────────────────────────┐
│                    HybridRetriever 내부 구조                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  retrieve(query, query_type)                                    │
│    │                                                            │
│    ├─ query_type == ONTOLOGY                                   │
│    │    └─ top_n = min(3, final_top_n)  # 문서 검색 최소화     │
│    │                                                            │
│    ├─ query_type == HYBRID                                     │
│    │    └─ top_n = final_top_n (5)      # 표준 검색            │
│    │                                                            │
│    └─ query_type == RAG                                        │
│         └─ top_n = final_top_n (5)      # 문서 중심 검색       │
│                                                                 │
│    │                                                            │
│    ▼                                                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  _search_with_rerank() - 2단계 검색                       │ │
│  │  ─────────────────────────────────────────────────────────│ │
│  │                                                           │ │
│  │  Stage 1: Bi-encoder (VectorStore.search)                │ │
│  │    • OpenAI text-embedding-3-small                       │ │
│  │    • ChromaDB cosine similarity                          │ │
│  │    • initial_top_k = 20개 후보                           │ │
│  │                                                           │ │
│  │           │ 20개 후보                                     │ │
│  │           ▼                                               │ │
│  │                                                           │ │
│  │  Stage 2: Cross-encoder (VectorStore.search_with_rerank) │ │
│  │    • BAAI/bge-reranker-base (한국어 지원)                │ │
│  │    • Query-Document 쌍 분석                              │ │
│  │    • final_top_n = 5개 최종 선택                         │ │
│  │                                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│    │                                                            │
│    ▼                                                            │
│  _convert_to_document_refs()                                   │
│    • SearchResult → DocumentReference 변환                     │
│    • similarity_threshold (0.3) 필터링                         │
│    • snippet 생성 (200자 잘라내기)                             │
│                                                                 │
│    │                                                            │
│    ▼                                                            │
│  RetrievalResult                                               │
│    • document_refs: List[DocumentReference]                    │
│    • total_candidates: int                                     │
│    • reranked: bool                                            │
│    • search_time_ms: float                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 구현 상세

### 4.1 신규/수정 파일 목록

| 파일 | 라인 수 | 상태 | 설명 |
|------|--------|------|------|
| `src/rag/hybrid_retriever.py` | 270 | **신규** | HybridRetriever 클래스 |
| `src/rag/__init__.py` | 90 | 수정 | HybridRetriever export 추가 |
| `src/api/routes/chat.py` | 295 | 수정 | retriever 통합 |
| `src/api/main.py` | 155 | 수정 | get_retriever 싱글톤 추가 |
| `configs/settings.yaml` | 175 | 수정 | rerank 설정 섹션 추가 |

### 4.2 HybridRetriever 클래스

```python
class HybridRetriever:
    """하이브리드 검색기

    질문 유형에 따라 다른 검색 전략을 적용:
    - RAG: VectorStore + Reranker (문서만)
    - HYBRID: VectorStore + Reranker + 온톨로지 컨텍스트
    - ONTOLOGY: 온톨로지 전용 (문서 검색 최소화)
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        use_reranker: Optional[bool] = None,
    ):
        # 설정에서 로드
        self.settings = get_settings()
        self.use_reranker = self.settings.rerank.enabled
        self.initial_top_k = self.settings.rerank.initial_top_k  # 20
        self.final_top_n = self.settings.rerank.final_top_n  # 5
        self.similarity_threshold = self.settings.retrieval.similarity_threshold  # 0.3

    def retrieve(
        self,
        query: str,
        query_type: QueryType,
        filter_metadata: Optional[Dict[str, str]] = None,
    ) -> RetrievalResult:
        """질문 유형에 따른 문서 검색"""
        pass

    def _search_with_rerank(self, query, filter_metadata, top_n):
        """2단계 검색 (Bi-encoder + Cross-encoder)"""
        pass

    def _convert_to_document_refs(self, search_results):
        """SearchResult → DocumentReference 변환"""
        pass
```

### 4.3 chat.py 수정 사항

```python
# 변경 전
response = generator.generate(
    classification,
    reasoning,
    request.context
)

# 변경 후
# 2. 문서 검색 (HybridRetriever - VectorStore + Reranker)
if _get_retriever:
    retriever = _get_retriever()
    retrieval_result = retriever.retrieve(
        query=classification.query,
        query_type=classification.query_type,
    )
    document_refs = retrieval_result.document_refs

# 4. 응답 생성 (document_refs 포함)
response = generator.generate(
    classification,
    reasoning,
    request.context,
    document_refs=document_refs,  # 문서 참조 전달
)
```

### 4.4 settings.yaml 추가 설정

```yaml
# [3.5] 리랭커 설정 (2단계 검색)
rerank:
  enabled: true                    # 리랭킹 활성화 여부
  model: "bge-reranker-base"       # Cross-Encoder 모델
  initial_top_k: 20                # 1단계 후보 수
  final_top_n: 5                   # 최종 반환 수
```

---

## 5. 파이프라인 흐름도 (전체)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        완전 통합 RAG 파이프라인                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User Query: "C153 에러가 발생했는데 어떻게 해결해야 하나요?"            │
│                                                                         │
│  ═══════════════════════════════════════════════════════════════════   │
│  STEP 1: 질문 이해 (QueryClassifier)                                   │
│  ═══════════════════════════════════════════════════════════════════   │
│                                                                         │
│    Input:  "C153 에러가 발생했는데 어떻게 해결해야 하나요?"              │
│                    │                                                    │
│                    ▼                                                    │
│    ┌────────────────────────────────────────────────────────────────┐  │
│    │  QueryClassifier                                               │  │
│    │  • 키워드 분석: "C153", "에러", "해결"                         │  │
│    │  • 패턴 매칭: ErrorCode 패턴 감지                              │  │
│    │  • 의도 분류: 트러블슈팅                                       │  │
│    └────────────────────────────────────────────────────────────────┘  │
│                    │                                                    │
│                    ▼                                                    │
│    Output:                                                             │
│      • query_type: HYBRID (온톨로지 + 문서 필요)                       │
│      • entities: [ExtractedEntity(id="C153", type="ErrorCode")]        │
│      • confidence: 0.75                                                │
│                                                                         │
│  ═══════════════════════════════════════════════════════════════════   │
│  STEP 2: 지식 검색 (병렬 실행)                                         │
│  ═══════════════════════════════════════════════════════════════════   │
│                                                                         │
│    ┌──────────────────────┐     ┌──────────────────────────────────┐  │
│    │ (A) OntologyEngine   │     │ (B) HybridRetriever              │  │
│    │ ────────────────────│     │ ──────────────────────────────── │  │
│    │                      │     │                                  │  │
│    │ C153                 │     │ Query: "C153 에러가..."          │  │
│    │   │                  │     │          │                       │  │
│    │   │ BFS 탐색         │     │          ▼                       │  │
│    │   │                  │     │ ┌──────────────────────────────┐ │  │
│    │   ▼                  │     │ │ Stage 1: Bi-encoder          │ │  │
│    │ ┌───────────┐        │     │ │ • text-embedding-3-small     │ │  │
│    │ │ CAUSED_BY │        │     │ │ • ChromaDB Top-K=20          │ │  │
│    │ └───────────┘        │     │ └──────────────────────────────┘ │  │
│    │   │                  │     │          │                       │  │
│    │   ▼                  │     │          ▼ (20개 후보)           │  │
│    │ ┌───────────────┐    │     │ ┌──────────────────────────────┐ │  │
│    │ │ CAUSE_COLLISION│   │     │ │ Stage 2: Cross-encoder       │ │  │
│    │ │ CAUSE_OVERLOAD │   │     │ │ • bge-reranker-base          │ │  │
│    │ │ CAUSE_POSITION │   │     │ │ • 정밀 리랭킹 Top-N=5        │ │  │
│    │ └───────────────┘    │     │ └──────────────────────────────┘ │  │
│    │   │                  │     │          │                       │  │
│    │   ▼                  │     │          ▼ (5개 최종)            │  │
│    │ ┌──────────────────┐ │     │ ┌──────────────────────────────┐ │  │
│    │ │ RESOLVED_BY     │ │     │ │ DocumentReference[]          │ │  │
│    │ │ RES_CHECK_AREA  │ │     │ │ • ErrorCodes.pdf (0.639)     │ │  │
│    │ │ RES_REDUCE_SPEED│ │     │ │ • service_manual.pdf (0.52) │ │  │
│    │ └──────────────────┘ │     │ └──────────────────────────────┘ │  │
│    └──────────────────────┘     └──────────────────────────────────┘  │
│              │                             │                          │
│              │ reasoning                   │ document_refs            │
│              │                             │                          │
│              └─────────────┬───────────────┘                          │
│                            │                                          │
│                            ▼                                          │
│  ═══════════════════════════════════════════════════════════════════   │
│  STEP 3: 응답 생성 (ResponseGenerator)                                 │
│  ═══════════════════════════════════════════════════════════════════   │
│                                                                         │
│    ┌────────────────────────────────────────────────────────────────┐  │
│    │  ResponseGenerator                                             │  │
│    │  ──────────────────────────────────────────────────────────── │  │
│    │                                                                │  │
│    │  Inputs:                                                       │  │
│    │    • classification: {query_type: HYBRID, entities: [C153]}   │  │
│    │    • reasoning: {conclusions: [...], recommendations: [...]}   │  │
│    │    • document_refs: [{doc_id: "ErrorCodes.pdf", ...}]         │  │
│    │                                                                │  │
│    │  Processing:                                                   │  │
│    │    1. ConfidenceGate 평가 → passed                            │  │
│    │    2. 분석 결과 구성                                          │  │
│    │    3. 권장사항 구성                                           │  │
│    │    4. Evidence 구성 (ontology_paths + document_refs)          │  │
│    │    5. 자연어 응답 생성                                        │  │
│    │                                                                │  │
│    └────────────────────────────────────────────────────────────────┘  │
│                            │                                          │
│                            ▼                                          │
│  ═══════════════════════════════════════════════════════════════════   │
│  Output: GeneratedResponse                                             │
│  ═══════════════════════════════════════════════════════════════════   │
│                                                                         │
│    {                                                                   │
│      "trace_id": "45146785-31bb-4724-95f8-d283a60e8b5c",               │
│      "query_type": "hybrid",                                           │
│      "answer": "원인을 분석해보니, 다음과 같은 가능성이 있습니다...",    │
│      "reasoning": {                                                    │
│        "confidence": 1.0,                                              │
│        "cause": "CAUSE_COLLISION"                                      │
│      },                                                                │
│      "recommendation": {                                               │
│        "immediate": "주변 확인: 로봇 주변 장애물 제거",                 │
│        "steps": ["장애물 제거", "작업 영역 확인", "프로그램 검토"]       │
│      },                                                                │
│      "evidence": {                                                     │
│        "ontology_paths": ["C153 →[CAUSED_BY]→ CAUSE_COLLISION"],       │
│        "document_refs": [{                                             │
│          "doc_id": "ErrorCodes.pdf",                                   │
│          "relevance": 0.639,                                           │
│          "snippet": "C151 Tool orientation close to limits..."         │
│        }]                                                              │
│      }                                                                 │
│    }                                                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 설정 가이드

### 6.1 settings.yaml 전체 구조

```yaml
# 검색 설정
retrieval:
  top_k: 5
  similarity_threshold: 0.3    # OpenAI 임베딩은 0.3~0.6 범위

# 리랭커 설정 (2단계 검색)
rerank:
  enabled: true                # false면 1단계만 수행
  model: "bge-reranker-base"
  initial_top_k: 20            # 1단계 후보 수
  final_top_n: 5               # 최종 반환 수
```

### 6.2 설정 조정 가이드

| 상황 | 조정 방법 |
|------|----------|
| 검색 결과가 너무 적음 | `similarity_threshold` 낮추기 (0.2~0.3) |
| 검색 결과가 너무 많음 | `similarity_threshold` 높이기 (0.4~0.5) |
| 검색 속도가 느림 | `rerank.enabled: false` 또는 `initial_top_k` 줄이기 |
| 검색 정확도 향상 | `initial_top_k` 늘리기 (30~50) |

---

## 7. 테스트 결과

### 7.1 통합 테스트

```
질문: C153 에러가 발생했는데 어떻게 해결해야 하나요?

1. 분류: hybrid (신뢰도: 0.75)
   엔티티: ['C153']

2. 문서 검색: 1개 (reranked=True)
   - ErrorCodes.pdf: 0.639

3. 온톨로지 추론: 신뢰도=1.00
   결론: 5개

4. 응답 생성:
   trace_id: 45146785-31bb-4724-95f8-d283a60e8b5c
   abstain: False
   document_refs: 1개

=== 응답 ===
원인을 분석해보니, 다음과 같은 가능성이 있습니다.
- 추정 원인: Collision (충돌) (신뢰도: 100%)
- 추정 원인: Overload (과부하) (신뢰도: 100%)
- 권장 조치: 주변 확인: 로봇 주변 장애물 제거...
```

### 7.2 성능 측정

| 단계 | 소요 시간 | 비고 |
|------|----------|------|
| 분류 | ~50ms | QueryClassifier |
| 문서 검색 (1단계) | ~100ms | VectorStore (Bi-encoder) |
| 리랭킹 (2단계) | ~20초 (첫 실행) | 모델 로딩 포함 |
| 리랭킹 (이후) | ~200-500ms | 모델 캐시 사용 |
| 온톨로지 추론 | ~50ms | OntologyEngine |
| 응답 생성 | ~50ms | ResponseGenerator |
| **총 소요 시간** | **~500ms** | 모델 로딩 후 |

---

## 8. 폴더 구조 (변경 후)

```
ur5e-ontology-rag/
├── src/
│   ├── rag/
│   │   ├── __init__.py          [수정] HybridRetriever export
│   │   ├── hybrid_retriever.py  [신규] HybridRetriever 클래스
│   │   ├── query_classifier.py
│   │   ├── response_generator.py
│   │   └── ...
│   │
│   ├── embedding/
│   │   ├── vector_store.py      # search_with_rerank() 제공
│   │   ├── reranker.py          # CrossEncoderReranker
│   │   └── ...
│   │
│   └── api/
│       ├── main.py              [수정] get_retriever 싱글톤
│       └── routes/
│           └── chat.py          [수정] HybridRetriever 통합
│
├── configs/
│   └── settings.yaml            [수정] rerank 설정 추가
│
└── docs/
    └── steps/
        └── step_14_하이브리드검색기_통합.md  [신규]
```

---

## 9. 다음 단계 (최적화)

### 9.1 성능 최적화 아이디어

| 항목 | 현재 | 최적화 방안 |
|------|------|------------|
| 리랭커 로딩 | 첫 요청 시 로드 | 서버 시작 시 사전 로드 |
| 병렬 처리 | 순차 실행 | 온톨로지/문서검색 병렬화 |
| 캐싱 | 없음 | 자주 묻는 질문 캐싱 |

### 9.2 정확도 개선 아이디어

| 항목 | 현재 | 개선 방안 |
|------|------|----------|
| 임베딩 모델 | text-embedding-3-small | text-embedding-3-large |
| 리랭커 모델 | bge-reranker-base | bge-reranker-large |
| 청크 사이즈 | 512 | 실험을 통한 최적값 탐색 |

---

## 10. 요약

### 10.1 완료된 작업

- [x] HybridRetriever 클래스 구현
- [x] chat.py에 HybridRetriever 연결
- [x] ResponseGenerator에 document_refs 전달
- [x] settings.yaml에 rerank 설정 추가
- [x] 통합 테스트 완료

### 10.2 주요 변경점

1. **새로운 컴포넌트**: `HybridRetriever` - VectorStore + Reranker 통합
2. **파이프라인 확장**: 문서 검색 → 응답 생성 연결 완료
3. **설정 추가**: `rerank` 섹션으로 2단계 검색 제어 가능
4. **Evidence 강화**: 온톨로지 경로 + 문서 참조 모두 포함

### 10.3 영향 범위

| 영역 | 영향 |
|------|------|
| API 응답 | `evidence.document_refs`에 검색된 문서 포함 |
| 응답 품질 | 온톨로지 + 문서 근거로 답변 신뢰도 향상 |
| 성능 | 리랭킹으로 ~200-500ms 추가 (모델 로딩 후) |
