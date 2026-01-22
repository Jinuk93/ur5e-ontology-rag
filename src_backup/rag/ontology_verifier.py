# ============================================================
# src/rag/ontology_verifier.py - 온톨로지 교차 검증기
# ============================================================
# GraphRetriever를 사용해 센서 패턴과 에러코드 관계를 검증합니다.
#
# Main-S5에서 구현
# ============================================================

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any


# ============================================================
# [1] 온톨로지 검증 결과
# ============================================================

@dataclass
class OntologyVerificationResult:
    """
    온톨로지 교차 검증 결과

    Attributes:
        is_match: 온톨로지 매칭 여부
        probability: 매칭 확률 (0.0 ~ 1.0)
        expected_patterns: 에러코드에 예상되는 패턴 목록
        matched_patterns: 실제로 매칭된 패턴 목록
        expected_causes: 예상 원인 목록
        details: 상세 정보
    """
    is_match: bool
    probability: float
    expected_patterns: List[Dict[str, Any]]
    matched_patterns: List[str]
    expected_causes: List[Dict[str, Any]]
    details: Dict[str, Any]


# ============================================================
# [2] OntologyVerifier 클래스
# ============================================================

class OntologyVerifier:
    """
    온톨로지 교차 검증기

    GraphRetriever를 사용해 센서 패턴과 에러코드 관계를 검증합니다.

    검증 항목:
        1. 패턴 → 에러코드 관계 (TRIGGERS)
        2. 패턴 → 원인 관계 (INDICATES)
        3. 관계 확률/신뢰도

    사용 예시:
        verifier = OntologyVerifier(graph_retriever)
        result = verifier.verify(pattern_type="collision", error_code="C153")
        if result.is_match:
            print(f"매칭 확률: {result.probability:.0%}")
    """

    def __init__(self, graph_retriever: Optional[Any] = None):
        """
        OntologyVerifier 초기화

        Args:
            graph_retriever: GraphRetriever 인스턴스 (Optional)
        """
        self.graph_retriever = graph_retriever

        # GraphRetriever가 없을 때 사용할 fallback 매핑
        self._fallback_pattern_error_map = {
            "collision": [
                {"error_code": "C153", "probability": 0.95},
                {"error_code": "C119", "probability": 0.80},
            ],
            "overload": [
                {"error_code": "C189", "probability": 0.90},
            ],
            "vibration": [
                {"error_code": "C204", "probability": 0.75},
            ],
            "drift": [],  # 직접 에러 유발 안함
        }

        self._fallback_pattern_cause_map = {
            "collision": [
                {"cause_id": "CAUSE_PHYSICAL_CONTACT", "description": "물리적 접촉", "confidence": 0.90},
                {"cause_id": "CAUSE_UNEXPECTED_OBSTACLE", "description": "예상치 못한 장애물", "confidence": 0.85},
                {"cause_id": "CAUSE_PROGRAM_ERROR", "description": "프로그램 경로 오류", "confidence": 0.70},
            ],
            "overload": [
                {"cause_id": "CAUSE_PAYLOAD_EXCEEDED", "description": "하중 초과", "confidence": 0.90},
            ],
            "vibration": [
                {"cause_id": "CAUSE_JOINT_WEAR", "description": "조인트 마모", "confidence": 0.70},
                {"cause_id": "CAUSE_LOOSE_BOLTS", "description": "볼트 풀림", "confidence": 0.65},
            ],
            "drift": [
                {"cause_id": "CAUSE_CALIBRATION_NEEDED", "description": "캘리브레이션 필요", "confidence": 0.80},
            ],
        }

    def verify(
        self,
        pattern_type: str,
        error_code: Optional[str] = None
    ) -> OntologyVerificationResult:
        """
        온톨로지 교차 검증 수행

        Args:
            pattern_type: 센서 패턴 유형 (collision, vibration, etc.)
            error_code: 검증할 에러코드 (Optional)

        Returns:
            OntologyVerificationResult: 검증 결과
        """
        # 예상 에러코드 조회
        expected_patterns = self._get_expected_errors_for_pattern(pattern_type)

        # 예상 원인 조회
        expected_causes = self._get_expected_causes_for_pattern(pattern_type)

        # 에러코드가 제공된 경우 매칭 확인
        is_match = False
        probability = 0.0
        matched_patterns = []

        if error_code:
            for ep in expected_patterns:
                if ep.get("error_code", "").upper() == error_code.upper():
                    is_match = True
                    probability = ep.get("probability", 0.5)
                    matched_patterns.append(pattern_type)
                    break

        return OntologyVerificationResult(
            is_match=is_match,
            probability=probability,
            expected_patterns=expected_patterns,
            matched_patterns=matched_patterns,
            expected_causes=expected_causes,
            details={
                "pattern_type": pattern_type,
                "error_code": error_code,
                "used_fallback": self.graph_retriever is None
            }
        )

    def verify_pattern_error_relation(
        self,
        pattern_type: str,
        error_code: str
    ) -> Tuple[bool, float]:
        """
        센서 패턴 → 에러코드 관계 검증

        Args:
            pattern_type: 센서 패턴 유형
            error_code: 에러코드

        Returns:
            Tuple[bool, float]: (매칭여부, 확률)
        """
        result = self.verify(pattern_type=pattern_type, error_code=error_code)
        return result.is_match, result.probability

    def get_expected_patterns_for_error(
        self,
        error_code: str
    ) -> List[Dict[str, Any]]:
        """
        에러코드에 대한 예상 센서 패턴 조회

        Args:
            error_code: 에러코드

        Returns:
            List[Dict]: 예상 패턴 목록 [{type, probability}, ...]
        """
        # GraphRetriever 사용 가능한 경우
        if self.graph_retriever:
            try:
                results = self.graph_retriever.search_error_patterns(error_code)
                if results:
                    patterns = []
                    for r in results:
                        for entity in r.related_entities:
                            if entity.get("type") == "SensorPattern":
                                patterns.append({
                                    "type": entity.get("pattern_type", ""),
                                    "probability": entity.get("probability", 0.5),
                                    "pattern_id": entity.get("pattern_id", "")
                                })
                    return patterns
            except Exception:
                pass  # fallback 사용

        # Fallback: 내장 매핑에서 역조회
        expected = []
        for pattern_type, errors in self._fallback_pattern_error_map.items():
            for error in errors:
                if error.get("error_code", "").upper() == error_code.upper():
                    expected.append({
                        "type": pattern_type,
                        "probability": error.get("probability", 0.5)
                    })

        return expected

    def get_causes_for_pattern(
        self,
        pattern_type: str
    ) -> List[Dict[str, Any]]:
        """
        센서 패턴에 대한 예상 원인 조회

        Args:
            pattern_type: 센서 패턴 유형

        Returns:
            List[Dict]: 예상 원인 목록
        """
        return self._get_expected_causes_for_pattern(pattern_type)

    def _get_expected_errors_for_pattern(
        self,
        pattern_type: str
    ) -> List[Dict[str, Any]]:
        """
        패턴 유형에 대한 예상 에러코드 조회 (내부 메서드)
        """
        # GraphRetriever 사용 가능한 경우
        if self.graph_retriever:
            try:
                results = self.graph_retriever.search_sensor_pattern_errors(pattern_type)
                if results:
                    errors = []
                    for entity in results[0].related_entities:
                        errors.append({
                            "error_code": entity.get("name", ""),
                            "probability": entity.get("probability", 0.5),
                            "title": entity.get("title", "")
                        })
                    return errors
            except Exception:
                pass  # fallback 사용

        # Fallback
        return self._fallback_pattern_error_map.get(pattern_type.lower(), [])

    def _get_expected_causes_for_pattern(
        self,
        pattern_type: str
    ) -> List[Dict[str, Any]]:
        """
        패턴 유형에 대한 예상 원인 조회 (내부 메서드)
        """
        # GraphRetriever 사용 가능한 경우
        if self.graph_retriever:
            try:
                results = self.graph_retriever.search_sensor_pattern_causes(pattern_type)
                if results:
                    causes = []
                    for entity in results[0].related_entities:
                        causes.append({
                            "cause_id": entity.get("cause_id", ""),
                            "description": entity.get("description", ""),
                            "confidence": entity.get("confidence", 0.5),
                            "category": entity.get("category", "")
                        })
                    return causes
            except Exception:
                pass  # fallback 사용

        # Fallback
        return self._fallback_pattern_cause_map.get(pattern_type.lower(), [])


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_ontology_verifier: Optional[OntologyVerifier] = None


def get_ontology_verifier(
    graph_retriever: Optional[Any] = None
) -> OntologyVerifier:
    """OntologyVerifier 싱글톤 반환"""
    global _ontology_verifier
    if _ontology_verifier is None:
        _ontology_verifier = OntologyVerifier(graph_retriever)
    return _ontology_verifier
