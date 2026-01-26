"""
질문 분류기

질문 유형을 자동 분류합니다 (ONTOLOGY / HYBRID / RAG).
"""

import logging
import re
from typing import Dict, List, Optional, Any

from .evidence_schema import QueryType, ClassificationResult, ExtractedEntity
from .entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)


class QueryClassifier:
    """온톨로지 기반 질문 분류기"""

    # ================================================================
    # 분류 지표 정의
    # ================================================================

    # 온톨로지성 질문 지표 (관계/맥락 추론 필요)
    ONTOLOGY_INDICATORS = {
        # 온톨로지 엔티티 정의 질문 (Fx, Fy, Fz, UR5e, Axia80 등 기본 정의)
        # NOTE: "사용법", "설명해" 패턴은 문맥 파장이 필요한 절차적 질문이므로 제거함. (RAG/Hybrid로 이관)
        "entity_definition_question": {
            "patterns": [
                r"(Fz|Fx|Fy|Tx|Ty|Tz|UR5e|Axia80)(?:가|이|는|은|의|란|이란)?\s*(뭐|무엇|무슨|어떤|뜻|의미|정의)",
                r"(뭐|무엇|무슨).{0,5}(Fz|Fx|Fy|Tx|Ty|Tz)",
                r"(힘|토크|Force|Torque).{0,5}(센서|축|뭐|무엇)",
            ],
            "weight": 0.95,
        },
        # 센서 값 + 질문 패턴
        "sensor_value_question": {
            "patterns": [
                r"(Fz|Fx|Fy|Tx|Ty|Tz)(?:으로|에서|가|이|를|을|은|는|도|의|로)?.{0,20}(뭐야|뭘까|무엇|왜|이유|원인|문제)",
                r"(-?\d+)\s*(N|Nm).{0,10}(뭐야|뭘까|무엇|왜|이유|원인|문제)",
                # 센서값 초과/이상 패턴
                r"(Fz|Fx|Fy|Tx|Ty|Tz).{0,10}(값|측정).{0,10}(\d+).{0,5}(N|Nm)?.{0,10}(넘|초과|이상|높|크)",
                r"(Fz|Fx|Fy|Tx|Ty|Tz).{0,5}(값이|가|이).{0,10}(넘|초과|이상|높|크)",
            ],
            "weight": 0.9,
        },
        # 패턴/원인 질문
        "pattern_cause_question": {
            "patterns": [
                r"(충돌|과부하|진동|드리프트).{0,10}(원인|이유|왜)",
                r"(collision|overload|vibration|drift).{0,10}(why|cause|reason)",
            ],
            "weight": 0.85,
        },
        # 예측 요청
        "prediction_request": {
            "patterns": [
                r"(예측|예상|발생.{0,5}(할까|가능성|확률)|앞으로|내일|다음)",
                r"(predict|forecast|will.{0,5}happen|probability)",
            ],
            "weight": 0.9,
        },
        # 상태 질문
        "state_question": {
            "patterns": [
                r"(상태|현재|지금).{0,10}(뭐야|어때|알려|확인)",
                r"(status|current|state).{0,10}(what|how|check)",
            ],
            "weight": 0.8,
        },
        # 시간 맥락 질문
        "temporal_context": {
            "patterns": [
                r"(어제|오늘|그제|아까|방금|며칠|언제|몇시).{0,10}(왜|뭐|이상|문제|발생)",
                r"(최근|요즘|근래).{0,15}(패턴|충돌|이상|에러|오류|문제)",
                r"(최근|요즘|근래).{0,15}(있나요|있어|있었|발생|감지)",
                # 시간 범위 + 패턴/에러 질문
                r"(지난|저번|이번|다음).{0,3}(주|달|일).{0,10}(에러|오류|패턴|이상|충돌|과부하)",
                r"(에러|오류|패턴|이상|충돌|과부하).{0,10}(패턴|이력|기록).{0,10}(알려|보여|확인)",
            ],
            "weight": 0.85,
        },
        # 패턴 존재/이력 질문
        "pattern_existence_question": {
            "patterns": [
                r"(충돌|과부하|진동|드리프트|이상).{0,10}(패턴|현상).{0,10}(있|발생|감지)",
                r"(패턴|현상).{0,10}(있나요|있어요|있습니까|발생|감지)",
                r"(있나요|있어요|발생했).{0,5}(충돌|과부하|진동|드리프트)",
            ],
            "weight": 0.85,
        },
        # 관계 탐색 질문
        "relationship_query": {
            "patterns": [
                r"(관계|연결|연관|영향|관련).{0,10}(뭐|있|알려)",
                r"(무엇이|어떤것이).{0,10}(영향|관련|연결)",
            ],
            "weight": 0.9,
        },
        # 엔티티 비교 질문 (Fx와 Fz 비교, 정상 범위 차이 등)
        "entity_comparison_question": {
            "patterns": [
                r"(Fz|Fx|Fy|Tx|Ty|Tz).{0,10}(와|과|랑).{0,10}(Fz|Fx|Fy|Tx|Ty|Tz).{0,10}(비교|차이|다른)",
                r"(비교|차이).{0,10}(Fz|Fx|Fy|Tx|Ty|Tz).{0,10}(Fz|Fx|Fy|Tx|Ty|Tz)",
                r"(Fz|Fx|Fy|Tx|Ty|Tz).{0,5}(Fz|Fx|Fy|Tx|Ty|Tz).{0,10}(비교|차이|다른)",
            ],
            "weight": 0.9,
        },
        # 엔티티 사양/스펙 질문 (Joint 범위, 센서 정상 범위, 로봇 페이로드 등)
        "entity_specification_question": {
            "patterns": [
                # Joint 관련 사양
                r"(Joint|joint|조인트|축).{0,5}[_\-]?\d.{0,15}(범위|가동|회전|동작|모션|각도)",
                r"(범위|가동|회전|동작|모션|각도).{0,15}(Joint|joint|조인트|축).{0,5}[_\-]?\d",
                # 센서 사양
                r"(Fz|Fx|Fy|Tx|Ty|Tz).{0,15}(정상|범위|한계|측정|스펙)",
                r"(정상|범위|한계|측정|스펙).{0,15}(Fz|Fx|Fy|Tx|Ty|Tz)",
                # 로봇/장비 사양
                r"(UR5e|Axia80|로봇|센서).{0,15}(페이로드|무게|반경|범위|스펙|사양)",
                r"(페이로드|무게|반경|범위|스펙|사양).{0,15}(UR5e|Axia80|로봇|센서)",
            ],
            "weight": 0.95,
        },
    }

    # 하이브리드 질문 지표 (온톨로지 + 문서)
    HYBRID_INDICATORS = {
        # 에러코드 + 맥락 질문
        "error_context_question": {
            "patterns": [
                r"C\d{1,3}.{0,10}(자주|반복|계속|왜|이유|원인)",
                r"C\d{1,3}.{0,10}(어떤|무슨).{0,10}(상황|경우|조건)",
            ],
            "weight": 0.8,
        },
        # 해결 + 맥락 질문
        "resolution_context": {
            "patterns": [
                r"(해결|조치|수리|점검|대처).{0,10}(방법|어떻게|절차).{0,10}(이런|이|해당)",
                r"(이런|이|해당).{0,10}(상황|경우).{0,10}(해결|조치|대처|어떻게)",
                # 조건 + 대처/해결 패턴 (신규)
                r"(높|낮|이상|초과|부족|넘).{0,5}(을|면|때).{0,10}(어떻게|대처|해결|조치)",
                r"(어떻게).{0,5}(대처|해결|조치).{0,5}(하나요|해야|할까)",
            ],
            "weight": 0.75,
        },
        # 비교 질문
        "comparison_question": {
            "patterns": [
                r"(차이|비교|다른|vs|versus).{0,10}(뭐|있|알려)",
            ],
            "weight": 0.7,
        },
    }

    # 일반 RAG 질문 지표 (문서 검색만)
    RAG_INDICATORS = {
        # 사양 질문
        "specification_question": {
            "patterns": [
                r"(몇|얼마).{0,5}(kg|mm|N|Nm|도|초|분|시간)",
                r"(범위|한계|최대|최소|사양|스펙|규격)",
                r"(specification|spec|range|limit|maximum|minimum)",
            ],
            "weight": 0.8,
        },
        # 절차 질문
        "procedure_question": {
            "patterns": [
                r"(어떻게|방법|절차|순서|단계).{0,10}(하|해|설치|설정|조립)",
                r"(how to|procedure|steps|method).{0,10}(install|setup|configure)",
            ],
            "weight": 0.75,
        },
        # 정의 질문
        "definition_question": {
            "patterns": [
                r"(무엇|뭐).{0,5}(이야|인가|입니까)$",
                r"(what is|define|definition)",
            ],
            "weight": 0.6,  # 단독으로는 낮은 가중치
        },
        # 목록 요청
        "list_request": {
            "patterns": [
                r"(목록|리스트|종류|전부|모든|나열)",
                r"(list|all|types|kinds)",
            ],
            "weight": 0.7,
        },
    }

    def __init__(self, entity_extractor: Optional[EntityExtractor] = None):
        """초기화

        Args:
            entity_extractor: 엔티티 추출기 (없으면 자동 생성)
        """
        self._extractor = entity_extractor or EntityExtractor()
        logger.info("QueryClassifier 초기화 완료")

    def classify(self, query: str) -> ClassificationResult:
        """질문 유형 분류

        Args:
            query: 질문 문자열

        Returns:
            ClassificationResult
        """
        # 1. 엔티티 추출
        entities = self._extractor.extract(query)

        # 2. 지표 점수 계산
        ontology_score, ontology_indicators = self._calculate_score(
            query, self.ONTOLOGY_INDICATORS
        )
        hybrid_score, hybrid_indicators = self._calculate_score(
            query, self.HYBRID_INDICATORS
        )
        rag_score, rag_indicators = self._calculate_score(
            query, self.RAG_INDICATORS
        )

        # 3. 엔티티 기반 보정
        ontology_score += self._entity_bonus(entities)

        # 4. 최종 분류
        scores = {
            QueryType.ONTOLOGY: ontology_score,
            QueryType.HYBRID: hybrid_score,
            QueryType.RAG: rag_score,
        }

        # 가장 높은 점수의 유형 선택
        query_type = max(scores, key=scores.get)

        # 모든 점수가 낮으면 기본값 RAG
        max_score = scores[query_type]
        if max_score < 0.3:
            query_type = QueryType.RAG
            max_score = 0.5  # 기본 신뢰도

        # 지표 수집
        all_indicators = []
        if query_type == QueryType.ONTOLOGY:
            all_indicators = ontology_indicators
        elif query_type == QueryType.HYBRID:
            all_indicators = hybrid_indicators
        else:
            all_indicators = rag_indicators

        result = ClassificationResult(
            query=query,
            query_type=query_type,
            confidence=min(1.0, max_score),
            entities=entities,
            indicators=all_indicators,
            metadata={
                "scores": {k.value: round(v, 3) for k, v in scores.items()},
            },
        )

        logger.info(f"질문 분류: {query_type.value} (신뢰도: {result.confidence:.2%})")
        return result

    def _calculate_score(
        self,
        query: str,
        indicators: Dict[str, Dict]
    ) -> tuple[float, List[str]]:
        """지표 점수 계산

        Args:
            query: 질문
            indicators: 지표 정의

        Returns:
            (점수, 매칭된 지표 이름 리스트)
        """
        total_score = 0.0
        matched_indicators = []

        for indicator_name, config in indicators.items():
            patterns = config.get("patterns", [])
            weight = config.get("weight", 0.5)

            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    total_score += weight
                    matched_indicators.append(indicator_name)
                    break  # 같은 지표에서 하나만 매칭

        # 정규화 (최대 1.0)
        total_score = min(1.0, total_score)

        return total_score, matched_indicators

    def _entity_bonus(self, entities: List[ExtractedEntity]) -> float:
        """엔티티 기반 점수 보정

        온톨로지 엔티티가 많이 추출되면 온톨로지성 질문일 가능성 높음

        Args:
            entities: 추출된 엔티티 리스트

        Returns:
            보정 점수
        """
        bonus = 0.0

        entity_types = [e.entity_type for e in entities]

        # 센서 축 + 값 조합
        if "MeasurementAxis" in entity_types and "Value" in entity_types:
            bonus += 0.3

        # 패턴 타입 존재
        if "Pattern" in entity_types:
            bonus += 0.2

        # 시간 표현 존재
        if "TimeExpression" in entity_types:
            bonus += 0.15

        # Shift 존재
        if "Shift" in entity_types:
            bonus += 0.1

        # 제품 존재
        if "Product" in entity_types:
            bonus += 0.1

        return min(0.5, bonus)  # 최대 0.5 보정

    def is_ontology_query(self, query: str) -> bool:
        """온톨로지성 질문인지 확인"""
        result = self.classify(query)
        return result.query_type == QueryType.ONTOLOGY

    def is_hybrid_query(self, query: str) -> bool:
        """하이브리드 질문인지 확인"""
        result = self.classify(query)
        return result.query_type == QueryType.HYBRID

    def is_rag_query(self, query: str) -> bool:
        """일반 RAG 질문인지 확인"""
        result = self.classify(query)
        return result.query_type == QueryType.RAG

    def get_query_intent(self, query: str) -> Dict[str, Any]:
        """질문 의도 분석

        Args:
            query: 질문

        Returns:
            의도 분석 결과
        """
        result = self.classify(query)

        intent = {
            "type": result.query_type.value,
            "confidence": result.confidence,
            "entities": [e.to_dict() for e in result.entities],
            "indicators": result.indicators,
        }

        # 의도 세분화
        if result.query_type == QueryType.ONTOLOGY:
            if any("prediction" in i for i in result.indicators):
                intent["sub_intent"] = "prediction"
            elif any("state" in i for i in result.indicators):
                intent["sub_intent"] = "state_inquiry"
            elif any("cause" in i or "pattern" in i for i in result.indicators):
                intent["sub_intent"] = "cause_analysis"
            elif any("temporal" in i for i in result.indicators):
                intent["sub_intent"] = "temporal_analysis"
            else:
                intent["sub_intent"] = "sensor_analysis"

        elif result.query_type == QueryType.HYBRID:
            if any("error" in i for i in result.indicators):
                intent["sub_intent"] = "error_analysis"
            elif any("resolution" in i for i in result.indicators):
                intent["sub_intent"] = "resolution_inquiry"
            else:
                intent["sub_intent"] = "contextual_inquiry"

        else:  # RAG
            if any("specification" in i for i in result.indicators):
                intent["sub_intent"] = "specification"
            elif any("procedure" in i for i in result.indicators):
                intent["sub_intent"] = "procedure"
            elif any("definition" in i for i in result.indicators):
                intent["sub_intent"] = "definition"
            else:
                intent["sub_intent"] = "general_inquiry"

        return intent


# 편의 함수
def create_query_classifier() -> QueryClassifier:
    """QueryClassifier 인스턴스 생성"""
    return QueryClassifier()
