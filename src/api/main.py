# ============================================================
# src/api/main.py - FastAPI 메인 앱
# ============================================================
# UR5e RAG API 서버
#
# 실행 방법:
#   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
#
# API 문서:
#   - Swagger UI: http://localhost:8000/docs
#   - ReDoc: http://localhost:8000/redoc
# ============================================================

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.api.routes import health, query, search, info
from src.api.services.rag_service import RAGService


# ============================================================
# 앱 생명주기 관리
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 리소스 관리"""
    # 시작 시
    print("=" * 60)
    print("[*] Starting UR5e RAG API Server...")
    print("=" * 60)

    app.state.rag_service = RAGService()

    print("\n[OK] UR5e RAG API Server ready!")
    print("=" * 60)
    print("  Swagger UI: http://localhost:8000/docs")
    print("  ReDoc:      http://localhost:8000/redoc")
    print("=" * 60)

    yield

    # 종료 시
    print("\n[*] Shutting down UR5e RAG API Server...")
    app.state.rag_service.close()
    print("[OK] Server stopped")


# ============================================================
# FastAPI 앱 생성
# ============================================================

app = FastAPI(
    title="UR5e RAG API",
    description="""
## UR5e 로봇 에러 해결을 위한 RAG API

이 API는 UR5e 협동 로봇의 에러 해결 및 유지보수를 지원합니다.

### 주요 기능

- **질의 (Query)**: 자연어 질문에 대한 답변 생성
- **분석 (Analyze)**: 질문 분석 (에러 코드, 부품명 감지)
- **검색 (Search)**: 관련 문서 검색 (LLM 생성 없이)
- **정보 (Info)**: 에러 코드/부품 정보 조회

### 기술 스택

- **VectorDB**: ChromaDB (의미 기반 검색)
- **GraphDB**: Neo4j (관계 기반 검색)
- **LLM**: OpenAI GPT-4o-mini
- **검증**: Verifier (Hallucination 방지)

### 검색 전략

| 전략 | 설명 |
|------|------|
| `graph_first` | GraphDB 우선 검색 (에러 코드/부품 감지 시) |
| `vector_first` | VectorDB 우선 검색 (일반 질문) |
| `hybrid` | 둘 다 동시 검색 후 병합 |

### 검증 상태

| 상태 | 설명 |
|------|------|
| `verified` | 충분한 근거 있음 |
| `partial` | 일부 근거만 있음 |
| `unverified` | 근거 없음 |
| `insufficient` | 컨텍스트 부족 |
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# CORS 설정
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 라우터 등록
# ============================================================

# 헬스체크 (루트 레벨)
app.include_router(health.router, tags=["Health"])

# API v1 라우터
app.include_router(query.router, prefix="/api/v1", tags=["Query"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(info.router, prefix="/api/v1", tags=["Info"])


# ============================================================
# 루트 엔드포인트
# ============================================================

@app.get("/", tags=["Root"])
async def root():
    """
    API 루트

    서버 정보와 API 문서 링크를 반환합니다.
    """
    return {
        "name": "UR5e RAG API",
        "version": "1.0.0",
        "description": "UR5e 로봇 에러 해결을 위한 RAG API",
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "health": "/health",
            "query": "/api/v1/query",
            "analyze": "/api/v1/analyze",
            "search": "/api/v1/search",
            "errors": "/api/v1/errors",
            "components": "/api/v1/components"
        }
    }


# ============================================================
# 직접 실행 시
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
