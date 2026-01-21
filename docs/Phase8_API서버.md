# Phase 8: API 서버 구축

> **목표:** FastAPI 기반 RESTful API 서버 구축
>
> **핵심 학습:** FastAPI, 엔드포인트 설계, 비동기 처리
>
> **난이도:** ★★★☆☆

---

## 1. Phase 7 완료 및 Phase 8 필요성

### 1.1 현재 상황

```
[Phase 7까지 완성된 것]
├── VectorDB (ChromaDB) - 문서 검색
├── GraphDB (Neo4j) - 관계 기반 검색
├── Hybrid Retriever - 통합 검색
├── Verifier - 답변 검증
└── CLI 인터페이스 (scripts/run_rag_v3.py)

[문제점]
├── CLI로만 사용 가능
├── 다른 시스템과 연동 불가
├── 웹/모바일 앱에서 사용 불가
└── 외부 서비스 통합 어려움
```

### 1.2 Phase 8 해결 방향

```
[Phase 8 - API 서버]
├── RESTful API 엔드포인트
├── 웹/앱에서 HTTP 요청으로 사용
├── 다른 시스템과 쉽게 연동
└── Swagger UI로 API 문서화
```

---

## 2. Phase 8 목표

### 2.1 API 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     Phase 8 API Server                       │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    FastAPI App                       │    │
│  │                                                      │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │
│  │  │  /health    │  │  /query     │  │  /analyze   │ │    │
│  │  │  헬스체크   │  │  RAG 질의   │  │  질문 분석  │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │    │
│  │                                                      │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │
│  │  │  /search    │  │  /errors    │  │  /components│ │    │
│  │  │  검색만     │  │  에러 목록  │  │  부품 목록  │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              RAG Pipeline V3 (Phase 7)               │    │
│  │  ├── HybridRetriever                                │    │
│  │  ├── Verifier                                       │    │
│  │  ├── PromptBuilder                                  │    │
│  │  └── Generator                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│          ┌────────────────┼────────────────┐                │
│          ▼                ▼                ▼                │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│    │ ChromaDB │    │  Neo4j   │    │  OpenAI  │            │
│    │ (Vector) │    │ (Graph)  │    │  (LLM)   │            │
│    └──────────┘    └──────────┘    └──────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 핵심 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서버 상태 확인 |
| `/query` | POST | RAG 질의 (메인) |
| `/analyze` | POST | 질문 분석만 |
| `/search` | POST | 검색만 (답변 생성 X) |
| `/errors` | GET | 에러 코드 목록 |
| `/errors/{code}` | GET | 특정 에러 정보 |
| `/components` | GET | 부품 목록 |

---

## 3. 파일 구조 (계획)

```
src/
├── rag/                      ← 기존
└── api/                      ← 신규
    ├── __init__.py
    ├── main.py               ← FastAPI 앱
    ├── routes/               ← 라우터
    │   ├── __init__.py
    │   ├── health.py         ← 헬스체크
    │   ├── query.py          ← RAG 질의
    │   ├── search.py         ← 검색
    │   └── info.py           ← 에러/부품 정보
    ├── schemas/              ← Pydantic 모델
    │   ├── __init__.py
    │   ├── request.py        ← 요청 스키마
    │   └── response.py       ← 응답 스키마
    └── services/             ← 비즈니스 로직
        ├── __init__.py
        └── rag_service.py    ← RAG 서비스 래퍼

scripts/
└── run_api.py                ← 서버 실행 스크립트
```

---

## 4. 상세 구현 계획

### 4.1 Pydantic 스키마 (`schemas/`)

**요청 스키마 (request.py):**

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class QueryRequest(BaseModel):
    """RAG 질의 요청"""
    question: str = Field(..., description="사용자 질문", min_length=1)
    top_k: int = Field(default=5, ge=1, le=20, description="검색 결과 수")
    include_sources: bool = Field(default=True, description="출처 포함 여부")
    include_citation: bool = Field(default=True, description="인용 정보 포함")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "C4A15 에러가 발생했어요. 어떻게 해결하나요?",
                "top_k": 5,
                "include_sources": True,
                "include_citation": True
            }
        }

class AnalyzeRequest(BaseModel):
    """질문 분석 요청"""
    question: str = Field(..., description="분석할 질문")

class SearchRequest(BaseModel):
    """검색 요청 (답변 생성 없이)"""
    question: str = Field(..., description="검색 질문")
    top_k: int = Field(default=5, ge=1, le=20)
    strategy: Optional[str] = Field(
        default=None,
        description="검색 전략 (graph_first, vector_first, hybrid)"
    )
```

**응답 스키마 (response.py):**

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class VerificationStatusEnum(str, Enum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    INSUFFICIENT = "insufficient"

class SourceInfo(BaseModel):
    """출처 정보"""
    name: str
    type: str  # "graph" or "vector"
    score: float

class VerificationInfo(BaseModel):
    """검증 정보"""
    status: VerificationStatusEnum
    confidence: float
    evidence_count: int
    warnings: List[str] = []

class QueryResponse(BaseModel):
    """RAG 질의 응답"""
    answer: str = Field(..., description="생성된 답변")
    verification: VerificationInfo
    sources: Optional[List[SourceInfo]] = None
    query_analysis: Optional[Dict[str, Any]] = None
    latency_ms: float = Field(..., description="처리 시간 (밀리초)")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "C4A15 에러는 Joint 3과의 통신 손실입니다...",
                "verification": {
                    "status": "verified",
                    "confidence": 0.85,
                    "evidence_count": 2,
                    "warnings": []
                },
                "sources": [
                    {"name": "C4A15", "type": "graph", "score": 1.0}
                ],
                "latency_ms": 3500
            }
        }

class AnalyzeResponse(BaseModel):
    """질문 분석 응답"""
    original_query: str
    error_codes: List[str]
    components: List[str]
    query_type: str
    search_strategy: str

class SearchResult(BaseModel):
    """검색 결과 항목"""
    content: str
    source_type: str
    score: float
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    """검색 응답"""
    results: List[SearchResult]
    query_analysis: AnalyzeResponse
    total_count: int
    latency_ms: float

class ErrorCodeInfo(BaseModel):
    """에러 코드 정보"""
    code: str
    description: str
    causes: List[str] = []
    solutions: List[str] = []
    related_components: List[str] = []

class ComponentInfo(BaseModel):
    """부품 정보"""
    name: str
    aliases: List[str] = []
    related_errors: List[str] = []

class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    version: str
    components: Dict[str, str]
```

### 4.2 RAG 서비스 (`services/rag_service.py`)

**목적:** RAG 파이프라인을 API에서 사용하기 쉽게 래핑

```python
import time
from typing import Optional, Dict, Any, List
from src.rag.hybrid_retriever import HybridRetriever
from src.rag.verifier import Verifier, VerificationStatus
from src.rag.prompt_builder import PromptBuilder
from src.rag.generator import Generator
from src.rag.retriever import RetrievalResult
from src.api.schemas.response import (
    QueryResponse, AnalyzeResponse, SearchResponse,
    VerificationInfo, SourceInfo, SearchResult
)

class RAGService:
    """
    RAG 서비스 (Singleton)

    API에서 RAG 파이프라인을 사용하기 위한 서비스 클래스
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.hybrid_retriever = HybridRetriever(verbose=False)
        self.verifier = Verifier()
        self.prompt_builder = PromptBuilder()
        self.generator = Generator()
        self._initialized = True

    def query(
        self,
        question: str,
        top_k: int = 5,
        include_sources: bool = True,
        include_citation: bool = True,
    ) -> QueryResponse:
        """RAG 질의 실행"""
        start_time = time.time()

        # 1. 검색
        hybrid_results, analysis = self.hybrid_retriever.retrieve(
            question, top_k=top_k
        )

        # 2. 사전 검증
        pre_verification = self.verifier.verify_before_generation(
            analysis, hybrid_results
        )

        # 검증 실패 시 안전 응답
        if not pre_verification.is_safe_to_answer:
            safe_response = self.verifier.get_safe_response(
                pre_verification, analysis
            )
            return QueryResponse(
                answer=safe_response,
                verification=VerificationInfo(
                    status=pre_verification.status.value,
                    confidence=pre_verification.confidence,
                    evidence_count=pre_verification.evidence_count,
                    warnings=pre_verification.warnings
                ),
                sources=None,
                query_analysis=self._to_analysis_dict(analysis),
                latency_ms=(time.time() - start_time) * 1000
            )

        # 3. 컨텍스트 변환
        contexts = self._convert_contexts(hybrid_results)

        # 4. LLM 생성
        messages = self.prompt_builder.build(question, contexts)
        result = self.generator.generate(messages)
        answer = result.answer

        # 5. 사후 검증
        post_verification = self.verifier.verify_after_generation(
            answer, hybrid_results, analysis
        )

        # 6. 경고/출처 추가
        if post_verification.status == VerificationStatus.PARTIAL:
            if post_verification.warnings:
                answer = self.verifier.add_warning(answer, post_verification)

        if include_citation:
            answer = self.verifier.add_citation(answer, post_verification)

        # 출처 정보 구성
        sources = None
        if include_sources:
            sources = [
                SourceInfo(
                    name=hr.metadata.get("entity_name", hr.metadata.get("chunk_id", "unknown")),
                    type=hr.source_type,
                    score=hr.score
                )
                for hr in hybrid_results[:5]
            ]

        return QueryResponse(
            answer=answer,
            verification=VerificationInfo(
                status=post_verification.status.value,
                confidence=post_verification.confidence,
                evidence_count=post_verification.evidence_count,
                warnings=post_verification.warnings
            ),
            sources=sources,
            query_analysis=self._to_analysis_dict(analysis),
            latency_ms=(time.time() - start_time) * 1000
        )

    def analyze(self, question: str) -> AnalyzeResponse:
        """질문 분석만 수행"""
        analysis = self.hybrid_retriever.query_analyzer.analyze(question)
        return AnalyzeResponse(
            original_query=analysis.original_query,
            error_codes=analysis.error_codes,
            components=analysis.components,
            query_type=analysis.query_type,
            search_strategy=analysis.search_strategy
        )

    def search(
        self,
        question: str,
        top_k: int = 5,
        strategy: Optional[str] = None,
    ) -> SearchResponse:
        """검색만 수행 (LLM 생성 없이)"""
        start_time = time.time()

        hybrid_results, analysis = self.hybrid_retriever.retrieve(
            question, top_k=top_k, strategy=strategy
        )

        results = [
            SearchResult(
                content=hr.content[:500],  # 미리보기용 500자
                source_type=hr.source_type,
                score=hr.score,
                metadata=hr.metadata
            )
            for hr in hybrid_results
        ]

        return SearchResponse(
            results=results,
            query_analysis=AnalyzeResponse(
                original_query=analysis.original_query,
                error_codes=analysis.error_codes,
                components=analysis.components,
                query_type=analysis.query_type,
                search_strategy=analysis.search_strategy
            ),
            total_count=len(results),
            latency_ms=(time.time() - start_time) * 1000
        )

    def _convert_contexts(self, hybrid_results):
        """HybridResult를 RetrievalResult로 변환"""
        contexts = []
        for hr in hybrid_results:
            metadata = hr.metadata.copy()
            if hr.source_type == "graph":
                metadata["doc_type"] = "graph_result"
                metadata["source"] = "GraphDB (Neo4j)"
            else:
                metadata.setdefault("doc_type", "vector_result")
                metadata.setdefault("source", "VectorDB (ChromaDB)")

            contexts.append(RetrievalResult(
                chunk_id=metadata.get("chunk_id", f"graph_{hr.metadata.get('entity_name', 'unknown')}"),
                content=hr.content,
                metadata=metadata,
                score=hr.score,
            ))
        return contexts

    def _to_analysis_dict(self, analysis) -> Dict[str, Any]:
        """QueryAnalysis를 dict로 변환"""
        return {
            "error_codes": analysis.error_codes,
            "components": analysis.components,
            "query_type": analysis.query_type,
            "search_strategy": analysis.search_strategy
        }

    def close(self):
        """리소스 정리"""
        self.hybrid_retriever.close()
```

### 4.3 FastAPI 메인 앱 (`main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.routes import health, query, search, info
from src.api.services.rag_service import RAGService

# 앱 생명주기 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시
    print("[*] Starting UR5e RAG API Server...")
    app.state.rag_service = RAGService()
    print("[OK] RAG Service initialized")
    yield
    # 종료 시
    print("[*] Shutting down...")
    app.state.rag_service.close()
    print("[OK] RAG Service closed")

# FastAPI 앱 생성
app = FastAPI(
    title="UR5e RAG API",
    description="""
    UR5e 로봇 에러 해결을 위한 RAG (Retrieval-Augmented Generation) API

    ## 기능
    - **질의 (Query)**: 자연어 질문에 대한 답변 생성
    - **분석 (Analyze)**: 질문 분석 (에러 코드, 부품명 감지)
    - **검색 (Search)**: 관련 문서 검색
    - **정보 (Info)**: 에러 코드/부품 정보 조회

    ## 기술 스택
    - VectorDB: ChromaDB
    - GraphDB: Neo4j
    - LLM: OpenAI GPT-4o-mini
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health.router, tags=["Health"])
app.include_router(query.router, prefix="/api/v1", tags=["Query"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(info.router, prefix="/api/v1", tags=["Info"])

# 루트 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "UR5e RAG API Server",
        "docs": "/docs",
        "version": "1.0.0"
    }
```

### 4.4 라우터 구현 (`routes/`)

**헬스체크 (health.py):**

```python
from fastapi import APIRouter
from src.api.schemas.response import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """서버 상태 확인"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        components={
            "vectordb": "connected",
            "graphdb": "connected",
            "llm": "available"
        }
    )
```

**질의 (query.py):**

```python
from fastapi import APIRouter, Request, HTTPException
from src.api.schemas.request import QueryRequest, AnalyzeRequest
from src.api.schemas.response import QueryResponse, AnalyzeResponse

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest):
    """
    RAG 질의 실행

    사용자 질문을 분석하고, 관련 정보를 검색한 후, LLM으로 답변을 생성합니다.

    - **question**: 사용자 질문
    - **top_k**: 검색할 결과 수 (기본값: 5)
    - **include_sources**: 출처 정보 포함 여부
    - **include_citation**: 인용 정보 포함 여부
    """
    try:
        rag_service = request.app.state.rag_service
        response = rag_service.query(
            question=body.question,
            top_k=body.top_k,
            include_sources=body.include_sources,
            include_citation=body.include_citation,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: Request, body: AnalyzeRequest):
    """
    질문 분석

    질문에서 에러 코드, 부품명을 감지하고 검색 전략을 결정합니다.
    """
    try:
        rag_service = request.app.state.rag_service
        return rag_service.analyze(body.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**검색 (search.py):**

```python
from fastapi import APIRouter, Request, HTTPException
from src.api.schemas.request import SearchRequest
from src.api.schemas.response import SearchResponse

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search(request: Request, body: SearchRequest):
    """
    문서 검색 (LLM 생성 없이)

    관련 문서만 검색하고 결과를 반환합니다.
    """
    try:
        rag_service = request.app.state.rag_service
        return rag_service.search(
            question=body.question,
            top_k=body.top_k,
            strategy=body.strategy,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**정보 (info.py):**

```python
from fastapi import APIRouter, Request, HTTPException, Path
from typing import List
from src.api.schemas.response import ErrorCodeInfo, ComponentInfo

router = APIRouter()

@router.get("/errors", response_model=List[str])
async def list_errors(request: Request):
    """에러 코드 목록 조회"""
    # GraphDB에서 모든 에러 코드 조회
    # 간단 버전: 하드코딩된 범위 반환
    return [f"C{i}" for i in range(0, 56)]

@router.get("/errors/{code}", response_model=ErrorCodeInfo)
async def get_error(
    request: Request,
    code: str = Path(..., description="에러 코드 (예: C4A15)")
):
    """특정 에러 코드 정보 조회"""
    rag_service = request.app.state.rag_service

    # 검색으로 에러 정보 가져오기
    result = rag_service.search(f"{code} 에러 정보", top_k=3)

    if not result.results:
        raise HTTPException(status_code=404, detail=f"Error code {code} not found")

    # 첫 번째 결과에서 정보 추출 (간단 버전)
    return ErrorCodeInfo(
        code=code,
        description=result.results[0].content[:200],
        causes=[],
        solutions=[],
        related_components=[]
    )

@router.get("/components", response_model=List[str])
async def list_components():
    """부품 목록 조회"""
    # 알려진 부품 목록 반환
    return [
        "Control Box", "Teach Pendant", "Robot Arm",
        "Safety Control Board", "Motherboard",
        "Joint 0", "Joint 1", "Joint 2", "Joint 3", "Joint 4", "Joint 5",
        "Power Supply", "Emergency Stop"
    ]
```

---

## 5. API 엔드포인트 상세

### 5.1 POST /api/v1/query

**요청:**
```json
{
  "question": "C4A15 에러가 발생했어요. 어떻게 해결하나요?",
  "top_k": 5,
  "include_sources": true,
  "include_citation": true
}
```

**응답:**
```json
{
  "answer": "C4A15 에러는 Joint 3과의 통신 손실입니다...\n\n---\n**출처:**\n  - C4A15\n🟢 신뢰도: 85%",
  "verification": {
    "status": "verified",
    "confidence": 0.85,
    "evidence_count": 2,
    "warnings": []
  },
  "sources": [
    {"name": "C4A15", "type": "graph", "score": 1.0},
    {"name": "error_codes_C4_001", "type": "vector", "score": 0.75}
  ],
  "query_analysis": {
    "error_codes": ["C4A15"],
    "components": [],
    "query_type": "error_resolution",
    "search_strategy": "graph_first"
  },
  "latency_ms": 3500
}
```

### 5.2 POST /api/v1/analyze

**요청:**
```json
{
  "question": "Control Box에서 C50 에러가 발생했어요"
}
```

**응답:**
```json
{
  "original_query": "Control Box에서 C50 에러가 발생했어요",
  "error_codes": ["C50"],
  "components": ["control box"],
  "query_type": "error_resolution",
  "search_strategy": "graph_first"
}
```

### 5.3 POST /api/v1/search

**요청:**
```json
{
  "question": "조인트 통신 에러",
  "top_k": 3,
  "strategy": "hybrid"
}
```

**응답:**
```json
{
  "results": [
    {
      "content": "C4A15: Communication with joint 3 lost...",
      "source_type": "graph",
      "score": 0.95,
      "metadata": {"entity_name": "C4A15"}
    }
  ],
  "query_analysis": {...},
  "total_count": 3,
  "latency_ms": 500
}
```

---

## 6. 실행 방법

### 6.1 개발 서버

```bash
# 방법 1: uvicorn 직접 실행
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 방법 2: 스크립트 실행
python scripts/run_api.py
```

### 6.2 run_api.py

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

### 6.3 API 문서 접속

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 7. 테스트 시나리오

### 7.1 cURL 테스트

```bash
# 헬스체크
curl http://localhost:8000/health

# RAG 질의
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "C4A15 에러 해결법"}'

# 질문 분석
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "Control Box 에러 목록"}'

# 검색만
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"question": "조인트 통신", "top_k": 3}'
```

### 7.2 Python 테스트

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# RAG 질의
response = requests.post(
    f"{BASE_URL}/query",
    json={"question": "C4A15 에러가 발생했어요"}
)
print(response.json())
```

---

## 8. 구현 순서

### Step 1: 프로젝트 구조 생성
1. `src/api/` 디렉토리 생성
2. 필요한 `__init__.py` 파일 생성

### Step 2: 스키마 정의
1. `schemas/request.py` - 요청 모델
2. `schemas/response.py` - 응답 모델

### Step 3: RAG 서비스
1. `services/rag_service.py` - RAG 파이프라인 래퍼

### Step 4: 라우터 구현
1. `routes/health.py` - 헬스체크
2. `routes/query.py` - 질의/분석
3. `routes/search.py` - 검색
4. `routes/info.py` - 정보 조회

### Step 5: 메인 앱
1. `main.py` - FastAPI 앱 설정
2. 라우터 등록, CORS, 미들웨어

### Step 6: 테스트
1. 서버 실행
2. Swagger UI에서 테스트
3. cURL/Python 테스트

---

## 9. 체크리스트

- [ ] `src/api/` 디렉토리 구조 생성
- [ ] `schemas/request.py` 구현
- [ ] `schemas/response.py` 구현
- [ ] `services/rag_service.py` 구현
- [ ] `routes/health.py` 구현
- [ ] `routes/query.py` 구현
- [ ] `routes/search.py` 구현
- [ ] `routes/info.py` 구현
- [ ] `main.py` 구현
- [ ] `scripts/run_api.py` 구현
- [ ] 테스트 (Swagger UI, cURL)

---

## 10. 의존성

```
# requirements.txt에 추가
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
```

---

## 11. Phase 9 Preview

Phase 8 완료 후, Phase 9에서는:

```
Phase 9: UI 대시보드 (Streamlit)
├── 웹 기반 채팅 인터페이스
├── 검색 결과 시각화
├── 에러 코드 브라우저
└── 시스템 상태 대시보드
```
