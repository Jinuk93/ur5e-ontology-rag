# Step 17: 온톨로지 시스템 개선 - 완료 보고서

## 1. 요약

| 항목 | 내용 |
|------|------|
| Phase | 17 - 온톨로지 시스템 개선 |
| 상태 | **완료** |
| 날짜 | 2026-01-26 |
| 주요 산출물 | trend 예측 규칙, YAML 에러 처리, RuleEngine 테스트 |

---

## 2. 개선 항목

### 2.1 P1: "trend" 예측 규칙 구현

**문제**: `inference_rules.yaml`에 정의된 "trend" 타입 조건이 코드에서 처리되지 않음

**해결**: `rule_engine.py`의 `predict_error` 메서드에 추세 기반 예측 로직 추가

```python
# 기존: frequency 타입만 처리
if condition.get("type") == "frequency":
    # ...

# 개선: trend 타입 추가
elif condition_type == "trend":
    result = self._evaluate_trend_condition(...)
```

**새로 추가된 메서드**:

```python
def _evaluate_trend_condition(
    self,
    rule: Dict,
    pattern_id: str,
    pattern_events: List[Dict],
    condition: Dict,
    prediction: Dict
) -> Optional[InferenceResult]:
    """추세 기반 예측 조건 평가

    두 가지 감지 방식:
    1. 빈도 기반: 첫 절반 vs 후 절반 발생 횟수 비교
    2. 강도 기반: intensity 값의 평균 변화 감지

    Args:
        condition: {
            "direction": "increasing" | "decreasing",
            "threshold_pct": 20,  # 20% 변화
            "time_window_days": 7
        }
    """
```

**지원 기능**:
- `direction`: "increasing" (증가) 또는 "decreasing" (감소)
- `threshold_pct`: 변화율 임계값 (%)
- `time_window_days`: 분석 기간 (일)
- 두 가지 감지 방식:
  1. **빈도 기반**: 기간을 절반으로 나누어 발생 횟수 비교
  2. **강도 기반**: `intensity`, `severity`, `confidence` 등 값의 평균 변화 감지

---

### 2.2 P2: YAML 로드 실패 시 에러 처리 개선

**문제**: 설정 파일 로드 실패 시 빈 딕셔너리 반환하여 조용히 실패

```python
# 기존: 조용한 실패
except Exception as e:
    logger.warning(f"YAML 로드 실패: {path} - {e}")
    return {}  # ← 추론 엔진 무력화
```

**해결**:

```python
# 개선: 명시적 에러 처리
def _load_yaml(self, path: Path, required: bool = True) -> Dict:
    """YAML 파일 로드

    Args:
        required: True면 로드 실패 시 예외 발생

    Raises:
        FileNotFoundError: 필수 파일이 없을 때
        yaml.YAMLError: YAML 파싱 실패 시
        ValueError: 파일이 비어있을 때
    """
    if not path.exists():
        if required:
            raise FileNotFoundError(f"필수 설정 파일이 없습니다: {path}")
    # ...
```

**추가된 검증**:

```python
def _validate_required_keys(self) -> None:
    """필수 설정 키 검증"""
    # inference_rules 필수 키
    required_inference_keys = ["state_rules"]
    for key in required_inference_keys:
        if key not in self.inference_rules:
            raise ValueError(f"필수 키 '{key}'가 없습니다")

    # pattern_thresholds 필수 키
    required_threshold_keys = ["collision", "overload"]
    # ...
```

---

### 2.3 P3: RuleEngine 핵심 테스트 추가

**문제**: RuleEngine 테스트 전무

**해결**: 33개의 단위 테스트 추가

```
tests/unit/test_rule_engine.py

├── TestInferState (9개)
│   ├── test_infer_state_fz_normal_idle
│   ├── test_infer_state_fz_normal_load
│   ├── test_infer_state_fz_warning
│   ├── test_infer_state_fz_critical
│   ├── test_infer_state_fx_normal
│   ├── test_infer_state_fx_warning
│   ├── test_infer_state_unknown_axis
│   ├── test_infer_state_out_of_range
│   └── test_infer_states_multiple
│
├── TestDetectCollision (4개)
│   ├── test_detect_collision_positive
│   ├── test_detect_collision_slow_rise
│   ├── test_detect_collision_small_delta
│   └── test_detect_collision_insufficient_data
│
├── TestDetectOverload (3개)
│   ├── test_detect_overload_positive
│   ├── test_detect_overload_short_duration
│   └── test_detect_overload_below_threshold
│
├── TestPredictError (5개)
│   ├── test_predict_error_frequency_positive
│   ├── test_predict_error_frequency_insufficient
│   ├── test_predict_error_frequency_old_events
│   ├── test_predict_error_trend_increasing_frequency  ← 새 기능 테스트
│   └── test_predict_error_trend_with_intensity        ← 새 기능 테스트
│
├── TestInferCause (3개)
│   ├── test_infer_cause_collision
│   ├── test_infer_cause_with_context_boost
│   └── test_infer_cause_unknown_pattern
│
├── TestYAMLLoadError (5개)
│   ├── test_load_missing_inference_rules
│   ├── test_load_missing_pattern_thresholds
│   ├── test_load_invalid_yaml_syntax
│   ├── test_load_empty_yaml
│   └── test_validate_missing_state_rules
│
├── TestFullInference (2개)
│   ├── test_full_inference_with_collision
│   └── test_full_inference_no_patterns
│
└── TestInferenceResult (2개)
    ├── test_inference_result_creation
    └── test_inference_result_defaults
```

**테스트 결과**:

```
============================= 33 passed in 1.10s ==============================
```

---

## 3. 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| [src/ontology/rule_engine.py](src/ontology/rule_engine.py) | `_evaluate_trend_condition` 추가, YAML 에러 처리 개선, 필수 키 검증 추가 |
| [tests/unit/test_rule_engine.py](tests/unit/test_rule_engine.py) | 33개 단위 테스트 신규 추가 |

---

## 4. 개선 전/후 비교

### 4.1 "trend" 예측 규칙

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    개선 전/후: trend 예측 규칙                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [개선 전]                                                                 │
│  ═════════                                                                  │
│  inference_rules.yaml:                                                     │
│    - name: "VIBRATION_PREDICTION"                                          │
│      condition:                                                            │
│        type: "trend"         ← 설정에 있지만                               │
│        direction: "increasing"                                             │
│                                                                             │
│  rule_engine.py:                                                           │
│    if condition.get("type") == "frequency":                                │
│        # 처리                                                              │
│    # elif "trend": ← 미구현! 조용히 무시됨                                 │
│                                                                             │
│  결과: 진동 증가 추세 → 에러 예측 불가                                     │
│                                                                             │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  [개선 후]                                                                 │
│  ═════════                                                                  │
│  rule_engine.py:                                                           │
│    if condition_type == "frequency":                                       │
│        result = self._evaluate_frequency_condition(...)                    │
│    elif condition_type == "trend":                                         │
│        result = self._evaluate_trend_condition(...)  ← 구현 완료!          │
│                                                                             │
│  _evaluate_trend_condition:                                                │
│    - 빈도 기반: 첫 절반 vs 후 절반 횟수 비교                              │
│    - 강도 기반: intensity 값 평균 변화 감지                                │
│    - 증가/감소 방향 지원                                                   │
│    - threshold_pct 임계값 적용                                             │
│                                                                             │
│  결과: 진동 증가 추세 → C204 에러 예측 가능!                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 YAML 에러 처리

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    개선 전/후: YAML 에러 처리                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [개선 전]                                                                 │
│  ═════════                                                                  │
│  def _load_yaml(path):                                                     │
│      try:                                                                  │
│          return yaml.safe_load(f)                                          │
│      except Exception:                                                     │
│          logger.warning("로드 실패")                                       │
│          return {}  ← 빈 딕셔너리 반환 (조용한 실패)                       │
│                                                                             │
│  결과:                                                                     │
│  - inference_rules.yaml 누락 → 모든 추론 규칙 비활성화                     │
│  - pattern_thresholds.yaml 누락 → 패턴 감지 불가                           │
│  - 사용자는 문제를 인지하지 못함                                           │
│                                                                             │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  [개선 후]                                                                 │
│  ═════════                                                                  │
│  def _load_yaml(path, required=True):                                      │
│      if not path.exists():                                                 │
│          if required:                                                      │
│              raise FileNotFoundError("필수 설정 파일 없음")                │
│      try:                                                                  │
│          data = yaml.safe_load(f)                                          │
│          if data is None and required:                                     │
│              raise ValueError("파일이 비어있음")                           │
│          return data                                                       │
│      except yaml.YAMLError:                                                │
│          raise  ← 예외 전파                                                │
│                                                                             │
│  def _validate_required_keys():                                            │
│      if "state_rules" not in inference_rules:                              │
│          raise ValueError("필수 키 누락")                                  │
│                                                                             │
│  결과:                                                                     │
│  - 파일 누락 → 즉시 FileNotFoundError                                     │
│  - 빈 파일 → 즉시 ValueError                                              │
│  - 필수 키 누락 → 즉시 ValueError                                         │
│  - 서버 시작 시 명확한 에러 메시지                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 테스트 커버리지

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    개선 전/후: 테스트 커버리지                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [개선 전]                                                                 │
│  ═════════                                                                  │
│  tests/unit/                                                               │
│  ├── test_query_classifier.py      (있음)                                  │
│  ├── test_confidence_gate.py       (있음)                                  │
│  ├── test_evidence_schema.py       (있음)                                  │
│  ├── test_graph_traverser.py       (있음)                                  │
│  └── test_rule_engine.py           ❌ 없음                                 │
│                                                                             │
│  RuleEngine 테스트 커버리지: 0%                                            │
│                                                                             │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  [개선 후]                                                                 │
│  ═════════                                                                  │
│  tests/unit/test_rule_engine.py    ✅ 신규 추가                            │
│                                                                             │
│  테스트 항목:                                                              │
│  • 상태 추론 (infer_state): 9개                                            │
│  • 충돌 감지 (detect_collision): 4개                                       │
│  • 과부하 감지 (detect_overload): 3개                                      │
│  • 에러 예측 (predict_error): 5개                                          │
│  • 원인 추론 (infer_cause): 3개                                            │
│  • YAML 에러 처리: 5개                                                     │
│  • 전체 추론 (full_inference): 2개                                         │
│  • 데이터클래스: 2개                                                       │
│                                                                             │
│  총 33개 테스트 | 모두 통과 (1.10s)                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. 사용 예시

### 5.1 trend 예측 사용

```python
from src.ontology.rule_engine import RuleEngine
from datetime import datetime, timedelta

engine = RuleEngine()

# 진동 패턴 이력 (강도가 점점 증가)
now = datetime.now()
pattern_history = [
    {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=6)).isoformat(), "intensity": 0.3},
    {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=5)).isoformat(), "intensity": 0.35},
    {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=3)).isoformat(), "intensity": 0.5},
    {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=2)).isoformat(), "intensity": 0.6},
    {"pattern": "PAT_VIBRATION", "timestamp": (now - timedelta(days=1)).isoformat(), "intensity": 0.7},
]

# 에러 예측
predictions = engine.predict_error(pattern_history)

# 결과
for p in predictions:
    if p.result_id == "C204":
        print(f"예측: {p.result_id}")
        print(f"신뢰도: {p.confidence}")
        print(f"근거: {p.evidence}")
        # 예측: C204
        # 신뢰도: 0.7
        # 근거: {
        #   "condition_type": "trend",
        #   "detection_method": "intensity_based",
        #   "change_pct": 66.7,
        #   "threshold_pct": 20
        # }
```

### 5.2 에러 처리 확인

```python
from pathlib import Path
from src.ontology.rule_engine import RuleEngine

# 잘못된 경로로 초기화 시도
try:
    engine = RuleEngine(
        inference_rules_path=Path("nonexistent.yaml")
    )
except FileNotFoundError as e:
    print(f"에러: {e}")
    # 에러: 필수 설정 파일이 없습니다: nonexistent.yaml
```

---

## 6. 요약

| 항목 | 개선 전 | 개선 후 |
|------|--------|--------|
| **trend 예측** | 미구현 (조용히 무시) | 구현 완료 (빈도+강도 기반) |
| **YAML 에러** | 빈 딕셔너리 반환 | 명시적 예외 발생 |
| **필수 키 검증** | 없음 | `_validate_required_keys()` |
| **테스트 커버리지** | 0개 | 33개 (100% 통과) |

---

*작성일: 2026-01-26*
*Phase: 17 - 온톨로지 시스템 개선*
