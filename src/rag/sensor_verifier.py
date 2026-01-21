# ============================================================
# src/rag/sensor_verifier.py - 센서 증거 검증기
# ============================================================
# EnrichedContext의 센서 증거를 검증합니다.
#
# Main-S5에서 구현
# ============================================================

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any


# ============================================================
# [1] 센서 검증 결과
# ============================================================

@dataclass
class SensorVerificationResult:
    """
    센서 증거 검증 결과

    Attributes:
        is_valid: 유효 여부
        score: 점수 (0.0 ~ 1.0)
        pattern_types: 감지된 패턴 유형들
        warnings: 경고 메시지
        details: 상세 정보
    """
    is_valid: bool
    score: float
    pattern_types: List[str]
    warnings: List[str]
    details: Dict[str, Any]

    @property
    def has_anomaly(self) -> bool:
        """이상 패턴 존재 여부"""
        return len(self.pattern_types) > 0


# ============================================================
# [2] SensorVerifier 클래스
# ============================================================

class SensorVerifier:
    """
    센서 증거 검증기

    EnrichedContext의 센서 증거를 검증합니다.

    검증 항목:
        1. 패턴 유형 유효성
        2. 패턴 신뢰도
        3. 시간 범위 적합성
        4. 에러코드 관련성

    사용 예시:
        verifier = SensorVerifier()
        result = verifier.verify(sensor_evidence, error_code="C153")
        if result.is_valid:
            print(f"Score: {result.score}")
    """

    # 유효한 패턴 유형
    VALID_PATTERN_TYPES = ["collision", "vibration", "overload", "drift"]

    # 에러코드-패턴 매핑 (Main-S3 error_pattern_mapping.yaml 참조)
    ERROR_PATTERN_MAP = {
        "C153": ["collision"],
        "C119": ["collision"],
        "C189": ["overload"],
        "C204": ["vibration"],
    }

    def __init__(
        self,
        min_pattern_confidence: float = 0.7,
        max_time_gap_minutes: int = 60
    ):
        """
        SensorVerifier 초기화

        Args:
            min_pattern_confidence: 최소 패턴 신뢰도
            max_time_gap_minutes: 최대 허용 시간 간격 (분)
        """
        self.min_pattern_confidence = min_pattern_confidence
        self.max_time_gap_minutes = max_time_gap_minutes

    def verify(
        self,
        sensor_evidence: Optional[Any],
        error_code: Optional[str] = None,
        reference_time: Optional[datetime] = None
    ) -> SensorVerificationResult:
        """
        센서 증거 검증

        Args:
            sensor_evidence: SensorEvidence 객체 (from EnrichedContext)
            error_code: 관련 에러코드
            reference_time: 기준 시간

        Returns:
            SensorVerificationResult: 검증 결과
        """
        warnings = []
        details = {}

        # 센서 증거가 없는 경우
        if sensor_evidence is None:
            return SensorVerificationResult(
                is_valid=False,
                score=0.0,
                pattern_types=[],
                warnings=["센서 증거 없음"],
                details={"reason": "no_sensor_evidence"}
            )

        # 패턴 목록 추출
        patterns = sensor_evidence.patterns if hasattr(sensor_evidence, 'patterns') else []

        if not patterns:
            return SensorVerificationResult(
                is_valid=False,
                score=0.0,
                pattern_types=[],
                warnings=["감지된 패턴 없음"],
                details={"reason": "no_patterns"}
            )

        # ─────────────────────────────────────────────────────
        # 1. 패턴 유형 유효성 검증
        # ─────────────────────────────────────────────────────
        valid_patterns = []
        invalid_types = []

        for pattern in patterns:
            pattern_type = pattern.get("pattern_type", pattern.get("type", "unknown"))

            if pattern_type in self.VALID_PATTERN_TYPES:
                valid_patterns.append(pattern)
            else:
                invalid_types.append(pattern_type)

        if invalid_types:
            warnings.append(f"알 수 없는 패턴 유형: {invalid_types}")

        if not valid_patterns:
            return SensorVerificationResult(
                is_valid=False,
                score=0.0,
                pattern_types=[],
                warnings=["유효한 패턴 없음"] + warnings,
                details={"invalid_types": invalid_types}
            )

        # ─────────────────────────────────────────────────────
        # 2. 패턴 신뢰도 검증
        # ─────────────────────────────────────────────────────
        high_confidence_patterns = []
        low_confidence_patterns = []

        for pattern in valid_patterns:
            confidence = pattern.get("confidence", 0.5)
            if confidence >= self.min_pattern_confidence:
                high_confidence_patterns.append(pattern)
            else:
                low_confidence_patterns.append(pattern)

        if low_confidence_patterns:
            warnings.append(
                f"저신뢰 패턴 {len(low_confidence_patterns)}개 "
                f"(임계값: {self.min_pattern_confidence:.0%})"
            )

        # ─────────────────────────────────────────────────────
        # 3. 시간 범위 검증
        # ─────────────────────────────────────────────────────
        if reference_time and hasattr(sensor_evidence, 'time_range'):
            time_range = sensor_evidence.time_range
            if time_range and len(time_range) == 2:
                start_time, end_time = time_range

                # reference_time과의 시간 차이 확인
                if isinstance(start_time, datetime):
                    time_diff = abs((reference_time - start_time).total_seconds() / 60)
                    if time_diff > self.max_time_gap_minutes:
                        warnings.append(
                            f"시간 범위 불일치: {time_diff:.0f}분 차이 "
                            f"(허용: {self.max_time_gap_minutes}분)"
                        )
                        details["time_gap_minutes"] = time_diff

        # ─────────────────────────────────────────────────────
        # 4. 에러코드 관련성 검증
        # ─────────────────────────────────────────────────────
        pattern_types = list(set(
            p.get("pattern_type", p.get("type", "unknown"))
            for p in high_confidence_patterns
        ))

        error_match = False
        if error_code:
            expected_patterns = self.ERROR_PATTERN_MAP.get(error_code.upper(), [])
            matching_patterns = set(pattern_types) & set(expected_patterns)

            if matching_patterns:
                error_match = True
                details["error_match"] = {
                    "error_code": error_code,
                    "expected": expected_patterns,
                    "found": list(matching_patterns)
                }
            elif expected_patterns:
                warnings.append(
                    f"에러 {error_code}에 예상되는 패턴 {expected_patterns}이 "
                    f"감지되지 않음 (감지됨: {pattern_types})"
                )

        # ─────────────────────────────────────────────────────
        # 5. 점수 계산
        # ─────────────────────────────────────────────────────
        score = self._calculate_score(
            patterns=high_confidence_patterns,
            error_match=error_match,
            warnings=warnings
        )

        details["pattern_count"] = len(high_confidence_patterns)
        details["avg_confidence"] = (
            sum(p.get("confidence", 0.5) for p in high_confidence_patterns) /
            len(high_confidence_patterns)
        ) if high_confidence_patterns else 0.0

        return SensorVerificationResult(
            is_valid=score >= 0.5,
            score=score,
            pattern_types=pattern_types,
            warnings=warnings,
            details=details
        )

    def _calculate_score(
        self,
        patterns: List[Dict],
        error_match: bool,
        warnings: List[str]
    ) -> float:
        """
        센서 증거 점수 계산

        Args:
            patterns: 유효한 패턴 목록
            error_match: 에러-패턴 매칭 여부
            warnings: 경고 목록

        Returns:
            float: 점수 (0.0 ~ 1.0)
        """
        if not patterns:
            return 0.0

        # 기본 점수: 평균 신뢰도
        avg_confidence = sum(p.get("confidence", 0.5) for p in patterns) / len(patterns)
        score = avg_confidence * 0.6

        # 패턴 수 보너스
        if len(patterns) >= 2:
            score += 0.1
        if len(patterns) >= 3:
            score += 0.1

        # 에러 매칭 보너스
        if error_match:
            score += 0.15

        # 경고 페널티
        score -= len(warnings) * 0.05

        return max(0.0, min(1.0, score))

    def get_expected_patterns(self, error_code: str) -> List[str]:
        """
        에러코드에 대한 예상 패턴 조회

        Args:
            error_code: 에러코드

        Returns:
            List[str]: 예상 패턴 유형 목록
        """
        return self.ERROR_PATTERN_MAP.get(error_code.upper(), [])


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_sensor_verifier: Optional[SensorVerifier] = None


def get_sensor_verifier() -> SensorVerifier:
    """SensorVerifier 싱글톤 반환"""
    global _sensor_verifier
    if _sensor_verifier is None:
        _sensor_verifier = SensorVerifier()
    return _sensor_verifier
