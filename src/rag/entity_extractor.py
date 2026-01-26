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
        r'(?<![a-zA-Z])(Fz|Fx|Fy|Tx|Ty|Tz|Mx|My|Mz)' + KOREAN_PARTICLES + r'(?![a-zA-Z])',
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

    # 시간 패턴 (예: 14시, 14:00, 어제, 오늘, 최근, 지난 주)
    # NOTE: "최근"류 질의(이력/존재 여부)는 센서 이벤트/패턴 로그 조회로 처리할 수 있도록 포함
    TIME_PATTERN = re.compile(
        r'(\d{1,2}시|\d{1,2}:\d{2}|어제|오늘|내일|그제|모레|최근|최근에|요즘|근래|방금|'
        r'지난\s*주|저번\s*주|이번\s*주|다음\s*주|금주|전주|차주|'
        r'지난\s*달|저번\s*달|이번\s*달|다음\s*달|'
        r'며칠\s*전|일주일\s*전|한달\s*전|몇\s*일\s*전)',
        re.IGNORECASE,
    )

    # 패턴 타입 패턴
    PATTERN_TYPE_KEYWORDS = {
        "collision": ["충돌", "collision", "부딪", "접촉"],
        "overload": ["과부하", "overload", "과하중", "무거"],
        "drift": ["드리프트", "drift", "편차", "이동"],
        "vibration": ["진동", "vibration", "떨림"],
        "error": ["에러 패턴", "오류 패턴", "에러패턴", "오류패턴", "에러패", "오류패", "에러 이력", "오류 이력"],  # 일반 에러 패턴
        "anomaly": ["이상 패턴", "이상패턴", "이상", "비정상", "anomaly", "이상 징후", "이상징후"],  # 이상/비정상 패턴
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

    # 개념어 -> 측정축 매핑 (토크 -> Tx/Ty/Tz, 힘 -> Fx/Fy/Fz)
    CONCEPT_TO_AXES = {
        "토크": ["Tx", "Ty", "Tz"],
        "torque": ["Tx", "Ty", "Tz"],
        "회전력": ["Tx", "Ty", "Tz"],
        "힘": ["Fx", "Fy", "Fz"],
        "force": ["Fx", "Fy", "Fz"],
    }

    # 예비보전/예방보전 상태 키워드
    MAINTENANCE_KEYWORDS = [
        "예비보전", "예방보전", "예방 보전", "예비 보전",
        "predictive maintenance", "preventive maintenance",
        "보전 상태", "보전상태", "유지보수 상태", "정비 상태",
        "로봇 상태", "장비 상태", "시스템 상태", "건강 상태",
        "이상 징후", "이상징후", "anomaly",
    ]

    # 상태 확인 키워드 (현재 ~상태, ~어때 등)
    STATUS_CHECK_KEYWORDS = [
        "상태", "어때", "어떻게", "괜찮", "정상", "이상 없",
        "문제 없", "문제없", "점검", "체크", "확인",
    ]

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
            for key, entry in self._lexicon.items():
                # entry는 dict: {"canonical": "...", "synonyms": [...], "node_id": "..."}
                if isinstance(entry, dict):
                    canonical = entry.get("canonical", key)
                    # canonical 자체도 인덱싱
                    self._entity_index[canonical.lower()] = (canonical, "alias")
                    # synonyms 인덱싱
                    for alias in entry.get("synonyms", []):
                        self._entity_index[alias.lower()] = (canonical, "alias")
                else:
                    # 하위 호환: entry가 리스트인 경우
                    for alias in entry:
                        self._entity_index[alias.lower()] = (key, "alias")

        # 추가 별칭: Joint 언더스코어 없는 버전 (Joint1 → Joint_1)
        for i in range(6):
            self._entity_index[f"joint{i}"] = (f"Joint_{i}", "Joint")
            self._entity_index[f"조인트{i}"] = (f"Joint_{i}", "Joint")
            self._entity_index[f"관절{i}"] = (f"Joint_{i}", "Joint")

        # 개념어 별칭: 측정축 → MeasurementAxis (첫 번째 축 Fx를 대표로 사용)
        concept_aliases = {
            "측정축": ("Fx", "MeasurementAxis"),  # 대표 축
            "measurement axis": ("Fx", "MeasurementAxis"),
            "센서축": ("Fx", "MeasurementAxis"),
            "정상 범위": ("Fx", "MeasurementAxis"),  # 정상 범위 질문 처리용
        }
        for alias, (entity_id, entity_type) in concept_aliases.items():
            self._entity_index[alias.lower()] = (entity_id, entity_type)

        # Mx/My/Mz → Tx/Ty/Tz 별칭 (모멘트 = 토크)
        moment_aliases = {
            "mx": ("Tx", "MeasurementAxis"),
            "my": ("Ty", "MeasurementAxis"),
            "mz": ("Tz", "MeasurementAxis"),
        }
        for alias, (entity_id, entity_type) in moment_aliases.items():
            self._entity_index[alias.lower()] = (entity_id, entity_type)

        # 안전/절차 관련 별칭
        safety_aliases = {
            "긴급 정지": ("C159", "ErrorCode"),
            "긴급정지": ("C159", "ErrorCode"),
            "emergency stop": ("C159", "ErrorCode"),
            "비상 정지": ("C159", "ErrorCode"),
            "비상정지": ("C159", "ErrorCode"),
            "e-stop": ("C159", "ErrorCode"),
        }
        for alias, (entity_id, entity_type) in safety_aliases.items():
            self._entity_index[alias.lower()] = (entity_id, entity_type)

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

        # 10. 예비보전/상태 확인 추출
        entities.extend(self._extract_maintenance_status(query))

        # 11. 온톨로지 엔티티 직접 매칭
        entities.extend(self._extract_ontology_entities(query))

        # 12. 개념어 -> 측정축 매핑 (토크 -> Tx/Ty/Tz 등)
        entities.extend(self._extract_concept_axes(query))

        # 중복 제거
        entities = self._deduplicate(entities)

        logger.debug(f"추출된 엔티티: {[e.entity_id for e in entities]}")
        return entities

    # 모멘트 → 토크 별칭 매핑 (Mx/My/Mz → Tx/Ty/Tz)
    MOMENT_TO_TORQUE = {
        "Mx": "Tx",
        "My": "Ty",
        "Mz": "Tz",
    }

    def _extract_axes(self, query: str) -> List[ExtractedEntity]:
        """센서 축 추출 (한국어 조사 지원)

        "Fz가 -350N" → Fz 추출
        "Fz는 정상" → Fz 추출
        "Fz 값이" → Fz 추출
        "Mx가 -20Nm" → Tx 추출 (모멘트 → 토크 매핑)
        """
        entities = []
        for match in self.AXIS_PATTERN.finditer(query):
            axis = match.group(1)  # 축 이름만 (조사 제외)
            # 표준화 (대문자 첫글자)
            axis_id = axis[0].upper() + axis[1:].lower()
            # Mx/My/Mz → Tx/Ty/Tz 매핑
            axis_id = self.MOMENT_TO_TORQUE.get(axis_id, axis_id)
            entities.append(ExtractedEntity(
                text=axis,  # 축 이름만 저장 (조사 제외)
                entity_id=axis_id,
                entity_type="MeasurementAxis",
                confidence=1.0,
            ))
        return entities

    def _extract_concept_axes(self, query: str) -> List[ExtractedEntity]:
        """개념어에서 측정축 추출 (토크 -> Tx, Ty, Tz 등)

        "토크가 높아졌어" → Tx, Ty, Tz 추출
        "힘이 너무 세" → Fx, Fy, Fz 추출
        """
        entities = []
        query_lower = query.lower()

        for concept, axes in self.CONCEPT_TO_AXES.items():
            if concept.lower() in query_lower:
                # 해당 개념이 발견되면 관련 측정축 엔티티 추가
                for axis in axes:
                    entities.append(ExtractedEntity(
                        text=concept,
                        entity_id=axis,
                        entity_type="MeasurementAxis",
                        confidence=0.8,  # 개념 매핑은 직접 축 언급보다 약간 낮은 신뢰도
                        properties={"source": "concept_mapping"},
                    ))
                break  # 첫 번째 매칭된 개념만 처리

        return entities

    def _extract_values(self, query: str) -> List[ExtractedEntity]:
        """수치값 추출"""
        entities = []
        # 장비명/조인트명 내부 숫자를 제외하기 위한 패턴 (UR5e, Axia80, Joint_0 등)
        equipment_pattern = re.compile(r'(UR5e|Axia80|Joint[_\-]?\d)', re.IGNORECASE)
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

    def _extract_maintenance_status(self, query: str) -> List[ExtractedEntity]:
        """예비보전/예방보전 상태 쿼리 추출

        "현재 예비보전 상태는 어때?" → MaintenanceStatus 엔티티 추출
        "로봇 상태 확인해줘" → MaintenanceStatus 엔티티 추출
        """
        entities = []
        query_lower = query.lower()

        # 예비보전 관련 키워드 매칭
        for keyword in self.MAINTENANCE_KEYWORDS:
            if keyword.lower() in query_lower:
                # 상태 확인 키워드가 함께 있는지 확인
                has_status_check = any(
                    sk.lower() in query_lower
                    for sk in self.STATUS_CHECK_KEYWORDS
                )
                entities.append(ExtractedEntity(
                    text=keyword,
                    entity_id="MAINTENANCE_STATUS",
                    entity_type="MaintenanceStatus",
                    confidence=0.95 if has_status_check else 0.85,
                    properties={
                        "keyword": keyword,
                        "has_status_check": has_status_check,
                    },
                ))
                return entities  # 하나만 추출

        return entities

    def _extract_ontology_entities(self, query: str) -> List[ExtractedEntity]:
        """온톨로지 엔티티 직접 매칭 (한국어 호환)"""
        entities = []
        query_lower = query.lower()

        # 긴 것부터 매칭 (더 구체적인 엔티티 우선)
        sorted_keys = sorted(self._entity_index.keys(), key=len, reverse=True)

        matched_spans: List[Tuple[int, int]] = []

        def is_boundary(char: str) -> bool:
            """단어 경계 문자인지 확인 (ASCII 영숫자/언더스코어가 아니면 경계)"""
            if not char:
                return True
            # ASCII 영숫자 또는 언더스코어는 경계가 아님
            if char.isascii() and (char.isalnum() or char == '_'):
                return False
            return True

        for key in sorted_keys:
            # 단순 대소문자 무시 매칭
            pattern = re.compile(re.escape(key), re.IGNORECASE)
            for match in pattern.finditer(query_lower):
                start, end = match.start(), match.end()

                # 경계 검사: 앞뒤 문자가 영숫자/언더스코어가 아니어야 함
                char_before = query_lower[start - 1] if start > 0 else ''
                char_after = query_lower[end] if end < len(query_lower) else ''

                if not is_boundary(char_before) or not is_boundary(char_after):
                    continue

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
