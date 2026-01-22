"""
온톨로지 연결기

감지된 패턴을 온톨로지와 연결합니다.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from .patterns import DetectedPattern, PatternType
from src.ontology import (
    OntologySchema,
    Entity,
    Relationship,
    load_ontology,
    EntityType,
    RelationType,
)

logger = logging.getLogger(__name__)


class OntologyConnector:
    """온톨로지 연결기

    감지된 패턴을 온톨로지 엔티티 및 관계와 연결합니다.
    """

    MAPPING_PATH = Path("configs/error_pattern_mapping.yaml")

    # Shift 시간대 매핑 (기본값)
    DEFAULT_SHIFT_MAPPING = {
        "SHIFT_A": {"start_hour": 6, "end_hour": 14},
        "SHIFT_B": {"start_hour": 14, "end_hour": 22},
        "SHIFT_C": {"start_hour": 22, "end_hour": 6},
    }

    # 패턴 타입 → 온톨로지 엔티티 ID (기본값)
    DEFAULT_PATTERN_ENTITY_MAPPING = {
        PatternType.COLLISION: "PAT_COLLISION",
        PatternType.OVERLOAD: "PAT_OVERLOAD",
        PatternType.DRIFT: "PAT_DRIFT",
        PatternType.VIBRATION: "PAT_VIBRATION",
    }

    def __init__(
        self,
        ontology_schema: Optional[OntologySchema] = None,
        mapping_path: Optional[Path] = None
    ):
        """초기화

        Args:
            ontology_schema: 온톨로지 스키마 (없으면 자동 로드)
            mapping_path: 매핑 설정 파일 경로
        """
        if ontology_schema is not None:
            self._schema = ontology_schema
        else:
            self._schema = load_ontology()

        self._mapping_path = mapping_path or self.MAPPING_PATH
        self._mapping: Optional[Dict] = None
        self._event_counter = 0

        logger.info("OntologyConnector 초기화 완료")

    @property
    def schema(self) -> OntologySchema:
        """온톨로지 스키마"""
        return self._schema

    def load_mapping(self) -> Dict:
        """매핑 설정 로드

        Returns:
            매핑 설정 딕셔너리
        """
        if self._mapping is not None:
            return self._mapping

        if not self._mapping_path.exists():
            logger.warning(f"매핑 파일 없음: {self._mapping_path}")
            self._mapping = {}
            return self._mapping

        with open(self._mapping_path, "r", encoding="utf-8") as f:
            self._mapping = yaml.safe_load(f)

        logger.info(f"매핑 설정 로드: {self._mapping_path}")
        return self._mapping

    def map_pattern_to_errors(
        self,
        pattern: DetectedPattern
    ) -> List[Dict[str, Any]]:
        """패턴 → 에러코드 매핑

        Args:
            pattern: 감지된 패턴

        Returns:
            [{"code": "C153", "confidence": 0.95}, ...]
        """
        mapping = self.load_mapping()
        ontology_mapping = mapping.get("ontology_pattern_mapping", {})

        pattern_type = pattern.pattern_type.value
        pattern_config = ontology_mapping.get(pattern_type, {})

        triggers = pattern_config.get("triggers", [])

        # 패턴의 기존 에러 코드와 매핑 병합
        result = []
        existing_codes = set(pattern.related_error_codes)

        for trigger in triggers:
            code = trigger.get("code")
            confidence = trigger.get("confidence", 0.8)

            # 기존 에러 코드가 있으면 신뢰도 조정
            if code in existing_codes:
                confidence = min(1.0, confidence + 0.1)

            result.append({
                "code": code,
                "confidence": confidence,
                "source": "mapping",
            })

        # 기존 에러 코드 중 매핑에 없는 것 추가
        mapped_codes = {r["code"] for r in result}
        for code in existing_codes:
            if code not in mapped_codes:
                result.append({
                    "code": code,
                    "confidence": 0.9,  # 데이터 기반 높은 신뢰도
                    "source": "detected",
                })

        return result

    def map_pattern_to_causes(
        self,
        pattern: DetectedPattern
    ) -> List[Dict[str, Any]]:
        """패턴 → 원인 매핑

        Args:
            pattern: 감지된 패턴

        Returns:
            [{"cause": "CAUSE_PHYSICAL_CONTACT", "confidence": 0.95}, ...]
        """
        mapping = self.load_mapping()
        ontology_mapping = mapping.get("ontology_pattern_mapping", {})

        pattern_type = pattern.pattern_type.value
        pattern_config = ontology_mapping.get(pattern_type, {})

        indicates = pattern_config.get("indicates", [])

        return [
            {
                "cause": ind.get("cause"),
                "confidence": ind.get("confidence", 0.7),
            }
            for ind in indicates
        ]

    def get_pattern_entity_id(self, pattern_type: PatternType) -> str:
        """패턴 타입 → 온톨로지 엔티티 ID

        Args:
            pattern_type: 패턴 타입

        Returns:
            온톨로지 엔티티 ID
        """
        mapping = self.load_mapping()
        entity_mapping = mapping.get("pattern_entity_mapping", {})

        pattern_key = pattern_type.value
        if pattern_key in entity_mapping:
            return entity_mapping[pattern_key]

        return self.DEFAULT_PATTERN_ENTITY_MAPPING.get(
            pattern_type,
            f"PAT_{pattern_type.value.upper()}"
        )

    def get_shift_for_timestamp(self, timestamp: datetime) -> str:
        """시각 → Shift ID

        Args:
            timestamp: 시각

        Returns:
            Shift ID (SHIFT_A, SHIFT_B, SHIFT_C)
        """
        mapping = self.load_mapping()
        shift_mapping = mapping.get("shift_mapping", self.DEFAULT_SHIFT_MAPPING)

        hour = timestamp.hour

        for shift_id, config in shift_mapping.items():
            start = config.get("start_hour", 0)
            end = config.get("end_hour", 24)

            # 야간 근무 처리 (22 ~ 6)
            if start > end:
                if hour >= start or hour < end:
                    return shift_id
            else:
                if start <= hour < end:
                    return shift_id

        return "SHIFT_A"  # 기본값

    def create_event(
        self,
        pattern: DetectedPattern,
        context: Optional[Dict[str, Any]] = None
    ) -> Entity:
        """패턴 발생 이벤트 엔티티 생성

        Args:
            pattern: 감지된 패턴
            context: 컨텍스트 정보

        Returns:
            이벤트 Entity
        """
        self._event_counter += 1

        # 이벤트 ID: 패턴 ID 기반 또는 신규 생성
        if pattern.event_id:
            event_id = pattern.event_id
        else:
            event_id = f"EVT-{self._event_counter:03d}"

        # 컨텍스트 병합
        event_context = pattern.context.copy() if pattern.context else {}
        if context:
            event_context.update(context)

        event = Entity(
            id=event_id,
            type=EntityType.EVENT,
            name=f"패턴 이벤트 ({pattern.pattern_type.value})",
            properties={
                "pattern_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type.value,
                "timestamp": pattern.timestamp.isoformat(),
                "duration_ms": pattern.duration_ms,
                "confidence": pattern.confidence,
                "metrics": pattern.metrics,
                "context": event_context,
            },
        )

        return event

    def create_relationships(
        self,
        pattern: DetectedPattern,
        event: Optional[Entity] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Relationship]:
        """온톨로지 관계 생성

        Args:
            pattern: 감지된 패턴
            event: 이벤트 엔티티 (없으면 자동 생성)
            context: 컨텍스트 정보

        Returns:
            생성된 관계 목록
        """
        relationships = []

        # 패턴 엔티티 ID
        pattern_entity_id = self.get_pattern_entity_id(pattern.pattern_type)

        # 1. Pattern → ErrorCode (TRIGGERS)
        errors = self.map_pattern_to_errors(pattern)
        for error_info in errors:
            rel = Relationship(
                source=pattern_entity_id,
                relation=RelationType.TRIGGERS,
                target=error_info["code"],
                properties={
                    "confidence": error_info["confidence"],
                    "source": error_info.get("source", "mapping"),
                },
            )
            relationships.append(rel)

        # 2. Pattern → Cause (INDICATES)
        causes = self.map_pattern_to_causes(pattern)
        for cause_info in causes:
            rel = Relationship(
                source=pattern_entity_id,
                relation=RelationType.INDICATES,
                target=cause_info["cause"],
                properties={
                    "confidence": cause_info["confidence"],
                },
            )
            relationships.append(rel)

        # 3. 이벤트 관계 (Event → Pattern, Shift, Product)
        if event is not None:
            # Event → Pattern (INSTANCE_OF)
            rel = Relationship(
                source=event.id,
                relation=RelationType.INSTANCE_OF,
                target=pattern_entity_id,
                properties={
                    "timestamp": pattern.timestamp.isoformat(),
                },
            )
            relationships.append(rel)

            # Event → Shift (OCCURS_DURING)
            shift_id = self.get_shift_for_timestamp(pattern.timestamp)
            rel = Relationship(
                source=event.id,
                relation=RelationType.OCCURS_DURING,
                target=shift_id,
                properties={
                    "timestamp": pattern.timestamp.isoformat(),
                },
            )
            relationships.append(rel)

            # Event → Product (INVOLVES) - 컨텍스트에서
            if context and "product_id" in context:
                product_id = context["product_id"]
                if product_id:
                    rel = Relationship(
                        source=event.id,
                        relation=RelationType.INVOLVES,
                        target=product_id,
                        properties={},
                    )
                    relationships.append(rel)

        return relationships

    def enrich_ontology(
        self,
        patterns: List[DetectedPattern],
        include_events: bool = True
    ) -> OntologySchema:
        """패턴 기반 온톨로지 확장

        Args:
            patterns: 패턴 목록
            include_events: 이벤트 엔티티 포함 여부

        Returns:
            확장된 OntologySchema
        """
        # 기존 관계 ID 추적 (중복 방지)
        existing_rels = set()
        for rel in self._schema.relationships:
            key = (rel.source, rel.relation.value, rel.target)
            existing_rels.add(key)

        new_entities = []
        new_relationships = []

        for pattern in patterns:
            # 이벤트 생성
            event = None
            if include_events:
                event = self.create_event(pattern)
                new_entities.append(event)

            # 관계 생성
            relationships = self.create_relationships(
                pattern,
                event=event,
                context=pattern.context,
            )

            for rel in relationships:
                key = (rel.source, rel.relation.value, rel.target)
                if key not in existing_rels:
                    new_relationships.append(rel)
                    existing_rels.add(key)

        # 온톨로지에 추가
        for entity in new_entities:
            self._schema.add_entity(entity)

        for rel in new_relationships:
            self._schema.add_relationship(rel)

        logger.info(
            f"온톨로지 확장: {len(new_entities)} 엔티티, "
            f"{len(new_relationships)} 관계 추가"
        )

        return self._schema

    def get_pattern_context(
        self,
        pattern: DetectedPattern
    ) -> Dict[str, Any]:
        """패턴의 온톨로지 컨텍스트 조회

        Args:
            pattern: 감지된 패턴

        Returns:
            온톨로지 컨텍스트 (관련 엔티티, 관계)
        """
        pattern_entity_id = self.get_pattern_entity_id(pattern.pattern_type)

        # 패턴 엔티티 조회
        pattern_entity = self._schema.get_entity(pattern_entity_id)

        # 관련 관계 조회
        relationships = self._schema.get_relationships_for_entity(
            pattern_entity_id,
            direction="outgoing"
        )

        # 관련 에러 코드
        error_codes = [
            rel.target for rel in relationships
            if rel.relation == RelationType.TRIGGERS
        ]

        # 관련 원인
        causes = [
            rel.target for rel in relationships
            if rel.relation == RelationType.INDICATES
        ]

        return {
            "pattern_entity": pattern_entity.to_dict() if pattern_entity else None,
            "error_codes": error_codes,
            "causes": causes,
            "shift": self.get_shift_for_timestamp(pattern.timestamp),
            "relationships_count": len(relationships),
        }

    def get_summary(self) -> Dict[str, Any]:
        """연결 요약

        Returns:
            요약 딕셔너리
        """
        mapping = self.load_mapping()

        return {
            "ontology_entities": len(self._schema.entities),
            "ontology_relationships": len(self._schema.relationships),
            "pattern_types_mapped": len(
                mapping.get("ontology_pattern_mapping", {})
            ),
            "shift_mapping": list(
                mapping.get("shift_mapping", self.DEFAULT_SHIFT_MAPPING).keys()
            ),
        }


# 편의 함수
def create_ontology_connector(
    ontology_schema: Optional[OntologySchema] = None
) -> OntologyConnector:
    """OntologyConnector 인스턴스 생성"""
    return OntologyConnector(ontology_schema)
