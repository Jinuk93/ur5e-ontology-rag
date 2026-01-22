# ============================================================
# src/api/routes/search.py - 검색 라우터
# ============================================================

from fastapi import APIRouter, Request, HTTPException
from src.api.schemas.request import SearchRequest
from src.api.schemas.response import SearchResponse

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: Request, body: SearchRequest):
    """
    문서 검색 (LLM 생성 없이)

    관련 문서만 검색하고 결과를 반환합니다.
    답변 생성은 수행하지 않아 빠른 응답이 가능합니다.

    - **question**: 검색 질문 (필수)
    - **top_k**: 검색할 결과 수 (기본값: 5, 범위: 1-20)
    - **strategy**: 검색 전략 (옵션: graph_first, vector_first, hybrid)

    ## 응답

    - **results**: 검색 결과 리스트
      - content: 내용 (500자 미리보기)
      - source_type: 출처 타입 (graph/vector)
      - score: 관련성 점수
      - metadata: 메타데이터
    - **query_analysis**: 질문 분석 결과
    - **total_count**: 총 결과 수
    - **latency_ms**: 처리 시간 (밀리초)

    ## 예시

    ```json
    {
      "question": "조인트 통신 에러",
      "top_k": 3,
      "strategy": "hybrid"
    }
    ```
    """
    try:
        rag_service = request.app.state.rag_service
        return rag_service.search(
            question=body.question,
            top_k=body.top_k,
            strategy=body.strategy,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")
