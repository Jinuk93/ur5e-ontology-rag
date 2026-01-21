# Phase 8 완료 보고서: API 서버 구축

> **완료일:** 2026-01-21
>
> **목표:** FastAPI 기반 RESTful API 서버 구축
>
> **난이도:** ★★★☆☆

---

## 1. 구현 개요

### 1.1 Phase 8 목표

| 항목 | 설명 |
|------|------|
| **목적** | CLI 인터페이스를 HTTP API로 확장, 외부 시스템 연동 가능 |
| **핵심 기능** | RESTful 엔드포인트, Swagger 문서화, CORS 지원 |
| **주요 파일** | `src/api/`, `scripts/run_api.py` |

### 1.2 Phase 7 vs Phase 8

| 상황 | Phase 7 | Phase 8 |
|------|---------|---------|
| 접근 방식 | CLI 전용 (`run_rag_v3.py`) | HTTP API (`/api/v1/*`) |
| 외부 연동 | 불가능 | 가능 (REST API) |
| 문서화 | 수동 | Swagger UI / ReDoc 자동 |
| 웹/앱 통합 | 불가능 | 가능 |

---

## 2. 구현 완료 항목

### 2.1 신규 파일

| 파일 | 설명 | 라인 수 |
|------|------|--------|
| `src/api/__init__.py` | API 패키지 초기화 | ~5 |
| `src/api/main.py` | FastAPI 앱 (라우터, CORS, Lifespan) | ~175 |
| `src/api/schemas/__init__.py` | 스키마 패키지 | ~5 |
| `src/api/schemas/request.py` | Pydantic 요청 모델 | ~95 |
| `src/api/schemas/response.py` | Pydantic 응답 모델 | ~135 |
| `src/api/services/__init__.py` | 서비스 패키지 | ~5 |
| `src/api/services/rag_service.py` | RAG 서비스 래퍼 (Singleton) | ~200 |
| `src/api/routes/__init__.py` | 라우터 패키지 | ~5 |
| `src/api/routes/health.py` | 헬스체크 엔드포인트 | ~40 |
| `src/api/routes/query.py` | RAG 질의/분석 엔드포인트 | ~80 |
| `src/api/routes/search.py` | 검색 엔드포인트 | ~50 |
| `src/api/routes/info.py` | 에러/부품 정보 엔드포인트 | ~170 |
| `scripts/run_api.py` | API 서버 실행 스크립트 | ~110 |

**총 신규 코드:** ~1,075 라인

---

## 3. 아키텍처

### 3.1 시스템 구조

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

### 3.2 파일 구조

```
src/api/
├── __init__.py              # RAGService export
├── main.py                  # FastAPI 앱 (lifespan, CORS, 라우터)
├── routes/                  # API 라우터
│   ├── __init__.py
│   ├── health.py            # GET /health
│   ├── query.py             # POST /query, /analyze
│   ├── search.py            # POST /search
│   └── info.py              # GET /errors, /components
├── schemas/                 # Pydantic 모델
│   ├── __init__.py
│   ├── request.py           # QueryRequest, AnalyzeRequest, SearchRequest
│   └── response.py          # QueryResponse, SearchResponse, etc.
└── services/                # 비즈니스 로직
    ├── __init__.py
    └── rag_service.py       # RAGService (Singleton)

scripts/
└── run_api.py               # 서버 실행 스크립트
```

---

## 4. API 엔드포인트

### 4.1 엔드포인트 목록

| 엔드포인트 | 메서드 | 설명 | 응답 |
|-----------|--------|------|------|
| `/` | GET | API 루트 정보 | JSON |
| `/health` | GET | 서버 헬스체크 | HealthResponse |
| `/api/v1/query` | POST | RAG 질의 (LLM 생성) | QueryResponse |
| `/api/v1/analyze` | POST | 질문 분석만 | AnalyzeResponse |
| `/api/v1/search` | POST | 검색만 (LLM 없이) | SearchResponse |
| `/api/v1/errors` | GET | 에러 코드 목록 | List[str] |
| `/api/v1/errors/{code}` | GET | 특정 에러 정보 | ErrorCodeInfo |
| `/api/v1/components` | GET | 부품 목록 | List[str] |
| `/api/v1/components/{name}` | GET | 특정 부품 정보 | JSON |

### 4.2 API 문서

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 5. 테스트 결과

### 5.1 엔드포인트 테스트

| # | 엔드포인트 | 테스트 내용 | 상태 |
|---|-----------|------------|------|
| 1 | GET / | 루트 정보 반환 | ✅ |
| 2 | GET /health | 헬스체크 | ✅ |
| 3 | GET /api/v1/errors | 에러 코드 목록 (C0~C55) | ✅ |
| 4 | GET /api/v1/components | 부품 목록 (22개) | ✅ |
| 5 | POST /api/v1/analyze | 질문 분석 (에러 코드 감지) | ✅ |
| 6 | POST /api/v1/search | 검색 결과 반환 | ✅ |
| 7 | POST /api/v1/query | RAG 질의 + LLM 생성 | ✅ |

### 5.2 테스트 응답 예시

**GET /health:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "vectordb": "connected",
    "graphdb": "connected",
    "llm": "available"
  }
}
```

**POST /api/v1/analyze:**
```json
{
  "original_query": "C4A15 error occurred",
  "error_codes": ["C4A15"],
  "components": [],
  "query_type": "error_resolution",
  "search_strategy": "graph_first"
}
```

**POST /api/v1/search:**
```json
{
  "results": [
    {
      "content": "에러 코드: C4A15\n설명: Communication with joint 3 lost...",
      "source_type": "graph",
      "score": 1.0,
      "metadata": {"error_code": "C4A15", "entity_type": "ErrorCode"}
    }
  ],
  "query_analysis": {...},
  "total_count": 3,
  "latency_ms": 1938.29
}
```

**POST /api/v1/query:**
```json
{
  "answer": "C4A15 에러는 \"Communication with joint 3 lost\"라는 설명을 가지고 있습니다...\n\n---\n**출처:**\n  - C4A15\n🟡 신뢰도: 55%",
  "verification": {
    "status": "partial",
    "confidence": 0.55,
    "evidence_count": 1,
    "warnings": []
  },
  "sources": [
    {"name": "C4A15", "type": "graph", "score": 1.0}
  ],
  "query_analysis": {...},
  "latency_ms": 4266.83
}
```

### 5.3 성능 측정

| 엔드포인트 | 평균 응답 시간 |
|-----------|--------------|
| GET /health | ~10ms |
| GET /errors | ~5ms |
| POST /analyze | ~500ms |
| POST /search | ~1.9s |
| POST /query | ~4.3s |

---

## 6. 핵심 컴포넌트

### 6.1 RAGService (Singleton)

```python
class RAGService:
    """
    RAG 서비스 (Singleton)
    - 앱 시작 시 한 번만 초기화
    - 모든 요청에서 동일 인스턴스 공유
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def query(self, question, top_k, include_sources, include_citation)
    def analyze(self, question)
    def search(self, question, top_k, strategy)
    def get_health_status()
    def close()
```

### 6.2 Lifespan 관리

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 - RAG 서비스 초기화
    app.state.rag_service = RAGService()
    yield
    # 종료 시 - 리소스 정리
    app.state.rag_service.close()
```

### 6.3 Pydantic 스키마

**요청:**
- `QueryRequest`: question, top_k, include_sources, include_citation
- `AnalyzeRequest`: question
- `SearchRequest`: question, top_k, strategy

**응답:**
- `QueryResponse`: answer, verification, sources, query_analysis, latency_ms
- `SearchResponse`: results, query_analysis, total_count, latency_ms
- `HealthResponse`: status, version, components

---

## 7. 실행 방법

### 7.1 서버 시작

```bash
# 방법 1: 스크립트 사용 (개발 모드)
python scripts/run_api.py --reload

# 방법 2: uvicorn 직접 실행
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드 (워커 4개)
python scripts/run_api.py --workers 4
```

### 7.2 run_api.py 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--host` | 바인딩 호스트 | 0.0.0.0 |
| `--port` | 포트 번호 | 8000 |
| `--reload` | 자동 리로드 (개발용) | False |
| `--workers` | 워커 수 (프로덕션용) | 1 |
| `--log-level` | 로그 레벨 | info |

### 7.3 API 테스트

```bash
# 헬스체크
curl http://localhost:8000/health

# RAG 질의
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "C4A15 error how to fix"}'

# 질문 분석
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "C4A15 error occurred"}'

# 검색
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"question": "joint communication error", "top_k": 3}'
```

---

## 8. 체크리스트

### 8.1 구현

- [x] `src/api/` 디렉토리 구조 생성
- [x] `schemas/request.py` - Pydantic 요청 모델
- [x] `schemas/response.py` - Pydantic 응답 모델
- [x] `services/rag_service.py` - RAG 서비스 래퍼
- [x] `routes/health.py` - 헬스체크 라우터
- [x] `routes/query.py` - 질의/분석 라우터
- [x] `routes/search.py` - 검색 라우터
- [x] `routes/info.py` - 정보 라우터
- [x] `main.py` - FastAPI 앱
- [x] `scripts/run_api.py` - 실행 스크립트

### 8.2 테스트

- [x] GET / 루트 엔드포인트
- [x] GET /health 헬스체크
- [x] GET /api/v1/errors 에러 목록
- [x] GET /api/v1/components 부품 목록
- [x] POST /api/v1/analyze 질문 분석
- [x] POST /api/v1/search 검색
- [x] POST /api/v1/query RAG 질의

---

## 9. 의존성

```
# requirements.txt
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
```

---

## 10. 결론

Phase 8에서는 FastAPI 기반 RESTful API 서버를 성공적으로 구축했습니다.

### 주요 성과

1. **HTTP API 제공**: CLI 전용에서 REST API로 확장
2. **자동 문서화**: Swagger UI / ReDoc으로 API 문서 자동 생성
3. **외부 연동 가능**: 웹/앱/다른 시스템과 HTTP로 통신
4. **Singleton 패턴**: RAG 서비스 리소스 효율적 관리

### 수치적 성과

| 지표 | 값 |
|------|-----|
| 총 신규 코드 | ~1,075 라인 |
| API 엔드포인트 | 9개 |
| 테스트 통과율 | 100% (7/7) |
| 평균 질의 응답 시간 | ~4.3초 |

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
