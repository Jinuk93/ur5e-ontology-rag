"""
UR5e Ontology RAG API 모듈

FastAPI 기반 REST API 서버를 제공합니다.

사용 예시:
    # 서버 실행
    python scripts/run_api.py --reload

    # 또는 직접 uvicorn 사용
    uvicorn src.api.main:app --reload

API 엔드포인트:
    - GET  /health              - 헬스체크
    - POST /api/chat            - 채팅 API (Phase12 엔진)
    - GET  /api/evidence/{id}   - 근거 상세 조회
    - GET  /api/ontology/summary - 온톨로지 요약
"""

from .main import app

__all__ = ["app"]
