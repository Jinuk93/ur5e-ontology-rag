# Phase 8: API 서버

> **상태**: ✅ 완료
> **도메인**: 서빙 레이어 (Serving)
> **목표**: FastAPI 기반 REST API 구현

---

## 1. 개요

RAG 파이프라인을 HTTP API로 노출하여 외부 클라이언트(대시보드, 외부 시스템)에서
질의응답 기능을 사용할 수 있도록 구현하는 단계.

---

## 2. 태스크

| # | 태스크 | 상태 |
|---|--------|------|
| 1 | FastAPI 프로젝트 구조 설계 | ✅ |
| 2 | 엔드포인트 설계 | ✅ |
| 3 | 요청/응답 스키마 정의 | ✅ |
| 4 | 서비스 레이어 구현 | ✅ |
| 5 | 에러 처리 및 로깅 | ✅ |

---

## 3. API 설계

### 3.1 엔드포인트 목록

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/query` | RAG 질의응답 |
| GET | `/api/v1/search` | 벡터 검색만 |
| GET | `/api/v1/health` | 상태 점검 |
| GET | `/api/v1/graph/error/{code}` | 에러코드 그래프 조회 |
| GET | `/api/v1/graph/component/{name}` | 컴포넌트 그래프 조회 |
| GET | `/api/v1/evidence/{trace_id}` | 근거 조회 (Phase 12 추가) |

### 3.2 프로젝트 구조

```
src/api/
├── main.py                 # FastAPI 앱 진입점
├── routes/
│   ├── __init__.py
│   ├── query.py           # /query 엔드포인트
│   ├── search.py          # /search 엔드포인트
│   ├── graph.py           # /graph/* 엔드포인트
│   ├── health.py          # /health 엔드포인트
│   └── evidence.py        # /evidence 엔드포인트 (Phase 12)
├── schemas/
│   ├── __init__.py
│   ├── query.py           # 요청/응답 스키마
│   ├── search.py
│   └── common.py
├── services/
│   ├── __init__.py
│   ├── rag_service.py     # RAG 비즈니스 로직
│   └── graph_service.py   # 그래프 비즈니스 로직
└── dependencies.py        # 의존성 주입
```

---

## 4. 구현

### 4.1 메인 앱

```python
# src/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import query, search, graph, health

app = FastAPI(
    title="UR5e RAG API",
    description="UR5e 로봇 에러 진단 RAG 시스템 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])
```

### 4.2 Query 엔드포인트

```python
# src/api/routes/query.py

from fastapi import APIRouter, Depends
from src.api.schemas.query import QueryRequest, QueryResponse
from src.api.services.rag_service import RAGService

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """RAG 질의응답"""
    result = await rag_service.query(
        question=request.question,
        top_k=request.top_k
    )
    return QueryResponse(
        answer=result.answer,
        sources=result.sources,
        verification=result.verification,
        trace_id=result.trace_id
    )
```

### 4.3 스키마 정의

```python
# src/api/schemas/query.py

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class QueryRequest(BaseModel):
    question: str = Field(..., description="질문 텍스트")
    top_k: int = Field(default=5, ge=1, le=20, description="검색 결과 수")

class Source(BaseModel):
    doc_id: str
    page: int
    chunk_id: str
    score: float
    text_preview: str

class VerificationInfo(BaseModel):
    status: str
    confidence: float
    warnings: List[str]

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    verification: VerificationInfo
    trace_id: str
    processing_time_ms: int
```

### 4.4 서비스 레이어

```python
# src/api/services/rag_service.py

class RAGService:
    def __init__(
        self,
        retriever: HybridRetriever,
        generator: Generator,
        verifier: Verifier
    ):
        self.retriever = retriever
        self.generator = generator
        self.verifier = verifier

    async def query(self, question: str, top_k: int = 5) -> RAGResult:
        """RAG 파이프라인 실행"""
        # 1. 검색
        retrieval_result = await self.retriever.retrieve(question, top_k)

        # 2. 답변 생성
        generation_result = await self.generator.generate(
            question, retrieval_result.contexts
        )

        # 3. 검증
        verification_result = await self.verifier.verify(
            generation_result.causes,
            generation_result.actions,
            retrieval_result.evidence
        )

        return RAGResult(
            answer=generation_result.answer,
            sources=retrieval_result.sources,
            verification=verification_result,
            trace_id=str(uuid.uuid4())
        )
```

---

## 5. 산출물

### 5.1 파일 목록

| 파일 | 내용 | Lines |
|------|------|-------|
| `src/api/main.py` | FastAPI 앱 | ~50 |
| `src/api/routes/query.py` | Query 라우트 | ~40 |
| `src/api/routes/search.py` | Search 라우트 | ~30 |
| `src/api/routes/graph.py` | Graph 라우트 | ~50 |
| `src/api/routes/health.py` | Health 라우트 | ~20 |
| `src/api/schemas/*.py` | Pydantic 스키마 | ~150 |
| `src/api/services/*.py` | 서비스 레이어 | ~200 |

### 5.2 API 문서

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## 6. 테스트

### 6.1 API 테스트 (curl)

```bash
# Health Check
curl http://localhost:8000/api/v1/health

# Query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "C154A3 에러의 원인은?"}'

# Search
curl "http://localhost:8000/api/v1/search?q=fan+malfunction&top_k=5"
```

### 6.2 응답 예시

```json
{
  "answer": "C154A3는 Control Box 팬 오작동 에러입니다...",
  "sources": [
    {
      "doc_id": "error_codes",
      "page": 15,
      "chunk_id": "error_codes_p015_c002",
      "score": 0.92,
      "text_preview": "Error C154A3: Control box fan..."
    }
  ],
  "verification": {
    "status": "pass",
    "confidence": 0.88,
    "warnings": []
  },
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "processing_time_ms": 1850
}
```

---

## 7. 검증 체크리스트

- [x] /query 엔드포인트 동작
- [x] /search 엔드포인트 동작
- [x] /health 엔드포인트 동작
- [x] Swagger 문서 자동 생성
- [x] CORS 설정 완료
- [x] 에러 처리 구현

---

## 8. 다음 단계

→ [Phase 09: UI 대시보드](09_UI대시보드.md)

---

**Phase**: 8 / 19
**작성일**: 2026-01-22
