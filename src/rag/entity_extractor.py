"""
엔티티 추출기

질문에서 온톨로지 엔티티를 추출합니다.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple

from src.ontology import (
    load_ontology,
    load_lexicon,
    resolve_alias,
    OntologySchema,
    EntityType,
)
from .evidence_schema import ExtractedEntity

logger = logging.getLogger(__name__)


class EntityExtractor:
    """온톨로지 기반 엔티티 추출기"""

    # 센서 축 패턴
    AXIS_PATTERN = re.compile(r'\b(Fz|Fx|Fy|Tx|Ty|Tz)\b', re.IGNORECASE)

    # 수치값 패턴 (예: -350N, 500N, -20.5N)
    VALUE_PATTERN = re.compile(r'(-?\d+(?:\.\d+)?)\s*(N|Nm|kg|mm|도|℃)?')

    # 에러코드 패턴 (예: C153, C189, C10)
    ERROR_CODE_PATTERN = re.compile(r'\b(C\d{1,3})\b', re.IGNORECASE)

    # 시간 패턴 (예: 14시, 14:00, 어제, 오늘)
    TIME_PATTERN = re.compile(r'(\d{1,2}시|\d{1,2}:\d{2}|어제|오늘|내일|그제|모레)', re.IGNORECASE)

    # 패턴 타입 패턴
    PATTERN_TYPE_KEYWORDS = {
        "collision": ["충돌", "collision", "부딪", "접촉"],
        "overload": ["과부하", "overload", "과하중", "무거"],
        "drift": ["드리프트", "drift", "편차", "이동"],
        "vibration": ["진동", "vibration", "떨림"],
    }

    # Shift 패턴
    SHIFT_KEYWORDS = {
        "SHIFT_A": ["오전", "아침", "A조", "주간", "6시", "7시", "8시", "9시", "10시", "11시", "12시", "13시"],
        "SHIFT_B": ["오후", "B조", "14시", "15시", "16시", "17시", "18시", "19시", "20시", "21시"],
        "SHIFT_C": ["야간", "밤", "C조", "22시", "23시", "0시", "1시", "2시", "3시", "4시", "5시"],
    }

    # 제품 패턴
    PRODUCT_KEYWORDS = {
        "PART-A": ["PART-A", "파트A", "제품A", "A제품"],
        "PART-B": ["PART-B", "파트B", "제품B", "B제품"],
        "PART-C": ["PART-C", "파트C", "제품C", "C제품"],
    }

    def __init__(self, ontology: Optional[OntologySchema] = None):
        """초기화

        Args:
            ontology: 온톨로지 스키마 (없으면 자동 로드)
        """
        self._ontology = ontology or load_ontology()
        self._lexicon = load_lexicon()
        self._build_entity_index()
        logger.info(f"EntityExtractor 초기화 완료: {len(self._entity_index)} 엔티티")

    def _build_entity_index(self) -> None:
        """엔티티 인덱스 구축 (빠른 조회용)"""
        self._entity_index: Dict[str, Tuple[str, str]] = {}  # text -> (entity_id, entity_type)

        # 온톨로지 엔티티 인덱싱
        for entity in self._ontology.entities:
            # ID로 인덱싱
            self._entity_index[entity.id.lower()] = (entity.id, entity.type.value)
            # 이름으로 인덱싱
            self._entity_index[entity.name.lower()] = (entity.id, entity.type.value)

        # Lexicon (동의어) 인덱싱
        if self._lexicon:
            for entity_id, aliases in self._lexicon.items():
                for alias in aliases:
                    self._entity_index[alias.lower()] = (entity_id, "alias")

    def extract(self, query: str) -> List[ExtractedEntity]:
        """질문에서 엔티티 추출

        Args:
            query: 질문 문자열

        Returns:
            추출된 엔티티 리스트
        """
        entities: List[ExtractedEntity] = []

        # 1. 센서 축 추출
        entities.extend(self._extract_axes(query))

        # 2. 수치값 추출
        entities.extend(self._extract_values(query))

        # 3. 에러코드 추출
        entities.extend(self._extract_error_codes(query))

        # 4. 시간 추출
        entities.extend(self._extract_time(query))

        # 5. 패턴 타입 추출
        entities.extend(self._extract_pattern_types(query))

        # 6. Shift 추출
        entities.extend(self._extract_shifts(query))

        # 7. 제품 추출
        entities.extend(self._extract_products(query))

        # 8. 온톨로지 엔티티 직접 매칭
        entities.extend(self._extract_ontology_entities(query))

        # 중복 제거
        entities = self._deduplicate(entities)

        logger.debug(f"추출된 엔티티: {[e.entity_id for e in entities]}")
        return entities

    def _extract_axes(self, query: str) -> List[ExtractedEntity]:
        """센서 축 추출"""
        entities = []
        for match in self.AXIS_PATTERN.finditer(query):
            axis = match.group(1)
            # 표준화 (대문자 첫글자)
            axis_id = axis[0].upper() + axis[1:].lower()
            entities.append(ExtractedEntity(
                text=match.group(0),
                entity_id=axis_id,
                entity_type="MeasurementAxis",
                confidence=1.0,
            ))
        return entities

    def _extract_values(self, query: str) -> List[ExtractedEntity]:
        """수치값 추출"""
        entities = []
        for match in self.VALUE_PATTERN.finditer(query):
            value_str = match.group(1)
            unit = match.group(2) or ""
            try:
                value = float(value_str)
                entities.append(ExtractedEntity(
                    text=match.group(0),
                    entity_id=f"{value}{unit}",
                    entity_type="Value",
                    confidence=0.9,
                    properties={"value": value, "unit": unit},
                ))
            except ValueError:
                pass
        return entities

    def _extract_error_codes(self, query: str) -> List[ExtractedEntity]:
        """에러코드 추출"""
        entities = []
        for match in self.ERROR_CODE_PATTERN.finditer(query):
            code = match.group(1).upper()
            entities.append(ExtractedEntity(
                text=match.group(0),
                entity_id=code,
                entity_type="ErrorCode",
                confidence=1.0,
            ))
        return entities

    def _extract_time(self, query: str) -> List[ExtractedEntity]:
        """시간 표현 추출"""
        entities = []
        for match in self.TIME_PATTERN.finditer(query):
            time_text = match.group(1)
            entities.append(ExtractedEntity(
                text=time_text,
                entity_id=time_text,
                entity_type="TimeExpression",
                confidence=0.85,
            ))
        return entities

    def _extract_pattern_types(self, query: str) -> List[ExtractedEntity]:
        """패턴 타입 키워드 추출"""
        entities = []
        query_lower = query.lower()

        for pattern_type, keywords in self.PATTERN_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    entities.append(ExtractedEntity(
                        text=keyword,
                        entity_id=f"PAT_{pattern_type.upper()}",
                        entity_type="Pattern",
                        confidence=0.85,
                    ))
                    break  # 하나만 추가
        return entities

    def _extract_shifts(self, query: str) -> List[ExtractedEntity]:
        """근무 Shift 추출"""
        entities = []
        query_lower = query.lower()

        for shift_id, keywords in self.SHIFT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    entities.append(ExtractedEntity(
                        text=keyword,
                        entity_id=shift_id,
                        entity_type="Shift",
                        confidence=0.8,
                    ))
                    break
        return entities

    def _extract_products(self, query: str) -> List[ExtractedEntity]:
        """제품 추출"""
        entities = []
        query_upper = query.upper()

        for product_id, keywords in self.PRODUCT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.upper() in query_upper:
                    entities.append(ExtractedEntity(
                        text=keyword,
                        entity_id=product_id,
                        entity_type="Product",
                        confidence=0.9,
                    ))
                    break
        return entities

    def _extract_ontology_entities(self, query: str) -> List[ExtractedEntity]:
        """온톨로지 엔티티 직접 매칭"""
        entities = []
        query_lower = query.lower()

        # 긴 것부터 매칭 (더 구체적인 엔티티 우선)
        sorted_keys = sorted(self._entity_index.keys(), key=len, reverse=True)

        matched_spans: List[Tuple[int, int]] = []

        for key in sorted_keys:
            # 단어 경계 검사
            pattern = re.compile(r'\b' + re.escape(key) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(query_lower):
                start, end = match.start(), match.end()

                # 이미 매칭된 구간과 겹치지 않는지 확인
                overlaps = any(
                    not (end <= s or start >= e)
                    for s, e in matched_spans
                )
                if overlaps:
                    continue

                entity_id, entity_type = self._entity_index[key]
                entities.append(ExtractedEntity(
                    text=query[start:end],
                    entity_id=entity_id,
                    entity_type=entity_type,
                    confidence=0.9,
                ))
                matched_spans.append((start, end))

        return entities

    def _deduplicate(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """중복 엔티티 제거 (같은 entity_id)"""
        seen: Dict[str, ExtractedEntity] = {}
        for entity in entities:
            key = entity.entity_id
            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity
        return list(seen.values())

    def resolve_entity(self, text: str) -> Optional[ExtractedEntity]:
        """텍스트를 엔티티로 해석

        Args:
            text: 입력 텍스트

        Returns:
            해석된 엔티티 또는 None
        """
        text_lower = text.lower()

        # 직접 매칭
        if text_lower in self._entity_index:
            entity_id, entity_type = self._entity_index[text_lower]
            return ExtractedEntity(
                text=text,
                entity_id=entity_id,
                entity_type=entity_type,
                confidence=1.0,
            )

        # Lexicon 별칭 해석
        resolved = resolve_alias(text)
        if resolved and resolved != text:
            entity = self._ontology.get_entity(resolved)
            if entity:
                return ExtractedEntity(
                    text=text,
                    entity_id=entity.id,
                    entity_type=entity.type.value,
                    confidence=0.9,
                )

        return None


# 편의 함수
def create_entity_extractor() -> EntityExtractor:
    """EntityExtractor 인스턴스 생성"""
    return EntityExtractor()
