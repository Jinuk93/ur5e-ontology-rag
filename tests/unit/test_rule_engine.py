"""
RuleEngine 단위 테스트

테스트 대상:
- infer_state: 상태 추론
- detect_collision: 충돌 패턴 감지
- detect_overload: 과부하 패턴 감지
- predict_error: 에러 예측 (frequency + trend)
- YAML 로드 에러 처리
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import yaml

from src.ontology.rule_engine import RuleEngine, InferenceResult


class TestInferState:
    """상태 추론 테스트"""

    @pytest.fixture
    def rule_engine(self):
        """RuleEngine 인스턴스 생성"""
        return RuleEngine()

    def test_infer_state_fz_normal_idle(self, rule_engine):
        """Fz 정상 상태 (유휴) 테스트"""
        result = rule_engine.infer_state("Fz", -10)

        assert result is not None
        assert result.result_type == "state"
        assert result.result_id == "State_Normal"
        assert result.evidence["severity"] == "normal"
        assert "유휴" in result.message

    def test_infer_state_fz_normal_load(self, rule_engine):
        """Fz 정상 상태 (정상 부하) 테스트"""
        result = rule_engine.infer_state("Fz", -75)

        assert result is not None
        assert result.result_id == "State_Normal"
        assert result.evidence["severity"] == "normal"

    def test_infer_state_fz_warning(self, rule_engine):
        """Fz 경고 상태 테스트"""
        result = rule_engine.infer_state("Fz", -300)

        assert result is not None
        assert result.result_id == "State_Warning"
        assert result.evidence["severity"] == "warning"

    def test_infer_state_fz_critical(self, rule_engine):
        """Fz 위험 상태 테스트"""
        result = rule_engine.infer_state("Fz", -700)

        assert result is not None
        assert result.result_id == "State_Critical"
        assert result.evidence["severity"] == "critical"

    def test_infer_state_fx_normal(self, rule_engine):
        """Fx 정상 상태 테스트"""
        result = rule_engine.infer_state("Fx", 50)

        assert result is not None
        assert result.result_id == "State_Normal"

    def test_infer_state_fx_warning(self, rule_engine):
        """Fx 경고 상태 테스트"""
        result = rule_engine.infer_state("Fx", -100)

        assert result is not None
        assert result.result_id == "State_Warning"

    def test_infer_state_unknown_axis(self, rule_engine):
        """알 수 없는 축 테스트"""
        result = rule_engine.infer_state("Unknown", 100)

        assert result is None

    def test_infer_state_out_of_range(self, rule_engine):
        """범위 외 값 테스트"""
        # Fz 매핑에 정의되지 않은 양수 값
        result = rule_engine.infer_state("Fz", 100)

        # 매핑에 없으면 None 반환
        assert result is None

    def test_infer_states_multiple(self, rule_engine):
        """여러 축 동시 상태 추론 테스트"""
        measurements = {
            "Fz": -300,  # Warning
            "Fx": 50,    # Normal
            "Ty": 3,     # Warning
        }
        results = rule_engine.infer_states(measurements)

        assert len(results) == 3
        states = {r.evidence["axis"]: r.result_id for r in results}
        assert states["Fz"] == "State_Warning"
        assert states["Fx"] == "State_Normal"
        assert states["Ty"] == "State_Warning"


class TestDetectCollision:
    """충돌 패턴 감지 테스트"""

    @pytest.fixture
    def rule_engine(self):
        return RuleEngine()

    def test_detect_collision_positive(self, rule_engine):
        """충돌 감지 성공 테스트"""
        # 급격한 힘 변화 (500N 이상, 100ms 이내)
        fz_values = [0, -50, -600]
        timestamps_ms = [0, 50, 100]

        result = rule_engine.detect_collision(fz_values, timestamps_ms)

        assert result is not None
        assert result.result_id == "PAT_COLLISION"
        assert result.confidence >= 0.9
        assert "충돌" in result.message

    def test_detect_collision_slow_rise(self, rule_engine):
        """느린 상승 (비충돌) 테스트"""
        # 변화는 크지만 시간이 오래 걸림
        fz_values = [0, -300, -600]
        timestamps_ms = [0, 500, 1000]  # 500ms 간격

        result = rule_engine.detect_collision(fz_values, timestamps_ms)

        # 상승 시간이 100ms 초과하면 충돌 아님
        assert result is None

    def test_detect_collision_small_delta(self, rule_engine):
        """작은 변화 (비충돌) 테스트"""
        # 변화가 임계값 미만
        fz_values = [0, -100, -200]
        timestamps_ms = [0, 50, 100]

        result = rule_engine.detect_collision(fz_values, timestamps_ms)

        assert result is None

    def test_detect_collision_insufficient_data(self, rule_engine):
        """데이터 부족 테스트"""
        fz_values = [-100]
        timestamps_ms = [0]

        result = rule_engine.detect_collision(fz_values, timestamps_ms)

        assert result is None


class TestDetectOverload:
    """과부하 패턴 감지 테스트"""

    @pytest.fixture
    def rule_engine(self):
        return RuleEngine()

    def test_detect_overload_positive(self, rule_engine):
        """과부하 감지 성공 테스트"""
        # 300N 이상이 5초 이상 지속
        fz_values = [-350, -360, -340, -370, -350, -380]
        timestamps_s = [0, 1, 2, 3, 4, 6]  # 6초 동안

        result = rule_engine.detect_overload(fz_values, timestamps_s)

        assert result is not None
        assert result.result_id == "PAT_OVERLOAD"
        assert "과부하" in result.message

    def test_detect_overload_short_duration(self, rule_engine):
        """짧은 지속 시간 (비과부하) 테스트"""
        # 300N 이상이지만 5초 미만
        fz_values = [-350, -360, -340]
        timestamps_s = [0, 1, 2]  # 2초 동안

        result = rule_engine.detect_overload(fz_values, timestamps_s)

        assert result is None

    def test_detect_overload_below_threshold(self, rule_engine):
        """임계값 미만 (비과부하) 테스트"""
        # 300N 미만
        fz_values = [-100, -150, -200]
        timestamps_s = [0, 1, 2, 3, 4, 5, 6]

        result = rule_engine.detect_overload(fz_values, timestamps_s)

        assert result is None


class TestPredictError:
    """에러 예측 테스트"""

    @pytest.fixture
    def rule_engine(self):
        return RuleEngine()

    def test_predict_error_frequency_positive(self, rule_engine):
        """빈도 기반 예측 성공 테스트"""
        # 지난 4일간 PAT_OVERLOAD 3회 발생
        now = datetime.now()
        pattern_history = [
            {"pattern": "PAT_OVERLOAD", "timestamp": (now - timedelta(days=1)).isoformat()},
            {"pattern": "PAT_OVERLOAD", "timestamp": (now - timedelta(days=2)).isoformat()},
            {"pattern": "PAT_OVERLOAD", "timestamp": (now - timedelta(days=3)).isoformat()},
        ]

        results = rule_engine.predict_error(pattern_history)

        # OVERLOAD_PREDICTION 규칙 매칭 (count=3, window=4일)
        overload_predictions = [r for r in results if r.result_id == "C189"]
        assert len(overload_predictions) >= 1
        assert overload_predictions[0].evidence["condition_type"] == "frequency"

    def test_predict_error_frequency_insufficient(self, rule_engine):
        """빈도 기반 예측 실패 (횟수 부족) 테스트"""
        now = datetime.now()
        pattern_history = [
            {"pattern": "PAT_OVERLOAD", "timestamp": (now - timedelta(days=1)).isoformat()},
            {"pattern": "PAT_OVERLOAD", "timestamp": (now - timedelta(days=2)).isoformat()},
            # 2회만 (3회 미만)
        ]

        results = rule_engine.predict_error(pattern_history)

        overload_predictions = [r for r in results if r.result_id == "C189"]
        assert len(overload_predictions) == 0

    def test_predict_error_frequency_old_events(self, rule_engine):
        """빈도 기반 예측 실패 (오래된 이벤트) 테스트"""
        now = datetime.now()
        pattern_history = [
            {"pattern": "PAT_OVERLOAD", "timestamp": (now - timedelta(days=10)).isoformat()},
            {"pattern": "PAT_OVERLOAD", "timestamp": (now - timedelta(days=11)).isoformat()},
            {"pattern": "PAT_OVERLOAD", "timestamp": (now - timedelta(days=12)).isoformat()},
        ]

        results = rule_engine.predict_error(pattern_history)

        # 4일 윈도우 밖이므로 예측 없음
        overload_predictions = [r for r in results if r.result_id == "C189"]
        assert len(overload_predictions) == 0

    def test_predict_error_trend_increasing_frequency(self, rule_engine):
        """추세 기반 예측 (빈도 증가) 테스트"""
        now = datetime.now()
        # 첫 3.5일: 1회, 후 3.5일: 4회 (증가 추세)
        pattern_history = [
            # 첫 절반 (1회)
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=6)).isoformat()},
            # 후 절반 (4회)
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=3)).isoformat()},
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=2)).isoformat()},
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=1)).isoformat()},
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(hours=12)).isoformat()},
        ]

        results = rule_engine.predict_error(pattern_history)

        # VIBRATION_PREDICTION 규칙: trend, increasing, 20%, 7일
        vibration_predictions = [r for r in results if r.result_id == "C204"]
        assert len(vibration_predictions) >= 1
        assert vibration_predictions[0].evidence["condition_type"] == "trend"
        assert vibration_predictions[0].evidence["trend_direction"] == "increasing"

    def test_predict_error_trend_with_intensity(self, rule_engine):
        """추세 기반 예측 (강도 증가) 테스트"""
        now = datetime.now()
        # 강도가 점점 증가하는 패턴
        pattern_history = [
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=6)).isoformat(), "intensity": 0.3},
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=5)).isoformat(), "intensity": 0.35},
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=3)).isoformat(), "intensity": 0.5},
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=2)).isoformat(), "intensity": 0.6},
            {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=1)).isoformat(), "intensity": 0.7},
        ]

        results = rule_engine.predict_error(pattern_history)

        vibration_predictions = [r for r in results if r.result_id == "C204"]
        assert len(vibration_predictions) >= 1
        assert vibration_predictions[0].evidence["detection_method"] == "intensity_based"


class TestInferCause:
    """원인 추론 테스트"""

    @pytest.fixture
    def rule_engine(self):
        return RuleEngine()

    def test_infer_cause_collision(self, rule_engine):
        """충돌 패턴 원인 추론 테스트"""
        results = rule_engine.infer_cause("PAT_COLLISION")

        assert len(results) > 0
        cause_ids = [r.result_id for r in results]
        assert "CAUSE_COLLISION" in cause_ids

        # 신뢰도 내림차순 정렬 확인
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)

    def test_infer_cause_with_context_boost(self, rule_engine):
        """컨텍스트 기반 신뢰도 부스트 테스트"""
        # 무거운 작업 컨텍스트
        context = {"workload": "heavy"}

        results_with_context = rule_engine.infer_cause("PAT_COLLISION", context)
        results_without_context = rule_engine.infer_cause("PAT_COLLISION", {})

        # CAUSE_COLLISION의 신뢰도 비교
        collision_with = next((r for r in results_with_context if r.result_id == "CAUSE_COLLISION"), None)
        collision_without = next((r for r in results_without_context if r.result_id == "CAUSE_COLLISION"), None)

        assert collision_with is not None
        assert collision_without is not None
        # 컨텍스트가 있으면 부스트 적용
        assert collision_with.confidence >= collision_without.confidence

    def test_infer_cause_unknown_pattern(self, rule_engine):
        """알 수 없는 패턴 원인 추론 테스트"""
        results = rule_engine.infer_cause("PAT_UNKNOWN")

        assert len(results) == 0


class TestYAMLLoadError:
    """YAML 로드 에러 처리 테스트"""

    def test_load_missing_inference_rules(self):
        """필수 inference_rules.yaml 누락 시 예외 테스트"""
        with pytest.raises(FileNotFoundError) as exc_info:
            RuleEngine(
                inference_rules_path=Path("nonexistent/inference_rules.yaml")
            )

        assert "필수 설정 파일" in str(exc_info.value)

    def test_load_missing_pattern_thresholds(self):
        """필수 pattern_thresholds.yaml 누락 시 예외 테스트"""
        with pytest.raises(FileNotFoundError) as exc_info:
            RuleEngine(
                pattern_thresholds_path=Path("nonexistent/pattern_thresholds.yaml")
            )

        assert "필수 설정 파일" in str(exc_info.value)

    def test_load_invalid_yaml_syntax(self):
        """잘못된 YAML 문법 시 예외 테스트"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError):
                RuleEngine(inference_rules_path=temp_path)
        finally:
            temp_path.unlink()

    def test_load_empty_yaml(self):
        """빈 YAML 파일 시 예외 테스트"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")  # 빈 파일
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                RuleEngine(inference_rules_path=temp_path)
            assert "비어있습니다" in str(exc_info.value)
        finally:
            temp_path.unlink()

    def test_validate_missing_state_rules(self):
        """state_rules 누락 시 예외 테스트"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"cause_rules": []}, f)  # state_rules 없음
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                RuleEngine(inference_rules_path=temp_path)
            assert "state_rules" in str(exc_info.value)
        finally:
            temp_path.unlink()


class TestFullInference:
    """전체 추론 체인 테스트"""

    @pytest.fixture
    def rule_engine(self):
        return RuleEngine()

    def test_full_inference_with_collision(self, rule_engine):
        """충돌 포함 전체 추론 테스트"""
        sensor_data = {
            "Fz": [0, -50, -600, -550, -500],
            "timestamp_ms": [0, 50, 100, 150, 200],
        }

        results = rule_engine.full_inference(sensor_data)

        # 상태 추론 결과 확인
        assert "states" in results

        # 패턴 감지 결과 확인
        assert "patterns" in results
        pattern_ids = [p.result_id for p in results["patterns"]]
        assert "PAT_COLLISION" in pattern_ids

        # 원인 추론 결과 확인
        assert "causes" in results
        if results["causes"]:
            cause_ids = [c.result_id for c in results["causes"]]
            assert "CAUSE_COLLISION" in cause_ids

    def test_full_inference_no_patterns(self, rule_engine):
        """패턴 없는 정상 데이터 전체 추론 테스트"""
        sensor_data = {
            "Fz": [-50, -55, -52, -48, -51],
            "timestamp_ms": [0, 1000, 2000, 3000, 4000],
        }

        results = rule_engine.full_inference(sensor_data)

        # 패턴 없음
        assert len(results["patterns"]) == 0

        # 원인, 해결책도 없음
        assert len(results["causes"]) == 0
        assert len(results["resolutions"]) == 0


class TestInferenceResult:
    """InferenceResult 데이터클래스 테스트"""

    def test_inference_result_creation(self):
        """InferenceResult 생성 테스트"""
        result = InferenceResult(
            rule_name="TEST_RULE",
            result_type="state",
            result_id="State_Normal",
            confidence=0.95,
            evidence={"key": "value"},
            message="테스트 메시지"
        )

        assert result.rule_name == "TEST_RULE"
        assert result.result_type == "state"
        assert result.result_id == "State_Normal"
        assert result.confidence == 0.95
        assert result.evidence == {"key": "value"}
        assert result.message == "테스트 메시지"

    def test_inference_result_defaults(self):
        """InferenceResult 기본값 테스트"""
        result = InferenceResult(
            rule_name="TEST",
            result_type="test",
            result_id="TEST_ID",
            confidence=0.5
        )

        assert result.evidence == {}
        assert result.message == ""
