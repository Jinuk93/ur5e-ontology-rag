"""
UR5e Ontology RAG API Server

FastAPI 기반 REST API 서버.
Phase12 추론 엔진과 연동하여 챗봇 API를 제공합니다.

사용법:
    python scripts/run_api.py --reload
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from src.config import get_settings
from src.rag import (
    QueryClassifier,
    ResponseGenerator,
    QueryType,
)
from src.ontology import OntologyEngine

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
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

# Evidence 저장소 (세션 내 trace_id → response 매핑)
_evidence_store: Dict[str, Dict[str, Any]] = {}


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
# Request/Response 스키마
# ============================================================
class ChatRequest(BaseModel):
    """채팅 요청

    UI 명세서 기준: query 필드 사용
    하위 호환: message 필드도 허용 (query 우선)
    """
    query: Optional[str] = Field(None, description="사용자 질문 (권장)")
    message: Optional[str] = Field(None, description="사용자 질문 (하위 호환)")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추가 컨텍스트 (shift, product 등)"
    )

    @model_validator(mode='after')
    def validate_query_or_message(self):
        """query 또는 message 중 하나는 필수"""
        if not self.query and not self.message:
            raise ValueError("query 또는 message 중 하나는 필수입니다")
        # query 우선, 없으면 message 사용
        if not self.query:
            self.query = self.message
        return self


class AnalysisInfo(BaseModel):
    """분석 정보"""
    entity: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    state: Optional[str] = None
    normal_range: Optional[List[float]] = None
    deviation: Optional[str] = None


class ReasoningInfo(BaseModel):
    """추론 정보"""
    confidence: float
    pattern: Optional[str] = None
    pattern_confidence: Optional[float] = None
    cause: Optional[str] = None
    cause_confidence: Optional[float] = None


class PredictionInfo(BaseModel):
    """예측 정보"""
    error_code: Optional[str] = None
    probability: Optional[float] = None
    timeframe: Optional[str] = None


class RecommendationInfo(BaseModel):
    """권장사항"""
    immediate: Optional[str] = None
    reference: Optional[str] = None


class EvidenceInfo(BaseModel):
    """근거 정보"""
    ontology_paths: List[Dict[str, Any]] = Field(default_factory=list)
    document_refs: List[Dict[str, Any]] = Field(default_factory=list)
    similar_events: List[str] = Field(default_factory=list)  # 유사 이벤트 ID


class GraphNode(BaseModel):
    """그래프 노드"""
    id: str
    type: str
    label: str
    state: Optional[str] = None  # normal|warning|critical (UI 색상용)


class GraphEdge(BaseModel):
    """그래프 엣지"""
    source: str
    target: str
    relation: str


class GraphData(BaseModel):
    """그래프 데이터"""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """채팅 응답 (Phase12 스키마)"""
    trace_id: str = Field(..., description="추적 ID (근거 조회용)")
    query_type: str = Field(..., description="질문 유형 (ontology/hybrid/rag)")
    answer: str = Field(..., description="자연어 응답")
    analysis: Optional[AnalysisInfo] = None
    reasoning: Optional[ReasoningInfo] = None
    prediction: Optional[PredictionInfo] = None
    recommendation: Optional[RecommendationInfo] = None
    evidence: EvidenceInfo = Field(default_factory=EvidenceInfo)
    graph: GraphData = Field(default_factory=GraphData)
    abstain: bool = Field(default=False, description="ABSTAIN 여부")
    abstain_reason: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class EvidenceResponse(BaseModel):
    """근거 상세 응답"""
    trace_id: str
    found: bool
    evidence: Optional[Dict[str, Any]] = None
    full_response: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    version: str
    components: Dict[str, str]


# ============================================================
# API 엔드포인트
# ============================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """헬스체크"""
    settings = get_settings()

    # 컴포넌트 상태 확인
    components = {}
    try:
        get_classifier()
        components["classifier"] = "ok"
    except Exception as e:
        components["classifier"] = f"error: {str(e)}"

    try:
        get_engine()
        components["engine"] = "ok"
    except Exception as e:
        components["engine"] = f"error: {str(e)}"

    try:
        get_generator()
        components["generator"] = "ok"
    except Exception as e:
        components["generator"] = f"error: {str(e)}"

    return HealthResponse(
        status="healthy" if all(v == "ok" for v in components.values()) else "degraded",
        version="1.0.0",
        components=components,
    )


def _enrich_graph_node(node: Dict[str, Any], analysis: Dict[str, Any]) -> GraphNode:
    """GraphNode에 state 정보 추가 (UI 색상용)"""
    state = None

    # State 타입 노드는 이름에서 상태 추출
    node_type = node.get("type", "")
    node_id = node.get("id", "")

    if node_type == "State" or "State_" in node_id:
        if "Critical" in node_id or "CRITICAL" in node_id:
            state = "critical"
        elif "Warning" in node_id or "WARNING" in node_id:
            state = "warning"
        elif "Normal" in node_id or "NORMAL" in node_id:
            state = "normal"

    # analysis의 state 정보 활용
    if not state and analysis:
        analysis_state = analysis.get("state", "")
        if "Critical" in analysis_state:
            state = "critical"
        elif "Warning" in analysis_state:
            state = "warning"

    return GraphNode(
        id=node.get("id", ""),
        type=node.get("type", ""),
        label=node.get("label", ""),
        state=state,
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    채팅 API (Phase12 엔진 연동)

    사용자 질문을 받아 온톨로지 기반 추론 후 응답을 반환합니다.

    - **query**: 사용자 질문 (예: "Fz가 -350N인데 이게 뭐야?") - 권장
    - **message**: 사용자 질문 (하위 호환, query 없을 때 사용)
    - **context**: 추가 컨텍스트 (shift, product 등)

    응답에는 trace_id가 포함되며, /api/evidence/{trace_id}로
    근거 상세 정보를 조회할 수 있습니다.
    """
    try:
        # 1. 질문 분류 (query 우선, 없으면 message 사용 - validator에서 처리됨)
        classifier = get_classifier()
        classification = classifier.classify(request.query)

        # 2. 온톨로지 추론
        engine = get_engine()
        entities = [e.to_dict() for e in classification.entities]
        reasoning = engine.reason(
            classification.query,
            entities,
            request.context
        )

        # 3. 응답 생성
        generator = get_generator()
        response = generator.generate(
            classification,
            reasoning,
            request.context
        )

        # 4. 응답 변환
        response_dict = response.to_dict()

        # 5. Evidence Store에 저장 (trace_id로 조회 가능)
        _evidence_store[response.trace_id] = response_dict

        # 6. ChatResponse 구성
        chat_response = ChatResponse(
            trace_id=response.trace_id,
            query_type=response.query_type,
            answer=response.answer,
            analysis=AnalysisInfo(**response.analysis) if response.analysis else None,
            reasoning=ReasoningInfo(
                confidence=response.reasoning.get("confidence", 0.0),
                pattern=response.reasoning.get("pattern"),
                pattern_confidence=response.reasoning.get("pattern_confidence"),
                cause=response.reasoning.get("cause"),
                cause_confidence=response.reasoning.get("cause_confidence"),
            ) if response.reasoning else None,
            prediction=PredictionInfo(**response.prediction) if response.prediction else None,
            recommendation=RecommendationInfo(**response.recommendation) if response.recommendation else None,
            evidence=EvidenceInfo(
                ontology_paths=response.evidence.get("ontology_paths", []),
                document_refs=response.evidence.get("document_refs", []),
                similar_events=response.evidence.get("similar_events", []),
            ),
            graph=GraphData(
                nodes=[_enrich_graph_node(n, response.analysis) for n in response.graph.get("nodes", [])],
                edges=[GraphEdge(**e) for e in response.graph.get("edges", [])],
            ),
            abstain=response.abstain,
            abstain_reason=response.abstain_reason,
        )

        logger.info(f"Chat response generated: trace_id={response.trace_id}")
        return chat_response

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/evidence/{trace_id}", response_model=EvidenceResponse, tags=["Evidence"])
async def get_evidence(trace_id: str):
    """
    근거 상세 조회

    chat API 응답의 trace_id로 전체 응답 및 근거 상세 정보를 조회합니다.
    프론트엔드에서 "근거 보기" 버튼 클릭 시 사용합니다.
    """
    if trace_id not in _evidence_store:
        return EvidenceResponse(
            trace_id=trace_id,
            found=False,
            evidence=None,
            full_response=None,
        )

    full_response = _evidence_store[trace_id]
    return EvidenceResponse(
        trace_id=trace_id,
        found=True,
        evidence=full_response.get("evidence"),
        full_response=full_response,
    )


@app.get("/api/ontology/summary", tags=["Ontology"])
async def get_ontology_summary():
    """온톨로지 요약 정보"""
    try:
        engine = get_engine()
        summary = engine.get_summary()
        return {
            "status": "ok",
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 앱 시작/종료 이벤트
# ============================================================

@app.on_event("startup")
async def startup():
    """앱 시작 시 초기화"""
    logger.info("=" * 60)
    logger.info("  UR5e Ontology RAG API Starting...")
    logger.info("=" * 60)

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
    _evidence_store.clear()
