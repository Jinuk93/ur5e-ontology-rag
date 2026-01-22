# Step 08: 패턴 감지 - 완료 보고서

## 1. 완료 요약

| 항목 | 내용 |
|------|------|
| Phase | 08 - 패턴 감지 (Pattern Detection) |
| 상태 | ✅ 완료 |
| 완료일 | 2026-01-22 |
| 이전 단계 | Phase 07 - 센서 데이터 처리 |
| 다음 단계 | Phase 09 - 온톨로지 연결 |

---

## 2. 구현 파일 목록

| 파일 | 라인 수 | 설명 |
|------|---------|------|
| `src/sensor/patterns.py` | 92 | 패턴 데이터 모델 |
| `src/sensor/pattern_detector.py` | 629 | 패턴 감지 엔진 (+ 절대값 모드 fallback) |
| `src/sensor/__init__.py` | 73 | 모듈 노출 (업데이트) |
| **합계** | **794** | |

---

## 3. 구현 내용

### 3.1 패턴 데이터 모델 (patterns.py)

#### PatternType Enum
```python
class PatternType(Enum):
    COLLISION = "collision"    # 충돌 (급격한 피크)
    OVERLOAD = "overload"      # 과부하 (임계값 초과 지속)
    DRIFT = "drift"            # 드리프트 (baseline 이동)
    VIBRATION = "vibration"    # 진동 (표준편차 증가)
```

#### DetectedPattern 데이터클래스
```python
@dataclass
class DetectedPattern:
    pattern_id: str                   # PAT-001, PAT-002, ...
    pattern_type: PatternType         # 패턴 타입
    timestamp: datetime               # 패턴 발생 시각
    duration_ms: int                  # 지속 시간 (ms)
    confidence: float                 # 신뢰도 (0.0 ~ 1.0)
    metrics: Dict[str, Any]           # 패턴별 메트릭
    related_error_codes: List[str]    # 관련 에러 코드
    event_id: str                     # 이벤트 ID
    context: Dict[str, Any]           # 컨텍스트 정보
```

### 3.2 PatternDetector 클래스

```python
class PatternDetector:
    """패턴 감지 엔진"""

    # 감지 임계값
    COLLISION_THRESHOLD = -350.0      # Fz 충돌 임계값 (N)
    OVERLOAD_THRESHOLD = 300.0        # Fz 과부하 임계값 (N)
    DRIFT_THRESHOLD_PCT = 10.0        # Baseline 대비 변화율 (%)
    VIBRATION_STD_MULTIPLIER = 3.0    # 표준편차 증가 배수

    def __init__(self, sensor_store: SensorStore)
    def detect_all(self, axis: str = "Fz") -> List[DetectedPattern]
    def detect_collision(self, axis: str = "Fz") -> List[DetectedPattern]
    def detect_overload(self, axis: str = "Fz") -> List[DetectedPattern]
    def detect_drift(self, axis: str = "Fz") -> List[DetectedPattern]
    def detect_vibration(self, axis: str = "Fz") -> List[DetectedPattern]
    def load_existing_patterns(self) -> List[DetectedPattern]
    def save_patterns(self, patterns: List[DetectedPattern]) -> None
    def get_patterns_by_type(self, pattern_type: PatternType) -> List[DetectedPattern]
    def get_patterns_in_range(self, start: datetime, end: datetime) -> List[DetectedPattern]
    def get_summary(self) -> dict
```

---

## 4. 테스트 결과

### 4.1 기존 패턴 로드 테스트

```
=== PatternDetector Test ===
Records: 604800
Existing patterns: 17
```

✅ 17개 기존 패턴 정상 로드

### 4.2 패턴 타입별 분류

```
  collision: 2
  overload: 4
  drift: 11
  vibration: 0
```

✅ 타입별 분류 정상 동작

### 4.3 패턴 요약 통계

```python
{
    'total_patterns': 17,
    'by_type': {
        'collision': {'count': 2, 'avg_confidence': 1.0},
        'overload': {'count': 4, 'avg_confidence': 1.0},
        'drift': {'count': 11, 'avg_confidence': 0.985}
    }
}
```

### 4.4 충돌 패턴 상세

```python
DetectedPattern(
    id=PAT-001,
    type=collision,
    timestamp=2024-01-17T14:00:00,
    confidence=1.00
)
Metrics: {
    'peak_axis': 'Fz',
    'peak_value': -829.24,
    'baseline': -20.46,
    'deviation': 808.78
}
Error codes: ['C153', 'C119']
```

---

## 5. 감지 알고리즘 상세

> **참고**: 현재 구현은 Axia80 센서 데이터에 최적화된 하드코딩 임계값을 사용합니다.
> 범용 설정 파일(`configs/pattern_thresholds.yaml`)과 값이 다를 수 있습니다.

### 5.1 Collision 감지

| 항목 | 값 |
|------|-----|
| 임계값 | Fz < -350 N |
| 방식 | 급격한 음수 피크 감지 |
| Baseline | 피크 ±5초 평균 |
| 관련 에러 | C153, C119 |

### 5.2 Overload 감지

| 항목 | 값 |
|------|-----|
| 임계값 | \|Fz\| > 300 N |
| 최소 지속 | 5초 이상 |
| 방식 | 연속 구간 그룹핑 |
| 관련 에러 | C189 |

### 5.3 Drift 감지

| 항목 | 값 |
|------|-----|
| 윈도우 | 1시간 |
| 임계값 (퍼센트 모드) | Baseline 대비 10% 변화 |
| 임계값 (절대값 모드) | 5.0 N |
| 최소 지속 | 1시간 이상 |
| 방식 | Resampling + 변화율 계산 |

> **절대값 모드 Fallback**: Baseline이 1.0N 미만인 축(Fx, Fy 등)에서는 퍼센트 기반 계산이 의미없으므로, 자동으로 절대값 모드로 전환됩니다. 이 경우 `metrics.detection_mode = "absolute"`로 기록됩니다.

### 5.4 Vibration 감지

| 항목 | 값 |
|------|-----|
| 윈도우 | 60초 |
| 임계값 | 전역 표준편차 × 3 |
| 방식 | Rolling 표준편차 |

---

## 6. 에러 코드 매핑

### 6.1 기본 매핑 (DEFAULT_ERROR_MAPPING)

```python
{
    PatternType.COLLISION: ["C153", "C119"],  # 보호 정지, 관절 위치 이탈
    PatternType.OVERLOAD: ["C189"],            # 과부하 감지
    PatternType.DRIFT: [],                     # 경고 수준
    PatternType.VIBRATION: [],                 # 경고 수준
}
```

### 6.2 기존 패턴 데이터 분석

| 패턴 타입 | 관련 에러 코드 |
|----------|---------------|
| collision | C153, C119 |
| overload | C189 |
| drift | (없음) |

---

## 7. 체크리스트 완료

### 7.1 구현 항목

- [x] `src/sensor/patterns.py` 구현
  - [x] PatternType Enum
  - [x] DetectedPattern 데이터클래스
  - [x] DEFAULT_ERROR_MAPPING
- [x] `src/sensor/pattern_detector.py` 구현
  - [x] detect_collision()
  - [x] detect_overload()
  - [x] detect_drift() (+ 절대값 모드 fallback)
  - [x] detect_vibration()
  - [x] detect_all()
  - [x] detect() (호환성 메서드)
  - [x] load_existing_patterns()
  - [x] save_patterns()
  - [x] get_patterns_by_type()
  - [x] get_patterns_in_range()
  - [x] get_summary()
- [x] `src/sensor/__init__.py` 업데이트

### 7.2 검증 항목

- [x] 기존 17개 패턴 정상 로드
- [x] 패턴 타입별 분류 정확성
- [x] SensorStore 연동 정상 동작
- [x] JSON 직렬화/역직렬화

---

## 8. 폴더 구조 (Phase 8 완료)

```
ur5e-ontology-rag/
├── data/
│   └── sensor/
│       └── processed/
│           └── detected_patterns.json  # 17개 패턴
│
└── src/
    └── sensor/
        ├── __init__.py          [73줄, 업데이트]
        ├── data_loader.py       [138줄, Phase 7]
        ├── sensor_store.py      [265줄, Phase 7]
        ├── patterns.py          [92줄, 신규]
        └── pattern_detector.py  [629줄, 신규]
```

---

## 9. 다음 단계 (Phase 9)

### Phase 9 (온톨로지 연결)에서의 활용

```python
from src.sensor import PatternDetector, PatternType
from src.sensor.ontology_connector import OntologyConnector

detector = PatternDetector(store)
patterns = detector.load_existing_patterns()

# 온톨로지 연결
connector = OntologyConnector()

for pattern in patterns:
    # 패턴 → 에러코드 매핑
    error_codes = connector.map_pattern_to_errors(pattern)

    # 패턴 → 원인 매핑
    causes = connector.map_pattern_to_causes(pattern)

    # INDICATES, TRIGGERS 관계 생성
    connector.create_relationships(pattern, error_codes, causes)
```

### Phase 9 구현 예정 파일

- `configs/error_pattern_mapping.yaml`
- `src/sensor/ontology_connector.py`

---

## 10. 문서 정보

| 항목 | 값 |
|------|------|
| 문서 버전 | v1.0 |
| 작성일 | 2026-01-22 |
| ROADMAP 섹션 | Stage 3, Phase 8 |
| Spec 섹션 | 8.3 패턴 감지 |
