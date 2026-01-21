# Main-S2: 센서 패턴 감지 상세 설계서

> **Phase**: Main-S2 (센서 통합 Phase 2)
> **목표**: 센서 데이터에서 이상 패턴 자동 감지
> **선행 조건**: Main-S1 (센서 데이터 생성) 완료
> **참조**: Main__Spec.md Section 9, 11 / Main__ROADMAP.md Main-S2

---

## 1. 개요

### 1.1 배경

Main-S1에서 생성된 센서 데이터(7일, 604,800 레코드)에는 다음 이상 패턴이 포함되어 있습니다:

| 시나리오 | 이벤트 수 | 패턴 유형 | 에러코드 |
|----------|:--------:|----------|----------|
| A (충돌) | 2 | collision | C153 |
| B (반복재발) | 4 | overload | C189 (Day 4) |
| C (오탐/유사) | 4 | tool_change, recalibration, drift | - |

**Main-S2의 목표**: 이러한 이상 패턴을 자동으로 감지하는 PatternDetector 구현

### 1.2 핵심 가치

| 가치 | 설명 |
|------|------|
| **조기 감지** | 충돌/과부하 발생 전 전조 패턴 감지 |
| **원인 추적** | 센서 패턴 → 에러코드 연관으로 진단 보강 |
| **오탐 방지** | 정상 운영 변화(툴교체 등)와 이상 구분 |
| **이중 검증** | Verifier에서 문서+센서 근거 확인 |

### 1.3 목표

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Main-S2 목표                                      │
├─────────────────────────────────────────────────────────────────────┤
│ 1. 4가지 패턴 유형 감지 (collision, vibration, overload, drift)     │
│ 2. 감지 정확도 F1 > 85%                                              │
│ 3. 패턴 → 에러코드 매핑 정의                                         │
│ 4. Main-S3 (Context Enricher) 연동 준비                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 아키텍처

### 2.1 전체 흐름

```
┌─────────────────────────────────────────────────────────────────────┐
│                    센서 데이터 파이프라인                              │
│                                                                       │
│  ┌─────────────┐   ┌───────────────┐   ┌─────────────────┐         │
│  │ Parquet     │──▶│ PatternDetector│──▶│ detected_       │         │
│  │ (원본 데이터) │   │               │   │ patterns.json   │         │
│  └─────────────┘   └───────────────┘   └─────────────────┘         │
│                           │                                          │
│                           ▼                                          │
│                    ┌─────────────┐                                  │
│                    │ SensorStore │                                  │
│                    │ (조회 API)   │                                  │
│                    └─────────────┘                                  │
│                           │                                          │
│                           ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    ONLINE (RAG 파이프라인)                    │   │
│  │                                                               │   │
│  │  Context Enricher ─── Verifier ─── Generator                 │   │
│  │        ↑                                                      │   │
│  │   SensorStore.get_patterns(error_code, time_window)          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 파일 구조

```
ur5e-ontology-rag/
├── src/
│   └── sensor/
│       ├── __init__.py                 # [S2] 패키지 초기화
│       ├── pattern_detector.py         # [S2] 핵심 클래스
│       ├── algorithms/
│       │   ├── __init__.py
│       │   ├── spike_detector.py       # [S2] 충돌 감지
│       │   ├── vibration_detector.py   # [S2] 진동 감지
│       │   ├── overload_detector.py    # [S2] 과부하 감지
│       │   └── drift_detector.py       # [S2] 드리프트 감지
│       └── sensor_store.py             # [S2] 센서 데이터 조회
│
├── data/
│   └── sensor/
│       ├── raw/
│       │   └── axia80_week_01.parquet  # [S1] 원본
│       ├── processed/
│       │   ├── anomaly_events.json     # [S1] 생성 시 삽입한 이벤트
│       │   └── detected_patterns.json  # [S2] 감지된 패턴
│       └── metadata/
│           ├── sensor_config.yaml      # [S1] 센서 설정
│           └── pattern_config.yaml     # [S2] 패턴 감지 설정
│
├── configs/
│   └── pattern_thresholds.yaml         # [S2] 임계값 설정
│
└── tests/
    └── unit/
        └── test_pattern_detector.py    # [S2] 단위 테스트
```

---

## 3. 상세 설계

### 3.1 DetectedPattern 데이터클래스

```python
# src/sensor/pattern_detector.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class DetectedPattern:
    """감지된 이상 패턴"""
    pattern_id: str                          # PAT-001
    pattern_type: str                        # collision, vibration, overload, drift
    timestamp: datetime                      # 감지 시점
    duration_ms: int                         # 지속 시간 (밀리초)
    confidence: float                        # 신뢰도 (0.0~1.0)

    # 측정값
    metrics: Dict[str, float] = field(default_factory=dict)
    # {
    #   "peak_axis": "Fz",
    #   "peak_value": 824.2,
    #   "baseline": -15.0,
    #   "deviation": 839.2
    # }

    # 연관 정보
    related_error_codes: List[str] = field(default_factory=list)
    event_id: Optional[str] = None           # S1에서 삽입한 이벤트 ID (검증용)
    context: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """JSON 직렬화용"""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "confidence": self.confidence,
            "metrics": self.metrics,
            "related_error_codes": self.related_error_codes,
            "event_id": self.event_id,
            "context": self.context
        }
```

### 3.2 PatternDetector 클래스

```python
# src/sensor/pattern_detector.py

import pandas as pd
import yaml
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

class PatternDetector:
    """
    센서 데이터 이상 패턴 감지기

    4가지 패턴 유형을 감지합니다:
    - collision: 급격한 힘 증가 (충돌)
    - vibration: 고주파 진동 패턴
    - overload: 지속적인 과부하
    - drift: 점진적 baseline 이동

    사용 예시:
        detector = PatternDetector()
        patterns = detector.detect(df, pattern_types=["collision", "overload"])
    """

    def __init__(self, config_path: str = "configs/pattern_thresholds.yaml"):
        """
        Args:
            config_path: 패턴 감지 임계값 설정 파일
        """
        self.config = self._load_config(config_path)
        self._pattern_counter = 0

    def _load_config(self, path: str) -> dict:
        """설정 파일 로드"""
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return self._default_config()

    def _default_config(self) -> dict:
        """기본 설정"""
        return {
            "collision": {
                "threshold_N": 500,
                "rise_time_ms": 100,
                "min_deviation": 300
            },
            "vibration": {
                "freq_threshold_hz": 50,
                "amplitude_threshold": 2.0,
                "window_s": 5
            },
            "overload": {
                "threshold_N": 300,
                "duration_s": 5,
                "axis": "Fz"
            },
            "drift": {
                "window_h": 1,
                "deviation_pct": 10,
                "min_duration_h": 0.5
            }
        }

    def detect(
        self,
        data: pd.DataFrame,
        pattern_types: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[DetectedPattern]:
        """
        센서 데이터에서 이상 패턴 감지

        Args:
            data: 센서 데이터 DataFrame
                  필수 컬럼: timestamp, Fx, Fy, Fz, Tx, Ty, Tz
            pattern_types: 감지할 패턴 유형 (None이면 전체)
            start_time: 분석 시작 시간
            end_time: 분석 종료 시간

        Returns:
            감지된 패턴 목록
        """
        if pattern_types is None:
            pattern_types = ["collision", "vibration", "overload", "drift"]

        # 시간 범위 필터링
        if start_time or end_time:
            data = self._filter_time_range(data, start_time, end_time)

        patterns = []

        for ptype in pattern_types:
            if ptype == "collision":
                patterns.extend(self._detect_collision(data))
            elif ptype == "vibration":
                patterns.extend(self._detect_vibration(data))
            elif ptype == "overload":
                patterns.extend(self._detect_overload(data))
            elif ptype == "drift":
                patterns.extend(self._detect_drift(data))

        return sorted(patterns, key=lambda p: p.timestamp)

    def _detect_collision(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """충돌 패턴 감지 (Spike Detection)"""
        patterns = []
        config = self.config["collision"]
        threshold = config["threshold_N"]
        min_deviation = config["min_deviation"]

        # Fz 축에서 급격한 변화 감지
        fz = data["Fz"].values
        timestamps = pd.to_datetime(data["timestamp"])

        # baseline (rolling median)
        baseline = data["Fz"].rolling(window=60, min_periods=1).median()
        deviation = abs(fz - baseline)

        # 임계값 초과 구간 찾기
        spikes = deviation > min_deviation

        # 연속 구간 그룹화
        spike_groups = self._find_consecutive_groups(spikes)

        for start_idx, end_idx in spike_groups:
            peak_idx = start_idx + deviation[start_idx:end_idx+1].argmax()
            peak_value = abs(fz[peak_idx])

            if peak_value > threshold:
                self._pattern_counter += 1
                patterns.append(DetectedPattern(
                    pattern_id=f"PAT-{self._pattern_counter:03d}",
                    pattern_type="collision",
                    timestamp=timestamps.iloc[peak_idx],
                    duration_ms=int((end_idx - start_idx) * 1000),
                    confidence=min(1.0, peak_value / threshold),
                    metrics={
                        "peak_axis": "Fz",
                        "peak_value": float(fz[peak_idx]),
                        "baseline": float(baseline.iloc[peak_idx]),
                        "deviation": float(deviation[peak_idx])
                    },
                    related_error_codes=["C153", "C119"]  # Safety Stop 관련
                ))

        return patterns

    def _detect_vibration(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """진동 패턴 감지 (FFT Analysis)"""
        patterns = []
        config = self.config["vibration"]
        window_s = config["window_s"]
        amp_threshold = config["amplitude_threshold"]

        # 토크 축(Tx, Ty) 노이즈 분석
        for axis in ["Tx", "Ty"]:
            # 윈도우별 표준편차 계산
            rolling_std = data[axis].rolling(window=window_s, min_periods=1).std()
            baseline_std = data[axis].std()

            # 기준 대비 높은 노이즈 구간
            high_noise = rolling_std > (baseline_std * amp_threshold)
            noise_groups = self._find_consecutive_groups(high_noise)

            for start_idx, end_idx in noise_groups:
                duration = end_idx - start_idx
                if duration > window_s * 2:  # 최소 지속시간
                    self._pattern_counter += 1
                    timestamps = pd.to_datetime(data["timestamp"])
                    patterns.append(DetectedPattern(
                        pattern_id=f"PAT-{self._pattern_counter:03d}",
                        pattern_type="vibration",
                        timestamp=timestamps.iloc[start_idx],
                        duration_ms=duration * 1000,
                        confidence=min(1.0, float(rolling_std.iloc[start_idx:end_idx].max() / baseline_std / amp_threshold)),
                        metrics={
                            "axis": axis,
                            "noise_level": float(rolling_std.iloc[start_idx:end_idx].mean()),
                            "baseline_std": float(baseline_std),
                            "increase_ratio": float(rolling_std.iloc[start_idx:end_idx].mean() / baseline_std)
                        },
                        related_error_codes=["C204"]  # Joint 진동 관련
                    ))

        return patterns

    def _detect_overload(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """과부하 패턴 감지 (Threshold Duration)"""
        patterns = []
        config = self.config["overload"]
        threshold = config["threshold_N"]
        min_duration = config["duration_s"]

        # Fz 절대값이 임계값 초과
        overload = abs(data["Fz"]) > threshold
        overload_groups = self._find_consecutive_groups(overload)

        timestamps = pd.to_datetime(data["timestamp"])

        for start_idx, end_idx in overload_groups:
            duration = end_idx - start_idx
            if duration >= min_duration:
                self._pattern_counter += 1
                fz_segment = data["Fz"].iloc[start_idx:end_idx+1]
                patterns.append(DetectedPattern(
                    pattern_id=f"PAT-{self._pattern_counter:03d}",
                    pattern_type="overload",
                    timestamp=timestamps.iloc[start_idx],
                    duration_ms=duration * 1000,
                    confidence=min(1.0, float(abs(fz_segment).max() / threshold)),
                    metrics={
                        "axis": "Fz",
                        "max_value": float(fz_segment.abs().max()),
                        "mean_value": float(fz_segment.abs().mean()),
                        "duration_s": duration
                    },
                    related_error_codes=["C189"]  # 과부하 관련
                ))

        return patterns

    def _detect_drift(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """드리프트 패턴 감지 (Baseline Deviation)"""
        patterns = []
        config = self.config["drift"]
        window_h = config["window_h"]
        deviation_pct = config["deviation_pct"]

        # 1시간 윈도우 rolling mean
        window_size = window_h * 3600  # 초 단위
        rolling_mean = data["Fz"].rolling(window=window_size, min_periods=1).mean()

        # 전체 baseline
        baseline = data["Fz"].median()

        # baseline 대비 편차 계산
        deviation = abs((rolling_mean - baseline) / abs(baseline)) * 100
        drift_detected = deviation > deviation_pct

        drift_groups = self._find_consecutive_groups(drift_detected)
        timestamps = pd.to_datetime(data["timestamp"])

        for start_idx, end_idx in drift_groups:
            duration_h = (end_idx - start_idx) / 3600
            if duration_h >= config["min_duration_h"]:
                self._pattern_counter += 1
                patterns.append(DetectedPattern(
                    pattern_id=f"PAT-{self._pattern_counter:03d}",
                    pattern_type="drift",
                    timestamp=timestamps.iloc[start_idx],
                    duration_ms=int((end_idx - start_idx) * 1000),
                    confidence=min(1.0, float(deviation.iloc[start_idx:end_idx].max() / deviation_pct / 2)),
                    metrics={
                        "baseline": float(baseline),
                        "drift_amount": float(rolling_mean.iloc[end_idx] - baseline),
                        "deviation_pct": float(deviation.iloc[start_idx:end_idx].max()),
                        "duration_hours": duration_h
                    },
                    related_error_codes=[]  # 드리프트는 특정 에러 없음
                ))

        return patterns

    def _find_consecutive_groups(self, mask: pd.Series) -> List[tuple]:
        """연속된 True 구간 찾기"""
        groups = []
        in_group = False
        start_idx = 0

        for i, val in enumerate(mask):
            if val and not in_group:
                in_group = True
                start_idx = i
            elif not val and in_group:
                in_group = False
                groups.append((start_idx, i - 1))

        if in_group:
            groups.append((start_idx, len(mask) - 1))

        return groups

    def _filter_time_range(
        self,
        data: pd.DataFrame,
        start: Optional[datetime],
        end: Optional[datetime]
    ) -> pd.DataFrame:
        """시간 범위 필터링"""
        df = data.copy()
        if start:
            df = df[pd.to_datetime(df["timestamp"]) >= start]
        if end:
            df = df[pd.to_datetime(df["timestamp"]) <= end]
        return df
```

### 3.3 패턴 감지 설정 (pattern_thresholds.yaml)

```yaml
# configs/pattern_thresholds.yaml
# 패턴 감지 임계값 설정

# ============================================================
# 충돌 감지 (Spike Detection)
# ============================================================
collision:
  # 힘 임계값 (N) - 이 값 이상이면 충돌로 판정
  threshold_N: 500

  # 상승 시간 (ms) - 이 시간 내 급격히 증가하면 충돌
  rise_time_ms: 100

  # 최소 편차 (N) - baseline 대비 이 값 이상 변화해야 함
  min_deviation: 300

  # 관련 에러코드
  related_errors:
    - C153  # Safety Stop - Collision
    - C119  # Safety Limit Violation

# ============================================================
# 진동 감지 (FFT Analysis / Rolling STD)
# ============================================================
vibration:
  # 주파수 임계값 (Hz) - 이 주파수 이상 성분이 증가하면 진동
  freq_threshold_hz: 50

  # 진폭 임계값 - baseline 대비 N배 이상이면 진동
  amplitude_threshold: 2.0

  # 분석 윈도우 (초)
  window_s: 5

  # 최소 지속 시간 (초)
  min_duration_s: 10

  # 관련 에러코드
  related_errors:
    - C204  # Joint vibration warning

# ============================================================
# 과부하 감지 (Threshold Duration)
# ============================================================
overload:
  # 힘 임계값 (N)
  threshold_N: 300

  # 최소 지속 시간 (초) - 이 시간 이상 지속되어야 과부하
  duration_s: 5

  # 감지 축
  axis: "Fz"

  # 관련 에러코드
  related_errors:
    - C189  # Payload overload

# ============================================================
# 드리프트 감지 (Baseline Deviation)
# ============================================================
drift:
  # 분석 윈도우 (시간)
  window_h: 1

  # 편차 임계값 (%) - baseline 대비 이 % 이상 이동하면 드리프트
  deviation_pct: 10

  # 최소 지속 시간 (시간)
  min_duration_h: 0.5

  # 드리프트는 특정 에러코드와 매핑되지 않음
  # 캘리브레이션 권고로 처리
  related_errors: []

# ============================================================
# 에러코드 매핑
# ============================================================
error_code_mapping:
  C153:
    patterns: ["collision"]
    description: "Safety Stop - 충돌 감지"
    confidence_boost: 0.2

  C119:
    patterns: ["collision"]
    description: "Safety Limit Violation"
    confidence_boost: 0.1

  C189:
    patterns: ["overload"]
    description: "Payload 과부하"
    confidence_boost: 0.2

  C204:
    patterns: ["vibration"]
    description: "Joint 진동 경고"
    confidence_boost: 0.15
```

### 3.4 SensorStore 클래스

```python
# src/sensor/sensor_store.py

import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any


class SensorStore:
    """
    센서 데이터 저장소

    Parquet 파일에서 센서 데이터를 로드하고,
    감지된 패턴을 조회하는 기능을 제공합니다.

    사용 예시:
        store = SensorStore()
        patterns = store.get_patterns(error_code="C153", time_window="1h")
        data = store.get_data(start="2024-01-17T10:00:00", end="2024-01-17T11:00:00")
    """

    def __init__(
        self,
        data_path: str = "data/sensor/raw/axia80_week_01.parquet",
        patterns_path: str = "data/sensor/processed/detected_patterns.json"
    ):
        self.data_path = Path(data_path)
        self.patterns_path = Path(patterns_path)
        self._data: Optional[pd.DataFrame] = None
        self._patterns: Optional[List[Dict]] = None

    def load_data(self) -> pd.DataFrame:
        """센서 데이터 로드"""
        if self._data is None:
            self._data = pd.read_parquet(self.data_path)
        return self._data

    def load_patterns(self) -> List[Dict]:
        """감지된 패턴 로드"""
        if self._patterns is None:
            if self.patterns_path.exists():
                with open(self.patterns_path, "r", encoding="utf-8") as f:
                    self._patterns = json.load(f)
            else:
                self._patterns = []
        return self._patterns

    def get_data(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        시간 범위로 센서 데이터 조회

        Args:
            start: 시작 시간 (ISO 8601)
            end: 종료 시간 (ISO 8601)
            columns: 조회할 컬럼 목록 (None이면 전체)

        Returns:
            필터링된 DataFrame
        """
        df = self.load_data()

        if start:
            df = df[pd.to_datetime(df["timestamp"]) >= start]
        if end:
            df = df[pd.to_datetime(df["timestamp"]) <= end]
        if columns:
            df = df[["timestamp"] + columns]

        return df

    def get_patterns(
        self,
        error_code: Optional[str] = None,
        pattern_type: Optional[str] = None,
        time_window: Optional[str] = None,
        reference_time: Optional[datetime] = None
    ) -> List[Dict]:
        """
        조건에 맞는 패턴 조회

        Args:
            error_code: 연관 에러코드
            pattern_type: 패턴 유형 (collision, vibration, overload, drift)
            time_window: 시간 윈도우 (예: "1h", "30m", "1d")
            reference_time: 기준 시간 (None이면 현재)

        Returns:
            조건에 맞는 패턴 목록
        """
        patterns = self.load_patterns()

        # 에러코드 필터
        if error_code:
            patterns = [
                p for p in patterns
                if error_code in p.get("related_error_codes", [])
            ]

        # 패턴 유형 필터
        if pattern_type:
            patterns = [
                p for p in patterns
                if p.get("pattern_type") == pattern_type
            ]

        # 시간 윈도우 필터
        if time_window and reference_time:
            window_delta = self._parse_time_window(time_window)
            start_time = reference_time - window_delta
            end_time = reference_time + window_delta

            patterns = [
                p for p in patterns
                if start_time <= datetime.fromisoformat(p["timestamp"]) <= end_time
            ]

        return patterns

    def get_statistics(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        axes: List[str] = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]
    ) -> Dict[str, Dict[str, float]]:
        """
        지정 구간의 통계 정보

        Returns:
            {axis: {"mean": float, "std": float, "min": float, "max": float}}
        """
        df = self.get_data(start=start, end=end, columns=axes)

        stats = {}
        for axis in axes:
            if axis in df.columns:
                stats[axis] = {
                    "mean": float(df[axis].mean()),
                    "std": float(df[axis].std()),
                    "min": float(df[axis].min()),
                    "max": float(df[axis].max())
                }

        return stats

    def _parse_time_window(self, window: str) -> timedelta:
        """시간 윈도우 문자열 파싱"""
        unit = window[-1]
        value = int(window[:-1])

        if unit == "m":
            return timedelta(minutes=value)
        elif unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)
        else:
            return timedelta(hours=1)

    def save_patterns(self, patterns: List[Dict]):
        """감지된 패턴 저장"""
        self.patterns_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.patterns_path, "w", encoding="utf-8") as f:
            json.dump(patterns, f, ensure_ascii=False, indent=2)
        self._patterns = patterns
```

---

## 4. 에러코드 매핑

### 4.1 패턴 → 에러코드 매핑 테이블

| 패턴 유형 | 에러코드 | 설명 | 신뢰도 가중치 |
|----------|----------|------|:------------:|
| `collision` | C153 | Safety Stop - 충돌 감지 | +0.2 |
| `collision` | C119 | Safety Limit Violation | +0.1 |
| `overload` | C189 | Payload 과부하 | +0.2 |
| `vibration` | C204 | Joint 진동 경고 | +0.15 |
| `drift` | - | 캘리브레이션 권고 | - |

### 4.2 에러코드별 센서 증거 연관

```python
# 에러코드로 센서 패턴 조회 예시
error_to_patterns = {
    "C153": {
        "expected_patterns": ["collision"],
        "sensor_evidence": "Fz 축 급격한 변화 (500N 이상)",
        "time_correlation": "에러 발생 직전 50-100ms"
    },
    "C189": {
        "expected_patterns": ["overload"],
        "sensor_evidence": "Fz 지속적 과부하 (300N 이상, 5초 이상)",
        "time_correlation": "에러 발생 전 5-30초"
    },
    "C119": {
        "expected_patterns": ["collision", "overload"],
        "sensor_evidence": "안전 한계 초과 힘/토크",
        "time_correlation": "에러 발생 직전"
    }
}
```

---

## 5. 구현 태스크

### 5.1 태스크 목록

```
Main-S2-1: PatternDetector 클래스 구현
├── src/sensor/pattern_detector.py 작성
├── DetectedPattern 데이터클래스 정의
├── detect() 메서드 구현
├── 4가지 패턴 감지 알고리즘 구현
│   ├── _detect_collision() - Spike Detection
│   ├── _detect_vibration() - FFT/Rolling STD
│   ├── _detect_overload() - Threshold Duration
│   └── _detect_drift() - Baseline Deviation
└── 검증: S1 데이터에서 10개 이벤트 감지

Main-S2-2: 설정 파일 작성
├── configs/pattern_thresholds.yaml 작성
├── 각 패턴별 임계값 정의
├── 에러코드 매핑 정의
└── 검증: 설정 로드 테스트

Main-S2-3: SensorStore 클래스 구현
├── src/sensor/sensor_store.py 작성
├── get_data() - 시간 범위 조회
├── get_patterns() - 패턴 조회
├── get_statistics() - 통계 조회
└── 검증: 조회 성능 < 100ms

Main-S2-4: 배치 감지 스크립트
├── scripts/detect_patterns.py 작성
├── S1 데이터 전체 분석
├── detected_patterns.json 생성
└── 검증: F1 > 85%

Main-S2-5: 단위 테스트
├── tests/unit/test_pattern_detector.py 작성
├── 각 패턴 유형별 테스트
├── 에지 케이스 테스트
└── 검증: 테스트 커버리지 > 80%
```

### 5.2 감지 정확도 평가

S1에서 삽입한 10개 이벤트와 비교:

| Event ID | 시나리오 | 예상 패턴 | 감지 여부 |
|----------|----------|----------|:--------:|
| EVT-001 | A | collision | [ ] |
| EVT-002 | A | collision | [ ] |
| EVT-003 | B | overload | [ ] |
| EVT-004 | B | overload | [ ] |
| EVT-005 | B | overload | [ ] |
| EVT-006 | B | overload | [ ] |
| EVT-007 | C | (정상) | [ ] |
| EVT-008 | C | (정상) | [ ] |
| EVT-009 | C | (정상) | [ ] |
| EVT-010 | C | drift | [ ] |

**목표**: Recall ≥ 90%, Precision ≥ 80%, F1 ≥ 85%

---

## 6. 테스트 계획

### 6.1 단위 테스트

```python
# tests/unit/test_pattern_detector.py

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.sensor.pattern_detector import PatternDetector, DetectedPattern


@pytest.fixture
def sample_data():
    """테스트용 샘플 데이터"""
    timestamps = pd.date_range("2024-01-15", periods=1000, freq="1s")
    return pd.DataFrame({
        "timestamp": timestamps,
        "Fx": np.random.normal(0, 2, 1000),
        "Fy": np.random.normal(0, 2, 1000),
        "Fz": np.random.normal(-15, 3, 1000),
        "Tx": np.random.normal(0, 0.1, 1000),
        "Ty": np.random.normal(0, 0.1, 1000),
        "Tz": np.random.normal(0, 0.05, 1000)
    })


@pytest.fixture
def detector():
    """테스트용 PatternDetector"""
    return PatternDetector()


class TestCollisionDetection:
    """충돌 감지 테스트"""

    def test_detect_collision_spike(self, detector, sample_data):
        """급격한 Fz 증가 감지"""
        # 충돌 삽입
        sample_data.loc[500:502, "Fz"] = -800

        patterns = detector.detect(sample_data, pattern_types=["collision"])

        assert len(patterns) > 0
        assert patterns[0].pattern_type == "collision"
        assert patterns[0].metrics["peak_value"] < -500

    def test_no_collision_normal(self, detector, sample_data):
        """정상 데이터에서 충돌 없음"""
        patterns = detector.detect(sample_data, pattern_types=["collision"])
        assert len(patterns) == 0


class TestOverloadDetection:
    """과부하 감지 테스트"""

    def test_detect_overload(self, detector, sample_data):
        """지속적 과부하 감지"""
        # 과부하 삽입 (10초간)
        sample_data.loc[300:310, "Fz"] = -350

        patterns = detector.detect(sample_data, pattern_types=["overload"])

        assert len(patterns) > 0
        assert patterns[0].pattern_type == "overload"

    def test_no_overload_short_duration(self, detector, sample_data):
        """짧은 과부하는 무시"""
        # 3초만 과부하
        sample_data.loc[300:303, "Fz"] = -350

        patterns = detector.detect(sample_data, pattern_types=["overload"])
        assert len(patterns) == 0


class TestVibrationDetection:
    """진동 감지 테스트"""

    def test_detect_vibration(self, detector, sample_data):
        """토크 노이즈 증가 감지"""
        # 진동 삽입
        sample_data.loc[200:250, "Tx"] = np.random.normal(0, 0.5, 51)

        patterns = detector.detect(sample_data, pattern_types=["vibration"])

        assert len(patterns) > 0
        assert patterns[0].pattern_type == "vibration"


class TestDriftDetection:
    """드리프트 감지 테스트"""

    def test_detect_drift(self, detector):
        """점진적 baseline 이동 감지"""
        # 4시간 데이터
        timestamps = pd.date_range("2024-01-15", periods=14400, freq="1s")
        fz = np.linspace(-15, -30, 14400) + np.random.normal(0, 1, 14400)

        data = pd.DataFrame({
            "timestamp": timestamps,
            "Fx": np.zeros(14400),
            "Fy": np.zeros(14400),
            "Fz": fz,
            "Tx": np.zeros(14400),
            "Ty": np.zeros(14400),
            "Tz": np.zeros(14400)
        })

        patterns = detector.detect(data, pattern_types=["drift"])

        assert len(patterns) > 0
        assert patterns[0].pattern_type == "drift"


class TestDetectedPattern:
    """DetectedPattern 데이터클래스 테스트"""

    def test_to_dict(self):
        """to_dict() 직렬화"""
        pattern = DetectedPattern(
            pattern_id="PAT-001",
            pattern_type="collision",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            duration_ms=100,
            confidence=0.95,
            metrics={"peak_value": -800},
            related_error_codes=["C153"]
        )

        d = pattern.to_dict()

        assert d["pattern_id"] == "PAT-001"
        assert d["pattern_type"] == "collision"
        assert d["confidence"] == 0.95
        assert "C153" in d["related_error_codes"]
```

---

## 7. 코드 리뷰 체크포인트

### 7.1 기능 완전성

| 항목 | 확인 내용 |
|------|----------|
| ☐ | 4가지 패턴 유형 모두 감지 가능한가? |
| ☐ | S1의 10개 이벤트를 정확히 감지하는가? |
| ☐ | 에러코드 매핑이 정확한가? |
| ☐ | SensorStore 조회가 정상 동작하는가? |

### 7.2 성능

| 항목 | 확인 내용 |
|------|----------|
| ☐ | 7일 데이터 전체 분석이 30초 이내인가? |
| ☐ | 패턴 조회가 100ms 이내인가? |
| ☐ | 메모리 사용이 적절한가? |

### 7.3 정확도

| 항목 | 확인 내용 |
|------|----------|
| ☐ | Precision ≥ 80%인가? |
| ☐ | Recall ≥ 90%인가? |
| ☐ | F1 Score ≥ 85%인가? |
| ☐ | 오탐(False Positive)이 적절히 제어되는가? |

---

## 8. 완료 기준

### 8.1 필수 항목

- [ ] PatternDetector 클래스 구현 완료
- [ ] 4가지 패턴 유형 감지 가능
- [ ] configs/pattern_thresholds.yaml 작성
- [ ] SensorStore 클래스 구현 완료
- [ ] detected_patterns.json 생성
- [ ] 단위 테스트 10개 이상, 통과율 100%

### 8.2 품질 항목

- [ ] 감지 정확도 F1 > 85%
- [ ] S1 이벤트 10개 중 9개 이상 감지
- [ ] 조회 성능 < 100ms
- [ ] 코드 리뷰 체크리스트 통과

---

## 9. 다음 단계

### 9.1 Main-S3: Context Enricher

Main-S2 완료 후 진행:
- 문서 검색 결과에 센서 맥락 추가
- 에러코드 기반 센서 조회
- 상관관계 분석 (STRONG/MODERATE/WEAK/NONE)

### 9.2 Main-S4: 온톨로지 확장

- SensorPattern 노드 추가
- INDICATES 관계 정의
- GraphRetriever 확장

---

## 10. 참조

### 10.1 관련 문서
- [Main__Spec.md](Main__Spec.md) - Section 9 (센서 데이터 스키마)
- [Main__ROADMAP.md](Main__ROADMAP.md) - Main-S2
- [Main_S1_센서데이터생성.md](Main_S1_센서데이터생성.md) - 입력 데이터 스펙

### 10.2 생성/수정 파일 경로
```
src/sensor/__init__.py                      (생성)
src/sensor/pattern_detector.py              (생성)
src/sensor/sensor_store.py                  (생성)
configs/pattern_thresholds.yaml             (생성)
data/sensor/processed/detected_patterns.json (생성)
tests/unit/test_pattern_detector.py         (생성)
```

---

**작성일**: 2024-01-21
**참조**: Main__Spec.md, Main__ROADMAP.md, Main_S1_센서데이터생성.md
