"""
채팅 라우트

Chat 및 Evidence 관련 엔드포인트
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    EvidenceResponse,
    AnalysisInfo,
    ReasoningInfo,
    PredictionInfo,
    RecommendationInfo,
    EvidenceInfo,
    GraphNode,
    GraphEdge,
    GraphData,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])

# Evidence 저장소 (세션 내 trace_id → response 매핑)
_evidence_store: Dict[str, Dict[str, Any]] = {}

# 컴포넌트 getter 함수 (main.py에서 주입)
_get_classifier = None
_get_engine = None
_get_generator = None


def configure(get_classifier, get_engine, get_generator):
    """컴포넌트 getter 함수 주입"""
    global _get_classifier, _get_engine, _get_generator
    _get_classifier = get_classifier
    _get_engine = get_engine
    _get_generator = get_generator


def get_evidence_store() -> Dict[str, Dict[str, Any]]:
    """Evidence 저장소 접근"""
    return _evidence_store


def _enrich_graph_node(node: Dict[str, Any], analysis: Dict[str, Any]) -> GraphNode:
    """GraphNode에 state 정보 추가 (UI 색상용)"""
    state = None

    node_type = node.get("type", "")
    node_id = node.get("id", "")

    if node_type == "State" or "State_" in node_id:
        if "Critical" in node_id or "CRITICAL" in node_id:
            state = "critical"
        elif "Warning" in node_id or "WARNING" in node_id:
            state = "warning"
        elif "Normal" in node_id or "NORMAL" in node_id:
            state = "normal"

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


@router.post("/chat", response_model=ChatResponse)
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
        # 1. 질문 분류
        classifier = _get_classifier()
        classification = classifier.classify(request.query)

        # 2. 온톨로지 추론
        engine = _get_engine()
        entities = [e.to_dict() for e in classification.entities]
        reasoning = engine.reason(
            classification.query,
            entities,
            request.context
        )

        # 3. 응답 생성
        generator = _get_generator()
        response = generator.generate(
            classification,
            reasoning,
            request.context
        )

        # 4. 응답 변환
        response_dict = response.to_dict()

        # 5. Evidence Store에 저장
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


@router.get("/evidence/{trace_id}", response_model=EvidenceResponse)
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
