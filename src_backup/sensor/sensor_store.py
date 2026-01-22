# ============================================================
# src/sensor/sensor_store.py - 센서 데이터 저장소
# ============================================================
# Parquet 파일에서 센서 데이터를 로드하고,
# 감지된 패턴을 조회하는 기능을 제공합니다.
#
# Main-S2에서 구현
# ============================================================

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


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
        """
        Args:
            data_path: 센서 데이터 Parquet 파일 경로
            patterns_path: 감지된 패턴 JSON 파일 경로
        """
        self.data_path = Path(data_path)
        self.patterns_path = Path(patterns_path)
        self._data: Optional[pd.DataFrame] = None
        self._patterns: Optional[List[Dict]] = None

    # --------------------------------------------------------
    # [1] 데이터 로드
    # --------------------------------------------------------

    def load_data(self) -> pd.DataFrame:
        """
        센서 데이터 로드

        Returns:
            센서 데이터 DataFrame
        """
        if self._data is None:
            if not self.data_path.exists():
                raise FileNotFoundError(f"Sensor data not found: {self.data_path}")
            self._data = pd.read_parquet(self.data_path)
            self._data["timestamp"] = pd.to_datetime(self._data["timestamp"])
        return self._data

    def load_patterns(self) -> List[Dict]:
        """
        감지된 패턴 로드

        Returns:
            패턴 목록
        """
        if self._patterns is None:
            if self.patterns_path.exists():
                with open(self.patterns_path, "r", encoding="utf-8") as f:
                    self._patterns = json.load(f)
            else:
                self._patterns = []
        return self._patterns

    # --------------------------------------------------------
    # [2] 데이터 조회
    # --------------------------------------------------------

    def get_data(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        시간 범위로 센서 데이터 조회

        Args:
            start: 시작 시간 (ISO 8601 형식)
            end: 종료 시간 (ISO 8601 형식)
            columns: 조회할 컬럼 목록 (None이면 전체)

        Returns:
            필터링된 DataFrame
        """
        df = self.load_data().copy()

        if start:
            df = df[df["timestamp"] >= pd.to_datetime(start)]
        if end:
            df = df[df["timestamp"] <= pd.to_datetime(end)]
        if columns:
            available_cols = ["timestamp"] + [c for c in columns if c in df.columns]
            df = df[available_cols]

        return df

    def get_data_around_time(
        self,
        reference_time: datetime,
        window_before: str = "30m",
        window_after: str = "30m",
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        특정 시점 전후 데이터 조회

        Args:
            reference_time: 기준 시점
            window_before: 이전 윈도우 (예: "30m", "1h")
            window_after: 이후 윈도우
            columns: 조회할 컬럼

        Returns:
            해당 시간대 데이터
        """
        before_delta = self._parse_time_window(window_before)
        after_delta = self._parse_time_window(window_after)

        start = (reference_time - before_delta).isoformat()
        end = (reference_time + after_delta).isoformat()

        return self.get_data(start=start, end=end, columns=columns)

    # --------------------------------------------------------
    # [3] 패턴 조회
    # --------------------------------------------------------

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

            filtered = []
            for p in patterns:
                ts = p.get("timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                if start_time <= ts <= end_time:
                    filtered.append(p)
            patterns = filtered

        return patterns

    def get_patterns_by_event_id(self, event_id: str) -> List[Dict]:
        """
        이벤트 ID로 패턴 조회

        Args:
            event_id: S1에서 삽입한 이벤트 ID

        Returns:
            해당 이벤트의 패턴 목록
        """
        patterns = self.load_patterns()
        return [p for p in patterns if p.get("event_id") == event_id]

    # --------------------------------------------------------
    # [4] 통계 조회
    # --------------------------------------------------------

    def get_statistics(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        axes: List[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        지정 구간의 통계 정보

        Args:
            start: 시작 시간
            end: 종료 시간
            axes: 분석할 축 목록

        Returns:
            {axis: {"mean": float, "std": float, "min": float, "max": float}}
        """
        if axes is None:
            axes = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]

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

    def get_summary(self) -> Dict[str, Any]:
        """
        데이터 요약 정보

        Returns:
            요약 정보 딕셔너리
        """
        df = self.load_data()
        patterns = self.load_patterns()

        # 패턴 유형별 카운트
        pattern_counts = {}
        for p in patterns:
            ptype = p.get("pattern_type", "unknown")
            pattern_counts[ptype] = pattern_counts.get(ptype, 0) + 1

        return {
            "total_records": len(df),
            "time_range": {
                "start": df["timestamp"].min().isoformat(),
                "end": df["timestamp"].max().isoformat()
            },
            "total_patterns": len(patterns),
            "patterns_by_type": pattern_counts,
            "data_file": str(self.data_path),
            "patterns_file": str(self.patterns_path)
        }

    # --------------------------------------------------------
    # [5] 데이터 저장
    # --------------------------------------------------------

    def save_patterns(self, patterns: List[Dict]):
        """
        감지된 패턴 저장

        Args:
            patterns: 저장할 패턴 목록
        """
        self.patterns_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.patterns_path, "w", encoding="utf-8") as f:
            json.dump(patterns, f, ensure_ascii=False, indent=2)
        self._patterns = patterns
        print(f"[OK] Saved {len(patterns)} patterns to {self.patterns_path}")

    # --------------------------------------------------------
    # [6] 유틸리티
    # --------------------------------------------------------

    def _parse_time_window(self, window: str) -> timedelta:
        """
        시간 윈도우 문자열 파싱

        Args:
            window: "30m", "1h", "1d" 등

        Returns:
            timedelta 객체
        """
        unit = window[-1].lower()
        value = int(window[:-1])

        if unit == "s":
            return timedelta(seconds=value)
        elif unit == "m":
            return timedelta(minutes=value)
        elif unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)
        else:
            return timedelta(hours=1)

    def clear_cache(self):
        """캐시 클리어"""
        self._data = None
        self._patterns = None


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_sensor_store: Optional[SensorStore] = None


def get_sensor_store() -> SensorStore:
    """SensorStore 싱글톤 반환"""
    global _sensor_store
    if _sensor_store is None:
        _sensor_store = SensorStore()
    return _sensor_store


# ============================================================
# CLI 실행
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SensorStore Test")
    print("=" * 60)

    store = SensorStore()

    try:
        # 요약 정보
        print("\n[1] Data Summary:")
        summary = store.get_summary()
        print(f"    Total records: {summary['total_records']:,}")
        print(f"    Time range: {summary['time_range']['start']} ~ {summary['time_range']['end']}")
        print(f"    Total patterns: {summary['total_patterns']}")
        print(f"    Patterns by type: {summary['patterns_by_type']}")

        # 통계
        print("\n[2] Statistics (full range):")
        stats = store.get_statistics()
        for axis, s in stats.items():
            print(f"    {axis}: mean={s['mean']:.2f}, std={s['std']:.2f}, min={s['min']:.2f}, max={s['max']:.2f}")

        # 시간 범위 조회
        print("\n[3] Sample data query:")
        df = store.get_data(start="2024-01-17T10:00:00", end="2024-01-17T10:01:00")
        print(f"    Records: {len(df)}")

        print("\n" + "=" * 60)
        print("[OK] SensorStore test completed!")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"[WARN] {e}")
        print("[INFO] Run Main-S1 first to generate sensor data")
