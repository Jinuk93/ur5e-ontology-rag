# ============================================================
# src/api/routes/info.py - 정보 라우터
# ============================================================

from fastapi import APIRouter, Request, HTTPException, Path
from typing import List
from src.api.schemas.response import ErrorCodeInfo

router = APIRouter()

# 알려진 부품 목록
KNOWN_COMPONENTS = [
    "Control Box",
    "Teach Pendant",
    "Robot Arm",
    "Safety Control Board",
    "Motherboard",
    "Screen Board",
    "Joint 0",
    "Joint 1",
    "Joint 2",
    "Joint 3",
    "Joint 4",
    "Joint 5",
    "Power Supply",
    "Current Distributor",
    "Emergency Stop",
    "Safety System",
    "Communication Cable",
    "Power Cable",
    "Ethernet Cable",
    "Tool",
    "Gripper",
    "Euromap",
]


@router.get("/errors", response_model=List[str])
async def list_errors():
    """
    에러 코드 목록 조회

    UR5e 로봇의 모든 유효한 에러 코드 기본 번호를 반환합니다.
    (C0 ~ C55)

    ## 응답

    에러 코드 문자열 리스트

    ## 예시 응답

    ```json
    ["C0", "C1", "C2", ..., "C55"]
    ```
    """
    return [f"C{i}" for i in range(0, 56)]


@router.get("/errors/{code}", response_model=ErrorCodeInfo)
async def get_error(
    request: Request,
    code: str = Path(
        ...,
        description="에러 코드 (예: C4A15, C50)",
        pattern=r"^C\d+(?:A\d+)?$"
    )
):
    """
    특정 에러 코드 정보 조회

    지정된 에러 코드의 상세 정보를 검색하여 반환합니다.

    - **code**: 에러 코드 (예: C4A15, C50)

    ## 응답

    - **code**: 에러 코드
    - **description**: 에러 설명
    - **causes**: 원인 리스트
    - **solutions**: 해결 방법 리스트
    - **related_components**: 관련 부품 리스트

    ## 예시

    `/api/v1/errors/C4A15`
    """
    try:
        rag_service = request.app.state.rag_service

        # 검색으로 에러 정보 가져오기
        result = rag_service.search(f"{code} 에러 정보", top_k=3)

        if not result.results:
            raise HTTPException(
                status_code=404,
                detail=f"에러 코드 {code}에 대한 정보를 찾을 수 없습니다"
            )

        # 첫 번째 결과에서 정보 추출
        description = result.results[0].content[:300]

        return ErrorCodeInfo(
            code=code.upper(),
            description=description,
            causes=[],
            solutions=[],
            related_components=[]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"에러 정보 조회 실패: {str(e)}")


@router.get("/components", response_model=List[str])
async def list_components():
    """
    부품 목록 조회

    UR5e 로봇의 주요 부품 목록을 반환합니다.

    ## 응답

    부품명 문자열 리스트

    ## 예시 응답

    ```json
    ["Control Box", "Teach Pendant", "Robot Arm", ...]
    ```
    """
    return KNOWN_COMPONENTS


@router.get("/components/{name}")
async def get_component(
    request: Request,
    name: str = Path(..., description="부품명 (예: Control Box)")
):
    """
    특정 부품 정보 조회

    지정된 부품의 관련 에러 코드를 검색하여 반환합니다.

    - **name**: 부품명 (예: Control Box, Joint 3)

    ## 응답

    - **name**: 부품명
    - **related_errors**: 관련 에러 정보
    """
    try:
        rag_service = request.app.state.rag_service

        # 검색으로 부품 관련 에러 정보 가져오기
        result = rag_service.search(f"{name} 관련 에러", top_k=5)

        return {
            "name": name,
            "related_errors": [
                {
                    "content": r.content[:200],
                    "source_type": r.source_type,
                    "score": r.score
                }
                for r in result.results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"부품 정보 조회 실패: {str(e)}")
