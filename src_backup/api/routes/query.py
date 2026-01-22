# ============================================================
# src/api/routes/query.py - 질의 라우터
# ============================================================

from fastapi import APIRouter, Request, HTTPException
from src.api.schemas.request import QueryRequest, AnalyzeRequest
from src.api.schemas.response import QueryResponse, AnalyzeResponse

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest):
    """
    RAG 질의 실행

    사용자 질문을 분석하고, 관련 정보를 검색한 후, LLM으로 답변을 생성합니다.

    - **question**: 사용자 질문 (필수)
    - **top_k**: 검색할 결과 수 (기본값: 5, 범위: 1-20)
    - **include_sources**: 출처 정보 포함 여부 (기본값: true)
    - **include_citation**: 인용 정보 포함 여부 (기본값: true)

    ## 응답

    - **answer**: 생성된 답변
    - **verification**: 검증 정보 (상태, 신뢰도, 근거 수, 경고)
    - **sources**: 출처 목록 (옵션)
    - **query_analysis**: 질문 분석 결과
    - **latency_ms**: 처리 시간 (밀리초)

    ## 예시

    ```json
    {
      "question": "C4A15 에러가 발생했어요. 어떻게 해결하나요?"
    }
    ```
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
        raise HTTPException(status_code=500, detail=f"RAG 질의 실패: {str(e)}")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: Request, body: AnalyzeRequest):
    """
    질문 분석

    질문에서 에러 코드, 부품명을 감지하고 검색 전략을 결정합니다.
    LLM 생성 없이 분석만 수행합니다.

    - **question**: 분석할 질문 (필수)

    ## 응답

    - **original_query**: 원본 질문
    - **error_codes**: 감지된 에러 코드 리스트
    - **components**: 감지된 부품명 리스트
    - **query_type**: 쿼리 타입 (error_resolution, component_info, general)
    - **search_strategy**: 검색 전략 (graph_first, vector_first, hybrid)

    ## 예시

    ```json
    {
      "question": "Control Box에서 C50 에러가 발생했어요"
    }
    ```
    """
    try:
        rag_service = request.app.state.rag_service
        return rag_service.analyze(body.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질문 분석 실패: {str(e)}")
