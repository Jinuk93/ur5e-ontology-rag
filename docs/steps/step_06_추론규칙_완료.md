# Step 06: 추론 규칙 - 완료 보고서

## 1. 요약

| 항목 | 내용 |
|------|------|
| Phase | 06 - 추론 규칙 (Inference Rules) |
| 상태 | **완료** |

---

## 2. 완료된 작업

### 2.1 구현 파일 목록

| 파일 | 라인 수 | 상태 | 설명 |
|------|--------|------|------|
| `src/ontology/rule_engine.py` | 503 | 신규 작성 | RuleEngine 클래스 |
| `configs/inference_rules.yaml` | 211 | 신규 작성 | 추론 규칙 정의 |
| `src/ontology/__init__.py` | 89 | 업데이트 | RuleEngine 노출 |

### 2.2 기존 설정 파일 (활용)

| 파일 | 역할 |
|------|------|
| `configs/pattern_thresholds.yaml` | 패턴 감지 임계값 |

---

## 3. 구현 상세

### 3.1 RuleEngine 클래스 구조

```python
class RuleEngine:
    """온톨로지 기반 추론 규칙 엔진"""

    def infer_state(self, axis: str, value: float) -> Optional[InferenceResult]:
        """센서 값 → 상태 추론"""

    def detect_collision(self, fz_values, timestamps_ms) -> Optional[InferenceResult]:
        """충돌 패턴 감지"""

    def detect_overload(self, fz_values, timestamps_s) -> Optional[InferenceResult]:
        """과부하 패턴 감지"""

    def detect_patterns(self, data: Dict) -> List[InferenceResult]:
        """모든 패턴 감지"""

    def infer_cause(self, pattern_id: str, context: Dict) -> List[InferenceResult]:
        """패턴 → 원인 추론"""

    def predict_error(self, pattern_history: List) -> List[InferenceResult]:
        """패턴 이력 → 에러 예측"""

    def get_resolution(self, cause_id: str) -> List[InferenceResult]:
        """원인 → 해결책 조회"""

    def full_inference(self, sensor_data, context) -> Dict:
        """전체 추론 체인"""
```

### 3.2 InferenceResult 데이터클래스

```python
@dataclass
class InferenceResult:
    rule_name: str       # 규칙 이름
    result_type: str     # "state", "pattern", "cause", "prediction"
    result_id: str       # 엔티티 ID
    confidence: float    # 신뢰도 (0~1)
    evidence: Dict       # 근거 정보
    message: str         # 사람이 읽을 수 있는 메시지
```

### 3.3 추론 규칙 구조 (inference_rules.yaml)

```yaml
# 상태 추론 규칙
state_rules:
  - name: "FZ_STATE_MAPPING"
    axis: "Fz"
    mappings:
      - range: [-20, -10]
        state: "State_Normal"
        label: "유휴"
      - range: [-200, -100]
        state: "State_Warning"
        label: "경고"
      - range: [-1000, -500]
        state: "State_Critical"
        label: "위험"

# 원인 추론 규칙
cause_rules:
  - pattern: "PAT_COLLISION"
    causes:
      - cause_id: "CAUSE_COLLISION"
        base_confidence: 0.90

# 예측 추론 규칙
prediction_rules:
  - name: "OVERLOAD_PREDICTION"
    pattern: "PAT_OVERLOAD"
    condition:
      count: 3
      time_window_days: 4
    prediction:
      error_id: "C189"
      probability: 0.85
      time_horizon: "24h"
```

---

## 4. 사용법

### 4.1 기본 사용

```python
from src.ontology import RuleEngine, create_rule_engine

# 규칙 엔진 초기화
engine = create_rule_engine()

# 상태 추론
state = engine.infer_state("Fz", -180.0)
# InferenceResult(result_id="State_Warning", confidence=1.0)

# 원인 추론
causes = engine.infer_cause("PAT_COLLISION", {})
# [InferenceResult(result_id="CAUSE_COLLISION", confidence=0.90), ...]

# 해결책 조회
resolutions = engine.get_resolution("CAUSE_COLLISION")
# [InferenceResult(result_id="RES_CLEAR_PATH", ...)]
```

### 4.2 전체 추론 체인

```python
# 센서 데이터 → 패턴 → 원인 → 해결책
sensor_data = {
    "Fz": [-50, -48, 450, -52, -51],
    "timestamp_ms": [0, 100, 200, 300, 400]
}

results = engine.full_inference(sensor_data, context={})

print(f"Patterns: {len(results['patterns'])}")
print(f"Causes: {len(results['causes'])}")
print(f"Resolutions: {len(results['resolutions'])}")
```

### 4.3 에러 예측

```python
history = [
    {"pattern": "PAT_OVERLOAD", "timestamp": "2026-01-20T10:00:00"},
    {"pattern": "PAT_OVERLOAD", "timestamp": "2026-01-21T14:00:00"},
    {"pattern": "PAT_OVERLOAD", "timestamp": "2026-01-22T09:00:00"},
]

predictions = engine.predict_error(history)
# C189 에러 발생 가능성 85%
```

---

## 5. 테스트 결과

```
=== State Inference Test ===
  State: State_Warning
  Message: Fz=-180.0N → 중부하

=== Cause Inference Test ===
  Cause: CAUSE_COLLISION (confidence: 90%)
  Cause: CAUSE_PROGRAM_ERROR (confidence: 70%)

=== Resolution Lookup Test ===
  Resolution: RES_CLEAR_PATH
  Message: 해결책: 경로 확보

=== RuleEngine Test Complete ===
```

---

## 6. 아키텍처 정합성

### 6.1 Unified_ROADMAP.md 충족 사항

| ROADMAP 요구사항 | 구현 내용 | 상태 |
|-----------------|----------|------|
| 상태 추론 규칙 | infer_state(), state_rules | O |
| 패턴 추론 규칙 | detect_patterns() | O |
| 원인 추론 규칙 | infer_cause(), cause_rules | O |
| 예측 규칙 | predict_error(), prediction_rules | O |

### 6.2 온톨로지 연결

| 온톨로지 요소 | RuleEngine 사용처 |
|-------------|-----------------|
| State 엔티티 | infer_state() 결과 |
| Pattern 엔티티 | detect_patterns() 결과 |
| INDICATES 관계 | cause_rules 근거 |
| RESOLVED_BY 관계 | get_resolution() 조회 |
| TRIGGERS 관계 | pattern_error_mapping |

---

## 7. 폴더 구조

```
ur5e-ontology-rag/
├── configs/
│   ├── inference_rules.yaml          # Phase 6: 추론 규칙
│   └── pattern_thresholds.yaml       # 패턴 임계값 (선택)
│
└── src/
    └── ontology/
        ├── __init__.py [업데이트]    # RuleEngine 노출
        ├── rule_engine.py [신규]     # 추론 규칙 엔진
        ├── loader.py
        ├── models.py
        └── schema.py
```

---

## 8. 다음 단계 준비

### Phase 7-9 (센서 통합)와의 연결

| Phase 6 산출물 | Phase 7-9 사용처 |
|---------------|-----------------|
| RuleEngine.detect_patterns() | PatternDetector |
| RuleEngine.infer_state() | 실시간 상태 판단 |
| pattern_thresholds.yaml | 패턴 감지 임계값 |

### Phase 10-12 (RAG)와의 연결

| Phase 6 산출물 | RAG 사용처 |
|---------------|------------|
| RuleEngine.infer_cause() | 원인 분석 응답 |
| RuleEngine.get_resolution() | 해결책 제안 |
| RuleEngine.full_inference() | 종합 분석 |

---

## 9. 이슈 및 참고사항

### 9.1 해결된 이슈

없음 - 구현 완료

### 9.2 설계 결정

1. **규칙 파일 기준**: Phase 6 추론 규칙은 `configs/inference_rules.yaml`에 정의
2. **기존 설정 활용**: pattern_thresholds.yaml 재사용
3. **YAML 형식**: 가독성과 유지보수 용이

### 9.3 검증 명령어

```python
from src.ontology import create_rule_engine

engine = create_rule_engine()
state = engine.infer_state("Fz", -180.0)
print(f"State: {state.result_id}")  # State_Warning
```

---

## 10. 리팩토링 수행 내역

### 10.1 설계서 업데이트 (v1.0 → v2.0)

| 추가/변경 섹션 | 내용 |
|---------------|------|
| 구현 상태 업데이트 | "신규 작성" → "완료됨 (X줄)" 상태 반영 |
| 체크리스트 완료 | [ ] → [x] 모든 항목 완료 표시 |
| 실제 구현 결과 | Section 11 추가 |

### 10.2 코드 리팩토링

추가 리팩토링 불필요 - 초기 구현 완료

---

## 11. 문서 정보

| 항목 | 값 |
|------|---|
| 문서 버전 | v2.0 |
| 설계서 참조 | [step_06_추론규칙_설계.md](step_06_추론규칙_설계.md) |
| ROADMAP 섹션 | A.2 Phase 6 |
| Spec 섹션 | 2.2, 12.3 |

---

*Phase 06 완료. Phase 07 (센서 데이터 처리)로 진행합니다.*
