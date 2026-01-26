"""
채팅 라우트

Chat 및 Evidence 관련 엔드포인트
"""

import httpx
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Header
from openai import OpenAI

from src.config import get_settings
from src.rag import ResponseGenerator, HybridRetriever, QueryType

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
_get_retriever = None


def configure(get_classifier, get_engine, get_generator, get_retriever=None):
    """컴포넌트 getter 함수 주입"""
    global _get_classifier, _get_engine, _get_generator, _get_retriever
    _get_classifier = get_classifier
    _get_engine = get_engine
    _get_generator = get_generator
    _get_retriever = get_retriever


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


def _create_llm_client(api_key: Optional[str]) -> Optional[OpenAI]:
    """OpenAI 클라이언트 생성 (API 키 우선순위: 헤더 > 서버 설정)"""
    # 1. 클라이언트 제공 API 키 사용
    if api_key and api_key.startswith("sk-"):
        return OpenAI(api_key=api_key)

    # 2. 서버 설정의 API 키 사용 (fallback)
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAI(api_key=settings.openai_api_key)

    return None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_openai_api_key: Optional[str] = Header(None, alias="X-OpenAI-API-Key"),
):
    """
    채팅 API (Phase12 엔진 연동)

    사용자 질문을 받아 온톨로지 기반 추론 후 응답을 반환합니다.

    - **query**: 사용자 질문 (예: "Fz가 -350N인데 이게 뭐야?") - 권장
    - **message**: 사용자 질문 (하위 호환, query 없을 때 사용)
    - **context**: 추가 컨텍스트 (shift, product 등)
    - **X-OpenAI-API-Key**: OpenAI API 키 (헤더로 전달)

    응답에는 trace_id가 포함되며, /api/evidence/{trace_id}로
    근거 상세 정보를 조회할 수 있습니다.
    """
    # --- 이벤트 통계 fetch 유틸 ---
    async def fetch_7d_stats():
        """7일치 이벤트/센서/정량 데이터 API로 집계"""
        settings = get_settings()
        base_url = settings.api.internal_base_url
        try:
            async with httpx.AsyncClient() as client:
                # 1. 이벤트(충돌 등) 7일치
                events_resp = await client.get(f"{base_url}/api/sensors/events?limit=1000")
                events_resp.raise_for_status()
                events_data = events_resp.json()
                now = datetime.now()
                def is_within_7d(dtstr):
                    try:
                        t = datetime.fromisoformat(dtstr)
                        return (now - t) <= timedelta(days=7)
                    except Exception:
                        return False
                events_7d = [e for e in events_data["events"] if is_within_7d(e.get("start_time", ""))]
                collision_events = [e for e in events_7d if e.get("event_type") == "collision"]
                collision_count = len(collision_events)
                # 2. 센서 데이터 7일치
                sensor_resp = await client.get(f"{base_url}/api/sensors/readings/range?hours=168&samples=500")
                sensor_resp.raise_for_status()
                sensor_data = sensor_resp.json()
                readings = sensor_data.get("readings", [])
                def safe_float(val):
                    try: return float(val)
                    except: return 0.0
                fz_vals = [safe_float(r.get("Fz")) for r in readings if "Fz" in r]
                fx_vals = [safe_float(r.get("Fx")) for r in readings if "Fx" in r]
                fy_vals = [safe_float(r.get("Fy")) for r in readings if "Fy" in r]
                fz_avg = sum(fz_vals)/len(fz_vals) if fz_vals else 0.0
                fz_max = max(fz_vals) if fz_vals else 0.0
                fz_min = min(fz_vals) if fz_vals else 0.0
                fz_last = fz_vals[-1] if fz_vals else 0.0
                # 기타 축/센서도 필요시 추가
                return {
                    "collision_count": collision_count,
                    "events_7d": len(events_7d),
                    "fz_avg": fz_avg,
                    "fz_max": fz_max,
                    "fz_min": fz_min,
                    "fz_last": fz_last,
                    "fx_avg": sum(fx_vals)/len(fx_vals) if fx_vals else 0.0,
                    "fy_avg": sum(fy_vals)/len(fy_vals) if fy_vals else 0.0,
                }
        except Exception as ex:
            logger.error(f"7d stats fetch error: {ex}")
            return None

    try:
        # 1. 질문 분류
        if not _get_classifier:
            raise HTTPException(status_code=500, detail="QueryClassifier가 초기화되지 않았습니다. 서버 설정을 확인하세요.")
        classifier = _get_classifier()
        if not classifier:
            raise HTTPException(status_code=500, detail="QueryClassifier 인스턴스를 가져올 수 없습니다.")
        classification = classifier.classify(request.query)

        # --- 충돌 패턴 질문이면 이벤트 통계 fetch ---
        is_collision_query = any(
            kw in (classification.query or "").lower() for kw in ["충돌", "collision", "센서", "이벤트", "정량", "패턴", "이상"]
        )
        stats = None
        if is_collision_query:
            stats = await fetch_7d_stats()

        # 2. 문서 검색 + 온톨로지 추론 (병렬 실행)
        import asyncio
        import time

        parallel_start = time.time()

        # 병렬 실행할 태스크 정의
        async def run_document_search():
            """문서 검색 (비동기 래퍼)"""
            if not _get_retriever:
                return None
            try:
                retriever = _get_retriever()
                # 동기 함수를 스레드에서 실행
                result = await asyncio.to_thread(
                    retriever.retrieve,
                    classification.query,
                    classification.query_type,
                    None,  # filter_metadata
                    request.context,
                )
                return result
            except Exception as e:
                logger.warning(f"문서 검색 실패 (계속 진행): {e}")
                return None

        async def run_ontology_reasoning():
            """온톨로지 추론 (비동기 래퍼)"""
            if not _get_engine:
                raise ValueError("OntologyEngine getter가 초기화되지 않았습니다.")
            engine = _get_engine()
            if not engine:
                raise ValueError("OntologyEngine 인스턴스를 가져올 수 없습니다.")
            entities = [e.to_dict() for e in classification.entities]
            # 동기 함수를 스레드에서 실행
            result = await asyncio.to_thread(
                engine.reason,
                classification.query,
                entities,
                request.context,
            )
            return result

        # 병렬 실행
        retrieval_result, reasoning = await asyncio.gather(
            run_document_search(),
            run_ontology_reasoning(),
        )

        parallel_elapsed = (time.time() - parallel_start) * 1000

        # 문서 검색 결과 처리
        document_refs = None
        if retrieval_result:
            document_refs = retrieval_result.document_refs
            logger.info(
                f"병렬 처리 완료: 문서={len(document_refs)}건 "
                f"(reranked={retrieval_result.reranked}), "
                f"총 소요={parallel_elapsed:.1f}ms"
            )
        else:
            logger.info(f"병렬 처리 완료: 문서=0건, 총 소요={parallel_elapsed:.1f}ms")

        # 4. 응답 생성 (LLM 클라이언트가 있으면 사용)
        llm_client = _create_llm_client(x_openai_api_key)

        # LLM 클라이언트가 있으면 새 Generator 생성, 없으면 기본 사용
        if llm_client:
            generator = ResponseGenerator(llm_client=llm_client)
        else:
            if not _get_generator:
                raise HTTPException(status_code=500, detail="ResponseGenerator getter가 초기화되지 않았습니다.")
            generator = _get_generator()
            if not generator:
                raise HTTPException(status_code=500, detail="ResponseGenerator 인스턴스를 가져올 수 없습니다.")

        response = generator.generate(
            classification,
            reasoning,
            request.context,
            document_refs=document_refs,  # 문서 참조 전달
        )

        # 4. 응답 변환
        response_dict = response.to_dict()

        # 5. Evidence Store에 저장
        _evidence_store[response.trace_id] = response_dict

        # 6. ChatResponse 구성 (충돌 패턴 질문이면 통계 기반 답변 오버라이드)
        answer = response.answer
        if is_collision_query and stats:
            answer = (
                f"최근 7일 내 충돌 이벤트 {stats['collision_count']}건, "
                f"Fz 평균 {stats['fz_avg']:.1f}N, 최대 {stats['fz_max']:.1f}N, 최소 {stats['fz_min']:.1f}N, 실시간 {stats['fz_last']:.1f}N. "
                f"Fx 평균 {stats['fx_avg']:.1f}N, Fy 평균 {stats['fy_avg']:.1f}N. "
                f"(7일 내 이벤트 총 {stats['events_7d']}건)"
            )

        chat_response = ChatResponse(
            trace_id=response.trace_id,
            query_type=response.query_type,
            answer=answer,
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

    except HTTPException:
        # 이미 HTTPException인 경우 그대로 전달
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        # 구조화된 에러 응답 (ChatResponse와 호환)
        error_detail = {
            "error_type": type(e).__name__,
            "message": str(e),
            "abstain": True,
            "abstain_reason": f"시스템 오류: {str(e)}",
        }
        raise HTTPException(status_code=500, detail=error_detail)


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
