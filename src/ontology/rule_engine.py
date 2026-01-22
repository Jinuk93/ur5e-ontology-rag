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
        """
        self.inference_rules = self._load_yaml(
            inference_rules_path or self.DEFAULT_INFERENCE_RULES_PATH
        )
        self.pattern_thresholds = self._load_yaml(
            pattern_thresholds_path or self.DEFAULT_PATTERN_THRESHOLDS_PATH
        )
        self.ontology = load_ontology()

        logger.info("RuleEngine 초기화 완료")

    def _load_yaml(self, path: Path) -> Dict:
        """YAML 파일 로드"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"YAML 로드 실패: {path} - {e}")
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

        # TODO: 진동, 드리프트 감지 추가

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
        except Exception:
            pass

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
                [{"pattern": "PAT_OVERLOAD", "timestamp": "2026-01-20T10:00:00"}, ...]

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

            if condition.get("type") == "frequency":
                # 빈도 기반 예측
                count_threshold = condition.get("count", 3)
                time_window_days = condition.get("time_window_days", 3)

                # 최근 N일 내 이벤트 필터
                cutoff = datetime.now() - timedelta(days=time_window_days)
                recent_events = [
                    e for e in pattern_events
                    if self._parse_timestamp(e.get("timestamp")) > cutoff
                ]

                if len(recent_events) >= count_threshold:
                    results.append(InferenceResult(
                        rule_name=rule["name"],
                        result_type="prediction",
                        result_id=prediction.get("error_id", ""),
                        confidence=prediction.get("probability", 0.5),
                        evidence={
                            "pattern": pattern_id,
                            "event_count": len(recent_events),
                            "time_window_days": time_window_days,
                            "threshold": count_threshold
                        },
                        message=prediction.get("message", "")
                    ))

        return results

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
