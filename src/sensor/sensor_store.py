"""
센서 데이터 저장소

센서 데이터 조회 및 분석 API를 제공합니다.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd

from .data_loader import DataLoader

logger = logging.getLogger(__name__)


class SensorStore:
    """센서 데이터 저장소"""

    def __init__(self, data: Optional[pd.DataFrame] = None):
        """초기화

        Args:
            data: 센서 데이터 (없으면 자동 로드)
        """
        if data is not None:
            self._data = data
        else:
            self._data = DataLoader.load()

        self._rule_engine = None
        logger.info(f"SensorStore 초기화 완료: {len(self._data)} 레코드")

    @property
    def data(self) -> pd.DataFrame:
        """전체 데이터"""
        return self._data

    def load_data(self, path: Optional[str] = None) -> None:
        """데이터 로드 (호환성 메서드)

        기존 스크립트(detect_patterns.py)와의 호환성을 위해 제공됩니다.
        __init__에서 이미 데이터가 로드되므로, 이 메서드는 재로드가 필요할 때만 사용합니다.

        Args:
            path: Parquet 파일 경로 (기본: DEFAULT_PATH)
        """
        from pathlib import Path as PathLib
        path_obj = PathLib(path) if path else None
        self._data = DataLoader.load(path_obj, use_cache=False)
        logger.info(f"SensorStore 데이터 재로드: {len(self._data)} 레코드")

    def get_data(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        axes: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """시간 범위 데이터 조회

        Args:
            start: 시작 시각 (기본: 전체)
            end: 종료 시각 (기본: 전체)
            axes: 조회할 축 목록 (기본: 전체)

        Returns:
            필터링된 DataFrame
        """
        df = self._data.copy()

        # 시간 범위 필터
        if start is not None:
            df = df[df["timestamp"] >= start]
        if end is not None:
            df = df[df["timestamp"] <= end]

        # 축 필터
        if axes is not None:
            columns = ["timestamp"] + [a for a in axes if a in df.columns]
            df = df[columns]

        return df

    def get_statistics(
        self,
        axis: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """축별 통계

        Args:
            axis: 측정 축 (Fx, Fy, Fz, Tx, Ty, Tz)
            start: 시작 시각
            end: 종료 시각

        Returns:
            통계 딕셔너리 (mean, std, min, max, count)
        """
        df = self.get_data(start=start, end=end, axes=[axis])

        if axis not in df.columns or len(df) == 0:
            return {"error": f"No data for axis {axis}"}

        values = df[axis]
        time_range = DataLoader.get_time_range(df)

        return {
            "axis": axis,
            "mean": round(float(values.mean()), 4),
            "std": round(float(values.std()), 4),
            "min": round(float(values.min()), 4),
            "max": round(float(values.max()), 4),
            "count": len(values),
            "period": {
                "start": time_range[0].isoformat(),
                "end": time_range[1].isoformat()
            }
        }

    def get_current_state(self) -> Dict[str, str]:
        """현재 상태 (각 축별)

        RuleEngine을 사용하여 최신 값의 상태를 추론합니다.

        Returns:
            축별 상태 딕셔너리
        """
        # RuleEngine 지연 로딩
        if self._rule_engine is None:
            try:
                from src.ontology import create_rule_engine
                self._rule_engine = create_rule_engine()
            except ImportError:
                logger.warning("RuleEngine 로드 실패, 기본 상태 반환")
                return {axis: "Unknown" for axis in DataLoader.SENSOR_AXES}

        states = {}
        latest_row = self._data.iloc[-1]

        for axis in DataLoader.SENSOR_AXES:
            if axis in latest_row:
                value = float(latest_row[axis])
                result = self._rule_engine.infer_state(axis, value)
                states[axis] = result.result_id if result else "Unknown"
            else:
                states[axis] = "Unknown"

        return states

    def get_anomalies(
        self,
        axis: str,
        threshold: float,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        direction: str = "absolute"
    ) -> pd.DataFrame:
        """이상치 조회

        Args:
            axis: 측정 축
            threshold: 임계값
            start: 시작 시각
            end: 종료 시각
            direction: "absolute" (절대값), "above" (초과), "below" (미만)

        Returns:
            이상치 DataFrame
        """
        df = self.get_data(start=start, end=end)

        if axis not in df.columns:
            return pd.DataFrame()

        if direction == "absolute":
            mask = df[axis].abs() > threshold
        elif direction == "above":
            mask = df[axis] > threshold
        elif direction == "below":
            mask = df[axis] < threshold
        else:
            mask = df[axis].abs() > threshold

        return df[mask]

    def get_window(
        self,
        center: datetime,
        window_seconds: float = 5.0
    ) -> pd.DataFrame:
        """특정 시점 주변 데이터 (이벤트 스니펫)

        Args:
            center: 중심 시각
            window_seconds: 윈도우 크기 (±초)

        Returns:
            해당 구간 DataFrame
        """
        delta = timedelta(seconds=window_seconds)
        start = center - delta
        end = center + delta

        return self.get_data(start=start, end=end)

    def get_context_at(self, timestamp: datetime) -> Dict[str, Any]:
        """특정 시점의 컨텍스트 정보

        Args:
            timestamp: 조회 시각

        Returns:
            컨텍스트 딕셔너리
        """
        # 가장 가까운 시점 찾기
        idx = (self._data["timestamp"] - timestamp).abs().idxmin()
        row = self._data.loc[idx]

        context = {
            "timestamp": row["timestamp"].isoformat(),
        }

        for col in DataLoader.get_context_columns():
            if col in row:
                value = row[col]
                # NaN 처리
                if pd.isna(value):
                    context[col] = None
                else:
                    context[col] = value

        return context

    def get_summary(self) -> Dict[str, Any]:
        """전체 데이터 요약

        Returns:
            요약 딕셔너리
        """
        time_range = DataLoader.get_time_range(self._data)

        summary = {
            "total_records": len(self._data),
            "time_range": {
                "start": time_range[0].isoformat(),
                "end": time_range[1].isoformat(),
                "duration_days": (time_range[1] - time_range[0]).days + 1
            },
            "axes": {},
            "current_state": self.get_current_state()
        }

        # 각 축별 통계
        for axis in DataLoader.SENSOR_AXES:
            summary["axes"][axis] = self.get_statistics(axis)

        return summary


# 편의 함수
def create_sensor_store() -> SensorStore:
    """SensorStore 인스턴스 생성 (편의 함수)"""
    return SensorStore()
