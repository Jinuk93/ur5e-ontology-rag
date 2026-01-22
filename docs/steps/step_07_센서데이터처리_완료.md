# Step 07: 센서 데이터 처리 - 완료 보고서

## 1. 완료 요약

| 항목 | 내용 |
|------|------|
| Phase | 07 - 센서 데이터 처리 (Sensor Data Processing) |
| 상태 | ✅ 완료 |
| 완료일 | 2026-01-22 |
| 이전 단계 | Phase 06 - 추론 규칙 |
| 다음 단계 | Phase 08 - 패턴 감지 |

---

## 2. 구현 파일 목록

| 파일 | 라인 수 | 설명 |
|------|---------|------|
| `src/sensor/data_loader.py` | 125 | Parquet 데이터 로드 및 전처리 |
| `src/sensor/sensor_store.py` | 251 | 센서 데이터 저장소 및 조회 API |
| `src/sensor/__init__.py` | 42 | 모듈 노출 |
| **합계** | **418** | |

---

## 3. 구현 내용

### 3.1 DataLoader 클래스

```python
class DataLoader:
    """센서 데이터 로더"""

    DEFAULT_PATH = Path("data/sensor/raw/axia80_week_01.parquet")
    SENSOR_AXES = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]
    CONTEXT_COLUMNS = ["task_mode", "work_order_id", "product_id", ...]

    @classmethod
    def load(cls, path=None, use_cache=True) -> pd.DataFrame

    @classmethod
    def preprocess(cls, df: pd.DataFrame) -> pd.DataFrame

    @classmethod
    def get_time_range(cls, df) -> Tuple[datetime, datetime]
```

**주요 기능:**
- Parquet 파일 로드 (캐시 지원)
- 타임스탬프 파싱 및 정렬
- 결측치 처리 (선형 보간)
- 컨텍스트 컬럼 지원 (task_mode, shift, product_id 등)

### 3.2 SensorStore 클래스

```python
class SensorStore:
    """센서 데이터 저장소"""

    def __init__(self, data: Optional[pd.DataFrame] = None)

    def get_data(self, start=None, end=None, axes=None) -> pd.DataFrame

    def get_statistics(self, axis, start=None, end=None) -> Dict[str, Any]

    def get_current_state(self) -> Dict[str, str]

    def get_anomalies(self, axis, threshold, direction="absolute") -> pd.DataFrame

    def get_window(self, center, window_seconds=5.0) -> pd.DataFrame

    def get_context_at(self, timestamp) -> Dict[str, Any]

    def get_summary(self) -> Dict[str, Any]
```

**주요 기능:**
- 시간 범위 데이터 조회
- 축별 통계 계산 (mean, std, min, max, count)
- 현재 상태 조회 (RuleEngine 연동)
- 이상치 조회 (절대값, 초과, 미만)
- 이벤트 스니펫 조회 (특정 시점 ±n초)
- 컨텍스트 정보 조회
- 전체 데이터 요약

---

## 4. 테스트 결과

### 4.1 데이터 로드 테스트

```
=== SensorStore Test ===
Records: 604800
```

✅ 604,800 레코드 정상 로드 (7일, 125Hz)

### 4.2 통계 계산 테스트

```
Fz stats: {
    'axis': 'Fz',
    'mean': -20.1522,
    'std': 15.2995,
    'min': -829.2387,
    'max': 10.6745,
    'count': 604800
}
```

✅ 통계 계산 정상 동작

### 4.3 RuleEngine 연동 테스트

```
Current states: {
    'Fx': 'State_Normal',
    'Fy': 'State_Normal',
    'Fz': 'State_Normal',
    'Tx': 'Unknown',
    'Ty': 'Unknown',
    'Tz': 'Unknown'
}
```

✅ RuleEngine.infer_state() 연동 성공
- Force 축 (Fx, Fy, Fz): 상태 추론 성공
- Torque 축 (Tx, Ty, Tz): 규칙 없음 → Unknown

### 4.4 이상치 조회 테스트

```
Anomalies (|Fz| > 300): 82 records
```

✅ 이상치 조회 정상 동작

---

## 5. 데이터 구조 분석

### 5.1 Parquet 파일 컬럼 (21개)

| 그룹 | 컬럼 |
|------|------|
| 시간 | timestamp |
| 센서 축 | Fx, Fy, Fz, Tx, Ty, Tz |
| 작업 정보 | task_mode, work_order_id, product_id |
| 운영 정보 | shift, operator_id |
| 로봇 상태 | gripper_state, payload_kg, payload_class, tool_id, status |
| 이벤트 | event_id, error_code |
| 품질 | valid, quality_flag |

### 5.2 시간 범위

| 항목 | 값 |
|------|-----|
| 시작 | 2024-01-15 00:00:00 |
| 종료 | 2024-01-21 23:59:59 |
| 기간 | 7일 |
| 샘플링 | 125 Hz |

---

## 6. 온톨로지 연결

### 6.1 연결 구조

```
SensorStore.get_current_state()
    ↓
RuleEngine.infer_state(axis, value)
    ↓
MeasurementAxis → State 추론
```

### 6.2 활용 예시

```python
from src.sensor import SensorStore
from src.ontology import create_rule_engine

store = SensorStore()

# 현재 상태 조회 (RuleEngine 자동 연동)
states = store.get_current_state()
# {'Fx': 'State_Normal', 'Fy': 'State_Normal', 'Fz': 'State_Normal', ...}

# 통계 기반 상태 판단 근거
stats = store.get_statistics("Fz")
# {'axis': 'Fz', 'mean': -20.15, 'std': 15.30, 'min': -829.24, 'max': 10.67, ...}
```

---

## 7. 체크리스트 완료

### 7.1 구현 항목

- [x] `src/sensor/data_loader.py` 구현
  - [x] Parquet 로드 (캐시 지원)
  - [x] 타임스탬프 파싱
  - [x] 결측치 처리 (선형 보간)
  - [x] 컨텍스트 컬럼 지원
- [x] `src/sensor/sensor_store.py` 구현
  - [x] 시간 범위 조회
  - [x] 통계 계산
  - [x] 현재 상태 조회 (RuleEngine 연동)
  - [x] 이상치 조회
  - [x] 이벤트 스니펫 조회
  - [x] 컨텍스트 정보 조회
  - [x] 전체 데이터 요약
- [x] `src/sensor/__init__.py` 업데이트

### 7.2 검증 항목

- [x] 604,800 레코드 정상 로드
- [x] 시간 범위 조회 정확성
- [x] 통계 계산 정확성
- [x] RuleEngine 연동 정상 동작

---

## 8. 폴더 구조 (Phase 7 완료)

```
ur5e-ontology-rag/
├── data/
│   └── sensor/
│       ├── raw/
│       │   └── axia80_week_01.parquet    # 604,800 레코드
│       ├── processed/
│       │   ├── detected_patterns.json     # 17개 패턴
│       │   └── anomaly_events.json
│       └── metadata/
│           └── sensor_config.yaml
│
└── src/
    └── sensor/
        ├── __init__.py      [42줄, 업데이트]
        ├── data_loader.py   [126줄, 신규]
        └── sensor_store.py  [252줄, 신규]
```

---

## 9. 다음 단계 (Phase 8)

### Phase 8에서의 SensorStore 활용

```python
from src.sensor import SensorStore

store = SensorStore()

# 패턴 감지를 위한 데이터 조회
data = store.get_data(start=start_time, end=end_time)

# 이상치 기반 패턴 후보 추출
anomalies = store.get_anomalies("Fz", threshold=300)

# 이벤트 스니펫 조회 (패턴 분석용)
snippet = store.get_window(center=event_time, window_seconds=5.0)

# 컨텍스트 정보 조회 (패턴 분류용)
context = store.get_context_at(event_time)
```

---

## 10. 문서 정보

| 항목 | 값 |
|------|------|
| 문서 버전 | v1.0 |
| 작성일 | 2026-01-22 |
| ROADMAP 섹션 | Stage 3, Phase 7 |
| Spec 섹션 | 8.2 센서 데이터 |
