"""
UR5e Ontology RAG API Server

FastAPI 기반 REST API 서버.
Phase12 추론 엔진과 연동하여 챗봇 API를 제공합니다.

사용법:
    python scripts/run_api.py --reload
"""

import logging
import os
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.rag import QueryClassifier, ResponseGenerator
from src.ontology import OntologyEngine

from src.api.routes import (
    system_router,
    chat_router,
    sensor_router,
    configure_system,
    configure_chat,
    get_evidence_store,
)

# ============================================================
# 로깅 설정
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# FastAPI 앱 초기화
# ============================================================
app = FastAPI(
    title="UR5e Ontology RAG API",
    description="제조 AX를 위한 온톨로지 기반 RAG API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정 (프론트엔드 연동용)
# 환경변수 CORS_ORIGINS로 허용 도메인 설정 (쉼표 구분)
# 예: CORS_ORIGINS=http://localhost:3000,https://myapp.com
_cors_origins_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = (
    [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
    if _cors_origins_env
    else ["http://localhost:3000", "http://127.0.0.1:3000"]  # 개발용 기본값
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 전역 상태 (싱글톤 컴포넌트)
# ============================================================
_classifier: Optional[QueryClassifier] = None
_engine: Optional[OntologyEngine] = None
_generator: Optional[ResponseGenerator] = None


def get_classifier() -> QueryClassifier:
    """QueryClassifier 싱글톤"""
    global _classifier
    if _classifier is None:
        _classifier = QueryClassifier()
    return _classifier


def get_engine() -> OntologyEngine:
    """OntologyEngine 싱글톤"""
    global _engine
    if _engine is None:
        _engine = OntologyEngine()
    return _engine


def get_generator() -> ResponseGenerator:
    """ResponseGenerator 싱글톤"""
    global _generator
    if _generator is None:
        _generator = ResponseGenerator()
    return _generator


# ============================================================
# 라우터 설정 및 등록
# ============================================================
# 컴포넌트 getter 주입
configure_system(get_classifier, get_engine, get_generator)
configure_chat(get_classifier, get_engine, get_generator)

# 라우터 등록
app.include_router(system_router)
app.include_router(chat_router)
app.include_router(sensor_router)


# ============================================================
# 앱 시작/종료 이벤트
# ============================================================
@app.on_event("startup")
async def startup():
    """앱 시작 시 초기화"""
    logger.info("=" * 60)
    logger.info("  UR5e Ontology RAG API Starting...")
    logger.info("=" * 60)

    # CORS 설정 로깅
    logger.info(f"CORS allowed origins: {_cors_origins}")

    # 컴포넌트 사전 초기화 (첫 요청 지연 방지)
    try:
        get_classifier()
        get_engine()
        get_generator()
        logger.info("All components initialized successfully")
    except Exception as e:
        logger.error(f"Component initialization failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    """앱 종료 시 정리"""
    logger.info("UR5e Ontology RAG API Shutting down...")
    get_evidence_store().clear()
