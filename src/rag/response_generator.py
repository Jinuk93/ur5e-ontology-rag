"""
응답 생성기

추론 결과를 구조화된 응답으로 변환합니다.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .evidence_schema import (
    QueryType,
    ClassificationResult,
    DocumentReference,
)
from .confidence_gate import ConfidenceGate, GateResult
from .prompt_builder import PromptBuilder

# 온톨로지 로더 (지연 임포트로 순환 참조 방지)
_ontology_loader = None

def _get_ontology_loader():
    """OntologyLoader 지연 로딩"""
    global _ontology_loader
    if _ontology_loader is None:
        from src.ontology import OntologyLoader
        _ontology_loader = OntologyLoader
    return _ontology_loader

logger = logging.getLogger(__name__)


@dataclass
class GeneratedResponse:
    """생성된 응답"""
    trace_id: str                                       # 추적 ID
    query_type: str                                     # 질문 유형
    answer: str                                         # 자연어 응답
    analysis: Dict[str, Any] = field(default_factory=dict)      # 분석 결과
    context: Dict[str, Any] = field(default_factory=dict)       # 컨텍스트
    reasoning: Dict[str, Any] = field(default_factory=dict)     # 추론 결과
    prediction: Optional[Dict[str, Any]] = None         # 예측
    recommendation: Dict[str, Any] = field(default_factory=dict)  # 권장사항
    evidence: Dict[str, Any] = field(default_factory=dict)      # 근거
    abstain: bool = False                               # ABSTAIN 여부
    abstain_reason: Optional[str] = None                # ABSTAIN 사유
    graph: Dict[str, Any] = field(default_factory=dict)         # 그래프 데이터

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "trace_id": self.trace_id,
            "query_type": self.query_type,
            "answer": self.answer,
            "analysis": self.analysis,
            "context": self.context,
            "reasoning": self.reasoning,
            "prediction": self.prediction,
            "recommendation": self.recommendation,
            "evidence": self.evidence,
            "abstain": self.abstain,
            "abstain_reason": self.abstain_reason,
            "graph": self.graph,
        }


class ResponseGenerator:
    """응답 생성기

    추론 결과를 구조화된 응답으로 변환하고,
    필요시 LLM을 사용해 자연어 응답을 생성합니다.
    """

    def __init__(
        self,
        confidence_gate: Optional[ConfidenceGate] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        llm_client: Optional[Any] = None
    ):
        """초기화

        Args:
            confidence_gate: 신뢰도 게이트 (없으면 자동 생성)
            prompt_builder: 프롬프트 빌더 (없으면 자동 생성)
            llm_client: LLM 클라이언트 (선택적, 없으면 템플릿 기반 응답)
        """
        self.confidence_gate = confidence_gate or ConfidenceGate()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_client = llm_client
        logger.info("ResponseGenerator 초기화 완료")

    def generate(
        self,
        classification: ClassificationResult,
        reasoning: Any,  # ReasoningResult
        context: Optional[Dict[str, Any]] = None,
        document_refs: Optional[List[DocumentReference]] = None
    ) -> GeneratedResponse:
        """응답 생성

        Args:
            classification: 질문 분류 결과
            reasoning: 추론 결과 (ReasoningResult)
            context: 운영 컨텍스트 (shift, product 등)
            document_refs: 문서 참조 리스트

        Returns:
            GeneratedResponse
        """
        trace_id = str(uuid.uuid4())

        # 1. 신뢰도 게이트 평가
        gate_result = self.confidence_gate.evaluate(classification, reasoning)

        # 2. ABSTAIN 응답 생성
        if not gate_result.passed:
            return self._generate_abstain_response(
                trace_id, classification, gate_result
            )

        # 3. 정상 응답 생성
        return self._generate_normal_response(
            trace_id, classification, reasoning, context, document_refs, gate_result
        )

    def _generate_abstain_response(
        self,
        trace_id: str,
        classification: ClassificationResult,
        gate_result: GateResult
    ) -> GeneratedResponse:
        """ABSTAIN 응답 생성

        Args:
            trace_id: 추적 ID
            classification: 분류 결과
            gate_result: 게이트 결과

        Returns:
            GeneratedResponse (abstain=True)
        """
        return GeneratedResponse(
            trace_id=trace_id,
            query_type=classification.query_type.value,
            answer="해당 질문에 대한 충분한 근거를 찾지 못했습니다. 질문을 더 구체적으로 해주시거나, 다른 방식으로 질문해 주세요.",
            analysis={},
            context={},
            reasoning={},
            prediction=None,
            recommendation={
                "immediate": "질문을 더 구체적으로 해주세요.",
                "reference": None,
            },
            evidence={
                "ontology_paths": [],
                "document_refs": [],
            },
            abstain=True,
            abstain_reason=gate_result.abstain_reason,
            graph={"nodes": [], "edges": []},
        )

    def _generate_normal_response(
        self,
        trace_id: str,
        classification: ClassificationResult,
        reasoning: Any,
        context: Optional[Dict[str, Any]],
        document_refs: Optional[List[DocumentReference]],
        gate_result: GateResult
    ) -> GeneratedResponse:
        """정상 응답 생성

        Args:
            trace_id: 추적 ID
            classification: 분류 결과
            reasoning: 추론 결과
            context: 컨텍스트
            document_refs: 문서 참조
            gate_result: 게이트 결과

        Returns:
            GeneratedResponse
        """
        # 1. 분석 결과 구성
        analysis = self._build_analysis(classification, reasoning)

        # 2. 추론 결과 구성
        reasoning_dict = self._build_reasoning_dict(reasoning)

        # 3. 예측 구성
        prediction = self._build_prediction(reasoning)

        # 4. 권장사항 구성
        recommendation = self._build_recommendation(reasoning)

        # 5. 근거 구성
        evidence = self._build_evidence(reasoning, document_refs)

        # 6. 그래프 데이터 구성
        graph = self._build_graph_data(reasoning)

        # 7. 자연어 응답 생성
        answer = self._generate_natural_response(
            classification, reasoning, analysis, prediction, recommendation
        )

        return GeneratedResponse(
            trace_id=trace_id,
            query_type=classification.query_type.value,
            answer=answer,
            analysis=analysis,
            context=context or {},
            reasoning=reasoning_dict,
            prediction=prediction,
            recommendation=recommendation,
            evidence=evidence,
            abstain=False,
            abstain_reason=None,
            graph=graph,
        )

    def _build_analysis(
        self,
        classification: ClassificationResult,
        reasoning: Any
    ) -> Dict[str, Any]:
        """분석 결과 구성"""
        analysis: Dict[str, Any] = {}

        # 엔티티에서 분석 정보 추출
        for entity in classification.entities:
            if entity.entity_type == "MeasurementAxis":
                analysis["entity"] = entity.entity_id
            elif entity.entity_type == "Value":
                # 값 파싱
                value_str = entity.entity_id
                try:
                    # "-350.0N" → value=-350.0, unit="N"
                    match = re.match(r"(-?\d+\.?\d*)(.*)", value_str)
                    if match:
                        analysis["value"] = float(match.group(1))
                        unit = match.group(2).strip()
                        if unit:
                            analysis["unit"] = unit
                except (ValueError, AttributeError):
                    analysis["value"] = value_str

        # 추론 결과에서 상태 추출
        for conclusion in reasoning.conclusions:
            if conclusion.get("type") == "state":
                analysis["state"] = conclusion.get("state", "")
                if "entity" not in analysis:
                    analysis["entity"] = conclusion.get("entity", "")

        # 정상 범위 정보 (온톨로지에서 조회)
        entity_id = analysis.get("entity")
        if entity_id:
            try:
                loader = _get_ontology_loader()
                ontology = loader.load()
                entity = ontology.get_entity(entity_id)
                if entity and entity.properties:
                    normal_range = entity.properties.get("normal_range")
                    if normal_range:
                        analysis["normal_range"] = normal_range
                        if "value" in analysis:
                            value = analysis["value"]
                            # 정상 범위 벗어난 경우 편차 계산
                            range_min, range_max = normal_range
                            if value < range_min:
                                # 음수 방향으로 벗어남
                                deviation = abs(value) / abs(range_min) if range_min != 0 else abs(value)
                                analysis["deviation"] = f"정상 대비 약 {deviation:.1f}배"
                            elif value > range_max:
                                # 양수 방향으로 벗어남
                                deviation = abs(value) / abs(range_max) if range_max != 0 else abs(value)
                                analysis["deviation"] = f"정상 대비 약 {deviation:.1f}배"
            except Exception as e:
                logger.debug(f"온톨로지에서 정상 범위 조회 실패: {e}")

        return analysis

    def _build_reasoning_dict(self, reasoning: Any) -> Dict[str, Any]:
        """추론 결과 딕셔너리 구성"""
        result: Dict[str, Any] = {
            "confidence": reasoning.confidence,
        }

        pattern_id, pattern_conf = self._extract_primary_pattern(reasoning)
        if pattern_id:
            result["pattern"] = pattern_id
            if pattern_conf is not None:
                result["pattern_confidence"] = pattern_conf

        # 원인 추출
        for conclusion in reasoning.conclusions:
            if conclusion.get("type") == "cause":
                result["cause"] = conclusion.get("cause", "")
                result["cause_confidence"] = conclusion.get("confidence", 0)
                break

        # 유사 이벤트
        similar_events = reasoning.evidence.get("similar_events", [])
        if similar_events:
            result["similar_events"] = similar_events

        return result

    def _build_prediction(self, reasoning: Any) -> Optional[Dict[str, Any]]:
        """예측 구성"""
        # 1) predictions 우선 (OntologyEngine은 confidence를 쓰는 경우가 많음)
        if reasoning.predictions:
            pred = reasoning.predictions[0]
            probability = pred.get("probability")
            if probability is None:
                probability = pred.get("confidence", 0)
            return {
                "error_code": pred.get("error_code", pred.get("error", "")),
                "probability": probability,
                "timeframe": pred.get("timeframe", ""),
            }

        # 2) conclusions의 triggered_error도 예측으로 간주
        for conclusion in reasoning.conclusions:
            if conclusion.get("type") == "triggered_error":
                return {
                    "error_code": conclusion.get("error", ""),
                    "probability": conclusion.get("confidence", 0),
                    "timeframe": conclusion.get("timeframe", ""),
                }

        return None

    def _build_recommendation(self, reasoning: Any) -> Dict[str, Any]:
        """권장사항 구성"""
        result: Dict[str, Any] = {}

        if reasoning.recommendations:
            rec = reasoning.recommendations[0]
            result["immediate"] = rec.get("action", rec.get("resolution", ""))
            result["reference"] = rec.get("reference", None)
        else:
            # 결론에서 권장사항 추출
            for conclusion in reasoning.conclusions:
                if conclusion.get("type") == "cause":
                    cause = conclusion.get("cause", "")
                    result["immediate"] = self._get_action_for_cause(cause)
                    break

        return result

    def _get_action_for_cause(self, cause: str) -> str:
        """원인에 대한 권장 조치"""
        cause_actions = {
            "CAUSE_PHYSICAL_CONTACT": "장애물 제거 및 작업 영역 확인",
            "CAUSE_COLLISION": "장애물 제거 및 작업 영역 확인",
            "CAUSE_PAYLOAD_EXCEEDED": "페이로드 확인 및 감량",
            "CAUSE_GRIP_POSITION": "그립 위치 확인 및 조정",
            "CAUSE_TOOL_WEAR": "툴 상태 점검",
        }
        return cause_actions.get(cause, "상황 점검 필요")

    def _build_evidence(
        self,
        reasoning: Any,
        document_refs: Optional[List[DocumentReference]]
    ) -> Dict[str, Any]:
        """근거 구성"""
        evidence: Dict[str, Any] = {}

        # 온톨로지 경로
        if reasoning.ontology_paths:
            evidence["ontology_path"] = reasoning.ontology_paths[0] if reasoning.ontology_paths else ""
            evidence["ontology_paths"] = []
            for path_str in reasoning.ontology_paths:
                parsed = self._parse_ontology_path(path_str)
                if parsed:
                    evidence["ontology_paths"].append(parsed)

        # 문서 참조
        evidence["document_refs"] = []
        if document_refs:
            for ref in document_refs:
                evidence["document_refs"].append(ref.to_dict())

        # 유사 이벤트
        similar_events = reasoning.evidence.get("similar_events", [])
        if similar_events:
            evidence["similar_events"] = similar_events

        return evidence

    def _parse_ontology_path(self, path_str: str) -> Optional[Dict[str, Any]]:
        """온톨로지 경로 문자열 파싱

        "Fz →[HAS_STATE]→ CRITICAL" 형태를 파싱
        """
        if not path_str:
            return None

        # 간단한 파싱 (→ 또는 → 기준)
        nodes = []
        relations = []

        # "Fz →[HAS_STATE]→ CRITICAL →[INDICATES]→ PAT_OVERLOAD"
        parts = re.split(r'\s*→\s*', path_str)

        for part in parts:
            # [RELATION] 형태인지 확인
            match = re.match(r'\[(\w+)\]', part)
            if match:
                relations.append(match.group(1))
            else:
                node = part.strip()
                if node:
                    nodes.append(node)

        if not nodes:
            return None

        return {
            "path": nodes,
            "relations": relations,
            "confidence": 0.85,  # 기본값
        }

    def _build_graph_data(self, reasoning: Any) -> Dict[str, Any]:
        """그래프 데이터 구성"""
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        seen_ids: set = set()

        # 엔티티에서 노드 추출
        for entity in reasoning.entities:
            entity_id = entity.get("entity_id", entity.get("id", ""))
            if entity_id and entity_id not in seen_ids:
                nodes.append({
                    "id": entity_id,
                    "type": entity.get("entity_type", entity.get("type", "")),
                    "label": entity.get("text", entity_id),
                })
                seen_ids.add(entity_id)

        # 결론에서 추가 노드 및 엣지 추출
        for conclusion in reasoning.conclusions:
            c_type = conclusion.get("type", "")

            if c_type == "state":
                state = conclusion.get("state", "")
                entity = conclusion.get("entity", "")
                if state and state not in seen_ids:
                    nodes.append({"id": state, "type": "State", "label": state})
                    seen_ids.add(state)
                if entity and state:
                    edges.append({"source": entity, "target": state, "relation": "HAS_STATE"})

            elif c_type == "pattern":
                pattern = conclusion.get("pattern", "")
                if pattern and pattern not in seen_ids:
                    nodes.append({"id": pattern, "type": "Pattern", "label": pattern})
                    seen_ids.add(pattern)

            elif c_type == "cause":
                cause = conclusion.get("cause", "")
                pattern = conclusion.get("pattern", "")
                error = conclusion.get("error", "")

                # ErrorCode 질문 처리: C153 →[CAUSED_BY]→ CAUSE_*
                if error and error not in seen_ids:
                    nodes.append({"id": error, "type": "ErrorCode", "label": error})
                    seen_ids.add(error)
                if pattern and pattern not in seen_ids:
                    nodes.append({"id": pattern, "type": "Pattern", "label": pattern})
                    seen_ids.add(pattern)
                if cause and cause not in seen_ids:
                    nodes.append({"id": cause, "type": "Cause", "label": cause})
                    seen_ids.add(cause)

                if error and cause:
                    edges.append({"source": error, "target": cause, "relation": "CAUSED_BY"})
                if pattern and cause:
                    edges.append({"source": pattern, "target": cause, "relation": "INDICATES"})

            elif c_type == "triggered_error":
                error = conclusion.get("error", "")
                pattern = conclusion.get("pattern", "")
                if pattern and pattern not in seen_ids:
                    nodes.append({"id": pattern, "type": "Pattern", "label": pattern})
                    seen_ids.add(pattern)
                if error and error not in seen_ids:
                    nodes.append({"id": error, "type": "ErrorCode", "label": error})
                    seen_ids.add(error)
                if pattern and error:
                    edges.append({"source": pattern, "target": error, "relation": "TRIGGERS"})

            elif c_type == "triggering_pattern":
                # ErrorCode 질문 처리: PAT_* →[TRIGGERS]→ C153
                error = conclusion.get("error", "")
                pattern = conclusion.get("pattern", "")
                if pattern and pattern not in seen_ids:
                    nodes.append({"id": pattern, "type": "Pattern", "label": pattern})
                    seen_ids.add(pattern)
                if error and error not in seen_ids:
                    nodes.append({"id": error, "type": "ErrorCode", "label": error})
                    seen_ids.add(error)
                if pattern and error:
                    edges.append({"source": pattern, "target": error, "relation": "TRIGGERS"})

        return {"nodes": nodes, "edges": edges}

    def _extract_primary_pattern(self, reasoning: Any) -> tuple[str, Optional[float]]:
        """추론 결과에서 대표 패턴(PAT_*)을 추출

        OntologyEngine은 conclusions에 pattern 타입을 항상 넣지 않고,
        cause/triggered_error 결론에 pattern 필드를 포함하는 방식도 사용합니다.
        """
        # 1) pattern 타입 결론
        for conclusion in reasoning.conclusions:
            if conclusion.get("type") == "pattern":
                return conclusion.get("pattern", ""), conclusion.get("confidence")

        # 2) 다른 결론의 pattern 필드
        for conclusion in reasoning.conclusions:
            pattern = conclusion.get("pattern")
            if pattern:
                return pattern, conclusion.get("confidence")

        # 3) reasoning_chain에서 패턴 매칭 결과
        for step in getattr(reasoning, "reasoning_chain", []) or []:
            if step.get("step") in ("pattern_matching", "pattern_analysis"):
                result = step.get("result") or {}
                pattern = result.get("pattern") or result.get("pattern_id")
                if pattern:
                    return pattern, None

        return "", None

    def _generate_natural_response(
        self,
        classification: ClassificationResult,
        reasoning: Any,
        analysis: Dict[str, Any],
        prediction: Optional[Dict[str, Any]],
        recommendation: Dict[str, Any]
    ) -> str:
        """자연어 응답 생성

        LLM이 없으면 템플릿 기반 응답 생성
        """
        if self.llm_client:
            return self._generate_with_llm(classification, reasoning)

        return self._generate_template_response(
            classification, reasoning, analysis, prediction, recommendation
        )

    def _generate_template_response(
        self,
        classification: ClassificationResult,
        reasoning: Any,
        analysis: Dict[str, Any],
        prediction: Optional[Dict[str, Any]],
        recommendation: Dict[str, Any]
    ) -> str:
        """템플릿 기반 응답 생성 (LLM 없이)"""
        parts: List[str] = []

        # 1. 상태 분석
        if "entity" in analysis and "state" in analysis:
            entity = analysis["entity"]
            state = analysis["state"]
            value = analysis.get("value", "")

            if value:
                unit = analysis.get("unit", "")
                parts.append(f"{entity} 값 {value}{unit}은(는) {state} 상태입니다.")
            else:
                parts.append(f"{entity}은(는) {state} 상태입니다.")

            if "deviation" in analysis:
                parts.append(f"({analysis['deviation']})")

            if "normal_range" in analysis:
                nr = analysis["normal_range"]
                parts.append(f"정상 범위: {nr[0]}~{nr[1]}")

        # 2. 패턴/원인 분석
        for conclusion in reasoning.conclusions:
            c_type = conclusion.get("type", "")
            if c_type == "pattern":
                pattern = conclusion.get("pattern", "")
                conf = conclusion.get("confidence", 0)
                pattern_name = pattern.replace("PAT_", "").replace("_", " ").title()
                parts.append(f"감지된 패턴: {pattern_name} (신뢰도: {conf:.0%})")
            elif c_type == "cause":
                cause = conclusion.get("cause", "")
                conf = conclusion.get("confidence", 0)
                cause_name = cause.replace("CAUSE_", "").replace("_", " ").title()
                parts.append(f"추정 원인: {cause_name} (신뢰도: {conf:.0%})")

        # 3. 예측
        if prediction:
            error = prediction.get("error_code", "")
            prob = prediction.get("probability", 0)
            timeframe = prediction.get("timeframe", "")
            if error and prob:
                parts.append(f"예측: {error} 발생 확률 {prob:.0%}{f' ({timeframe})' if timeframe else ''}")

        # 4. 권장사항
        if recommendation.get("immediate"):
            parts.append(f"권장 조치: {recommendation['immediate']}")
        if recommendation.get("reference"):
            parts.append(f"참고: {recommendation['reference']}")

        return " ".join(parts)

    def _generate_with_llm(
        self,
        classification: ClassificationResult,
        reasoning: Any
    ) -> str:
        """LLM으로 자연어 응답 생성"""
        try:
            system_prompt = self.prompt_builder.build_system_prompt(
                classification.query_type
            )
            user_prompt = self.prompt_builder.build_prompt(classification, reasoning)

            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.warning(f"LLM 호출 실패, 템플릿 응답으로 대체: {e}")
            return self._generate_template_response(
                classification, reasoning, {}, None, {}
            )


# 편의 함수
def create_response_generator(
    llm_client: Optional[Any] = None
) -> ResponseGenerator:
    """ResponseGenerator 인스턴스 생성"""
    return ResponseGenerator(llm_client=llm_client)
