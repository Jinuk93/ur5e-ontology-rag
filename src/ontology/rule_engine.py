"""
온톨로지 추론 규칙 엔진

상태, 패턴, 원인, 예측 추론을 수행합니다.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import yaml

from .loader import load_ontology
from .models import OntologySchema

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """추론 결과"""
    rule_name: str
    result_type: str  # "state", "pattern", "cause", "prediction"
    result_id: str    # 엔티티 ID
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


class RuleEngine:
    """온톨로지 기반 추론 규칙 엔진"""

    DEFAULT_INFERENCE_RULES_PATH = Path("configs/inference_rules.yaml")
    DEFAULT_PATTERN_THRESHOLDS_PATH = Path("configs/pattern_thresholds.yaml")

    def __init__(
        self,
        inference_rules_path: Optional[Path] = None,
        pattern_thresholds_path: Optional[Path] = None
    ):
        """RuleEngine 초기화

        Args:
            inference_rules_path: 추론 규칙 파일 경로
            pattern_thresholds_path: 패턴 임계값 파일 경로

        Raises:
            FileNotFoundError: 필수 설정 파일이 없을 때
            ValueError: 필수 설정 키가 없을 때
        """
        # 추론 규칙 로드 (필수)
        self.inference_rules = self._load_yaml(
            inference_rules_path or self.DEFAULT_INFERENCE_RULES_PATH,
            required=True
        )

        # 패턴 임계값 로드 (필수)
        self.pattern_thresholds = self._load_yaml(
            pattern_thresholds_path or self.DEFAULT_PATTERN_THRESHOLDS_PATH,
            required=True
        )

        # 필수 키 검증
        self._validate_required_keys()

        # 온톨로지 로드
        self.ontology = load_ontology()

        logger.info(
            f"RuleEngine 초기화 완료: "
            f"state_rules={len(self.inference_rules.get('state_rules', []))}, "
            f"cause_rules={len(self.inference_rules.get('cause_rules', []))}, "
            f"prediction_rules={len(self.inference_rules.get('prediction_rules', []))}"
        )

    def _validate_required_keys(self) -> None:
        """필수 설정 키 검증

        Raises:
            ValueError: 필수 키가 없을 때
        """
        # inference_rules 필수 키
        required_inference_keys = ["state_rules"]
        for key in required_inference_keys:
            if key not in self.inference_rules:
                raise ValueError(
                    f"inference_rules.yaml에 필수 키 '{key}'가 없습니다. "
                    f"현재 키: {list(self.inference_rules.keys())}"
                )

        # pattern_thresholds 필수 키
        required_threshold_keys = ["collision", "overload"]
        for key in required_threshold_keys:
            if key not in self.pattern_thresholds:
                raise ValueError(
                    f"pattern_thresholds.yaml에 필수 키 '{key}'가 없습니다. "
                    f"현재 키: {list(self.pattern_thresholds.keys())}"
                )

    def _load_yaml(self, path: Path, required: bool = True) -> Dict:
        """YAML 파일 로드

        Args:
            path: YAML 파일 경로
            required: 필수 파일 여부 (True면 로드 실패 시 예외 발생)

        Returns:
            파싱된 딕셔너리

        Raises:
            FileNotFoundError: 필수 파일이 없을 때
            yaml.YAMLError: YAML 파싱 실패 시
        """
        if not path.exists():
            if required:
                error_msg = f"필수 설정 파일이 없습니다: {path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            else:
                logger.warning(f"선택적 설정 파일이 없습니다: {path}")
                return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data is None:
                    if required:
                        error_msg = f"설정 파일이 비어있습니다: {path}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                    return {}
                logger.info(f"설정 파일 로드 완료: {path}")
                return data
        except yaml.YAMLError as e:
            error_msg = f"YAML 파싱 실패: {path} - {e}"
            logger.error(error_msg)
            raise yaml.YAMLError(error_msg)
        except Exception as e:
            error_msg = f"설정 파일 로드 실패: {path} - {e}"
            logger.error(error_msg)
            if required:
                raise
            return {}

    # ================================================================
    # 상태 추론 (State Inference)
    # ================================================================

    def infer_state(self, axis: str, value: float) -> Optional[InferenceResult]:
        """센서 값에서 상태 추론

        Args:
            axis: 측정 축 (Fz, Fx, Fy, Tx, Ty, Tz)
            value: 측정값

        Returns:
            InferenceResult 또는 None
        """
        state_rules = self.inference_rules.get("state_rules", [])

        for rule in state_rules:
            if rule.get("axis") != axis:
                continue

            for mapping in rule.get("mappings", []):
                range_min, range_max = mapping["range"]
                if range_min <= value <= range_max:
                    return InferenceResult(
                        rule_name=rule["name"],
                        result_type="state",
                        result_id=mapping["state"],
                        confidence=1.0,
                        evidence={
                            "axis": axis,
                            "value": value,
                            "range": mapping["range"],
                            "severity": mapping.get("severity", "normal")
                        },
                        message=f"{axis}={value}{rule.get('unit', '')} → {mapping['label']}"
                    )

        return None

    def infer_states(self, measurements: Dict[str, float]) -> List[InferenceResult]:
        """여러 측정값에서 상태 추론

        Args:
            measurements: 축별 측정값 딕셔너리 {"Fz": -50.0, "Fx": 10.0, ...}

        Returns:
            InferenceResult 리스트
        """
        results = []
        for axis, value in measurements.items():
            result = self.infer_state(axis, value)
            if result:
                results.append(result)
        return results

    # ================================================================
    # 패턴 감지 (Pattern Detection)
    # ================================================================

    def detect_collision(self, fz_values: List[float], timestamps_ms: List[int]) -> Optional[InferenceResult]:
        """충돌 패턴 감지

        Args:
            fz_values: Fz 값 리스트
            timestamps_ms: 타임스탬프 리스트 (밀리초)

        Returns:
            InferenceResult 또는 None
        """
        collision_config = self.pattern_thresholds.get("collision", {})
        threshold = collision_config.get("threshold_N", 500)
        rise_time_ms = collision_config.get("rise_time_ms", 100)

        if len(fz_values) < 2:
            return None

        for i in range(1, len(fz_values)):
            delta = abs(fz_values[i] - fz_values[i-1])
            time_diff = timestamps_ms[i] - timestamps_ms[i-1]

            if delta > threshold and time_diff <= rise_time_ms:
                return InferenceResult(
                    rule_name="COLLISION_DETECTION",
                    result_type="pattern",
                    result_id="PAT_COLLISION",
                    confidence=0.95,
                    evidence={
                        "features": {
                            "delta_Fz_N": round(delta, 1),
                            "rise_time_ms": time_diff
                        },
                        "thresholds": {
                            "delta_threshold_N": threshold,
                            "rise_time_max_ms": rise_time_ms
                        },
                        "judgment": f"delta_Fz_N({delta:.1f}) > threshold({threshold}) within {time_diff}ms",
                        "data_index": i
                    },
                    message=f"충돌 감지: {delta:.1f}N 변화 ({time_diff}ms 내)"
                )

        return None

    def detect_overload(
        self,
        fz_values: List[float],
        timestamps_s: List[float]
    ) -> Optional[InferenceResult]:
        """과부하 패턴 감지

        Args:
            fz_values: Fz 값 리스트
            timestamps_s: 타임스탬프 리스트 (초)

        Returns:
            InferenceResult 또는 None
        """
        overload_config = self.pattern_thresholds.get("overload", {})
        threshold = overload_config.get("threshold_N", 300)
        duration_s = overload_config.get("duration_s", 5)

        if len(fz_values) < 2:
            return None

        # 연속 과부하 구간 찾기
        overload_start = None
        for i, (fz, ts) in enumerate(zip(fz_values, timestamps_s)):
            if abs(fz) > threshold:
                if overload_start is None:
                    overload_start = i
                elif ts - timestamps_s[overload_start] >= duration_s:
                    actual_duration = ts - timestamps_s[overload_start]
                    max_fz = max(abs(v) for v in fz_values[overload_start:i+1])
                    return InferenceResult(
                        rule_name="OVERLOAD_DETECTION",
                        result_type="pattern",
                        result_id="PAT_OVERLOAD",
                        confidence=0.90,
                        evidence={
                            "features": {
                                "max_Fz_N": round(max_fz, 1),
                                "overload_duration_s": round(actual_duration, 2)
                            },
                            "thresholds": {
                                "force_threshold_N": threshold,
                                "duration_threshold_s": duration_s
                            },
                            "judgment": f"max_Fz_N({max_fz:.1f}) > threshold({threshold}) for {actual_duration:.1f}s",
                            "data_range": {"start_idx": overload_start, "end_idx": i}
                        },
                        message=f"과부하 감지: {actual_duration:.1f}초 동안 {threshold}N 초과 (최대 {max_fz:.1f}N)"
                    )
            else:
                overload_start = None

        return None

    def detect_vibration(
        self,
        fz_values: List[float],
        timestamps_s: List[float]
    ) -> Optional[InferenceResult]:
        """진동 패턴 감지

        표준편차 증가로 진동을 감지합니다.

        Args:
            fz_values: Fz 값 리스트
            timestamps_s: 타임스탬프 리스트 (초)

        Returns:
            InferenceResult 또는 None
        """
        vibration_config = self.pattern_thresholds.get("vibration", {})
        window_s = vibration_config.get("window_s", 5)
        amplitude_threshold = vibration_config.get("amplitude_threshold", 2.0)
        min_duration_s = vibration_config.get("min_duration_s", 10)

        if len(fz_values) < 10:
            return None

        import numpy as np

        # 전체 표준편차 계산
        global_std = float(np.std(fz_values))
        if global_std < 0.01:  # 거의 변화가 없으면 스킵
            return None

        # 롤링 표준편차 계산 (간단 구현)
        window_size = max(2, int(len(fz_values) * window_s / (timestamps_s[-1] - timestamps_s[0])) if timestamps_s[-1] != timestamps_s[0] else 10)

        vibration_start = None
        max_local_std = 0

        for i in range(window_size, len(fz_values)):
            window_data = fz_values[i-window_size:i]
            local_std = float(np.std(window_data))

            if local_std > global_std * amplitude_threshold:
                if vibration_start is None:
                    vibration_start = i - window_size
                max_local_std = max(max_local_std, local_std)

                duration = timestamps_s[i] - timestamps_s[vibration_start]
                if duration >= min_duration_s:
                    return InferenceResult(
                        rule_name="VIBRATION_DETECTION",
                        result_type="pattern",
                        result_id="PAT_VIBRATION",
                        confidence=min(0.95, 0.6 + (local_std / global_std - amplitude_threshold) * 0.1),
                        evidence={
                            "features": {
                                "global_std": round(global_std, 3),
                                "max_local_std": round(max_local_std, 3),
                                "std_ratio": round(max_local_std / global_std, 2),
                                "duration_s": round(duration, 2)
                            },
                            "thresholds": {
                                "amplitude_threshold": amplitude_threshold,
                                "min_duration_s": min_duration_s
                            },
                            "judgment": f"std_ratio({max_local_std/global_std:.2f}) > threshold({amplitude_threshold}) for {duration:.1f}s",
                            "data_range": {"start_idx": vibration_start, "end_idx": i}
                        },
                        message=f"진동 감지: 표준편차 {max_local_std/global_std:.1f}배 증가 ({duration:.1f}초 지속)"
                    )
            else:
                vibration_start = None
                max_local_std = 0

        return None

    def detect_drift(
        self,
        fz_values: List[float],
        timestamps_s: List[float]
    ) -> Optional[InferenceResult]:
        """드리프트 패턴 감지

        Baseline 대비 지속적인 이동을 감지합니다.

        Args:
            fz_values: Fz 값 리스트
            timestamps_s: 타임스탬프 리스트 (초)

        Returns:
            InferenceResult 또는 None
        """
        drift_config = self.pattern_thresholds.get("drift", {})
        window_h = drift_config.get("window_h", 1)
        deviation_pct = drift_config.get("deviation_pct", 10)
        min_duration_h = drift_config.get("min_duration_h", 0.5)

        if len(fz_values) < 10:
            return None

        import numpy as np

        # 전체 baseline 계산
        baseline = float(np.mean(fz_values))

        # baseline이 0에 가까우면 절대값 기반 감지
        baseline_epsilon = 1.0
        drift_absolute_threshold = 5.0

        if abs(baseline) < baseline_epsilon:
            use_absolute_mode = True
        else:
            use_absolute_mode = False

        # 시간 범위 확인
        total_duration_s = timestamps_s[-1] - timestamps_s[0] if timestamps_s else 0
        total_duration_h = total_duration_s / 3600

        if total_duration_h < min_duration_h:
            return None

        # 데이터를 시간 구간별로 나누어 평균 계산
        window_s = window_h * 3600
        segments = []
        current_segment = []
        segment_start_s = timestamps_s[0]

        for fz, ts in zip(fz_values, timestamps_s):
            if ts - segment_start_s > window_s:
                if current_segment:
                    segments.append(float(np.mean(current_segment)))
                current_segment = [fz]
                segment_start_s = ts
            else:
                current_segment.append(fz)

        if current_segment:
            segments.append(float(np.mean(current_segment)))

        if len(segments) < 2:
            return None

        # 드리프트 감지
        drift_start_idx = None
        max_deviation = 0

        for i, seg_mean in enumerate(segments):
            if use_absolute_mode:
                deviation = abs(seg_mean - baseline)
                is_drift = deviation > drift_absolute_threshold
            else:
                deviation = abs((seg_mean - baseline) / abs(baseline) * 100)
                is_drift = deviation > deviation_pct

            if is_drift:
                if drift_start_idx is None:
                    drift_start_idx = i
                max_deviation = max(max_deviation, deviation)

                drift_duration_h = (i - drift_start_idx + 1) * window_h
                if drift_duration_h >= min_duration_h:
                    if use_absolute_mode:
                        judgment = f"deviation({max_deviation:.2f}N) > threshold({drift_absolute_threshold}N) for {drift_duration_h:.1f}h"
                        message = f"드리프트 감지: {max_deviation:.2f}N 편차 ({drift_duration_h:.1f}시간 지속)"
                    else:
                        judgment = f"deviation({max_deviation:.1f}%) > threshold({deviation_pct}%) for {drift_duration_h:.1f}h"
                        message = f"드리프트 감지: {max_deviation:.1f}% 편차 ({drift_duration_h:.1f}시간 지속)"

                    return InferenceResult(
                        rule_name="DRIFT_DETECTION",
                        result_type="pattern",
                        result_id="PAT_DRIFT",
                        confidence=min(0.90, 0.5 + max_deviation / (deviation_pct if not use_absolute_mode else drift_absolute_threshold) * 0.2),
                        evidence={
                            "features": {
                                "baseline": round(baseline, 3),
                                "max_deviation": round(max_deviation, 2),
                                "detection_mode": "absolute" if use_absolute_mode else "percentage",
                                "duration_h": round(drift_duration_h, 2)
                            },
                            "thresholds": {
                                "deviation_threshold": drift_absolute_threshold if use_absolute_mode else deviation_pct,
                                "min_duration_h": min_duration_h
                            },
                            "judgment": judgment,
                            "segment_range": {"start_idx": drift_start_idx, "end_idx": i}
                        },
                        message=message
                    )
            else:
                drift_start_idx = None
                max_deviation = 0

        return None

    def detect_patterns(self, data: Dict[str, List[float]]) -> List[InferenceResult]:
        """시계열 데이터에서 모든 패턴 감지

        Args:
            data: 센서 데이터 {"Fz": [...], "timestamp_ms": [...], ...}

        Returns:
            감지된 패턴 리스트
        """
        results = []

        fz = data.get("Fz", [])
        ts_ms = data.get("timestamp_ms", [])
        ts_s = data.get("timestamp_s", [i/1000 for i in ts_ms] if ts_ms else [])

        # 충돌 감지
        collision = self.detect_collision(fz, ts_ms)
        if collision:
            results.append(collision)

        # 과부하 감지
        overload = self.detect_overload(fz, ts_s)
        if overload:
            results.append(overload)

        # 진동 감지
        vibration = self.detect_vibration(fz, ts_s)
        if vibration:
            results.append(vibration)

        # 드리프트 감지
        drift = self.detect_drift(fz, ts_s)
        if drift:
            results.append(drift)

        return results

    # ================================================================
    # 원인 추론 (Cause Inference)
    # ================================================================

    def infer_cause(
        self,
        pattern_id: str,
        context: Optional[Dict] = None
    ) -> List[InferenceResult]:
        """패턴과 컨텍스트에서 원인 추론

        Args:
            pattern_id: 패턴 ID (예: "PAT_COLLISION")
            context: 컨텍스트 정보 (예: {"product_weight": 4.5})

        Returns:
            추론된 원인 리스트 (신뢰도 순)
        """
        context = context or {}
        cause_rules = self.inference_rules.get("cause_rules", [])
        results = []

        for rule in cause_rules:
            if rule.get("pattern") != pattern_id:
                continue

            for cause_info in rule.get("causes", []):
                confidence = cause_info.get("base_confidence", 0.5)

                # 컨텍스트 기반 신뢰도 조정
                for boost_rule in cause_info.get("context_boost", []):
                    if self._evaluate_context_condition(boost_rule.get("condition"), context):
                        confidence += boost_rule.get("boost", 0)

                confidence = min(1.0, confidence)

                # 온톨로지에서 원인 엔티티 조회
                cause_entity = self.ontology.get_entity(cause_info["cause_id"])
                cause_name = cause_entity.name if cause_entity else cause_info.get("description", "")

                results.append(InferenceResult(
                    rule_name=f"CAUSE_{pattern_id}",
                    result_type="cause",
                    result_id=cause_info["cause_id"],
                    confidence=confidence,
                    evidence={
                        "pattern": pattern_id,
                        "context": context,
                        "description": cause_info.get("description", "")
                    },
                    message=f"원인 추정: {cause_name} (신뢰도 {confidence:.0%})"
                ))

        # 신뢰도 순 정렬
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def _evaluate_context_condition(self, condition: Optional[str], context: Dict) -> bool:
        """컨텍스트 조건 평가 (간단한 구현)"""
        if not condition:
            return False

        try:
            # 간단한 비교 연산 지원
            if ">=" in condition:
                key, value = condition.split(">=")
                return context.get(key.strip(), 0) >= float(value.strip())
            elif "<=" in condition:
                key, value = condition.split("<=")
                return context.get(key.strip(), 0) <= float(value.strip())
            elif ">" in condition:
                key, value = condition.split(">")
                return context.get(key.strip(), 0) > float(value.strip())
            elif "<" in condition:
                key, value = condition.split("<")
                return context.get(key.strip(), 0) < float(value.strip())
            elif "==" in condition:
                key, value = condition.split("==")
                return str(context.get(key.strip())) == value.strip().strip("'\"")
        except Exception as e:
            logger.warning(f"조건 평가 실패 (condition={condition}): {e}")

        return False

    # ================================================================
    # 에러 예측 (Error Prediction)
    # ================================================================

    def predict_error(
        self,
        pattern_history: List[Dict]
    ) -> List[InferenceResult]:
        """패턴 이력에서 에러 예측

        Args:
            pattern_history: 패턴 발생 이력
                [{"pattern": "PAT_OVERLOAD", "timestamp": "2026-01-20T10:00:00", "intensity": 0.8}, ...]

        Returns:
            예측 결과 리스트
        """
        prediction_rules = self.inference_rules.get("prediction_rules", [])
        results = []

        for rule in prediction_rules:
            pattern_id = rule.get("pattern")
            condition = rule.get("condition", {})
            prediction = rule.get("prediction", {})

            # 해당 패턴만 필터
            pattern_events = [
                e for e in pattern_history
                if e.get("pattern") == pattern_id
            ]

            condition_type = condition.get("type")

            if condition_type == "frequency":
                # 빈도 기반 예측
                result = self._evaluate_frequency_condition(
                    rule, pattern_id, pattern_events, condition, prediction
                )
                if result:
                    results.append(result)

            elif condition_type == "trend":
                # 추세 기반 예측 (증가/감소 추세)
                result = self._evaluate_trend_condition(
                    rule, pattern_id, pattern_events, condition, prediction
                )
                if result:
                    results.append(result)

        return results

    def _evaluate_frequency_condition(
        self,
        rule: Dict,
        pattern_id: str,
        pattern_events: List[Dict],
        condition: Dict,
        prediction: Dict
    ) -> Optional[InferenceResult]:
        """빈도 기반 예측 조건 평가

        Args:
            rule: 규칙 정의
            pattern_id: 패턴 ID
            pattern_events: 해당 패턴의 이벤트 목록
            condition: 조건 정의
            prediction: 예측 정의

        Returns:
            InferenceResult 또는 None
        """
        count_threshold = condition.get("count", 3)
        time_window_days = condition.get("time_window_days", 3)

        # 최근 N일 내 이벤트 필터
        cutoff = datetime.now() - timedelta(days=time_window_days)
        recent_events = [
            e for e in pattern_events
            if self._parse_timestamp(e.get("timestamp")) > cutoff
        ]

        if len(recent_events) >= count_threshold:
            return InferenceResult(
                rule_name=rule["name"],
                result_type="prediction",
                result_id=prediction.get("error_id", ""),
                confidence=prediction.get("probability", 0.5),
                evidence={
                    "pattern": pattern_id,
                    "condition_type": "frequency",
                    "event_count": len(recent_events),
                    "time_window_days": time_window_days,
                    "threshold": count_threshold
                },
                message=prediction.get("message", "")
            )

        return None

    def _evaluate_trend_condition(
        self,
        rule: Dict,
        pattern_id: str,
        pattern_events: List[Dict],
        condition: Dict,
        prediction: Dict
    ) -> Optional[InferenceResult]:
        """추세 기반 예측 조건 평가

        패턴의 강도(intensity)가 시간에 따라 증가/감소하는 추세를 감지합니다.

        Args:
            rule: 규칙 정의
            pattern_id: 패턴 ID
            pattern_events: 해당 패턴의 이벤트 목록
            condition: 조건 정의 (direction, threshold_pct, time_window_days)
            prediction: 예측 정의

        Returns:
            InferenceResult 또는 None
        """
        direction = condition.get("direction", "increasing")  # "increasing" or "decreasing"
        threshold_pct = condition.get("threshold_pct", 20)  # 20% 변화
        time_window_days = condition.get("time_window_days", 7)

        # 최근 N일 내 이벤트 필터
        cutoff = datetime.now() - timedelta(days=time_window_days)
        recent_events = [
            e for e in pattern_events
            if self._parse_timestamp(e.get("timestamp")) > cutoff
        ]

        # 최소 2개 이상의 이벤트 필요
        if len(recent_events) < 2:
            return None

        # 시간순 정렬
        sorted_events = sorted(
            recent_events,
            key=lambda e: self._parse_timestamp(e.get("timestamp"))
        )

        # 강도(intensity) 값 추출
        # intensity, severity, confidence, magnitude 등 다양한 키 지원
        def get_intensity(event: Dict) -> Optional[float]:
            for key in ["intensity", "severity", "confidence", "magnitude", "value"]:
                val = event.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        pass
            return None

        intensities = [get_intensity(e) for e in sorted_events]
        valid_intensities = [i for i in intensities if i is not None]

        # 강도 값이 없으면 발생 빈도로 대체 (단순 카운트 증가)
        if len(valid_intensities) < 2:
            # 빈도 기반 추세: 기간을 절반으로 나누어 비교
            mid_time = cutoff + timedelta(days=time_window_days / 2)
            first_half = [e for e in sorted_events if self._parse_timestamp(e.get("timestamp")) < mid_time]
            second_half = [e for e in sorted_events if self._parse_timestamp(e.get("timestamp")) >= mid_time]

            if len(first_half) == 0:
                return None

            # 빈도 변화율 계산
            first_count = len(first_half)
            second_count = len(second_half)
            change_pct = ((second_count - first_count) / first_count) * 100 if first_count > 0 else 0

            trend_detected = (
                (direction == "increasing" and change_pct >= threshold_pct) or
                (direction == "decreasing" and change_pct <= -threshold_pct)
            )

            if trend_detected:
                return InferenceResult(
                    rule_name=rule["name"],
                    result_type="prediction",
                    result_id=prediction.get("error_id", ""),
                    confidence=prediction.get("probability", 0.5),
                    evidence={
                        "pattern": pattern_id,
                        "condition_type": "trend",
                        "trend_direction": direction,
                        "detection_method": "frequency_based",
                        "first_half_count": first_count,
                        "second_half_count": second_count,
                        "change_pct": round(change_pct, 1),
                        "threshold_pct": threshold_pct,
                        "time_window_days": time_window_days,
                        "total_events": len(sorted_events)
                    },
                    message=prediction.get("message", "")
                )
        else:
            # 강도 기반 추세: 전반부와 후반부 평균 비교
            mid_idx = len(valid_intensities) // 2
            first_half_avg = sum(valid_intensities[:mid_idx]) / mid_idx if mid_idx > 0 else 0
            second_half_avg = sum(valid_intensities[mid_idx:]) / (len(valid_intensities) - mid_idx) if len(valid_intensities) > mid_idx else 0

            if first_half_avg == 0:
                return None

            change_pct = ((second_half_avg - first_half_avg) / abs(first_half_avg)) * 100

            trend_detected = (
                (direction == "increasing" and change_pct >= threshold_pct) or
                (direction == "decreasing" and change_pct <= -threshold_pct)
            )

            if trend_detected:
                return InferenceResult(
                    rule_name=rule["name"],
                    result_type="prediction",
                    result_id=prediction.get("error_id", ""),
                    confidence=prediction.get("probability", 0.5),
                    evidence={
                        "pattern": pattern_id,
                        "condition_type": "trend",
                        "trend_direction": direction,
                        "detection_method": "intensity_based",
                        "first_half_avg": round(first_half_avg, 3),
                        "second_half_avg": round(second_half_avg, 3),
                        "change_pct": round(change_pct, 1),
                        "threshold_pct": threshold_pct,
                        "time_window_days": time_window_days,
                        "total_events": len(sorted_events)
                    },
                    message=prediction.get("message", "")
                )

        return None

    def _parse_timestamp(self, ts_str: Optional[str]) -> datetime:
        """타임스탬프 문자열 파싱"""
        if not ts_str:
            return datetime.min
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    # ================================================================
    # 해결책 조회 (Resolution Lookup)
    # ================================================================

    def get_resolution(self, cause_id: str) -> List[InferenceResult]:
        """원인에 대한 해결책 조회

        온톨로지의 RESOLVED_BY 관계를 활용

        Args:
            cause_id: 원인 ID

        Returns:
            해결책 리스트
        """
        results = []

        # 온톨로지에서 RESOLVED_BY 관계 조회
        rels = self.ontology.get_relationships_for_entity(cause_id, direction="outgoing")

        for rel in rels:
            if rel.relation.value == "RESOLVED_BY":
                resolution = self.ontology.get_entity(rel.target)
                if resolution:
                    results.append(InferenceResult(
                        rule_name="RESOLUTION_LOOKUP",
                        result_type="resolution",
                        result_id=resolution.id,
                        confidence=1.0,
                        evidence={
                            "cause": cause_id,
                            "steps": resolution.properties.get("steps", [])
                        },
                        message=f"해결책: {resolution.name}"
                    ))

        return results

    # ================================================================
    # 통합 추론 (Full Inference Chain)
    # ================================================================

    def full_inference(
        self,
        sensor_data: Dict[str, List[float]],
        context: Optional[Dict] = None
    ) -> Dict[str, List[InferenceResult]]:
        """전체 추론 체인 실행

        센서 데이터 → 패턴 감지 → 원인 추론 → 해결책 조회

        Args:
            sensor_data: 센서 데이터
            context: 컨텍스트 정보

        Returns:
            추론 결과 딕셔너리
        """
        context = context or {}
        results = {
            "states": [],
            "patterns": [],
            "causes": [],
            "resolutions": []
        }

        # 1. 상태 추론
        if "Fz" in sensor_data and sensor_data["Fz"]:
            latest_fz = sensor_data["Fz"][-1]
            state = self.infer_state("Fz", latest_fz)
            if state:
                results["states"].append(state)

        # 2. 패턴 감지
        patterns = self.detect_patterns(sensor_data)
        results["patterns"] = patterns

        # 3. 원인 추론 (감지된 패턴별)
        for pattern in patterns:
            causes = self.infer_cause(pattern.result_id, context)
            results["causes"].extend(causes)

        # 4. 해결책 조회 (추론된 원인별)
        for cause in results["causes"]:
            resolutions = self.get_resolution(cause.result_id)
            results["resolutions"].extend(resolutions)

        return results


# ================================================================
# 편의 함수
# ================================================================

def create_rule_engine() -> RuleEngine:
    """RuleEngine 인스턴스 생성 (편의 함수)"""
    return RuleEngine()
