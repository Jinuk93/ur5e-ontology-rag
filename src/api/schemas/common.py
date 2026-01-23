"""
공통 API 스키마

시스템 관련 스키마 정의
"""

from typing import Dict
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    version: str
    components: Dict[str, str]
