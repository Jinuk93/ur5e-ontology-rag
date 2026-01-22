# Phase 5: 기본 RAG

> **상태**: ✅ 완료
> **도메인**: 검색 레이어 (Retrieval)
> **목표**: 최소 동작 버전 (MVP) RAG 파이프라인 구현

---

## 1. 개요

질문 → 검색 → LLM 답변 생성의 기본 RAG 파이프라인을 구현하는 단계.
벡터 검색 기반의 최소 기능 버전을 먼저 완성하고, 이후 온톨로지를 통합.

---

## 2. 태스크

| # | 태스크 | 상태 |
|---|--------|------|
| 1 | Query Analyzer 구현 | ✅ |
| 2 | Retriever 구현 (벡터 검색) | ✅ |
| 3 | Generator 구현 (LLM 답변) | ✅ |
| 4 | RAG Pipeline 통합 | ✅ |
| 5 | 프롬프트 엔지니어링 | ✅ |

---

## 3. RAG 파이프라인

### 3.1 아키텍처

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Query     │──▶│  Retriever  │──▶│  Generator  │──▶│   Answer    │
│  (사용자)    │   │ (벡터 검색)  │   │  (LLM 생성)  │   │  (최종 답변) │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  ChromaDB   │
                  │  (벡터 DB)   │
                  └─────────────┘
```

### 3.2 처리 흐름

```
1. 사용자 질문 입력
   └─▶ "C154A3 에러의 원인과 해결 방법은?"

2. Query Analyzer
   └─▶ 질문 타입 분류 (error_code, component, general)
   └─▶ 키워드 추출 (C154A3)

3. Retriever
   └─▶ 질문 임베딩 생성
   └─▶ ChromaDB에서 유사 청크 검색 (top_k=5)
   └─▶ 관련 문서 반환

4. Generator
   └─▶ 프롬프트 구성 (질문 + 검색 결과)
   └─▶ LLM 호출 (gpt-4o-mini)
   └─▶ 답변 생성

5. 응답 반환
   └─▶ 답변 + 출처 (citation)
```

---

## 4. 구현

### 4.1 Query Analyzer

```python
# src/rag/query_analyzer.py

class QueryAnalyzer:
    def __init__(self):
        self.error_pattern = re.compile(r'[CSJ]\d{1,2}[A-F0-9]{3,4}', re.I)

    def analyze(self, query: str) -> QueryAnalysis:
        """질문 분석"""
        query_type = self._classify_type(query)
        entities = self._extract_entities(query)
        keywords = self._extract_keywords(query)

        return QueryAnalysis(
            original_query=query,
            query_type=query_type,
            entities=entities,
            keywords=keywords
        )

    def _classify_type(self, query: str) -> str:
        if self.error_pattern.search(query):
            return "error_code"
        elif any(comp in query.lower() for comp in ["joint", "control", "tool"]):
            return "component"
        return "general"
```

### 4.2 Retriever

```python
# src/rag/retriever.py

class Retriever:
    def __init__(self, vector_store: VectorStore, embedder: Embedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """벡터 유사도 기반 검색"""
        query_embedding = self.embedder.embed(query)
        results = self.vector_store.search(query_embedding, top_k)

        return [
            RetrievalResult(
                chunk_id=r.id,
                text=r.document,
                score=1 - r.distance,  # cosine distance → similarity
                metadata=r.metadata
            )
            for r in results
        ]
```

### 4.3 Generator

```python
# src/rag/generator.py

class Generator:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI()
        self.model = model

    def generate(self, query: str, context: List[str]) -> GeneratorResponse:
        """LLM 기반 답변 생성"""
        prompt = self._build_prompt(query, context)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return self._parse_response(response)

    def _build_prompt(self, query: str, context: List[str]) -> str:
        context_str = "\n\n".join([f"[문서 {i+1}]\n{c}" for i, c in enumerate(context)])
        return f"""
질문: {query}

참고 문서:
{context_str}

위 문서를 참고하여 질문에 답변하세요.
답변에는 반드시 출처(문서 번호)를 포함하세요.
"""
```

### 4.4 시스템 프롬프트

```
당신은 UR5e 로봇 기술 지원 전문가입니다.

규칙:
1. 제공된 문서만을 기반으로 답변하세요.
2. 문서에 없는 내용은 "문서에서 확인되지 않습니다"라고 답하세요.
3. 모든 답변에 출처를 명시하세요.
4. 안전과 관련된 내용은 공식 매뉴얼 확인을 권장하세요.

답변 형식:
- 원인: [에러 원인 설명]
- 해결 방법: [단계별 해결 방법]
- 출처: [참조 문서]
```

---

## 5. 산출물

### 5.1 파일 목록

| 파일 | 내용 | Lines |
|------|------|-------|
| `src/rag/query_analyzer.py` | 질문 분석기 | ~100 |
| `src/rag/retriever.py` | 벡터 검색 | ~80 |
| `src/rag/generator.py` | 답변 생성 | ~120 |
| `src/rag/pipeline.py` | 파이프라인 통합 | ~60 |

### 5.2 응답 스키마

```json
{
  "answer": "C154A3는 Control Box 팬 오작동 에러입니다...",
  "sources": [
    {
      "doc_id": "error_codes",
      "page": 15,
      "chunk_id": "error_codes_p015_c002"
    }
  ],
  "query_type": "error_code",
  "confidence": 0.85
}
```

---

## 6. 테스트 결과

### 6.1 샘플 QA

| 질문 | 응답 품질 |
|------|----------|
| C154A3 에러의 원인은? | ✅ 정확 |
| Control Box의 역할은? | ✅ 정확 |
| Joint 3 교체 방법은? | ⚠️ 부분 정확 |

### 6.2 초기 성능

| 지표 | 값 |
|------|-----|
| 응답 시간 | ~2초 |
| Recall@5 | ~75% |
| 답변 정확도 | ~70% |

---

## 7. 검증 체크리스트

- [x] 질문 → 검색 → 답변 흐름 동작
- [x] 에러코드 질문 처리 가능
- [x] 출처 citation 포함
- [x] 응답 시간 < 5초

---

## 8. 다음 단계

→ [Phase 06: 온톨로지 추론](06_온톨로지추론.md)

---

**Phase**: 5 / 19
**작성일**: 2026-01-22
