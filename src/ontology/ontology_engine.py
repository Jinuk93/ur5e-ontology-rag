"""
온톨로지 추론 엔진

QueryClassifier 결과를 받아 온톨로지 기반 추론을 수행합니다.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

import json
from pathlib import Path

from .models import OntologySchema, Entity
from .schema import RelationType, EntityType
from .loader import load_ontology
from .rule_engine import RuleEngine, InferenceResult
from .graph_traverser import GraphTraverser, OntologyPath, TraversalResult

logger = logging.getLogger(__name__)


def _get_entity_attr(entity, attr: str, default=None):
    """ExtractedEntity 객체 또는 딕셔너리에서 속성 가져오기"""
    if hasattr(entity, attr):
        return getattr(entity, attr)
    elif isinstance(entity, dict):
        return entity.get(attr, default)
    return default


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
        self._pattern_log_cache: Optional[List[Dict[str, Any]]] = None
        logger.info("OntologyEngine 초기화 완료")

    def _load_detected_patterns(self) -> List[Dict[str, Any]]:
        """감지된 패턴 로그 로드 (캐싱)

        data/sensor/processed/detected_patterns.json을 사용합니다.
        """
        if self._pattern_log_cache is not None:
            return self._pattern_log_cache

        root = Path(__file__).resolve().parents[2]
        patterns_path = root / "data" / "sensor" / "processed" / "detected_patterns.json"
        if not patterns_path.exists():
            self._pattern_log_cache = []
            return self._pattern_log_cache

        try:
            with open(patterns_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._pattern_log_cache = data
            else:
                self._pattern_log_cache = []
        except Exception as e:
            logger.warning(f"패턴 로그 로드 실패: {e}")
            self._pattern_log_cache = []

        return self._pattern_log_cache

    def _build_pattern_history(self, resolved_pattern_id: str, limit: int = 3) -> Dict[str, Any]:
        """패턴 이력(최근 감지 여부) 요약"""
        patterns = self._load_detected_patterns()

        target_type = resolved_pattern_id.replace("PAT_", "").lower()
        matched: List[Dict[str, Any]] = []
        for p in patterns:
            pid = (p.get("pattern_id") or p.get("id") or "").upper()
            ptype = (p.get("pattern_type") or p.get("type") or "").lower()
            if pid == resolved_pattern_id or ptype == target_type:
                matched.append(p)

        # 타임스탬프 필드 후보
        def _ts(item: Dict[str, Any]) -> str:
            return str(item.get("timestamp") or item.get("start_time") or item.get("time") or "")

        matched_sorted = sorted(matched, key=_ts)
        count = len(matched_sorted)
        latest_ts = _ts(matched_sorted[-1]) if count else ""
        recent_samples = [
            {
                "timestamp": _ts(x),
                "confidence": float(x.get("confidence", 0.0)) if x.get("confidence") is not None else 0.0,
                "metrics": x.get("metrics", {}),
            }
            for x in matched_sorted[-limit:]
        ]

        # 데이터 기간(전체) 추정
        all_ts = [_ts(x) for x in patterns if _ts(x)]
        time_range = {
            "start": min(all_ts) if all_ts else "",
            "end": max(all_ts) if all_ts else "",
        }

        if patterns and count == 0:
            desc = (
                f"최근 데이터 기간({time_range['start']} ~ {time_range['end']})에서 "
                f"{resolved_pattern_id} 감지 기록이 없습니다."
            )
            confidence = 0.9
        elif not patterns:
            desc = (
                "패턴 이력 데이터(detected_patterns.json)를 찾지 못해 최근 감지 여부를 확인할 수 없습니다. "
                "(패턴 감지 파이프라인 실행 또는 데이터 경로 확인이 필요합니다.)"
            )
            confidence = 0.4
        else:
            desc = (
                f"최근 데이터 기간({time_range['start']} ~ {time_range['end']})에서 "
                f"{resolved_pattern_id} 패턴이 {count}회 감지되었습니다. "
                f"마지막 감지 시각: {latest_ts}"
            )
            confidence = 0.95

        return {
            "description": desc,
            "count": count,
            "latest_timestamp": latest_ts,
            "samples": recent_samples,
            "time_range": time_range,
            "confidence": confidence,
        }

    def _build_all_patterns_history(self, limit: int = 5) -> Dict[str, Any]:
        """모든 패턴 이력(에러 패턴 전체) 요약

        "지난 주 에러 패턴 알려줘" 같은 일반적인 패턴 조회 시 사용
        """
        patterns = self._load_detected_patterns()

        # 타임스탬프 필드 후보
        def _ts(item: Dict[str, Any]) -> str:
            return str(item.get("timestamp") or item.get("start_time") or item.get("time") or "")

        # 전체 패턴 정렬
        patterns_sorted = sorted(patterns, key=_ts, reverse=True)
        count = len(patterns_sorted)

        # 패턴 타입별 카운트
        type_counts: Dict[str, int] = {}
        for p in patterns_sorted:
            ptype = (p.get("pattern_type") or p.get("type") or "unknown").lower()
            type_counts[ptype] = type_counts.get(ptype, 0) + 1

        # 최근 샘플
        recent_samples = [
            {
                "timestamp": _ts(x),
                "pattern_type": x.get("pattern_type") or x.get("type") or "unknown",
                "confidence": float(x.get("confidence", 0.0)) if x.get("confidence") is not None else 0.0,
            }
            for x in patterns_sorted[:limit]
        ]

        # 데이터 기간
        all_ts = [_ts(x) for x in patterns if _ts(x)]
        time_range = {
            "start": min(all_ts) if all_ts else "",
            "end": max(all_ts) if all_ts else "",
        }

        if not patterns:
            desc = (
                "현재 저장된 패턴 이력 데이터가 없습니다. "
                "센서 데이터는 최근 7일치만 보관되며, 해당 기간에 감지된 패턴이 없거나 "
                "요청하신 기간의 데이터가 존재하지 않을 수 있습니다."
            )
            confidence = 0.85
        elif count == 0:
            desc = (
                f"데이터 기간({time_range['start']} ~ {time_range['end']})에서 "
                "감지된 에러/이상 패턴이 없습니다."
            )
            confidence = 0.9
        else:
            type_summary = ", ".join([f"{k}: {v}건" for k, v in type_counts.items()])
            latest_ts = _ts(patterns_sorted[0]) if count else ""
            desc = (
                f"데이터 기간({time_range['start']} ~ {time_range['end']})에서 "
                f"총 {count}건의 패턴이 감지되었습니다.\n"
                f"패턴 유형별: {type_summary}\n"
                f"마지막 감지 시각: {latest_ts}"
            )
            confidence = 0.95

        return {
            "description": desc,
            "count": count,
            "latest_timestamp": _ts(patterns_sorted[0]) if count else "",
            "samples": recent_samples,
            "time_range": time_range,
            "type_counts": type_counts,
            "confidence": confidence,
        }

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

        # 0. 질문 유형 확인
        has_value = any(_get_entity_attr(e, "entity_type") == "Value" for e in entities)
        is_definition_query = self._is_definition_query(query)
        is_comparison_query = self._is_comparison_query(query)
        is_specification_query = self._is_specification_query(query)
        is_relationship_query = self._is_relationship_query(query)
        is_resolution_query = self._is_resolution_query(query)

        # 0-1. 관계 질문 처리 (Axia80은 어디에 장착돼?)
        if is_relationship_query and not has_value and len(entities) >= 1:
            result = self._process_relationship_query(entities, query)
            if result:
                reasoning_chain.extend(result.get("reasoning", []))
                conclusions.extend(result.get("conclusions", []))
                ontology_paths.extend(result.get("paths", []))
                evidence["entities_processed"].extend([_get_entity_attr(e, "entity_id") for e in entities])
                return ReasoningResult(
                    query=query,
                    entities=entities,
                    reasoning_chain=reasoning_chain,
                    conclusions=conclusions,
                    predictions=predictions,
                    recommendations=recommendations,
                    ontology_paths=list(set(ontology_paths)),
                    confidence=result.get("confidence", 0.9),
                    evidence=evidence,
                )

        # 0-2. 비교 질문 처리 (여러 엔티티 비교)
        if is_comparison_query and not has_value:
            axis_entities = [e for e in entities if _get_entity_attr(e, "entity_type") == "MeasurementAxis"]
            if len(axis_entities) >= 2:
                result = self._process_comparison(axis_entities, query)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].extend([_get_entity_attr(e, "entity_id") for e in axis_entities])
                    # 비교 질문 처리 완료 시 조기 반환
                    return ReasoningResult(
                        query=query,
                        entities=entities,
                        reasoning_chain=reasoning_chain,
                        conclusions=conclusions,
                        predictions=predictions,
                        recommendations=recommendations,
                        ontology_paths=list(set(ontology_paths)),
                        confidence=result.get("confidence", 0.9),
                        evidence=evidence,
                    )

        # 0-3. 대처/해결 질문 처리 (토크가 높을 때 어떻게 대처?)
        if is_resolution_query and not has_value:
            axis_entities = [e for e in entities if _get_entity_attr(e, "entity_type") == "MeasurementAxis"]
            if axis_entities:
                result = self._process_resolution_query(axis_entities, query)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    recommendations.extend(result.get("recommendations", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].extend([_get_entity_attr(e, "entity_id") for e in axis_entities])
                    return ReasoningResult(
                        query=query,
                        entities=entities,
                        reasoning_chain=reasoning_chain,
                        conclusions=conclusions,
                        predictions=predictions,
                        recommendations=recommendations,
                        ontology_paths=list(set(ontology_paths)),
                        confidence=result.get("confidence", 0.9),
                        evidence=evidence,
                    )

        # 1. 엔티티별 컨텍스트 로딩 및 처리
        for entity_info in entities:
            entity_id = _get_entity_attr(entity_info, "entity_id", "")
            entity_type = _get_entity_attr(entity_info, "entity_type", "")
            entity_text = _get_entity_attr(entity_info, "text", "")

            # 정의 질문 처리 (값 없이 "Fy가 뭐야?", "UR5e가 뭐야?" 같은 질문)
            definition_entity_types = (
                "MeasurementAxis", "Robot", "Sensor", "Equipment",
                "ControlBox", "ToolFlange", "Joint", "Component"
            )
            if entity_type in definition_entity_types and not has_value and is_definition_query:
                result = self._process_entity_definition(entity_id, entity_type)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].append(entity_id)
                continue

            # 사양 질문 처리 (값 없이 "UR5e 페이로드가 몇 kg?", "Joint_0 가동 범위?" 같은 질문)
            spec_entity_types = ("Robot", "Sensor", "Equipment", "MeasurementAxis", "Joint")
            if entity_type in spec_entity_types and not has_value and is_specification_query:
                result = self._process_specification(entity_id, entity_type, query)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].append(entity_id)
                continue

            # MeasurementAxis + Value 조합 처리
            if entity_type == "MeasurementAxis":
                result = self._process_measurement(entity_id, entities, context)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    predictions.extend(result.get("predictions", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].append(entity_id)
                elif not has_value and not is_definition_query:
                    # 값이 없고 정의 질문도 아닌 경우 (트렌드/이상 질문)
                    # 측정축 정보와 함께 안내 제공
                    result = self._process_measurement_info(entity_id, query)
                    if result:
                        reasoning_chain.extend(result.get("reasoning", []))
                        conclusions.extend(result.get("conclusions", []))
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

            # ErrorCategory 처리 (joint position 에러, communication 에러 등)
            elif entity_type == "ErrorCategory":
                result = self._process_error_category(entity_id, entity_text, context)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    recommendations.extend(result.get("recommendations", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].append(entity_id)

            # MaintenanceStatus 처리 (예비보전 상태 등)
            elif entity_type == "MaintenanceStatus":
                result = self._process_maintenance_status(entity_id, entity_text, context)
                if result:
                    reasoning_chain.extend(result.get("reasoning", []))
                    conclusions.extend(result.get("conclusions", []))
                    recommendations.extend(result.get("recommendations", []))
                    ontology_paths.extend(result.get("paths", []))
                    evidence["entities_processed"].append(entity_id)

        # 2. 신뢰도 계산
        if conclusions:
            confidences = []
            for c in conclusions:
                if isinstance(c, str):
                    confidences.append(0.8)  # 문자열 결론은 기본 신뢰도
                elif isinstance(c, dict):
                    confidences.append(c.get("confidence", 0.5))
                else:
                    confidences.append(0.5)
            total_confidence = sum(confidences) / len(confidences)
        else:
            # 결론 없으면 낮은 신뢰도 (ABSTAIN 가능성)
            total_confidence = 0.3

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

    def _is_definition_query(self, query: str) -> bool:
        """정의 질문인지 확인"""
        import re
        definition_patterns = [
            r"(뭐|무엇|무슨|어떤|뜻|의미|정의)",
            # "사용법", "설명해" 등은 구체적인 절차나 문맥이 필요하므로 RAG 검색으로 넘깁니다.
            # 단순 정의 질문(What is)에만 온톨로지 엔진이 개입하도록 완화합니다.
        ]
        for pattern in definition_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _is_specification_query(self, query: str) -> bool:
        """사양 질문인지 확인 (페이로드, 범위, 무게 등)"""
        import re
        spec_patterns = [
            r"(몇|얼마|어느 정도|최대|최소)",
            r"(kg|mm|N|Nm|도|℃|Hz)",
            r"(페이로드|payload|무게|중량|반경|범위|reach|속도|토크|힘)",
        ]
        for pattern in spec_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _is_resolution_query(self, query: str) -> bool:
        """대처/해결 질문인지 확인 (높을 때 어떻게 대처하나요? 등)"""
        import re
        resolution_patterns = [
            r"(대처|해결|조치|처리|수정|고치|fix)",
            r"어떻게.*(하|해|할)",
            r"(높|낮|이상|초과|부족).{0,5}(을|면|때).{0,10}(어떻게|뭘|무엇)",
        ]
        for pattern in resolution_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _process_resolution_query(self, axis_entities: list, query: str) -> Optional[Dict]:
        """대처/해결 질문 처리 (토크가 높을 때 어떻게 대처?)"""
        import re

        reasoning = []
        conclusions = []
        recommendations = []
        paths = []

        # 높음/낮음 여부 판단
        is_high = bool(re.search(r"(높|크|초과|넘|이상)", query))
        is_low = bool(re.search(r"(낮|작|부족|미달)", query))

        for entity_info in axis_entities:
            entity_id = _get_entity_attr(entity_info, "entity_id", "")
            entity = self.ontology.get_entity(entity_id)
            if not entity:
                continue

            props = entity.properties or {}
            measurement_type = props.get("measurement_type", "")
            axis = props.get("axis", "")
            unit = props.get("unit", "")
            normal_range = props.get("normal_range", [])

            reasoning.append(f"{entity_id} ({measurement_type}) 대처 방법을 분석합니다.")

            # 토크 관련 대처
            if measurement_type == "torque" or entity_id in ("Tx", "Ty", "Tz"):
                if is_high:
                    conclusion_text = f"""**{entity_id} (토크) 값이 높을 때 대처 방법:**

1. **즉시 조치**
   - 로봇 속도를 낮추세요 (속도가 빠를수록 토크 부하 증가)
   - 페이로드(적재 중량)를 확인하고 필요시 감량하세요

2. **점검 사항**
   - 조인트 상태 점검: 마모, 이물질, 윤활 상태 확인
   - 케이블 꼬임이나 간섭 여부 확인
   - 작업 경로가 특정 관절에 무리를 주는지 검토

3. **예방 조치**
   - 정상 범위: {normal_range[0]}~{normal_range[1]} {unit}
   - 작업 프로그램의 가감속 설정 완화
   - 정기적인 조인트 캘리브레이션 수행"""
                else:
                    conclusion_text = f"{entity_id} 토크 관련 일반 대처: 정상 범위({normal_range[0]}~{normal_range[1]} {unit}) 내 유지를 권장합니다."

            # 힘 관련 대처
            elif measurement_type == "force" or entity_id in ("Fx", "Fy", "Fz"):
                if is_high:
                    conclusion_text = f"""**{entity_id} (힘) 값이 높을 때 대처 방법:**

1. **즉시 조치**
   - 로봇을 일시 정지하고 충돌 여부 확인
   - 작업물이나 환경에 장애물이 있는지 점검

2. **점검 사항**
   - 그리퍼/툴 장착 상태 확인
   - 센서 캘리브레이션 상태 점검
   - 작업 경로가 물체와 간섭하는지 확인

3. **예방 조치**
   - 정상 범위: {normal_range[0]}~{normal_range[1]} {unit}
   - 힘 제한(Force Limit) 설정 검토
   - 충돌 감지 민감도 조정"""
                else:
                    conclusion_text = f"{entity_id} 힘 관련 일반 대처: 정상 범위({normal_range[0]}~{normal_range[1]} {unit}) 내 유지를 권장합니다."
            else:
                conclusion_text = f"{entity_id} 값 이상 시 센서 상태 및 캘리브레이션을 점검하세요."

            conclusions.append({
                "type": "resolution",
                "entity_id": entity_id,
                "description": conclusion_text,
                "confidence": 0.9,
            })

            # 권장사항 추가
            if is_high:
                recommendations.append({
                    "type": "immediate",
                    "action": f"{entity_id} 과부하 대처: 속도 감소, 페이로드 확인, 경로 점검",
                    "steps": ["속도 파라미터 조정", "적재 중량 확인", "작업 경로 재검토", "조인트/센서 점검"],
                })

            paths.append(f"{entity_id} → 대처방법 분석")

        if conclusions:
            return {
                "reasoning": reasoning,
                "conclusions": conclusions,
                "recommendations": recommendations,
                "paths": paths,
                "confidence": 0.9,
            }
        return None

    def _is_relationship_query(self, query: str) -> bool:
        """관계 질문인지 확인 (어디에 장착, 연결, 구성, 어떤 센서가 측정 등)"""
        import re
        rel_patterns = [
            r"어디에.*(장착|연결|설치|부착)",
            r"(장착|연결|설치|부착).*(어디|위치)",
            r"(구성요소|컴포넌트|부품).*(뭐|무엇)",
            r"뭐가.*(연결|장착|설치)",
            r"(포함|구성|이루어)",
            # 측정 관계 질문: "어떤 센서가 측정해?", "무엇이 측정하는지"
            r"어떤.*(센서|장비).*(측정|감지)",
            r"(측정|감지).*(센서|장비).*(뭐|무엇|어떤)",
            r"(뭐|무엇|뭘|어떤).*(측정|감지)",
            # 정방향 측정 질문: "뭘 측정해?", "무엇을 측정해?"
            r"(측정|감지).*(뭐|무엇|뭘)",
        ]
        for pattern in rel_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _process_relationship_query(self, entities: list, query: str) -> Optional[Dict]:
        """관계 질문 처리 (Axia80은 어디에 장착돼?)"""
        if len(entities) < 1:
            return None

        reasoning = []
        conclusions = []
        paths = []

        # 주요 엔티티들의 관계 찾기
        for entity_info in entities:
            entity_id = _get_entity_attr(entity_info, "entity_id", "")
            entity = self.ontology.get_entity(entity_id)
            if not entity:
                continue

            reasoning.append(f"{entity_id} 엔티티의 관계를 탐색합니다.")

            # 나가는 관계 조회
            outgoing_rels = self.ontology.get_relationships_for_entity(entity_id, direction="outgoing")
            # 들어오는 관계 조회
            incoming_rels = self.ontology.get_relationships_for_entity(entity_id, direction="incoming")

            all_rels = outgoing_rels + incoming_rels

            for rel in all_rels:
                # Relationship 객체에서 속성 가져오기
                if hasattr(rel, 'relation'):
                    rel_type = rel.relation.value if hasattr(rel.relation, 'value') else str(rel.relation)
                else:
                    rel_type = rel.get('relation', '') if isinstance(rel, dict) else str(rel)
                source = rel.source if hasattr(rel, 'source') else (rel.get('source', '') if isinstance(rel, dict) else '')
                target = rel.target if hasattr(rel, 'target') else (rel.get('target', '') if isinstance(rel, dict) else '')

                # 장착/연결 관계 처리
                if rel_type in ("MOUNTED_ON", "CONNECTED_TO", "HAS_COMPONENT", "PART_OF"):
                    if source == entity_id:
                        reasoning.append(f"{source}는 {target}에 {rel_type} 관계로 연결됩니다.")
                        if rel_type == "MOUNTED_ON":
                            conclusions.append(f"{source}는 {target}에 장착되어 있습니다.")
                        elif rel_type == "CONNECTED_TO":
                            conclusions.append(f"{source}는 {target}에 연결되어 있습니다.")
                        elif rel_type == "HAS_COMPONENT":
                            conclusions.append(f"{source}는 {target}를 구성요소로 포함합니다.")
                    else:
                        reasoning.append(f"{target}는 {source}의 일부입니다 ({rel_type}).")
                        if rel_type == "MOUNTED_ON":
                            conclusions.append(f"{target}는 {source}에 장착되어 있습니다.")
                        elif rel_type == "HAS_COMPONENT":
                            conclusions.append(f"{source}는 {target}를 포함합니다.")

                    paths.append(f"{source} --[{rel_type}]--> {target}")

                # 측정 관계 처리 (MEASURES)
                elif rel_type == "MEASURES":
                    if target == entity_id:
                        # 역방향: "어떤 센서가 Fz를 측정해?" → source(Axia80)가 측정
                        reasoning.append(f"{source}가 {target}를 측정합니다 (MEASURES 관계).")
                        conclusions.append(f"{source} 센서가 {target}를 측정합니다.")
                        paths.append(f"{source} --[{rel_type}]--> {target}")
                    else:
                        # 정방향: "Axia80이 뭘 측정해?" → target(Fx,Fy,...)를 측정
                        reasoning.append(f"{source}가 {target}를 측정합니다.")
                        conclusions.append(f"{source}는 {target}를 측정합니다.")
                        paths.append(f"{source} --[{rel_type}]--> {target}")

        if conclusions:
            return {
                "reasoning": reasoning,
                "conclusions": conclusions,
                "paths": paths,
                "confidence": 0.9,
            }
        return None

    def _process_specification(self, entity_id: str, entity_type: str, query: str) -> Optional[Dict]:
        """사양 질문 처리 (페이로드가 몇 kg? 등)"""
        entity = self.ontology.get_entity(entity_id)
        if not entity:
            return None

        reasoning = []
        conclusions = []
        paths = []

        props = entity.properties or {}
        entity_name = entity.name or entity_id

        # 쿼리에서 어떤 사양을 묻는지 파악
        query_lower = query.lower()
        found_specs = []

        # 페이로드/무게 관련
        if any(kw in query_lower for kw in ["페이로드", "payload", "무게", "중량", "kg"]):
            if "payload_kg" in props:
                found_specs.append(f"최대 페이로드: {props['payload_kg']}kg")
            elif "max_payload" in props:
                found_specs.append(f"최대 페이로드: {props['max_payload']}kg")

        # 범위/반경 관련
        if any(kw in query_lower for kw in ["범위", "반경", "reach", "mm", "가동", "동작", "회전", "모션"]):
            if "reach_mm" in props:
                found_specs.append(f"작업 반경: {props['reach_mm']}mm")
            if "range" in props:
                r = props["range"]
                unit = props.get("unit", "")
                found_specs.append(f"측정 범위: {r[0]}~{r[1]} {unit}")
            if "normal_range" in props:
                nr = props["normal_range"]
                unit = props.get("unit", "")
                found_specs.append(f"정상 범위: {nr[0]}~{nr[1]} {unit}")
            # Joint 가동 범위 (range_deg)
            if "range_deg" in props:
                rd = props["range_deg"]
                found_specs.append(f"가동 범위: {rd[0]}°~{rd[1]}°")

        # 조인트/축 관련
        if any(kw in query_lower for kw in ["조인트", "joint", "축", "몇 축"]):
            if "joints" in props:
                found_specs.append(f"조인트 수: {props['joints']}축")
            if "axes" in props:
                found_specs.append(f"측정 축 수: {props['axes']}축")

        # 샘플링/주파수 관련
        if any(kw in query_lower for kw in ["샘플링", "sampling", "주파수", "hz"]):
            if "sampling_hz" in props:
                found_specs.append(f"샘플링 주파수: {props['sampling_hz']}Hz")

        # 특정 사양을 못 찾으면 모든 사양 반환
        if not found_specs:
            for key, value in props.items():
                if key in ["manufacturer", "model", "type", "description"]:
                    continue
                if isinstance(value, (int, float)):
                    found_specs.append(f"{key}: {value}")
                elif isinstance(value, list) and len(value) == 2:
                    found_specs.append(f"{key}: {value[0]}~{value[1]}")

        if not found_specs:
            return None

        reasoning.append({
            "step": "specification_lookup",
            "description": f"온톨로지에서 {entity_id} 사양 조회",
            "result": {"entity_id": entity_id, "specs": found_specs}
        })

        description = f"{entity_name}의 사양 정보입니다:\n" + "\n".join([f"- {spec}" for spec in found_specs])

        conclusions.append({
            "type": "specification",
            "entity_id": entity_id,
            "entity_name": entity_name,
            "description": description,
            "specs": found_specs,
            "confidence": 0.95,
        })

        paths.append(f"Ontology → {entity_id} → properties")

        return {
            "reasoning": reasoning,
            "conclusions": conclusions,
            "paths": paths,
        }

    def _is_comparison_query(self, query: str) -> bool:
        """비교 질문인지 확인"""
        import re
        comparison_patterns = [
            r"(비교|차이|다른|다르)",
            r"(compare|difference|different|vs)",
        ]
        for pattern in comparison_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _process_comparison(self, axis_entities: List[Dict], query: str) -> Optional[Dict]:
        """엔티티 비교 처리 (Fx와 Fz 비교 등)"""
        if len(axis_entities) < 2:
            return None

        reasoning = []
        conclusions = []
        paths = []

        # 비교할 엔티티들의 정보 수집
        comparison_data = []
        for entity_info in axis_entities:
            entity_id = _get_entity_attr(entity_info, "entity_id", "")
            entity = self.ontology.get_entity(entity_id)
            if entity:
                props = entity.properties or {}
                comparison_data.append({
                    "entity_id": entity_id,
                    "name": entity.name or entity_id,
                    "unit": props.get("unit", ""),
                    "normal_range": props.get("normal_range"),
                    "range": props.get("range"),
                    "measurement_type": props.get("measurement_type", ""),
                    "axis": props.get("axis", ""),
                })
                paths.append(f"Ontology → {entity_id}")

        if len(comparison_data) < 2:
            return None

        reasoning.append({
            "step": "comparison_analysis",
            "description": f"엔티티 비교 분석: {', '.join([d['entity_id'] for d in comparison_data])}",
            "result": comparison_data,
        })

        # 비교 결과 텍스트 생성
        comparison_text_parts = []
        for i, data in enumerate(comparison_data):
            entity_id = data["entity_id"]
            axis = data["axis"].upper() if data["axis"] else ""
            mtype = data["measurement_type"]

            if mtype == "force":
                type_desc = f"{axis}축 힘(Force)"
            elif mtype == "torque":
                type_desc = f"{axis}축 토크(Torque)"
            else:
                type_desc = entity_id

            nr = data.get("normal_range")
            spec_r = data.get("range")  # 스펙상 측정 범위
            unit = data.get("unit", "")
            
            desc = f"- {entity_id}: {type_desc}"
            if nr:
                desc += f", 정상 범위 {nr[0]}~{nr[1]} {unit}"
            if spec_r:
                desc += f", 측정 한계(Spec) {spec_r[0]}~{spec_r[1]} {unit}"
            comparison_text_parts.append(desc)

        # 차이점 분석
        diff_parts = []
        if len(comparison_data) == 2:
            d1, d2 = comparison_data[0], comparison_data[1]
            # 측정 유형 비교
            if d1.get("measurement_type") != d2.get("measurement_type"):
                t1 = "힘" if d1.get("measurement_type") == "force" else "토크"
                t2 = "힘" if d2.get("measurement_type") == "force" else "토크"
                diff_parts.append(f"측정 유형이 다릅니다 ({d1['entity_id']}: {t1}, {d2['entity_id']}: {t2})")
            
            # 1. 정상 범위(Maintenance) 비교
            nr1, nr2 = d1.get("normal_range"), d2.get("normal_range")
            if nr1 and nr2:
                # 범위가 완전히 같은지 확인
                if nr1 == nr2:
                    diff_parts.append(f"정상 범위가 동일합니다 ({nr1[0]}~{nr1[1]}).")
                else:
                    # Min/Max 비교
                    if nr1[1] != nr2[1]:
                        larger = d1['entity_id'] if nr1[1] > nr2[1] else d2['entity_id']
                        smaller = d2['entity_id'] if nr1[1] > nr2[1] else d1['entity_id']
                        max_val = max(nr1[1], nr2[1])
                        min_val = min(nr1[1], nr2[1])
                        diff_parts.append(f"{larger}의 정상 허용치가 {smaller}보다 높습니다 ({max_val} > {min_val}).")
                    
                    # 폭(Range Width) 비교
                    width1 = nr1[1] - nr1[0]
                    width2 = nr2[1] - nr2[0]
                    if abs(width1 - width2) > 1:
                         larger_width = d1['entity_id'] if width1 > width2 else d2['entity_id']
                         diff_parts.append(f"{larger_width}의 정상 범위 폭이 더 넓습니다 ({width1} vs {width2}).")
            
            # 2. 측정 한계(Spec) 비교
            sr1, sr2 = d1.get("range"), d2.get("range")
            if sr1 and sr2:
                # 스펙 최대값 비교
                if sr1[1] != sr2[1]:
                    larger_spec = d1['entity_id'] if sr1[1] > sr2[1] else d2['entity_id']
                    smaller_spec = d2['entity_id'] if sr1[1] > sr2[1] else d1['entity_id']
                    diff_parts.append(f"{larger_spec}가 측정 가능한 최대 한계(Spec)가 더 큽니다 ({max(sr1[1], sr2[1])} vs {min(sr1[1], sr2[1])}).")

        # 최종 비교 설명 조합
        comparison_desc = "\n".join(comparison_text_parts)
        if diff_parts:
            comparison_desc += "\n\n" + "차이점:\n" + "\n".join([f"- {d}" for d in diff_parts])

        conclusions.append({
            "type": "comparison",
            "entities": [d["entity_id"] for d in comparison_data],
            "description": comparison_desc,
            "comparison_data": comparison_data,
            "confidence": 0.95,
        })

        return {
            "reasoning": reasoning,
            "conclusions": conclusions,
            "paths": paths,
            "confidence": 0.95,
        }

    def _process_entity_definition(self, entity_id: str, entity_type: str = "") -> Optional[Dict]:
        """엔티티 정의 질문 처리 (Fx, Fy, UR5e, Axia80 등 기본 설명)"""
        entity = self.ontology.get_entity(entity_id)
        if not entity:
            return None

        reasoning = []
        conclusions = []
        paths = []

        # 엔티티 속성 추출
        props = entity.properties or {}
        entity_name = entity.name or entity_id
        entity_type_str = entity.type.value if hasattr(entity.type, 'value') else str(entity.type)

        # 엔티티 타입별 설명 생성
        description_parts = []

        # MeasurementAxis (Fx, Fy, Fz, Tx, Ty, Tz)
        if props.get("measurement_type") == "force":
            axis = props.get("axis", "").upper()
            description_parts.append(f"{entity_id}는 {axis}축 방향의 힘(Force)을 측정하는 센서 축이에요.")
        elif props.get("measurement_type") == "torque":
            axis = props.get("axis", "").upper()
            description_parts.append(f"{entity_id}는 {axis}축의 토크(Torque, 회전력)를 측정하는 센서 축이에요.")

        # Robot (UR5e)
        elif entity_type in ("Robot",) or entity_type_str == "Robot":
            manufacturer = props.get("manufacturer", "")
            payload = props.get("payload_kg", "")
            reach = props.get("reach_mm", "")
            joints = props.get("joints", "")
            description_parts.append(f"{entity_name}은(는) {manufacturer}에서 제조한 협동로봇이에요.")
            if payload:
                description_parts.append(f"최대 {payload}kg까지 들 수 있고,")
            if reach:
                description_parts.append(f"작업 반경은 {reach}mm입니다.")
            if joints:
                description_parts.append(f"{joints}축 로봇으로 다양한 작업이 가능해요.")

        # Sensor (Axia80)
        elif entity_type in ("Sensor",) or entity_type_str == "Sensor":
            manufacturer = props.get("manufacturer", "")
            sampling = props.get("sampling_hz", "")
            description_parts.append(f"{entity_name}은(는) {manufacturer}에서 제조한 6축 힘/토크 센서예요.")
            description_parts.append("로봇 끝단에 장착되어 힘(Fx, Fy, Fz)과 토크(Tx, Ty, Tz)를 실시간으로 측정합니다.")
            if sampling:
                description_parts.append(f"샘플링 주파수는 {sampling}Hz입니다.")

        # 일반 엔티티 (fallback)
        else:
            description_parts.append(f"{entity_name}은(는) {entity_type_str} 타입의 엔티티입니다.")

        if props.get("unit"):
            description_parts.append(f"단위는 {props['unit']}입니다.")

        if props.get("normal_range"):
            nr = props["normal_range"]
            description_parts.append(f"정상 범위는 {nr[0]}~{nr[1]} {props.get('unit', '')}이에요.")

        if props.get("range"):
            r = props["range"]
            description_parts.append(f"측정 가능 범위는 {r[0]}~{r[1]} {props.get('unit', '')}입니다.")

        reasoning.append({
            "step": "entity_definition",
            "description": f"온톨로지에서 {entity_id} 정의 조회",
            "result": {
                "entity_id": entity_id,
                "entity_name": entity_name,
                "entity_type": entity_type_str,
                "properties": props,
            }
        })

        conclusions.append({
            "type": "definition",
            "entity_id": entity_id,
            "entity_name": entity_name,
            "description": " ".join(description_parts),
            "properties": props,
            "confidence": 0.95,
        })

        paths.append(f"Ontology → {entity_id}")

        return {
            "reasoning": reasoning,
            "conclusions": conclusions,
            "paths": paths,
        }

    def _process_measurement_info(
        self,
        axis_id: str,
        query: str
    ) -> Optional[Dict]:
        """측정축 정보 제공 (값이 없는 트렌드/이상 질문용)

        "Fy가 계속 증가하고 있어" 같은 질문에 대해
        정상 범위 정보와 함께 확인 방법을 안내합니다.
        """
        entity = self.ontology.get_entity(axis_id)
        if not entity:
            return None

        reasoning = []
        conclusions = []
        paths = []

        props = entity.properties or {}
        normal_range = props.get("normal_range")
        unit = props.get("unit", "")

        # 질문 유형 판단 (증가/감소/진동/이상 등)
        query_lower = query.lower()
        is_increasing = any(kw in query_lower for kw in ["증가", "올라", "높아", "커지"])
        is_decreasing = any(kw in query_lower for kw in ["감소", "내려", "낮아", "작아", "떨어"])
        is_vibrating = any(kw in query_lower for kw in ["진동", "흔들", "변동", "불안정"])
        is_problem = any(kw in query_lower for kw in ["문제", "이상", "위험", "비정상"])

        reasoning.append({
            "step": "measurement_info",
            "description": f"{axis_id} 측정축 정보 조회",
            "result": {
                "normal_range": normal_range,
                "unit": unit,
            }
        })

        # 응답 구성
        info_parts = []
        info_parts.append(f"{axis_id} 센서 값의 변화가 감지되었군요.")

        if normal_range:
            info_parts.append(f"정상 범위는 {normal_range[0]}~{normal_range[1]}{unit}입니다.")

        if is_increasing:
            info_parts.append(f"값이 계속 증가하고 있다면, 정상 범위 상한({normal_range[1] if normal_range else '?'}{unit}) 근처에서 주의가 필요합니다.")
        elif is_decreasing:
            info_parts.append(f"값이 계속 감소하고 있다면, 정상 범위 하한({normal_range[0] if normal_range else '?'}{unit}) 근처에서 주의가 필요합니다.")
        elif is_vibrating:
            info_parts.append("값이 진동하는 경우, PAT_VIBRATION(진동) 패턴의 징후일 수 있습니다.")

        if is_problem:
            info_parts.append("현재 값을 확인하여 정상 범위를 벗어났는지 점검해 주세요.")

        conclusions.append(" ".join(info_parts))
        paths.append(f"Ontology → {axis_id} (정보 조회)")

        return {
            "reasoning": reasoning,
            "conclusions": conclusions,
            "paths": paths,
            "confidence": 0.8,
        }

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
            if _get_entity_attr(e, "entity_type") == "Value":
                value_entity = e
                break

        if not value_entity:
            return None

        # 값 파싱
        try:
            value_text = _get_entity_attr(value_entity, "text", "0")
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
            "에러 패턴": "PAT_ERROR",
            "오류 패턴": "PAT_ERROR",
            "에러패턴": "PAT_ERROR",
            "오류패턴": "PAT_ERROR",
        }

        resolved_pattern_id = pattern_id
        if not resolved_pattern_id or not resolved_pattern_id.startswith("PAT_"):
            resolved_pattern_id = pattern_mapping.get(pattern_text.lower(), "")
        if not resolved_pattern_id:
            return None

        # 시간 컨텍스트(최근/어제/오늘 등)가 있으면 '원인/예측'이 아니라 '이력/존재 여부'로 응답
        if context.get("has_temporal_context"):
            # PAT_ERROR는 모든 패턴 조회
            if resolved_pattern_id == "PAT_ERROR":
                history = self._build_all_patterns_history()
            else:
                history = self._build_pattern_history(resolved_pattern_id)
            return {
                "reasoning": [
                    {
                        "step": "pattern_history",
                        "description": f"패턴 이력 조회: {resolved_pattern_id}",
                        "result": history,
                    }
                ],
                "conclusions": [
                    {
                        "type": "pattern_history",
                        "pattern": resolved_pattern_id,
                        "count": history.get("count", 0),
                        "latest_timestamp": history.get("latest_timestamp", ""),
                        "samples": history.get("samples", []),
                        "time_range": history.get("time_range", {}),
                        "description": history.get("description", ""),
                        "confidence": history.get("confidence", 0.5),
                    }
                ],
                "recommendations": [],
                "paths": [f"SensorLog → detected_patterns.json → {resolved_pattern_id}"],
            }

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
            # 존재하지 않는 에러코드에 대한 응답
            return {
                "reasoning": [{
                    "step": "error_lookup",
                    "description": f"에러 코드 조회: {error_code}",
                    "result": "not_found",
                }],
                "conclusions": [{
                    "type": "definition",
                    "entity_id": error_code,
                    "entity_name": error_code,
                    "description": f"{error_code}은(는) 등록된 에러 코드가 아닙니다. UR5e 에러 코드는 C0~C255 범위이며, 티치펜던트나 로그에서 정확한 에러 코드를 확인해 주세요.",
                    "properties": {},
                    "confidence": 0.9,
                }],
                "recommendations": [{
                    "action": "티치펜던트 로그에서 정확한 에러 코드 확인",
                    "reference": "UR5e 사용자 매뉴얼 - 에러 코드",
                }],
                "paths": [],
            }

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
                        # action 필드 생성 (ResponseGenerator 호환)
                        steps = resolution.properties.get("steps", [])
                        action = resolution.name
                        if steps:
                            action = f"{resolution.name}: {steps[0]}" if len(steps) == 1 else f"{resolution.name}: {', '.join(steps[:2])}..."

                        recommendations.append({
                            "type": "resolution",
                            "for_cause": cause_id,
                            "resolution_id": resolution.id,
                            "name": resolution.name,
                            "action": action,  # ResponseGenerator 호환
                            "resolution": action,  # 대체 필드
                            "steps": steps,
                            "confidence": res_path.total_confidence,
                        })
                        paths.append(f"{error_code} →[CAUSED_BY]→ {cause_id} →[RESOLVED_BY]→ {resolution.id}")

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

        # 결론이 없으면 에러코드 기본 정의 반환
        if not conclusions:
            description = error_entity.properties.get("description", "")
            severity = error_entity.properties.get("severity", "unknown")
            error_name = error_entity.name or error_code

            # 정의 결론 추가
            def_text = f"{error_code}는 '{error_name}' 에러입니다."
            if description:
                def_text += f" {description}"
            if severity and severity != "unknown":
                def_text += f" (심각도: {severity})"

            conclusions.append({
                "type": "definition",
                "entity_id": error_code,
                "entity_name": error_name,
                "description": def_text,
                "properties": {
                    "severity": severity,
                    "category": error_entity.properties.get("category", ""),
                    "recoverable": error_entity.properties.get("recoverable", None),
                },
                "confidence": 0.9,
            })

        return {
            "reasoning": reasoning,
            "conclusions": conclusions,
            "recommendations": recommendations,
            "paths": paths,
        }

    def _process_error_category(
        self,
        category_id: str,
        category_text: str,
        context: Dict
    ) -> Optional[Dict]:
        """에러 카테고리 처리 (joint position, communication 등)

        카테고리에 해당하는 모든 에러 코드를 찾아 분석합니다.
        """
        # 카테고리 키워드 매핑
        category_keywords = {
            "CAT_JOINT_POSITION": ["position", "위치"],
            "CAT_JOINT_COMMUNICATION": ["communication", "통신"],
            "CAT_JOINT_CURRENT": ["current", "전류"],
            "CAT_JOINT_SPEED": ["speed", "속도"],
            "CAT_JOINT_TEMPERATURE": ["temperature", "온도", "과열"],
            "CAT_COMMUNICATION": ["communication", "통신", "연결"],
            "CAT_SAFETY": ["safety", "안전", "보호정지"],
            "CAT_POWER": ["power", "전원", "전력"],
            "CAT_ENCODER": ["encoder", "엔코더"],
            "CAT_CALIBRATION": ["calibration", "캘리브레이션", "보정"],
            "CAT_OVERLOAD": ["overload", "과부하"],
            "CAT_VIBRATION": ["vibration", "진동"],
            "CAT_SENSOR": ["sensor", "센서"],
        }

        keywords = category_keywords.get(category_id, [])
        if not keywords:
            return None

        reasoning = []
        conclusions = []
        recommendations = []
        paths = []

        # 온톨로지에서 카테고리에 해당하는 에러 코드 찾기
        matching_errors = []
        for entity in self.ontology.entities:
            if entity.type.value == "ErrorCode":
                # 에러 이름이나 설명에서 키워드 검색
                name_lower = (entity.name or "").lower()
                desc_lower = (entity.properties.get("description", "") or "").lower()
                category_str = (entity.properties.get("category", "") or "").lower()

                for keyword in keywords:
                    if keyword.lower() in name_lower or keyword.lower() in desc_lower or keyword.lower() in category_str:
                        matching_errors.append(entity)
                        break

        if not matching_errors:
            # 카테고리에 해당하는 에러가 없으면 일반적인 설명 제공
            reasoning.append({
                "step": "error_category_search",
                "description": f"카테고리 검색: {category_text}",
                "result": {"found": 0, "message": "해당 카테고리의 에러가 발견되지 않았습니다."}
            })
            conclusions.append({
                "type": "error_category",
                "category": category_id,
                "description": f"{category_text} 관련 에러는 현재 온톨로지에 등록되어 있지 않습니다.",
                "confidence": 0.5,
            })
            return {
                "reasoning": reasoning,
                "conclusions": conclusions,
                "recommendations": recommendations,
                "paths": paths,
            }

        # 발견된 에러 분석
        reasoning.append({
            "step": "error_category_search",
            "description": f"카테고리 검색: {category_text}",
            "result": {
                "found": len(matching_errors),
                "errors": [e.id for e in matching_errors[:5]],  # 상위 5개만 표시
            }
        })

        # 에러별 원인과 해결책 분석
        causes_summary = []
        resolutions_summary = []

        for error in matching_errors[:3]:  # 상위 3개만 상세 분석
            error_result = self._process_error_code(error.id, context)
            if error_result:
                # 원인 수집
                for conc in error_result.get("conclusions", []):
                    if conc.get("type") == "cause":
                        causes_summary.append({
                            "error": error.id,
                            "error_name": error.name,
                            "cause": conc.get("cause"),
                            "cause_name": conc.get("cause_name"),
                        })

                # 해결책 수집
                for rec in error_result.get("recommendations", []):
                    resolutions_summary.append({
                        "error": error.id,
                        "resolution": rec.get("name"),
                        "steps": rec.get("steps", []),
                    })

                paths.extend(error_result.get("paths", []))

        # 카테고리 종합 결론
        error_names = [f"{e.id} ({e.name})" for e in matching_errors[:5]]
        description_parts = [
            f"{category_text} 관련 에러 {len(matching_errors)}개를 찾았습니다:",
            "관련 에러 코드: " + ", ".join(error_names),
        ]

        if causes_summary:
            unique_causes = list({c["cause_name"] for c in causes_summary if c.get("cause_name")})
            if unique_causes:
                description_parts.append("주요 원인: " + ", ".join(unique_causes[:3]))

        if resolutions_summary:
            unique_resolutions = list({r["resolution"] for r in resolutions_summary if r.get("resolution")})
            if unique_resolutions:
                description_parts.append("해결 방법: " + ", ".join(unique_resolutions[:3]))

        conclusions.append({
            "type": "error_category",
            "category": category_id,
            "matching_errors": [e.id for e in matching_errors],
            "error_count": len(matching_errors),
            "description": "\n".join(description_parts),
            "causes": causes_summary,
            "confidence": 0.85,
        })

        # 해결책 추천
        for res in resolutions_summary[:2]:
            recommendations.append({
                "type": "resolution",
                "for_category": category_id,
                "resolution": res.get("resolution"),
                "steps": res.get("steps", []),
                "confidence": 0.8,
            })

        paths.append(f"ErrorCategory → {category_id} → matched {len(matching_errors)} errors")

        return {
            "reasoning": reasoning,
            "conclusions": conclusions,
            "recommendations": recommendations,
            "paths": paths,
        }

    def _process_maintenance_status(
        self,
        entity_id: str,
        entity_text: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """예비보전/예방보전 상태 쿼리 처리

        현재 로봇 상태를 종합적으로 분석하여 보고합니다:
        - 최근 감지된 패턴 (충돌, 과부하, 진동 등)
        - 최근 에러 발생 빈도
        - 센서 데이터 이상 징후
        """
        reasoning = []
        conclusions = []
        recommendations = []
        paths = []

        # 1. 최근 패턴 이력 조회
        patterns = self._load_detected_patterns()
        recent_patterns = []
        if patterns:
            # 최근 7일 내 패턴만 필터링 (있으면)
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(days=7)
            for p in patterns:
                ts = p.get("timestamp")
                if ts:
                    try:
                        pt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if pt.replace(tzinfo=None) >= cutoff:
                            recent_patterns.append(p)
                    except (ValueError, TypeError):
                        recent_patterns.append(p)  # 파싱 실패 시 포함
                else:
                    recent_patterns.append(p)

        reasoning.append({
            "step": "pattern_analysis",
            "description": "최근 패턴 이력 분석",
            "result": {
                "total_patterns": len(patterns) if patterns else 0,
                "recent_patterns": len(recent_patterns),
            }
        })

        # 2. 상태 평가
        status_level = "정상"
        issues = []

        if recent_patterns:
            pattern_counts = {}
            for p in recent_patterns:
                pt = p.get("pattern_type", "unknown")
                pattern_counts[pt] = pattern_counts.get(pt, 0) + 1

            for pt, count in pattern_counts.items():
                if count >= 3:
                    status_level = "주의"
                    issues.append(f"{pt} 패턴이 {count}회 감지됨")
                elif count >= 1:
                    if status_level == "정상":
                        status_level = "양호"
                    issues.append(f"{pt} 패턴이 {count}회 감지됨")

        # 3. 결론 생성
        if status_level == "정상":
            description = (
                "현재 예비보전 상태: 정상\n\n"
                "최근 7일간 특이 패턴이 감지되지 않았습니다. "
                "로봇 시스템이 안정적으로 운영되고 있습니다."
            )
            confidence = 0.9
        elif status_level == "양호":
            description = (
                "현재 예비보전 상태: 양호\n\n"
                f"최근 감지된 사항:\n- " + "\n- ".join(issues) + "\n\n"
                "경미한 패턴이 감지되었으나 즉각적인 조치가 필요한 수준은 아닙니다. "
                "지속적인 모니터링을 권장합니다."
            )
            confidence = 0.85
        else:  # 주의
            description = (
                "현재 예비보전 상태: 주의 필요\n\n"
                f"최근 감지된 사항:\n- " + "\n- ".join(issues) + "\n\n"
                "반복적인 패턴이 감지되었습니다. 원인 분석 및 예방 조치를 권장합니다."
            )
            confidence = 0.85
            recommendations.append({
                "type": "maintenance",
                "action": "점검 권장",
                "description": "반복적인 패턴이 감지되어 사전 점검을 권장합니다.",
                "priority": "medium",
            })

        conclusions.append({
            "type": "maintenance_status",
            "status_level": status_level,
            "description": description,
            "recent_pattern_count": len(recent_patterns),
            "issues": issues,
            "confidence": confidence,
        })

        paths.append("MaintenanceStatus → PatternHistory → StatusEvaluation")

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
