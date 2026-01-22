# Step 07: 센서 데이터 처리 - 설계서

## 1. 개요

| 항목 | 내용 |
|------|------|
| Phase | 07 - 센서 데이터 처리 (Sensor Data Processing) |
| 목표 | 센서 데이터 저장소 및 조회 API 구축 |
| 이전 단계 | Phase 06 - 추론 규칙 |
| 다음 단계 | Phase 08 - 패턴 감지 |
| ROADMAP 섹션 | Stage 3: Sensor Integration |

---

## 2. 요구사항 분석

### 2.1 Unified_ROADMAP.md 요구사항

| 요구사항 | 설명 |
|----------|------|
| Parquet 데이터 로드 | `data/sensor/raw/axia80_week_01.parquet` 로드 |
| 시간 범위 조회 API | 특정 시간 범위 데이터 조회 |
| 통계 계산 | mean, std, min, max 계산 |
| 이상치 마킹 | 임계값 기반 이상치 표시 |

### 2.2 Unified_Spec.md 데이터 현황

| 항목 | 값 |
|------|-----|
| 기간 | 7일 (2024-01-15 ~ 2024-01-21) |
| 샘플링 | 125 Hz |
| 레코드 수 | 604,800개 |
| 파일 크기 | 34.15 MB |
| 저장 형식 | Parquet |

### 2.3 기존 데이터 구조

```
data/sensor/
├── raw/
│   └── axia80_week_01.parquet    # 원본 센서 데이터
├── processed/
│   ├── detected_patterns.json     # 감지된 패턴 (17개)
│   ├── anomaly_events.json        # 이상 이벤트
│   └── validation_results.json    # 검증 결과
└── metadata/
    └── sensor_config.yaml         # 센서 설정
```

---

## 3. 설계

### 3.1 구현 파일 목록

| 파일 | 설명 |
|------|------|
| `src/sensor/data_loader.py` | Parquet 데이터 로드 및 전처리 |
| `src/sensor/sensor_store.py` | 센서 데이터 저장소 및 조회 API |
| `src/sensor/__init__.py` | 모듈 노출 |

### 3.2 클래스 설계

#### DataLoader

```python
class DataLoader:
    """센서 데이터 로더"""

    DEFAULT_PATH = Path("data/sensor/raw/axia80_week_01.parquet")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> pd.DataFrame:
        """Parquet 파일 로드"""

    @classmethod
    def preprocess(cls, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 전처리 (타임스탬프 파싱, 결측치 처리)"""

    @classmethod
    def get_time_range(cls, df: pd.DataFrame) -> Tuple[datetime, datetime]:
        """데이터 시간 범위 반환"""
```

#### SensorStore

```python
class SensorStore:
    """센서 데이터 저장소"""

    def __init__(self, data: Optional[pd.DataFrame] = None):
        """초기화 (데이터 자동 로드)"""

    def get_data(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        axes: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """시간 범위 데이터 조회"""

    def get_statistics(
        self,
        axis: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> Dict[str, float]:
        """축별 통계 (mean, std, min, max)"""

    def get_current_state(self) -> Dict[str, str]:
        """현재 상태 (각 축별 State)"""

    def get_anomalies(
        self,
        axis: str,
        threshold: float,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """이상치 조회"""

    def get_window(
        self,
        center: datetime,
        window_seconds: float = 5.0
    ) -> pd.DataFrame:
        """특정 시점 주변 데이터 (이벤트 스니펫)"""
```

### 3.3 온톨로지 연결

| SensorStore | 온톨로지 요소 |
|-------------|--------------|
| 축 데이터 (Fx, Fy, Fz, Tx, Ty, Tz) | MeasurementAxis 엔티티 |
| get_current_state() | RuleEngine.infer_state() 활용 |
| get_statistics() | State 판단 근거 |

### 3.4 RuleEngine 연동

```python
from src.ontology import create_rule_engine

class SensorStore:
    def get_current_state(self) -> Dict[str, str]:
        """현재 상태 판단"""
        engine = create_rule_engine()
        states = {}

        for axis in ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]:
            latest = self.data[axis].iloc[-1]
            result = engine.infer_state(axis, latest)
            states[axis] = result.result_id if result else "Unknown"

        return states
```

---

## 4. 데이터 스키마

### 4.1 Parquet 컬럼 (예상)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| timestamp | datetime | 측정 시각 |
| Fx | float | X축 힘 (N) |
| Fy | float | Y축 힘 (N) |
| Fz | float | Z축 힘 (N) |
| Tx | float | X축 토크 (Nm) |
| Ty | float | Y축 토크 (Nm) |
| Tz | float | Z축 토크 (Nm) |

### 4.2 통계 출력 형식

```python
{
    "axis": "Fz",
    "mean": -52.3,
    "std": 15.2,
    "min": -350.0,
    "max": 10.0,
    "count": 604800,
    "period": {
        "start": "2024-01-15T00:00:00",
        "end": "2024-01-21T23:59:59"
    }
}
```

---

## 5. 체크리스트

### 5.1 구현 항목

- [ ] `src/sensor/data_loader.py` 구현
  - [ ] Parquet 로드
  - [ ] 타임스탬프 파싱
  - [ ] 결측치 처리
- [ ] `src/sensor/sensor_store.py` 구현
  - [ ] 시간 범위 조회
  - [ ] 통계 계산
  - [ ] 현재 상태 조회 (RuleEngine 연동)
  - [ ] 이상치 조회
  - [ ] 이벤트 스니펫 조회
- [ ] `src/sensor/__init__.py` 업데이트
- [ ] 단위 테스트

### 5.2 검증 항목

- [ ] 604,800 레코드 정상 로드
- [ ] 시간 범위 조회 정확성
- [ ] 통계 계산 정확성
- [ ] RuleEngine 연동 정상 동작

---

## 6. 폴더 구조 (Phase 7 완료 후)

```
ur5e-ontology-rag/
├── data/
│   └── sensor/
│       ├── raw/
│       │   └── axia80_week_01.parquet
│       └── processed/
│           ├── detected_patterns.json
│           └── anomaly_events.json
│
└── src/
    └── sensor/
        ├── __init__.py [업데이트]
        ├── data_loader.py [신규]
        └── sensor_store.py [신규]
```

---

## 7. 다음 단계 연결

### Phase 8 (패턴 감지)에서의 사용

```python
from src.sensor import SensorStore

store = SensorStore()

# 패턴 감지를 위한 데이터 조회
data = store.get_data(start=start_time, end=end_time)

# 이상치 기반 패턴 후보 추출
anomalies = store.get_anomalies("Fz", threshold=300)
```

---

## 8. 문서 정보

| 항목 | 값 |
|------|---|
| 문서 버전 | v1.0 |
| 작성일 | 2026-01-22 |
| ROADMAP 섹션 | Stage 3, Phase 7 |
| Spec 섹션 | 8.2 센서 데이터 |
