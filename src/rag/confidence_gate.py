"""
신뢰도 기반 응답 검증

응답 생성 전 신뢰도를 평가하고 ABSTAIN 여부를 결정합니다.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any, Dict

from .evidence_schema import ClassificationResult, ExtractedEntity

logger = logging.getLogger(__name__)


@dataclass
class GateResult:
    """게이트 통과 결과"""
    passed: bool                              # 통과 여부
    abstain_reason: Optional[str] = None      # ABSTAIN 사유
    confidence: float = 0.0                   # 최종 신뢰도
    warnings: List[str] = field(default_factory=list)  # 경고 메시지

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "passed": self.passed,
            "abstain_reason": self.abstain_reason,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


class ConfidenceGate:
    """신뢰도 기반 응답 검증

    응답 생성 전 추론 결과의 품질을 평가하고,
    신뢰도가 부족한 경우 ABSTAIN을 결정합니다.
    """

    # 임계값 설정
    MIN_CONFIDENCE = 0.4           # 최소 추론 신뢰도 (0.5 → 0.4)
    MIN_ENTITY_CONFIDENCE = 0.5    # 최소 엔티티 신뢰도 (0.6 → 0.5)
    MIN_CLASSIFICATION_CONFIDENCE = 0.25  # 최소 분류 신뢰도 (0.4 → 0.3 → 0.25)

    def __init__(
        self,
        min_confidence: float = 0.4,
        min_entity_confidence: float = 0.5,
        min_classification_confidence: float = 0.25
    ):
        """초기화

        Args:
            min_confidence: 최소 추론 신뢰도 (기본값 0.4)
            min_entity_confidence: 최소 엔티티 신뢰도 (기본값 0.5)
            min_classification_confidence: 최소 분류 신뢰도 (기본값 0.25)
        """
        self.min_confidence = min_confidence
        self.min_entity_confidence = min_entity_confidence
        self.min_classification_confidence = min_classification_confidence
        logger.info("ConfidenceGate 초기화 완료")

    def evaluate(
        self,
        classification: ClassificationResult,
        reasoning: Any  # ReasoningResult (순환 import 방지)
    ) -> GateResult:
        """신뢰도 평가

        Args:
            classification: 질문 분류 결과
            reasoning: 추론 결과 (ReasoningResult)

        Returns:
            GateResult: 게이트 통과 결과
        """
        warnings: List[str] = []

        # 1. 분류 신뢰도 검사
        passed, reason = self._check_classification_quality(classification)
        if not passed:
            logger.info(f"ABSTAIN: {reason}")
            return GateResult(
                passed=False,
                abstain_reason=reason,
                confidence=classification.confidence,
                warnings=warnings,
            )

        # 2. 엔티티 품질 검사
        passed, reason = self._check_entity_quality(classification.entities)
        if not passed:
            logger.info(f"ABSTAIN: {reason}")
            return GateResult(
                passed=False,
                abstain_reason=reason,
                confidence=classification.confidence,
                warnings=warnings,
            )

        # 3. 추론 품질 검사
        passed, reason, reasoning_warnings = self._check_reasoning_quality(reasoning)
        warnings.extend(reasoning_warnings)
        if not passed:
            logger.info(f"ABSTAIN: {reason}")
            return GateResult(
                passed=False,
                abstain_reason=reason,
                confidence=reasoning.confidence if reasoning else 0.0,
                warnings=warnings,
            )

        # 4. 근거 품질 검사
        passed, reason, evidence_warnings = self._check_evidence_quality(reasoning)
        warnings.extend(evidence_warnings)
        if not passed:
            logger.info(f"ABSTAIN: {reason}")
            return GateResult(
                passed=False,
                abstain_reason=reason,
                confidence=reasoning.confidence if reasoning else 0.0,
                warnings=warnings,
            )

        # 최종 신뢰도 계산
        final_confidence = self._calculate_final_confidence(classification, reasoning)

        # 최종 신뢰도 임계값 검사
        if final_confidence < self.min_confidence:
            reason = f"confidence below threshold ({final_confidence:.2f} < {self.min_confidence})"
            logger.info(f"ABSTAIN: {reason}")
            return GateResult(
                passed=False,
                abstain_reason=reason,
                confidence=final_confidence,
                warnings=warnings,
            )

        logger.info(f"Gate PASSED: confidence={final_confidence:.2f}")
        return GateResult(
            passed=True,
            abstain_reason=None,
            confidence=final_confidence,
            warnings=warnings,
        )

    def _check_classification_quality(
        self,
        classification: ClassificationResult
    ) -> Tuple[bool, Optional[str]]:
        """분류 품질 검사

        Args:
            classification: 분류 결과

        Returns:
            (통과 여부, 실패 사유)
        """
        # 엔티티가 있으면 분류 신뢰도 요구조건 완화
        # (유용한 엔티티가 추출되면 분류 신뢰도가 낮아도 질문에 답할 수 있음)
        effective_threshold = self.min_classification_confidence
        if classification.entities:
            # 고신뢰도 엔티티 (MeasurementAxis, ErrorCode, Pattern 등)가 있으면 임계값 낮춤
            high_value_types = {"MeasurementAxis", "ErrorCode", "Pattern", "ErrorCategory", "TimeExpression"}
            has_high_value_entity = any(
                e.entity_type in high_value_types for e in classification.entities
            )
            if has_high_value_entity:
                effective_threshold = 0.15  # 고가치 엔티티가 있으면 매우 낮은 임계값 적용
            else:
                effective_threshold = 0.20  # 일반 엔티티라도 있으면 임계값 낮춤

        if classification.confidence < effective_threshold:
            return False, f"classification confidence too low ({classification.confidence:.2f} < {effective_threshold})"

        return True, None

    def _check_entity_quality(
        self,
        entities: List[ExtractedEntity]
    ) -> Tuple[bool, Optional[str]]:
        """엔티티 품질 검사

        Args:
            entities: 추출된 엔티티 리스트

        Returns:
            (통과 여부, 실패 사유)
        """
        if not entities:
            return False, "no entities extracted"

        # 평균 엔티티 신뢰도 검사
        avg_confidence = sum(e.confidence for e in entities) / len(entities)
        if avg_confidence < self.min_entity_confidence:
            return False, f"entity confidence too low ({avg_confidence:.2f} < {self.min_entity_confidence})"

        return True, None

    def _check_reasoning_quality(
        self,
        reasoning: Any
    ) -> Tuple[bool, Optional[str], List[str]]:
        """추론 품질 검사

        Args:
            reasoning: 추론 결과

        Returns:
            (통과 여부, 실패 사유, 경고 리스트)
        """
        warnings: List[str] = []

        if reasoning is None:
            return False, "no reasoning result", warnings

        # 추론 체인 검사
        if not reasoning.reasoning_chain:
            has_other_signal = bool(
                reasoning.conclusions
                or reasoning.predictions
                or reasoning.recommendations
                or reasoning.ontology_paths
            )
            if not has_other_signal:
                return False, "no reasoning chain", warnings
            warnings.append("no reasoning chain")

        # 결론 검사
        if not reasoning.conclusions:
            warnings.append("no conclusions in reasoning")
            # 결론이 없어도 추론 체인이 있으면 통과

        # 추론 신뢰도 검사
        if reasoning.confidence < self.min_confidence:
            return False, f"reasoning confidence too low ({reasoning.confidence:.2f} < {self.min_confidence})", warnings

        return True, None, warnings

    def _check_evidence_quality(
        self,
        reasoning: Any
    ) -> Tuple[bool, Optional[str], List[str]]:
        """근거 품질 검사

        Args:
            reasoning: 추론 결과

        Returns:
            (통과 여부, 실패 사유, 경고 리스트)
        """
        warnings: List[str] = []

        if reasoning is None:
            return False, "no reasoning for evidence check", warnings

        # 온톨로지 경로 검사
        if not reasoning.ontology_paths:
            warnings.append("no ontology paths found")
            # 경로가 없어도 추론 결과가 있으면 통과 가능

        return True, None, warnings

    def _calculate_final_confidence(
        self,
        classification: ClassificationResult,
        reasoning: Any
    ) -> float:
        """최종 신뢰도 계산

        Args:
            classification: 분류 결과
            reasoning: 추론 결과

        Returns:
            최종 신뢰도 (0.0 ~ 1.0)
        """
        # 가중 평균 계산
        classification_weight = 0.3
        reasoning_weight = 0.5
        entity_weight = 0.2

        # 엔티티 평균 신뢰도
        entity_confidence = 0.0
        if classification.entities:
            entity_confidence = sum(e.confidence for e in classification.entities) / len(classification.entities)

        # 추론 신뢰도
        reasoning_confidence = reasoning.confidence if reasoning else 0.0

        final_confidence = (
            classification.confidence * classification_weight +
            reasoning_confidence * reasoning_weight +
            entity_confidence * entity_weight
        )

        return min(1.0, final_confidence)


# 편의 함수
def create_confidence_gate(
    min_confidence: float = 0.5,
    min_entity_confidence: float = 0.6
) -> ConfidenceGate:
    """ConfidenceGate 인스턴스 생성"""
    return ConfidenceGate(
        min_confidence=min_confidence,
        min_entity_confidence=min_entity_confidence
    )
