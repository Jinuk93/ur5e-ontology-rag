# Step 06: 추론 규칙 - 설계서

## 1. 개요

### 1.1 Phase 정보
- **Phase 번호**: 06
- **Phase 명**: 추론 규칙 (Inference Rules)
- **Stage**: Stage 2 - 온톨로지 핵심 (Ontology Core) ★
- **목표**: 온톨로지 기반 추론 규칙 정의 및 구현

### 1.2 Phase 목표 (Unified_ROADMAP.md 기준)
- 상태 추론 규칙 (Fz 값 → State)
- 패턴 추론 규칙 (센서 데이터 → Pattern)
- 원인 추론 규칙 (Pattern + Context → Cause)
- 예측 규칙 (Pattern 반복 → Error 예측)

### 1.3 핵심 산출물
- `configs/inference_rules.yaml` (추론 규칙 정의)
- `configs/pattern_thresholds.yaml` (패턴 감지 임계값)
- `src/ontology/rule_engine.py` (규칙 엔진)

> 참고: `configs/rules.yaml`은 EntityLinker 규칙(정규화/링킹)으로 별도 용도입니다.

---

## 2. 다룰 파일

### 2.1 핵심 구현 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `src/ontology/rule_engine.py` | 규칙 엔진 클래스 | 완료됨 (340줄) |
| `configs/inference_rules.yaml` | 추론 규칙 정의 | 완료됨 |

> 참고: `configs/rules.yaml`은 EntityLinker용 규칙 파일로 별도 용도입니다.

### 2.2 Phase 5 산출물 (사용)

| 파일 경로 | 역할 |
|-----------|------|
| `data/processed/ontology/ontology.json` | 엔티티/관계 데이터 |
| `src/ontology/loader.py` | 온톨로지 로더 |

---

## 3. 설계 상세

### 3.1 추론 규칙 카테고리

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Inference Rule Categories                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. State Rules (상태 추론)                                             │
│     센서 값 → 상태                                                       │
│     예: Fz = -50N → STATE_NORMAL_LOAD                                   │
│                                                                          │
│  2. Pattern Rules (패턴 추론)                                           │
│     센서 시계열 → 패턴                                                   │
│     예: Fz spike > 500N/100ms → PAT_COLLISION                           │
│                                                                          │
│  3. Cause Rules (원인 추론)                                             │
│     패턴 + 컨텍스트 → 원인                                               │
│     예: PAT_OVERLOAD + SHIFT_B + PART-C → CAUSE_GRIP_POSITION            │
│                                                                          │
│  4. Prediction Rules (예측 추론)                                         │
│     패턴 반복 → 에러 예측                                                │
│     예: PAT_OVERLOAD 3회 연속 → C189 발생 가능성 높음                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 상태 추론 규칙 (State Rules)

#### 3.2.1 Fz 상태 매핑

| State | Fz Range (N) | 설명 | Severity |
|-------|--------------|------|----------|
| STATE_IDLE | [-20, -10] | 유휴 상태 | normal |
| STATE_LIGHT_LOAD | [-40, -20) | 경부하 상태 | normal |
| STATE_NORMAL_LOAD | [-70, -40) | 정상 부하 | normal |
| STATE_HEAVY_LOAD | [-100, -70) | 중부하 상태 | low |
| STATE_WARNING | [-200, -100) | 경고 상태 | medium |
| STATE_CRITICAL | [-235, -200) | 위험 상태 | critical |

#### 3.2.2 규칙 형식

```yaml
state_rules:
  - name: "FZ_STATE_MAPPING"
    axis: "Fz"
    mappings:
      - range: [-20, -10]
        state: "State_Normal"
        label: "유휴"
      - range: [-70, -40]
        state: "State_Normal"
        label: "정상 부하"
      - range: [-200, -100]
        state: "State_Warning"
        label: "경고"
      - range: [-235, -200]
        state: "State_Critical"
        label: "위험"
```

### 3.3 패턴 추론 규칙 (Pattern Rules)

#### 3.3.1 정의된 패턴

| 패턴 ID | 조건 | 신뢰도 | 관련 에러 |
|---------|------|--------|----------|
| PAT_COLLISION | abs(delta_Fz) > 500N in 100ms | 0.95 | C153, C119 |
| PAT_OVERLOAD | Fz > 150N for 5s | 0.90 | C189 |
| PAT_VIBRATION | std(Tx,Ty) > 2x baseline for 10s | 0.70 | C204 |
| PAT_DRIFT | baseline shift > 10% for 30min | 0.80 | - |

#### 3.3.2 규칙 형식

```yaml
pattern_rules:
  - name: "COLLISION_DETECTION"
    pattern_id: "PAT_COLLISION"
    condition:
      type: "spike"
      axis: "Fz"
      threshold: 500
      time_window_ms: 100
    confidence: 0.95
    triggers:
      - error: "C153"
        probability: 0.95
      - error: "C119"
        probability: 0.80

  - name: "OVERLOAD_DETECTION"
    pattern_id: "PAT_OVERLOAD"
    condition:
      type: "sustained"
      axis: "Fz"
      threshold: 150
      duration_s: 5
    confidence: 0.90
    triggers:
      - error: "C189"
        probability: 0.90
```

### 3.4 원인 추론 규칙 (Cause Rules)

#### 3.4.1 패턴 → 원인 매핑

```
PAT_COLLISION
    └──[INDICATES 0.9]──→ CAUSE_COLLISION (물리적 충돌)
    └──[INDICATES 0.7]──→ CAUSE_PROGRAM_ERROR (프로그램 경로 오류)

PAT_OVERLOAD
    └──[INDICATES 0.9]──→ CAUSE_OVERLOAD (하중 초과)
    └──[INDICATES 0.6]──→ CAUSE_GRIP_ERROR (그립 위치 불량)

PAT_VIBRATION
    └──[INDICATES 0.7]──→ CAUSE_JOINT_WEAR (조인트 마모)
    └──[INDICATES 0.65]──→ CAUSE_LOOSE_BOLTS (볼트 풀림)

PAT_DRIFT
    └──[INDICATES 0.8]──→ CAUSE_CALIBRATION (캘리브레이션 필요)
```

#### 3.4.2 규칙 형식

```yaml
cause_rules:
  - name: "COLLISION_CAUSE"
    pattern: "PAT_COLLISION"
    causes:
      - cause: "CAUSE_COLLISION"
        confidence: 0.90
        context_boost:
          - condition: "shift == 'B'"
            boost: 0.05
      - cause: "CAUSE_PROGRAM_ERROR"
        confidence: 0.70

  - name: "OVERLOAD_CAUSE"
    pattern: "PAT_OVERLOAD"
    causes:
      - cause: "CAUSE_OVERLOAD"
        confidence: 0.90
        context_boost:
          - condition: "product.weight_kg > 4.0"
            boost: 0.05
```

### 3.5 예측 추론 규칙 (Prediction Rules)

#### 3.5.1 반복 패턴 기반 예측

```yaml
prediction_rules:
  - name: "OVERLOAD_PREDICTION"
    pattern: "PAT_OVERLOAD"
    condition:
      type: "frequency"
      count: 3
      time_window_days: 4
    prediction:
      error: "C189"
      probability: 0.85
      time_horizon_days: 1

  - name: "VIBRATION_PREDICTION"
    pattern: "PAT_VIBRATION"
    condition:
      type: "trend"
      direction: "increasing"
      threshold_pct: 20
      time_window_days: 7
    prediction:
      error: "C204"
      probability: 0.70
      time_horizon_days: 3
```

---

## 4. rule_engine.py 인터페이스

### 4.1 클래스 구조

```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml

from .loader import load_ontology
from .models import OntologySchema

@dataclass
class InferenceResult:
    """추론 결과"""
    rule_name: str
    result_type: str  # "state", "pattern", "cause", "prediction"
    result_id: str    # 엔티티 ID
    confidence: float
    evidence: Dict[str, Any]

class RuleEngine:
    """온톨로지 기반 추론 규칙 엔진"""

    DEFAULT_RULES_PATH = Path("configs/rules.yaml")

    def __init__(self, rules_path: Optional[Path] = None):
        self.rules = self._load_rules(rules_path)
        self.ontology = load_ontology()

    def infer_state(self, axis: str, value: float) -> Optional[InferenceResult]:
        """센서 값에서 상태 추론"""
        pass

    def detect_pattern(self, data: Dict[str, List[float]]) -> List[InferenceResult]:
        """시계열 데이터에서 패턴 감지"""
        pass

    def infer_cause(self, pattern_id: str, context: Dict) -> List[InferenceResult]:
        """패턴과 컨텍스트에서 원인 추론"""
        pass

    def predict_error(self, pattern_history: List[Dict]) -> List[InferenceResult]:
        """패턴 이력에서 에러 예측"""
        pass
```

### 4.2 사용 예시

```python
from src.ontology.rule_engine import RuleEngine

# 규칙 엔진 초기화
engine = RuleEngine()

# 1. 상태 추론
state = engine.infer_state("Fz", -180.0)
# InferenceResult(rule_name="FZ_STATE", result_type="state",
#                 result_id="State_Warning", confidence=1.0)

# 2. 패턴 감지
data = {"Fz": [-50, -48, 450, -52, -51], "timestamp_ms": [0, 100, 200, 300, 400]}
patterns = engine.detect_pattern(data)
# [InferenceResult(rule_name="COLLISION", result_type="pattern",
#                  result_id="PAT_COLLISION", confidence=0.95)]

# 3. 원인 추론
context = {"shift": "B", "product": {"id": "PART-C", "weight_kg": 4.2}}
causes = engine.infer_cause("PAT_COLLISION", context)
# [InferenceResult(rule_name="COLLISION_CAUSE", result_type="cause",
#                  result_id="CAUSE_COLLISION", confidence=0.95)]

# 4. 에러 예측
history = [
    {"pattern": "PAT_OVERLOAD", "timestamp": "2026-01-20T10:00:00"},
    {"pattern": "PAT_OVERLOAD", "timestamp": "2026-01-21T14:00:00"},
    {"pattern": "PAT_OVERLOAD", "timestamp": "2026-01-22T09:00:00"},
]
predictions = engine.predict_error(history)
# [InferenceResult(rule_name="OVERLOAD_PREDICTION", result_type="prediction",
#                  result_id="C189", confidence=0.85)]
```

---

## 5. configs/rules.yaml 전체 구조

```yaml
# ============================================================
# rules.yaml - 온톨로지 추론 규칙
# ============================================================
version: "1.0"

# ------------------------------------------------------------
# 상태 추론 규칙
# ------------------------------------------------------------
state_rules:
  - name: "FZ_STATE_MAPPING"
    axis: "Fz"
    mappings:
      - range: [-20, -10]
        state: "State_Normal"
      - range: [-40, -20]
        state: "State_Normal"
      - range: [-70, -40]
        state: "State_Normal"
      - range: [-100, -70]
        state: "State_Warning"
      - range: [-200, -100]
        state: "State_Warning"
      - range: [-1000, -200]
        state: "State_Critical"

# ------------------------------------------------------------
# 패턴 추론 규칙
# ------------------------------------------------------------
pattern_rules:
  - name: "COLLISION_DETECTION"
    pattern_id: "PAT_COLLISION"
    condition:
      type: "spike"
      axis: "Fz"
      threshold: 500
      time_window_ms: 100
    confidence: 0.95
    triggers:
      - error: "C153"
        probability: 0.95
      - error: "C119"
        probability: 0.80

  - name: "OVERLOAD_DETECTION"
    pattern_id: "PAT_OVERLOAD"
    condition:
      type: "sustained"
      axis: "Fz"
      threshold: 150
      duration_s: 5
    confidence: 0.90
    triggers:
      - error: "C189"
        probability: 0.90

  - name: "VIBRATION_DETECTION"
    pattern_id: "PAT_VIBRATION"
    condition:
      type: "variance"
      axes: ["Tx", "Ty"]
      multiplier: 2.0
      duration_s: 10
    confidence: 0.70
    triggers:
      - error: "C204"
        probability: 0.75

  - name: "DRIFT_DETECTION"
    pattern_id: "PAT_DRIFT"
    condition:
      type: "drift"
      deviation_pct: 10
      duration_min: 30
    confidence: 0.80

# ------------------------------------------------------------
# 원인 추론 규칙
# ------------------------------------------------------------
cause_rules:
  - pattern: "PAT_COLLISION"
    causes:
      - cause: "CAUSE_COLLISION"
        base_confidence: 0.90
      - cause: "CAUSE_PROGRAM_ERROR"
        base_confidence: 0.70

  - pattern: "PAT_OVERLOAD"
    causes:
      - cause: "CAUSE_OVERLOAD"
        base_confidence: 0.90
      - cause: "CAUSE_GRIP_ERROR"
        base_confidence: 0.60

  - pattern: "PAT_VIBRATION"
    causes:
      - cause: "CAUSE_JOINT_WEAR"
        base_confidence: 0.70
      - cause: "CAUSE_LOOSE_BOLTS"
        base_confidence: 0.65

  - pattern: "PAT_DRIFT"
    causes:
      - cause: "CAUSE_CALIBRATION"
        base_confidence: 0.80

# ------------------------------------------------------------
# 예측 추론 규칙
# ------------------------------------------------------------
prediction_rules:
  - name: "OVERLOAD_PREDICTION"
    pattern: "PAT_OVERLOAD"
    condition:
      count: 3
      time_window_days: 4
    prediction:
      error: "C189"
      probability: 0.85

  - name: "PREDICT_C189"
    pattern: "PAT_OVERLOAD"
    condition:
      count: 3
      time_window_days: 4
      same_time_window: true
      same_product: true
      trend: "increasing"
    prediction:
      error: "C189"
      probability: 0.85
      timeframe: "24h"

  - name: "COLLISION_PREDICTION"
    pattern: "PAT_COLLISION"
    condition:
      count: 2
      time_window_days: 1
    prediction:
      error: "C153"
      probability: 0.90

  - name: "VIBRATION_PREDICTION"
    pattern: "PAT_VIBRATION"
    condition:
      trend: "increasing"
      threshold_pct: 20
      time_window_days: 7
    prediction:
      error: "C204"
      probability: 0.70
```

---

## 6. 온톨로지 연결

### 6.1 Phase 5 (엔티티/관계)와의 연결

| Phase 5 산출물 | Phase 6 사용처 |
|---------------|---------------|
| State 엔티티 | state_rules 결과 |
| Pattern 엔티티 | pattern_rules 결과 |
| INDICATES 관계 | cause_rules 근거 |
| TRIGGERS 관계 | prediction_rules 근거 |

### 6.2 Phase 7-9 (센서)와의 연결

| Phase 6 산출물 | Phase 7-9 사용처 |
|---------------|-----------------|
| pattern_rules | PatternDetector |
| state_rules | 실시간 상태 판단 |
| prediction_rules | 예방적 유지보수 |

### 6.3 Phase 10-12 (RAG)와의 연결

| Phase 6 산출물 | RAG 사용처 |
|---------------|------------|
| RuleEngine.infer_state() | 상태 질문 응답 |
| RuleEngine.infer_cause() | 원인 분석 응답 |
| RuleEngine.predict_error() | 예측 응답 |

---

## 7. Unified_Spec.md 정합성 검증

### 7.1 추론 규칙 요구사항

| Spec 요구사항 | Phase 6 구현 내용 | 충족 여부 |
|--------------|------------------|----------|
| 상태 추론 | state_rules | O |
| 패턴 감지 | pattern_rules | O |
| 원인 추론 | cause_rules + INDICATES 관계 | O |
| 에러 예측 | prediction_rules + TRIGGERS 관계 | O |

### 7.2 추론 흐름

```
센서 값 ──→ State Rules ──→ 현재 상태
    │
    └──→ Pattern Rules ──→ 패턴 감지
              │
              └──→ Cause Rules ──→ 원인 추론
                        │
                        └──→ Resolution (ontology.json)
```

---

## 8. 구현 체크리스트

### 8.1 코드 구현

- [x] `src/ontology/rule_engine.py` - RuleEngine 클래스 (340줄)
- [x] `configs/rules.yaml` - 추론 규칙 정의
- [x] `src/ontology/__init__.py` - RuleEngine 모듈 노출

### 8.2 검증 명령어

```python
from src.ontology.rule_engine import RuleEngine

engine = RuleEngine()

# 상태 추론 테스트
state = engine.infer_state("Fz", -180.0)
print(f"State: {state.result_id}")  # State_Warning

# 원인 추론 테스트
causes = engine.infer_cause("PAT_COLLISION", {})
print(f"Causes: {[c.result_id for c in causes]}")
```

---

## 9. 설계 결정 사항

### 9.1 규칙 형식: YAML

**결정**: YAML 파일로 규칙 정의

**근거**:
1. 가독성: JSON보다 읽기 쉬움
2. 주석 지원: 규칙 설명 가능
3. 유지보수: 비개발자도 수정 가능

### 9.2 규칙 분리

**결정**: 규칙 유형별 분리 (state, pattern, cause, prediction)

**근거**:
1. 관심사 분리: 각 규칙 유형의 독립적 관리
2. 확장성: 새 규칙 유형 추가 용이
3. 테스트 용이: 개별 규칙 테스트 가능

---

## 10. 다음 Phase 연결

### Phase 7-9 (센서 통합)와의 연결

| Phase 6 산출물 | Phase 7-9 사용처 |
|---------------|-----------------|
| pattern_rules | 패턴 감지 임계값 |
| state_rules | 실시간 상태 판단 |
| RuleEngine | 패턴 감지 시 호출 |

---

## 11. 현재 구현 현황 (참고)

### 11.1 최종 파일 목록

| 파일 | 라인 수 | 설명 |
|------|--------|------|
| `src/ontology/rule_engine.py` | 340 | RuleEngine 클래스 |
| `configs/inference_rules.yaml` | 180 | 추론 규칙 정의 |
| `configs/pattern_thresholds.yaml` | 106 | 패턴 감지 임계값 (기존) |

### 11.2 테스트 결과

```python
engine = create_rule_engine()
state = engine.infer_state("Fz", -180.0)
# State: State_Warning (confidence: 100%)

causes = engine.infer_cause("PAT_COLLISION", {})
# CAUSE_COLLISION (90%), CAUSE_PROGRAM_ERROR (70%)
```

---

## 12. 문서 정보

| 항목 | 값 |
|------|---|
| 문서 버전 | v2.0 |
| 작성일 | 2026-01-22 |
| 최종 갱신일 | 2026-01-22 |
| 완료 보고서 | [step_06_추론규칙_완료.md](step_06_추론규칙_완료.md) |
| ROADMAP 섹션 | A.2 Phase 6 |
| Spec 섹션 | 2.2, 12.3 |
