"""
UR5e Ontology-based RAG System

제조 AX (AI Transformation)를 위한 온톨로지 기반 RAG 시스템.
UR5e 로봇 및 Axia80 센서의 문서, 센서 데이터, 지식 그래프를 통합하여
컨텍스트 인식 진단 및 예측을 제공합니다.

주요 모듈:
    - config: 프로젝트 설정 관리
    - ingestion: PDF 문서 처리 및 청크 생성
    - embedding: 텍스트 임베딩 생성
    - ontology: 온톨로지 스키마 및 추론 엔진
    - sensor: 센서 데이터 처리 및 패턴 감지
    - rag: 검색 증강 생성 파이프라인
    - api: FastAPI REST API 서버
    - dashboard: Streamlit 대시보드 UI

사용 예시:
    from src.config import get_settings

    settings = get_settings()
    print(settings.llm.model)  # 'gpt-4o-mini'
"""

__version__ = "0.1.0"
__author__ = "UR5e Ontology RAG Team"

# 설정 모듈 노출
from src.config import get_settings, reload_settings, Settings

__all__ = [
    "get_settings",
    "reload_settings",
    "Settings",
    "__version__",
]
