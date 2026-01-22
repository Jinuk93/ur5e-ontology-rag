"""
온톨로지 추론 엔진

QueryClassifier 결과를 받아 온톨로지 기반 추론을 수행합니다.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from .models import OntologySchema, Entity
from .schema import RelationType, EntityType
from .loader import load_ontology
from .rule_engine import RuleEngine, InferenceResult
from .graph_traverser import GraphTraverser, OntologyPath, TraversalResult

logger = logging.getLogger(__name__)


@dataclass
class EntityContext:
    """엔티티 컨텍스트"""
    entity: Entity
    properties: Dict[str, Any]
    states: List[str]
    related_patterns: List[str]
    related_errors: List[str]
    related_causes: List[str]
    related_resolutions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity.id,
            "entity_type": self.entity.type.value,
            "entity_name": self.entity.name,
            "properties": self.properties,
            "states": self.states,
            "related_patterns": self.related_patterns,
            "related_errors": self.related_errors,
            "related_causes": self.related_causes,
            "related_resolutions": self.related_resolutions,
        }


@dataclass
class ReasoningResult:
    """추론 결과"""
    query: str
    entities: List[Dict[str, Any]]
    reasoning_chain: List[Dict[str, Any]]
    conclusions: List[Dict[str, Any]]
    predictions: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    ontology_paths: List[str]
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "entities": self.entities,
            "reasoning_chain": self.reasoning_chain,
            "conclusions": self.conclusions,
            "predictions": self.predictions,
            "recommendations": self.recommendations,
            "ontology_paths": self.ontology_paths,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


class OntologyEngine:
    """온톨로지 기반 추론 엔진

    QueryClassifier에서 추출한 엔티티를 기반으로
    온톨로지 그래프를 탐색하고 추론을 수행합니다.
    """

    def __init__(
        self,
        ontology: Optional[OntologySchema] = None,
        rule_engine: Optional[RuleEngine] = None
    ):
        """초기화

        Args:
            ontology: 온톨로지 스키마 (없으면 자동 로드)
            rule_engine: 추론 규칙 엔진 (없으면 자동 생성)
        """
        self.ontology = ontology or load_ontology()
        self.rule_engine = rule_engine or RuleEngine()
        self.traverser = GraphTraverser(self.ontology)
        logger.info("OntologyEngine 초기화 완료")

    # ================================================================
    # 엔티티 컨텍스트 로딩
    # ================================================================

    def get_context(self, entity_id: str) -> Optional[EntityContext]:
        """엔티티 컨텍스트 로딩

        Args:
            entity_id: 엔티티 ID

        Returns:
            EntityContext 또는 None
        """
        entity = self.ontology.get_entity(entity_id)
        if not entity:
            # 별칭으로 시도
            from .loader import resolve_alias
            resolved_id = resolve_alias(entity_id)
            if resolved_id != entity_id:
                entity = self.ontology.get_entity(resolved_id)
            if not entity:
                logger.warning(f"엔티티 없음: {entity_id}")
                return None

        # 관계 탐색
        context_data = self.traverser.get_entity_context(entity.id, depth=2)

        # 관계별로 분류
        outgoing = context_data.get("outgoing_relations", {})
        incoming = context_data.get("incoming_relations", {})

        states = outgoing.get("HAS_STATE", [])
        related_patterns = incoming.get("INDICATES", []) + incoming.get("TRIGGERS", [])
        related_errors = outgoing.get("TRIGGERS", []) + incoming.get("CAUSED_BY", [])
        related_causes = outgoing.get("INDICATES", []) + outgoing.get("CAUSED_BY", [])
        related_resolutions = outgoing.get("RESOLVED_BY", [])

        return EntityContext(
            entity=entity,
            properties=entity.properties,
            states=states,
            related_patterns=list(set(related_patterns)),
            related_errors=list(set(related_errors)),
            related_causes=list(set(related_causes)),
            related_resolutions=list(set(related_resolutions)),
        )

    # ================================================================
    # 경로 탐색
    # ================================================================

    def find_path(self, source_id: str, target_id: str) -> Optional[OntologyPath]:
        """두 엔티티 간 경로 탐색

        Args:
            source_id: 시작 엔티티 ID
            target_id: 목표 엔티티 ID

        Returns:
            OntologyPath 또는 None
        """
        return self.traverser.find_path(source_id, target_id)

    def get_related_entities(
        self,
        entity_id: str,
        depth: int = 2,
        relation_filter: Optional[List[RelationType]] = None
    ) -> TraversalResult:
        """관련 엔티티 탐색

        Args:
            entity_id: 엔티티 ID
            depth: 탐색 깊이
            relation_filter: 필터링할 관계 타입

        Returns:
            TraversalResult
        """
        return self.traverser.bfs(entity_id, max_depth=depth, relation_filter=relation_filter)

    # ================================================================
    # 핵심 추론
    # ================================================================

    def reason(
        self,
        query: str,
        entities: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        """온톨로지 기반 추론

        Args:
            query: 원본 질문
            entities: 추출된 엔티티 리스트 [{"entity_id": "...", "entity_type": "...", "text": "..."}]
            context: 추가 컨텍스트 (시간, 제품 등)

        Returns:
            ReasoningResult
        """
        context = context or {}
        reasoning_chain = []
        conclusions = []
        predictions = []
        recommendations = []
        ontology_paths = []
        total_confidence = 1.0
        evidence = {"entities_processed": [], "rules_applied": []}

        # 1. 엔티티별 컨텍스트 로딩 및 처리
        for entity_info in entities:
            entity_id = entity_info.get("entity_id", "")
            entity_type = entity_info.get("entity_type", "")
            entity_text = entity_info.get("text", "")

            # MeasurementAxis + Value 조합 처리
            if entity_type == "MeasurementAxis":
                result = self._process_measurement(entity_id, entities, context)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    predictions.extend(result.get("predictions", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].append(entity_id)

            # Pattern 처리
            elif entity_type == "Pattern":
                result = self._process_pattern(pattern_id=entity_id, pattern_text=entity_text, context=context)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    recommendations.extend(result.get("recommendations", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].append(entity_id)

            # ErrorCode 처리
            elif entity_type == "ErrorCode":
                result = self._process_error_code(entity_id, context)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    recommendations.extend(result.get("recommendations", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].append(entity_id)

            # TimeExpression 처리
            elif entity_type == "TimeExpression":
                context["has_temporal_context"] = True
                reasoning_chain.append({
                    "step": "temporal_context",
                    "description": f"시간 컨텍스트 확인: {entity_text}",
                    "result": "이력 분석 필요",
                })

        # 2. 신뢰도 계산
        if conclusions:
            confidences = [c.get("confidence", 0.5) for c in conclusions]
            total_confidence = sum(confidences) / len(confidences)

        # 3. 중복 제거
        ontology_paths = list(set(ontology_paths))

        return ReasoningResult(
            query=query,
            entities=entities,
            reasoning_chain=reasoning_chain,
            conclusions=conclusions,
            predictions=predictions,
            recommendations=recommendations,
            ontology_paths=ontology_paths,
            confidence=total_confidence,
            evidence=evidence,
        )

    def _process_measurement(
        self,
        axis_id: str,
        entities: List[Dict],
        context: Dict
    ) -> Optional[Dict]:
        """측정 축 + 값 처리"""
        # 값 엔티티 찾기
        value_entity = None
        for e in entities:
            if e.get("entity_type") == "Value":
                value_entity = e
                break

        if not value_entity:
            return None

        # 값 파싱
        try:
            value_text = value_entity.get("text", "0")
            # 숫자 부분만 추출
            import re
            match = re.search(r'-?\d+(?:\.\d+)?', value_text)
            if match:
                value = float(match.group())
            else:
                return None
        except (ValueError, TypeError):
            return None

        reasoning = []
        conclusions = []
        predictions = []
        paths = []

        # 1. 축 컨텍스트 로딩
        axis_context = self.get_context(axis_id)
        if axis_context:
            reasoning.append({
                "step": "context_loading",
                "description": f"{axis_id} 컨텍스트 로딩",
                "result": {
                    "normal_range": axis_context.properties.get("normal_range"),
                    "critical_thresholds": axis_context.properties.get("critical_thresholds"),
                    "states": axis_context.states,
                }
            })

        # 2. 상태 추론
        state_result = self.rule_engine.infer_state(axis_id, value)
        if state_result:
            reasoning.append({
                "step": "state_inference",
                "description": f"{axis_id}={value} → 상태 추론",
                "result": {
                    "state": state_result.result_id,
                    "confidence": state_result.confidence,
                    "message": state_result.message,
                }
            })
            conclusions.append({
                "type": "state",
                "entity": axis_id,
                "value": value,
                "state": state_result.result_id,
                "severity": state_result.evidence.get("severity", "unknown"),
                "confidence": state_result.confidence,
            })
            paths.append(f"{axis_id} → {state_result.result_id}")

            # 3. CRITICAL/WARNING 상태면 패턴 매칭
            severity = state_result.evidence.get("severity", "")
            if severity in ("critical", "warning"):
                # 값이 음수이고 크면 충돌/과부하 패턴 가능
                if abs(value) > 300:
                    if value < 0:
                        pattern_id = "PAT_COLLISION"
                        pattern_name = "충돌 패턴"
                    else:
                        pattern_id = "PAT_OVERLOAD"
                        pattern_name = "과부하 패턴"

                    reasoning.append({
                        "step": "pattern_matching",
                        "description": f"비정상 값 → 패턴 매칭",
                        "result": {
                            "pattern": pattern_id,
                            "pattern_name": pattern_name,
                        }
                    })

                    # 패턴 추론 경로 생성
                    pattern_reasoning = self.traverser.get_reasoning_path(pattern_id)
                    if pattern_reasoning:
                        for cause_path in pattern_reasoning.get("cause_paths", []):
                            conclusions.append({
                                "type": "cause",
                                "pattern": pattern_id,
                                "cause": cause_path["cause_id"],
                                "confidence": cause_path["confidence"],
                            })
                            paths.append(cause_path["path"])

                        for error_path in pattern_reasoning.get("error_paths", []):
                            predictions.append({
                                "type": "error_prediction",
                                "error": error_path["error_id"],
                                "from_pattern": pattern_id,
                                "confidence": error_path["confidence"],
                            })
                            paths.append(error_path["path"])

        return {
            "reasoning": reasoning,
            "conclusions": conclusions,
            "predictions": predictions,
            "paths": paths,
        }

    def _process_pattern(
        self,
        pattern_id: str,
        pattern_text: str,
        context: Dict
    ) -> Optional[Dict]:
        """패턴 처리

        EntityExtractor는 Pattern 엔티티를 보통 다음 형태로 제공합니다:
        - entity_id: "PAT_COLLISION" 같은 정규화 ID
        - text: "충돌" 같은 원문 키워드(동의어 포함 가능)

        가능하면 pattern_id를 우선 사용하고, 없거나 비표준이면 text로 매핑합니다.
        """
        # 패턴 텍스트 → 패턴 ID 매핑
        pattern_mapping = {
            "충돌": "PAT_COLLISION",
            "과부하": "PAT_OVERLOAD",
            "드리프트": "PAT_DRIFT",
            "진동": "PAT_VIBRATION",
            "collision": "PAT_COLLISION",
            "overload": "PAT_OVERLOAD",
            "drift": "PAT_DRIFT",
            "vibration": "PAT_VIBRATION",
        }

        resolved_pattern_id = pattern_id
        if not resolved_pattern_id or not resolved_pattern_id.startswith("PAT_"):
            resolved_pattern_id = pattern_mapping.get(pattern_text.lower(), "")
        if not resolved_pattern_id:
            return None

        reasoning = []
        conclusions = []
        recommendations = []
        paths = []

        # 패턴 추론 경로 생성
        pattern_reasoning = self.traverser.get_reasoning_path(resolved_pattern_id)

        if pattern_reasoning:
            reasoning.append({
                "step": "pattern_analysis",
                "description": f"패턴 분석: {pattern_text} → {resolved_pattern_id}",
                "result": pattern_reasoning,
            })

            # 원인 추출
            for cause_path in pattern_reasoning.get("cause_paths", []):
                conclusions.append({
                    "type": "cause",
                    "pattern": resolved_pattern_id,
                    "cause": cause_path["cause_id"],
                    "confidence": cause_path["confidence"],
                })
                paths.append(cause_path["path"])

            # 해결책 추출
            for res_path in pattern_reasoning.get("resolution_paths", []):
                resolution = self.ontology.get_entity(res_path["resolution_id"])
                if resolution:
                    recommendations.append({
                        "type": "resolution",
                        "resolution_id": res_path["resolution_id"],
                        "name": resolution.name,
                        "steps": resolution.properties.get("steps", []),
                        "confidence": res_path["confidence"],
                    })
                paths.append(res_path["path"])

            # 예상 에러 추출
            for error_path in pattern_reasoning.get("error_paths", []):
                conclusions.append({
                    "type": "triggered_error",
                    "pattern": resolved_pattern_id,
                    "error": error_path["error_id"],
                    "confidence": error_path["confidence"],
                })
                paths.append(error_path["path"])

        return {
            "reasoning": reasoning,
            "conclusions": conclusions,
            "recommendations": recommendations,
            "paths": paths,
        }

    def _process_error_code(
        self,
        error_code: str,
        context: Dict
    ) -> Optional[Dict]:
        """에러 코드 처리"""
        error_entity = self.ontology.get_entity(error_code)
        if not error_entity:
            return None

        reasoning = []
        conclusions = []
        recommendations = []
        paths = []

        # 에러 컨텍스트 로딩
        error_context = self.get_context(error_code)
        if error_context:
            reasoning.append({
                "step": "error_context",
                "description": f"에러 코드 분석: {error_code}",
                "result": {
                    "name": error_entity.name,
                    "description": error_entity.properties.get("description", ""),
                    "severity": error_entity.properties.get("severity", "unknown"),
                }
            })

        # CAUSED_BY 관계로 원인 탐색
        cause_paths = self.traverser.follow_relation_chain(
            error_code,
            [RelationType.CAUSED_BY]
        )
        for path in cause_paths:
            cause_id = path.end_entity
            cause = self.ontology.get_entity(cause_id)
            if cause:
                conclusions.append({
                    "type": "cause",
                    "error": error_code,
                    "cause": cause_id,
                    "cause_name": cause.name,
                    "confidence": path.total_confidence,
                })
                paths.append(path.to_string())

                # 원인 → 해결책
                resolution_paths = self.traverser.follow_relation_chain(
                    cause_id,
                    [RelationType.RESOLVED_BY]
                )
                for res_path in resolution_paths:
                    resolution = self.ontology.get_entity(res_path.end_entity)
                    if resolution:
                        recommendations.append({
                            "type": "resolution",
                            "for_cause": cause_id,
                            "resolution_id": resolution.id,
                            "name": resolution.name,
                            "steps": resolution.properties.get("steps", []),
                            "confidence": res_path.total_confidence,
                        })
                        paths.append(f"{error_code} → {path.to_string()} → {res_path.to_string()}")

        # TRIGGERS 역방향으로 원인 패턴 탐색
        rels = self.ontology.get_relationships_for_entity(error_code, direction="incoming")
        for rel in rels:
            if rel.relation == RelationType.TRIGGERS:
                pattern = self.ontology.get_entity(rel.source)
                if pattern:
                    conclusions.append({
                        "type": "triggering_pattern",
                        "error": error_code,
                        "pattern": rel.source,
                        "pattern_name": pattern.name,
                        "confidence": rel.properties.get("confidence", 1.0),
                    })
                    paths.append(f"{rel.source} →[TRIGGERS]→ {error_code}")

        return {
            "reasoning": reasoning,
            "conclusions": conclusions,
            "recommendations": recommendations,
            "paths": paths,
        }

    # ================================================================
    # 예측 기능
    # ================================================================

    def predict(
        self,
        pattern_history: List[Dict],
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """패턴 이력 기반 에러 예측

        Args:
            pattern_history: 패턴 발생 이력
            context: 추가 컨텍스트

        Returns:
            예측 결과 리스트
        """
        prediction_results = self.rule_engine.predict_error(pattern_history)
        return [
            {
                "error_id": r.result_id,
                "probability": r.confidence,
                "evidence": r.evidence,
                "message": r.message,
            }
            for r in prediction_results
        ]

    # ================================================================
    # 하이브리드 질문 처리
    # ================================================================

    def hybrid_query(
        self,
        query: str,
        entities: List[Dict[str, Any]],
        document_results: Optional[List[Dict]] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """하이브리드 질문 처리 (온톨로지 + 문서)

        Args:
            query: 원본 질문
            entities: 추출된 엔티티
            document_results: 문서 검색 결과
            context: 추가 컨텍스트

        Returns:
            통합 결과
        """
        # 온톨로지 추론
        reasoning_result = self.reason(query, entities, context)

        # 문서 결과와 통합
        return {
            "query": query,
            "ontology_result": reasoning_result.to_dict(),
            "document_results": document_results or [],
            "combined_confidence": reasoning_result.confidence,
            "evidence": {
                "ontology_paths": reasoning_result.ontology_paths,
                "documents": [d.get("doc_id") for d in (document_results or [])],
            }
        }

    # ================================================================
    # 요약 및 통계
    # ================================================================

    def get_summary(self) -> Dict[str, Any]:
        """엔진 상태 요약"""
        ontology_stats = self.ontology.get_statistics()
        return {
            "ontology": ontology_stats,
            "traverser": {
                "entities": len(self.ontology.entities),
                "relationships": len(self.ontology.relationships),
            },
            "rule_engine": {
                "state_rules": len(self.rule_engine.inference_rules.get("state_rules", [])),
                "cause_rules": len(self.rule_engine.inference_rules.get("cause_rules", [])),
                "prediction_rules": len(self.rule_engine.inference_rules.get("prediction_rules", [])),
            }
        }


# ================================================================
# 편의 함수
# ================================================================

def create_ontology_engine(ontology: Optional[OntologySchema] = None) -> OntologyEngine:
    """OntologyEngine 인스턴스 생성"""
    return OntologyEngine(ontology)
