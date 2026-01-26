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

    # 한국어 조사 패턴 (축 이름 뒤에 붙을 수 있는 조사들)
    # NOTE: 다문자 조사("에서", "으로")까지 고려해 alternation으로 정의
    KOREAN_PARTICLES = r'(?:으로|에서|가|이|를|을|은|는|도|의|로)?'

    # 센서 축 패턴 (한국어 조사 지원)
    # 예: "Fz", "Fz가", "Fz는", "Fz를" 모두 매칭
    AXIS_PATTERN = re.compile(
        r'(?<![a-zA-Z])(Fz|Fx|Fy|Tx|Ty|Tz)' + KOREAN_PARTICLES + r'(?![a-zA-Z])',
        re.IGNORECASE
    )

    # 수치값 패턴 (예: -350N, 500N, -20.5N)
    VALUE_PATTERN = re.compile(r'(-?\d+(?:\.\d+)?)\s*(N|Nm|kg|mm|도|℃)?')

    # 에러코드 패턴 (예: C153, C189, C10)
    # NOTE: 한국어 조사 결합(예: "C153이")도 허용하기 위해 \b 대신 ASCII 경계 기반 제약 사용
    ERROR_CODE_PATTERN = re.compile(
        r'(?<![a-zA-Z0-9])(C\d{1,3})' + KOREAN_PARTICLES + r'(?![a-zA-Z0-9])',
        re.IGNORECASE,
    )

    # 시간 패턴 (예: 14시, 14:00, 어제, 오늘, 최근)
    # NOTE: "최근"류 질의(이력/존재 여부)는 센서 이벤트/패턴 로그 조회로 처리할 수 있도록 포함
    TIME_PATTERN = re.compile(
        r'(\d{1,2}시|\d{1,2}:\d{2}|어제|오늘|내일|그제|모레|최근|최근에|요즘|근래|방금)',
        re.IGNORECASE,
    )

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

    # 장비 패턴 (UR5e, Axia80 등 - 한국어 조사 지원)
    EQUIPMENT_PATTERN = re.compile(
        r'(UR5e|Axia80|Axia)' + KOREAN_PARTICLES,
        re.IGNORECASE
    )

    # 에러 카테고리 키워드 (joint position 에러, communication 에러 등)
    ERROR_CATEGORY_KEYWORDS = {
        "joint_position": ["joint position", "조인트 위치", "관절 위치", "position 에러"],
        "joint_communication": ["joint communication", "조인트 통신", "관절 통신"],
        "joint_current": ["joint current", "조인트 전류", "관절 전류"],
        "joint_speed": ["joint speed", "조인트 속도", "관절 속도"],
        "joint_temperature": ["joint temperature", "조인트 온도", "관절 온도", "과열"],
        "communication": ["communication", "통신", "연결"],
        "safety": ["safety", "안전", "보호정지"],
        "power": ["power", "전원", "전력"],
        "encoder": ["encoder", "엔코더"],
        "calibration": ["calibration", "캘리브레이션", "보정"],
        "overload": ["overload", "과부하", "과하중"],
        "vibration": ["vibration", "진동"],
        "sensor": ["sensor", "센서", "force sensor", "힘 센서"],
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

        # 8. 장비 추출 (UR5e, Axia80)
        entities.extend(self._extract_equipment(query))

        # 9. 에러 카테고리 추출 (joint position 에러 등)
        entities.extend(self._extract_error_categories(query))

        # 10. 온톨로지 엔티티 직접 매칭
        entities.extend(self._extract_ontology_entities(query))

        # 중복 제거
        entities = self._deduplicate(entities)

        logger.debug(f"추출된 엔티티: {[e.entity_id for e in entities]}")
        return entities

    def _extract_axes(self, query: str) -> List[ExtractedEntity]:
        """센서 축 추출 (한국어 조사 지원)

        "Fz가 -350N" → Fz 추출
        "Fz는 정상" → Fz 추출
        "Fz 값이" → Fz 추출
        """
        entities = []
        for match in self.AXIS_PATTERN.finditer(query):
            axis = match.group(1)  # 축 이름만 (조사 제외)
            # 표준화 (대문자 첫글자)
            axis_id = axis[0].upper() + axis[1:].lower()
            entities.append(ExtractedEntity(
                text=axis,  # 축 이름만 저장 (조사 제외)
                entity_id=axis_id,
                entity_type="MeasurementAxis",
                confidence=1.0,
            ))
        return entities

    def _extract_values(self, query: str) -> List[ExtractedEntity]:
        """수치값 추출"""
        entities = []
        # 장비명 내부 숫자를 제외하기 위한 패턴 (UR5e, Axia80 등)
        equipment_pattern = re.compile(r'(UR5e|Axia80)', re.IGNORECASE)
        equipment_spans = [(m.start(), m.end()) for m in equipment_pattern.finditer(query)]

        for match in self.VALUE_PATTERN.finditer(query):
            # 에러 코드 "C153" 같은 토큰 내부 숫자(153)를 값으로 오인하지 않도록 필터링
            if match.start() > 0 and query[match.start() - 1] in ("C", "c"):
                continue

            # 장비명 내부 숫자(UR5e의 "5", Axia80의 "80")를 값으로 오인하지 않도록 필터링
            match_start, match_end = match.start(), match.end()
            is_inside_equipment = any(
                eq_start <= match_start < eq_end
                for eq_start, eq_end in equipment_spans
            )
            if is_inside_equipment:
                continue

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
                text=code,  # 조사 제외한 코드만 저장
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

    def _extract_equipment(self, query: str) -> List[ExtractedEntity]:
        """장비 추출 (UR5e, Axia80 등 - 한국어 조사 지원)"""
        entities = []
        for match in self.EQUIPMENT_PATTERN.finditer(query):
            equipment = match.group(1)
            # 표준화
            if equipment.lower() == "ur5e":
                equipment_id = "UR5e"
                equipment_type = "Robot"
            elif equipment.lower() in ("axia80", "axia"):
                equipment_id = "Axia80"
                equipment_type = "Sensor"
            else:
                equipment_id = equipment
                equipment_type = "Equipment"

            entities.append(ExtractedEntity(
                text=equipment,
                entity_id=equipment_id,
                entity_type=equipment_type,
                confidence=1.0,
            ))
        return entities

    def _extract_error_categories(self, query: str) -> List[ExtractedEntity]:
        """에러 카테고리 키워드 추출 (joint position 에러 등)

        "joint position 에러가 자주 나" → joint_position 카테고리 추출
        "통신 에러" → communication 카테고리 추출
        """
        entities = []
        query_lower = query.lower()

        for category_id, keywords in self.ERROR_CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    entities.append(ExtractedEntity(
                        text=keyword,
                        entity_id=f"CAT_{category_id.upper()}",
                        entity_type="ErrorCategory",
                        confidence=0.9,
                        properties={"category": category_id},
                    ))
                    break  # 카테고리당 하나만 추가
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
