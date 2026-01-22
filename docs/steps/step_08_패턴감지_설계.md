# Step 08: 패턴 감지 - 설계서

## 1. 개요

| 항목 | 내용 |
|------|------|
| Phase | 08 - 패턴 감지 (Pattern Detection) |
| 목표 | 센서 데이터에서 이상 패턴 자동 감지 |
| 이전 단계 | Phase 07 - 센서 데이터 처리 |
| 다음 단계 | Phase 09 - 온톨로지 연결 |
| ROADMAP 섹션 | Stage 3: Sensor Integration |

---

## 2. 요구사항 분석

### 2.1 Unified_ROADMAP.md 요구사항

| 요구사항 | 설명 |
|----------|------|
| Collision 감지 | 급격한 변화 (피크 값 감지) |
| Overload 감지 | 임계값 초과 지속 |
| Vibration 감지 | 표준편차 증가 |
| Drift 감지 | baseline 이동 |

### 2.2 기존 패턴 데이터 분석

`data/sensor/processed/detected_patterns.json` 분석:

| 패턴 타입 | 개수 | 특징 |
|----------|------|------|
| collision | 2 | peak_value: -829 ~ -815 N |
| overload | 4 | max_value: 327 ~ 394 N |
| drift | 11 | drift_amount: ±1.6 ~ 3.0 |
| **합계** | **17** | |

### 2.3 패턴별 특성

#### Collision 패턴
```json
{
  "pattern_type": "collision",
  "metrics": {
    "peak_axis": "Fz",
    "peak_value": -829.24,
    "baseline": -20.46,
    "deviation": 808.78
  },
  "related_error_codes": ["C153", "C119"]
}
```

#### Overload 패턴
```json
{
  "pattern_type": "overload",
  "metrics": {
    "axis": "Fz",
    "max_value": 369.01,
    "mean_value": 369.01,
    "duration_s": 22
  },
  "related_error_codes": ["C189"]
}
```

#### Drift 패턴
```json
{
  "pattern_type": "drift",
  "metrics": {
    "baseline": -15.99,
    "drift_amount": -1.60,
    "deviation_pct": 42.97,
    "duration_hours": 16.24
  }
}
```

---

## 3. 설계

### 3.1 구현 파일 목록

| 파일 | 설명 |
|------|------|
| `src/sensor/pattern_detector.py` | 패턴 감지 엔진 |
| `src/sensor/patterns.py` | 패턴 데이터 모델 |
| `src/sensor/__init__.py` | 모듈 노출 업데이트 |

### 3.2 데이터 모델 설계

#### DetectedPattern

```python
@dataclass
class DetectedPattern:
    """감지된 패턴"""
    pattern_id: str                   # PAT-001, PAT-002, ...
    pattern_type: PatternType         # collision, overload, drift, vibration
    timestamp: datetime               # 패턴 발생 시각
    duration_ms: int                  # 지속 시간 (ms)
    confidence: float                 # 신뢰도 (0.0 ~ 1.0)
    metrics: Dict[str, Any]           # 패턴별 메트릭
    related_error_codes: List[str]    # 관련 에러 코드
    event_id: str                     # 이벤트 ID
    context: Dict[str, Any]           # 컨텍스트 정보
```

#### PatternType

```python
class PatternType(Enum):
    COLLISION = "collision"   # 충돌
    OVERLOAD = "overload"     # 과부하
    DRIFT = "drift"           # 드리프트
    VIBRATION = "vibration"   # 진동
```

### 3.3 PatternDetector 클래스 설계

```python
class PatternDetector:
    """패턴 감지 엔진"""

    # 감지 임계값 설정
    COLLISION_THRESHOLD = -350.0      # Fz 충돌 임계값 (N)
    OVERLOAD_THRESHOLD = 300.0        # Fz 과부하 임계값 (N)
    DRIFT_THRESHOLD = 10.0            # Baseline 대비 변화율 (%)
    VIBRATION_STD_THRESHOLD = 5.0     # 표준편차 증가 임계값

    def __init__(self, sensor_store: SensorStore):
        """초기화"""

    def detect_all(self) -> List[DetectedPattern]:
        """모든 패턴 감지"""

    def detect_collision(self) -> List[DetectedPattern]:
        """충돌 패턴 감지
        - 급격한 음수 피크 감지
        - Fz < COLLISION_THRESHOLD
        """

    def detect_overload(self) -> List[DetectedPattern]:
        """과부하 패턴 감지
        - 임계값 초과 지속
        - |Fz| > OVERLOAD_THRESHOLD, duration > 5s
        """

    def detect_drift(self) -> List[DetectedPattern]:
        """드리프트 패턴 감지
        - Baseline 대비 지속적 이동
        - 시간 윈도우별 평균 변화
        """

    def detect_vibration(self) -> List[DetectedPattern]:
        """진동 패턴 감지
        - 표준편차 급격 증가
        - Rolling std > threshold
        """

    def load_existing_patterns(self) -> List[DetectedPattern]:
        """기존 감지 패턴 로드"""

    def save_patterns(self, patterns: List[DetectedPattern]) -> None:
        """패턴 저장"""
```

### 3.4 감지 알고리즘

#### Collision 감지
```python
def detect_collision(self, axis: str = "Fz") -> List[DetectedPattern]:
    """
    1. 데이터에서 threshold 미만 값 찾기
    2. 피크 값 주변 baseline 계산
    3. deviation = |peak - baseline|
    4. 연속 이벤트 그룹핑
    """
    data = self._store.get_data()
    peaks = data[data[axis] < self.COLLISION_THRESHOLD]
    # 피크별 패턴 생성
```

#### Overload 감지
```python
def detect_overload(self, axis: str = "Fz", min_duration_s: float = 5.0):
    """
    1. |value| > threshold 구간 찾기
    2. 연속 구간 그룹핑
    3. duration > min_duration_s 필터
    4. 평균/최대값 계산
    """
```

#### Drift 감지
```python
def detect_drift(self, window_hours: float = 1.0, threshold_pct: float = 10.0):
    """
    1. 시간 윈도우별 평균 계산
    2. 전체 baseline 대비 변화율 계산
    3. threshold_pct 초과 구간 식별
    4. 연속 구간 그룹핑
    """
```

---

## 4. SensorStore 연동

### 4.1 Phase 7에서 구현된 API 활용

```python
from src.sensor import SensorStore, create_sensor_store

store = create_sensor_store()

# 패턴 감지용 데이터 조회
data = store.get_data(start=start_time, end=end_time)

# 이상치 기반 패턴 후보
anomalies = store.get_anomalies("Fz", threshold=300)

# 이벤트 스니펫 (패턴 분석용)
snippet = store.get_window(center=event_time, window_seconds=5.0)

# 컨텍스트 정보
context = store.get_context_at(event_time)
```

### 4.2 통합 예시

```python
from src.sensor import SensorStore, PatternDetector

store = SensorStore()
detector = PatternDetector(store)

# 모든 패턴 감지
patterns = detector.detect_all()

# 특정 패턴만 감지
collisions = detector.detect_collision()
overloads = detector.detect_overload()
```

---

## 5. 온톨로지 연결 (Phase 9 준비)

### 5.1 Pattern 엔티티 타입

기존 온톨로지의 Pattern 타입 활용:

```python
# src/ontology/schema.py
class EntityType(Enum):
    PATTERN = "Pattern"  # Measurement Domain
```

### 5.2 관계 매핑 (Phase 9에서 구현)

| 패턴 타입 | 관계 | 타겟 |
|----------|------|------|
| collision | TRIGGERS | C153, C119 |
| overload | TRIGGERS | C189 |
| drift | INDICATES | CAUSE_SENSOR_DRIFT |
| vibration | INDICATES | CAUSE_VIBRATION |

---

## 6. 체크리스트

### 6.1 구현 항목

- [ ] `src/sensor/patterns.py` 구현
  - [ ] PatternType Enum
  - [ ] DetectedPattern 데이터클래스
- [ ] `src/sensor/pattern_detector.py` 구현
  - [ ] detect_collision()
  - [ ] detect_overload()
  - [ ] detect_drift()
  - [ ] detect_vibration()
  - [ ] detect_all()
  - [ ] load_existing_patterns()
  - [ ] save_patterns()
- [ ] `src/sensor/__init__.py` 업데이트
- [ ] 단위 테스트

### 6.2 검증 항목

- [ ] 기존 17개 패턴 정상 로드
- [ ] 각 패턴 타입별 감지 정확성
- [ ] SensorStore 연동 정상 동작

---

## 7. 폴더 구조 (Phase 8 완료 후)

```
ur5e-ontology-rag/
├── data/
│   └── sensor/
│       └── processed/
│           └── detected_patterns.json  # 17개 + 신규 감지
│
└── src/
    └── sensor/
        ├── __init__.py          [업데이트]
        ├── data_loader.py       [Phase 7]
        ├── sensor_store.py      [Phase 7]
        ├── patterns.py          [신규]
        └── pattern_detector.py  [신규]
```

---

## 8. 다음 단계 연결

### Phase 9 (온톨로지 연결)에서의 활용

```python
from src.sensor import PatternDetector
from src.sensor.ontology_connector import OntologyConnector

detector = PatternDetector(store)
patterns = detector.detect_all()

# 온톨로지 연결
connector = OntologyConnector()
for pattern in patterns:
    # 패턴 → 에러코드 매핑
    error_codes = connector.map_pattern_to_errors(pattern)
    # 관계 그래프 업데이트
    connector.update_relationships(pattern, error_codes)
```

---

## 9. 문서 정보

| 항목 | 값 |
|------|------|
| 문서 버전 | v1.0 |
| 작성일 | 2026-01-22 |
| ROADMAP 섹션 | Stage 3, Phase 8 |
| Spec 섹션 | 8.2 센서 데이터, 8.3 패턴 감지 |
