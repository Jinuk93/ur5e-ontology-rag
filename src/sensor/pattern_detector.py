# ============================================================
# src/sensor/pattern_detector.py - 센서 패턴 감지기
# ============================================================
# 센서 데이터에서 이상 패턴을 자동 감지합니다.
#
# 4가지 패턴 유형:
#   - collision: 급격한 힘 증가 (충돌)
#   - vibration: 고주파 진동 패턴
#   - overload: 지속적인 과부하
#   - drift: 점진적 baseline 이동
#
# Main-S2에서 구현
# ============================================================

import json
import numpy as np
import pandas as pd
import yaml
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# [1] DetectedPattern 데이터클래스
# ============================================================

@dataclass
class DetectedPattern:
    """
    감지된 이상 패턴

    Attributes:
        pattern_id: 패턴 고유 ID (PAT-001)
        pattern_type: 패턴 유형 (collision, vibration, overload, drift)
        timestamp: 감지 시점
        duration_ms: 지속 시간 (밀리초)
        confidence: 신뢰도 (0.0~1.0)
        metrics: 측정값 (peak_axis, peak_value, baseline 등)
        related_error_codes: 연관 에러코드
        event_id: S1에서 삽입한 이벤트 ID (검증용)
        context: 추가 컨텍스트
    """
    pattern_id: str
    pattern_type: str
    timestamp: datetime
    duration_ms: int
    confidence: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    related_error_codes: List[str] = field(default_factory=list)
    event_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용"""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "duration_ms": self.duration_ms,
            "confidence": self.confidence,
            "metrics": self.metrics,
            "related_error_codes": self.related_error_codes,
            "event_id": self.event_id,
            "context": self.context
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectedPattern":
        """딕셔너리에서 생성"""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(
            pattern_id=data.get("pattern_id", ""),
            pattern_type=data.get("pattern_type", ""),
            timestamp=timestamp,
            duration_ms=data.get("duration_ms", 0),
            confidence=data.get("confidence", 0.0),
            metrics=data.get("metrics", {}),
            related_error_codes=data.get("related_error_codes", []),
            event_id=data.get("event_id"),
            context=data.get("context", {})
        )


# ============================================================
# [2] PatternDetector 클래스
# ============================================================

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
                "min_deviation": 300,
                "related_errors": ["C153", "C119"]
            },
            "vibration": {
                "freq_threshold_hz": 50,
                "amplitude_threshold": 2.0,
                "window_s": 5,
                "min_duration_s": 10,
                "related_errors": ["C204"]
            },
            "overload": {
                "threshold_N": 300,
                "duration_s": 5,
                "axis": "Fz",
                "related_errors": ["C189"]
            },
            "drift": {
                "window_h": 1,
                "deviation_pct": 10,
                "min_duration_h": 0.5,
                "related_errors": []
            }
        }

    # --------------------------------------------------------
    # [2.1] 메인 감지 메서드
    # --------------------------------------------------------

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

        # 데이터 복사 및 전처리
        df = data.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # 시간 범위 필터링
        if start_time:
            df = df[df["timestamp"] >= start_time]
        if end_time:
            df = df[df["timestamp"] <= end_time]

        if len(df) == 0:
            return []

        patterns = []

        for ptype in pattern_types:
            if ptype == "collision":
                patterns.extend(self._detect_collision(df))
            elif ptype == "vibration":
                patterns.extend(self._detect_vibration(df))
            elif ptype == "overload":
                patterns.extend(self._detect_overload(df))
            elif ptype == "drift":
                patterns.extend(self._detect_drift(df))

        return sorted(patterns, key=lambda p: p.timestamp)

    # --------------------------------------------------------
    # [2.2] 충돌 감지 (Spike Detection)
    # --------------------------------------------------------

    def _detect_collision(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """
        충돌 패턴 감지

        Fz 축에서 급격한 힘 증가를 감지합니다.
        baseline 대비 min_deviation 이상, 절대값 threshold_N 이상.
        """
        patterns = []
        config = self.config["collision"]
        threshold = config["threshold_N"]
        min_deviation = config["min_deviation"]
        related_errors = config.get("related_errors", ["C153", "C119"])

        fz = data["Fz"].values
        timestamps = data["timestamp"].values

        # baseline (rolling median, 60초 윈도우)
        baseline = data["Fz"].rolling(window=60, min_periods=1, center=True).median()
        deviation = np.abs(fz - baseline.values)

        # 임계값 초과 지점 찾기
        spikes = deviation > min_deviation

        # 연속 구간 그룹화
        spike_groups = self._find_consecutive_groups(spikes)

        for start_idx, end_idx in spike_groups:
            segment = data.iloc[start_idx:end_idx + 1]
            fz_segment = segment["Fz"].values
            peak_idx_local = np.argmax(np.abs(fz_segment))
            peak_idx = start_idx + peak_idx_local
            peak_value = np.abs(fz[peak_idx])

            if peak_value > threshold:
                self._pattern_counter += 1

                # event_id 확인 (S1 삽입 이벤트와 매칭)
                event_id = None
                if "event_id" in data.columns:
                    events = segment["event_id"].dropna().unique()
                    if len(events) > 0:
                        event_id = events[0]

                patterns.append(DetectedPattern(
                    pattern_id=f"PAT-{self._pattern_counter:03d}",
                    pattern_type="collision",
                    timestamp=pd.Timestamp(timestamps[peak_idx]).to_pydatetime(),
                    duration_ms=int((end_idx - start_idx) * 1000),
                    confidence=min(1.0, peak_value / threshold),
                    metrics={
                        "peak_axis": "Fz",
                        "peak_value": float(fz[peak_idx]),
                        "baseline": float(baseline.iloc[peak_idx]),
                        "deviation": float(deviation[peak_idx])
                    },
                    related_error_codes=related_errors,
                    event_id=event_id
                ))

        return patterns

    # --------------------------------------------------------
    # [2.3] 진동 감지 (Rolling STD)
    # --------------------------------------------------------

    def _detect_vibration(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """
        진동 패턴 감지

        토크 축(Tx, Ty)의 노이즈 증가를 감지합니다.
        baseline 대비 amplitude_threshold 배 이상.
        """
        patterns = []
        config = self.config["vibration"]
        window_s = config["window_s"]
        amp_threshold = config["amplitude_threshold"]
        min_duration_s = config.get("min_duration_s", 10)
        related_errors = config.get("related_errors", ["C204"])

        timestamps = data["timestamp"].values

        # 토크 축 분석
        for axis in ["Tx", "Ty"]:
            if axis not in data.columns:
                continue

            # 윈도우별 표준편차 계산
            rolling_std = data[axis].rolling(window=window_s, min_periods=1).std()
            baseline_std = data[axis].std()

            if baseline_std == 0:
                continue

            # 기준 대비 높은 노이즈 구간
            high_noise = rolling_std > (baseline_std * amp_threshold)
            noise_groups = self._find_consecutive_groups(high_noise)

            for start_idx, end_idx in noise_groups:
                duration = end_idx - start_idx
                if duration >= min_duration_s:
                    self._pattern_counter += 1

                    # event_id 확인
                    event_id = None
                    if "event_id" in data.columns:
                        segment = data.iloc[start_idx:end_idx + 1]
                        events = segment["event_id"].dropna().unique()
                        if len(events) > 0:
                            event_id = events[0]

                    noise_level = float(rolling_std.iloc[start_idx:end_idx + 1].mean())

                    patterns.append(DetectedPattern(
                        pattern_id=f"PAT-{self._pattern_counter:03d}",
                        pattern_type="vibration",
                        timestamp=pd.Timestamp(timestamps[start_idx]).to_pydatetime(),
                        duration_ms=duration * 1000,
                        confidence=min(1.0, noise_level / baseline_std / amp_threshold),
                        metrics={
                            "axis": axis,
                            "noise_level": noise_level,
                            "baseline_std": float(baseline_std),
                            "increase_ratio": noise_level / baseline_std
                        },
                        related_error_codes=related_errors,
                        event_id=event_id
                    ))

        return patterns

    # --------------------------------------------------------
    # [2.4] 과부하 감지 (Threshold Duration)
    # --------------------------------------------------------

    def _detect_overload(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """
        과부하 패턴 감지

        Fz 절대값이 threshold_N을 duration_s 이상 초과.
        """
        patterns = []
        config = self.config["overload"]
        threshold = config["threshold_N"]
        min_duration = config["duration_s"]
        related_errors = config.get("related_errors", ["C189"])

        timestamps = data["timestamp"].values

        # Fz 절대값이 임계값 초과
        overload = np.abs(data["Fz"].values) > threshold
        overload_groups = self._find_consecutive_groups(overload)

        for start_idx, end_idx in overload_groups:
            duration = end_idx - start_idx
            if duration >= min_duration:
                self._pattern_counter += 1

                segment = data.iloc[start_idx:end_idx + 1]
                fz_segment = segment["Fz"]

                # event_id 확인
                event_id = None
                if "event_id" in data.columns:
                    events = segment["event_id"].dropna().unique()
                    if len(events) > 0:
                        event_id = events[0]

                patterns.append(DetectedPattern(
                    pattern_id=f"PAT-{self._pattern_counter:03d}",
                    pattern_type="overload",
                    timestamp=pd.Timestamp(timestamps[start_idx]).to_pydatetime(),
                    duration_ms=duration * 1000,
                    confidence=min(1.0, float(np.abs(fz_segment).max()) / threshold),
                    metrics={
                        "axis": "Fz",
                        "max_value": float(np.abs(fz_segment).max()),
                        "mean_value": float(np.abs(fz_segment).mean()),
                        "duration_s": duration
                    },
                    related_error_codes=related_errors,
                    event_id=event_id
                ))

        return patterns

    # --------------------------------------------------------
    # [2.5] 드리프트 감지 (Baseline Deviation)
    # --------------------------------------------------------

    def _detect_drift(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """
        드리프트 패턴 감지

        Fz baseline이 점진적으로 이동하는 패턴.
        """
        patterns = []
        config = self.config["drift"]
        window_h = config["window_h"]
        deviation_pct = config["deviation_pct"]
        min_duration_h = config.get("min_duration_h", 0.5)
        related_errors = config.get("related_errors", [])

        timestamps = data["timestamp"].values

        # 윈도우 크기 (초 단위)
        window_size = int(window_h * 3600)
        if window_size > len(data):
            window_size = len(data) // 2

        if window_size < 10:
            return patterns

        # rolling mean
        rolling_mean = data["Fz"].rolling(window=window_size, min_periods=1).mean()

        # 전체 baseline (중앙값)
        baseline = data["Fz"].median()

        if baseline == 0:
            return patterns

        # baseline 대비 편차 (%)
        deviation = np.abs((rolling_mean.values - baseline) / abs(baseline)) * 100
        drift_detected = deviation > deviation_pct

        drift_groups = self._find_consecutive_groups(drift_detected)

        for start_idx, end_idx in drift_groups:
            duration_h = (end_idx - start_idx) / 3600
            if duration_h >= min_duration_h:
                self._pattern_counter += 1

                # event_id 확인
                event_id = None
                if "event_id" in data.columns:
                    segment = data.iloc[start_idx:end_idx + 1]
                    events = segment["event_id"].dropna().unique()
                    if len(events) > 0:
                        event_id = events[0]

                patterns.append(DetectedPattern(
                    pattern_id=f"PAT-{self._pattern_counter:03d}",
                    pattern_type="drift",
                    timestamp=pd.Timestamp(timestamps[start_idx]).to_pydatetime(),
                    duration_ms=int((end_idx - start_idx) * 1000),
                    confidence=min(1.0, deviation[start_idx:end_idx + 1].max() / deviation_pct / 2),
                    metrics={
                        "baseline": float(baseline),
                        "drift_amount": float(rolling_mean.iloc[end_idx] - baseline),
                        "deviation_pct": float(deviation[start_idx:end_idx + 1].max()),
                        "duration_hours": duration_h
                    },
                    related_error_codes=related_errors,
                    event_id=event_id
                ))

        return patterns

    # --------------------------------------------------------
    # [2.6] 유틸리티
    # --------------------------------------------------------

    def _find_consecutive_groups(self, mask) -> List[Tuple[int, int]]:
        """연속된 True 구간 찾기"""
        if isinstance(mask, pd.Series):
            mask = mask.values

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

    def reset_counter(self):
        """패턴 카운터 리셋"""
        self._pattern_counter = 0


# ============================================================
# [3] 싱글톤 인스턴스
# ============================================================

_pattern_detector: Optional[PatternDetector] = None


def get_pattern_detector() -> PatternDetector:
    """PatternDetector 싱글톤 반환"""
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = PatternDetector()
    return _pattern_detector


# ============================================================
# CLI 실행
# ============================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("PatternDetector Test")
    print("=" * 60)

    # 테스트 데이터 생성
    print("\n[1] Generating test data...")
    np.random.seed(42)
    timestamps = pd.date_range("2024-01-15", periods=1000, freq="1s")

    test_data = pd.DataFrame({
        "timestamp": timestamps,
        "Fx": np.random.normal(0, 2, 1000),
        "Fy": np.random.normal(0, 2, 1000),
        "Fz": np.random.normal(-15, 3, 1000),
        "Tx": np.random.normal(0, 0.1, 1000),
        "Ty": np.random.normal(0, 0.1, 1000),
        "Tz": np.random.normal(0, 0.05, 1000)
    })

    # 충돌 삽입
    test_data.loc[500:502, "Fz"] = -800
    print("    Injected collision at index 500-502")

    # 과부하 삽입
    test_data.loc[700:720, "Fz"] = -350
    print("    Injected overload at index 700-720")

    # 감지 실행
    print("\n[2] Running detection...")
    detector = PatternDetector()
    patterns = detector.detect(test_data)

    print(f"\n[3] Detected {len(patterns)} patterns:")
    for p in patterns:
        print(f"    {p.pattern_id}: {p.pattern_type} at {p.timestamp}")
        print(f"        confidence: {p.confidence:.2f}")
        print(f"        metrics: {p.metrics}")

    print("\n" + "=" * 60)
    print("[OK] PatternDetector test completed!")
    print("=" * 60)
