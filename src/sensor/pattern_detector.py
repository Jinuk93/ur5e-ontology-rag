"""
패턴 감지 엔진

센서 데이터에서 이상 패턴을 자동 감지합니다.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from .patterns import DetectedPattern, PatternType, DEFAULT_ERROR_MAPPING
from .sensor_store import SensorStore

logger = logging.getLogger(__name__)


class PatternDetector:
    """패턴 감지 엔진"""

    # 감지 임계값 설정
    COLLISION_THRESHOLD = -350.0      # Fz 충돌 임계값 (N), 음수 피크
    OVERLOAD_THRESHOLD = 300.0        # Fz 과부하 임계값 (N), 절대값
    DRIFT_THRESHOLD_PCT = 10.0        # Baseline 대비 변화율 (%)
    VIBRATION_STD_MULTIPLIER = 2.0    # 표준편차 증가 배수 (2.0x = 민감, 3.0x = 엄격)

    # 최소 지속 시간
    OVERLOAD_MIN_DURATION_S = 5.0     # 과부하 최소 지속 시간 (초)
    DRIFT_MIN_DURATION_H = 1.0        # 드리프트 최소 지속 시간 (시간)

    # 윈도우 설정
    DRIFT_WINDOW_HOURS = 1.0          # 드리프트 감지 윈도우 (시간)
    VIBRATION_WINDOW_SECONDS = 60.0   # 진동 감지 윈도우 (초)

    # Baseline 임계값 (이 값 미만이면 절대값 기반 드리프트 감지로 전환)
    DRIFT_BASELINE_EPSILON = 1.0      # N (baseline이 이 값 미만이면 절대값 모드)
    DRIFT_ABSOLUTE_THRESHOLD = 5.0    # N (절대값 모드에서 드리프트 임계값)

    # 패턴 저장 경로
    PATTERNS_PATH = Path("data/sensor/processed/detected_patterns.json")

    def __init__(self, sensor_store: Optional[SensorStore] = None):
        """초기화

        Args:
            sensor_store: 센서 저장소 (없으면 자동 생성)
        """
        if sensor_store is not None:
            self._store = sensor_store
        else:
            self._store = SensorStore()

        self._pattern_counter = 0
        self._existing_patterns: List[DetectedPattern] = []

        logger.info("PatternDetector 초기화 완료")

    @property
    def sensor_store(self) -> SensorStore:
        """센서 저장소"""
        return self._store

    def detect(
        self,
        df: Optional[pd.DataFrame] = None,
        axis: str = "Fz"
    ) -> List[DetectedPattern]:
        """패턴 감지 (호환성 메서드)

        기존 스크립트(detect_patterns.py)와의 호환성을 위해 제공됩니다.
        DataFrame을 직접 받아 패턴을 감지합니다.

        Args:
            df: 센서 데이터 DataFrame (None이면 내부 store 사용)
            axis: 분석할 축

        Returns:
            감지된 패턴 목록
        """
        # df가 제공되면 임시 store 생성
        if df is not None:
            original_store = self._store
            self._store = SensorStore(data=df)

        try:
            patterns = []
            patterns.extend(self.detect_collision(axis=axis))
            patterns.extend(self.detect_overload(axis=axis))
            patterns.extend(self.detect_drift(axis=axis))
            patterns.extend(self.detect_vibration(axis=axis))
            return patterns
        finally:
            # 원래 store 복원
            if df is not None:
                self._store = original_store

    def detect_all(
        self,
        axis: str = "Fz",
        include_existing: bool = True
    ) -> List[DetectedPattern]:
        """모든 패턴 감지

        Args:
            axis: 분석할 축
            include_existing: 기존 패턴 포함 여부

        Returns:
            감지된 패턴 목록
        """
        patterns = []

        if include_existing:
            patterns.extend(self.load_existing_patterns())

        # 새 패턴 감지 (기존 패턴과 중복 방지를 위해 별도 처리 가능)
        # 여기서는 기존 패턴만 로드하는 것으로 구현
        # 실제 실시간 감지는 별도 메서드 호출

        logger.info(f"총 {len(patterns)}개 패턴 로드/감지")
        return patterns

    def detect_collision(
        self,
        axis: str = "Fz",
        threshold: Optional[float] = None
    ) -> List[DetectedPattern]:
        """충돌 패턴 감지

        급격한 음수 피크를 감지합니다.

        Args:
            axis: 분석할 축
            threshold: 임계값 (기본: COLLISION_THRESHOLD)

        Returns:
            충돌 패턴 목록
        """
        threshold = threshold or self.COLLISION_THRESHOLD
        data = self._store.data

        # 임계값 미만 데이터 찾기
        collision_mask = data[axis] < threshold
        collision_indices = data[collision_mask].index.tolist()

        if not collision_indices:
            return []

        # 연속 구간 그룹핑
        groups = self._group_continuous_indices(collision_indices)
        patterns = []

        for group in groups:
            group_data = data.loc[group]
            peak_idx = group_data[axis].idxmin()
            peak_row = data.loc[peak_idx]

            # 피크 주변 baseline 계산 (±5초)
            timestamp = peak_row["timestamp"]
            window = self._store.get_window(timestamp, window_seconds=5.0)
            baseline_data = window[window[axis] > threshold]
            baseline = baseline_data[axis].mean() if len(baseline_data) > 0 else 0

            peak_value = float(peak_row[axis])
            deviation = abs(peak_value - baseline)

            pattern = DetectedPattern(
                pattern_id=self._generate_pattern_id(),
                pattern_type=PatternType.COLLISION,
                timestamp=timestamp,
                duration_ms=0,  # 순간 이벤트
                confidence=1.0,
                metrics={
                    "peak_axis": axis,
                    "peak_value": peak_value,
                    "baseline": baseline,
                    "deviation": deviation,
                },
                related_error_codes=DEFAULT_ERROR_MAPPING[PatternType.COLLISION].copy(),
            )
            patterns.append(pattern)

        logger.info(f"충돌 패턴 {len(patterns)}개 감지")
        return patterns

    def detect_overload(
        self,
        axis: str = "Fz",
        threshold: Optional[float] = None,
        min_duration_s: Optional[float] = None
    ) -> List[DetectedPattern]:
        """과부하 패턴 감지

        임계값 초과가 지속되는 구간을 감지합니다.

        Args:
            axis: 분석할 축
            threshold: 임계값 (기본: OVERLOAD_THRESHOLD)
            min_duration_s: 최소 지속 시간 (초)

        Returns:
            과부하 패턴 목록
        """
        threshold = threshold or self.OVERLOAD_THRESHOLD
        min_duration_s = min_duration_s or self.OVERLOAD_MIN_DURATION_S
        data = self._store.data

        # 절대값이 임계값 초과하는 데이터
        overload_mask = data[axis].abs() > threshold
        overload_indices = data[overload_mask].index.tolist()

        if not overload_indices:
            return []

        # 연속 구간 그룹핑
        groups = self._group_continuous_indices(overload_indices)
        patterns = []

        for group in groups:
            group_data = data.loc[group]

            # 지속 시간 계산
            start_time = group_data["timestamp"].min()
            end_time = group_data["timestamp"].max()
            duration_s = (end_time - start_time).total_seconds()

            # 최소 지속 시간 필터
            if duration_s < min_duration_s:
                continue

            max_value = float(group_data[axis].abs().max())
            mean_value = float(group_data[axis].abs().mean())

            pattern = DetectedPattern(
                pattern_id=self._generate_pattern_id(),
                pattern_type=PatternType.OVERLOAD,
                timestamp=start_time,
                duration_ms=int(duration_s * 1000),
                confidence=1.0,
                metrics={
                    "axis": axis,
                    "max_value": max_value,
                    "mean_value": mean_value,
                    "duration_s": duration_s,
                },
                related_error_codes=DEFAULT_ERROR_MAPPING[PatternType.OVERLOAD].copy(),
            )
            patterns.append(pattern)

        logger.info(f"과부하 패턴 {len(patterns)}개 감지")
        return patterns

    def detect_drift(
        self,
        axis: str = "Fz",
        window_hours: Optional[float] = None,
        threshold_pct: Optional[float] = None,
        min_duration_h: Optional[float] = None
    ) -> List[DetectedPattern]:
        """드리프트 패턴 감지

        Baseline 대비 지속적인 이동을 감지합니다.
        Baseline이 0에 가까운 경우 절대값 기반 감지로 전환됩니다.

        Args:
            axis: 분석할 축
            window_hours: 분석 윈도우 (시간)
            threshold_pct: 변화율 임계값 (%)
            min_duration_h: 최소 지속 시간 (시간)

        Returns:
            드리프트 패턴 목록
        """
        window_hours = window_hours or self.DRIFT_WINDOW_HOURS
        threshold_pct = threshold_pct or self.DRIFT_THRESHOLD_PCT
        min_duration_h = min_duration_h or self.DRIFT_MIN_DURATION_H

        data = self._store.data

        # 전체 baseline 계산
        baseline = float(data[axis].mean())

        # 시간 윈도우별 평균 계산
        data_indexed = data.set_index("timestamp")
        window_str = f"{int(window_hours * 60)}min"  # 분 단위
        rolling_mean = data_indexed[axis].resample(window_str).mean()

        # baseline이 0에 가까우면 절대값 기반 감지로 전환
        use_absolute_mode = abs(baseline) < self.DRIFT_BASELINE_EPSILON

        if use_absolute_mode:
            logger.info(f"드리프트 감지: 절대값 모드 (baseline={baseline:.4f}, 임계값={self.DRIFT_ABSOLUTE_THRESHOLD}N)")
            # 절대값 기반: rolling_mean이 절대 임계값을 초과하는지 확인
            deviation_abs = (rolling_mean - baseline).abs()
            drift_mask = deviation_abs > self.DRIFT_ABSOLUTE_THRESHOLD
            # deviation_pct는 참고용으로 계산 (baseline=0 방지)
            deviation_pct = deviation_abs  # 절대값 모드에서는 절대값을 저장
        else:
            # 퍼센트 기반: baseline 대비 변화율
            deviation_pct = ((rolling_mean - baseline) / abs(baseline)) * 100
            drift_mask = deviation_pct.abs() > threshold_pct

        drift_times = deviation_pct[drift_mask].index.tolist()

        if not drift_times:
            return []

        # 연속 구간 그룹핑 (시간 기반)
        patterns = []
        current_group_start = None
        current_group_end = None
        group_deviations = []

        for i, ts in enumerate(drift_times):
            if current_group_start is None:
                current_group_start = ts
                current_group_end = ts
                group_deviations = [deviation_pct[ts]]
            else:
                # 연속 여부 판단 (2배 윈도우 이내)
                gap = (ts - current_group_end).total_seconds() / 3600
                if gap <= window_hours * 2:
                    current_group_end = ts
                    group_deviations.append(deviation_pct[ts])
                else:
                    # 이전 그룹 저장
                    duration_h = (current_group_end - current_group_start).total_seconds() / 3600
                    if duration_h >= min_duration_h:
                        avg_deviation = np.mean(group_deviations)

                        if use_absolute_mode:
                            # 절대값 모드: drift_amount = avg_deviation (이미 절대값)
                            drift_amount = avg_deviation
                            confidence = min(1.0, avg_deviation / self.DRIFT_ABSOLUTE_THRESHOLD * 0.5 + 0.5)
                            deviation_pct_value = 0.0  # 퍼센트 의미 없음
                        else:
                            # 퍼센트 모드
                            drift_amount = avg_deviation * abs(baseline) / 100
                            confidence = min(1.0, abs(avg_deviation) / threshold_pct * 0.5 + 0.5)
                            deviation_pct_value = abs(avg_deviation)

                        pattern = DetectedPattern(
                            pattern_id=self._generate_pattern_id(),
                            pattern_type=PatternType.DRIFT,
                            timestamp=current_group_start,
                            duration_ms=int(duration_h * 3600 * 1000),
                            confidence=confidence,
                            metrics={
                                "baseline": baseline,
                                "drift_amount": drift_amount,
                                "deviation_pct": deviation_pct_value,
                                "duration_hours": duration_h,
                                "detection_mode": "absolute" if use_absolute_mode else "percentage",
                            },
                        )
                        patterns.append(pattern)

                    # 새 그룹 시작
                    current_group_start = ts
                    current_group_end = ts
                    group_deviations = [deviation_pct[ts]]

        # 마지막 그룹 처리
        if current_group_start is not None:
            duration_h = (current_group_end - current_group_start).total_seconds() / 3600
            if duration_h >= min_duration_h:
                avg_deviation = np.mean(group_deviations)

                if use_absolute_mode:
                    # 절대값 모드
                    drift_amount = avg_deviation
                    confidence = min(1.0, avg_deviation / self.DRIFT_ABSOLUTE_THRESHOLD * 0.5 + 0.5)
                    deviation_pct_value = 0.0
                else:
                    # 퍼센트 모드
                    drift_amount = avg_deviation * abs(baseline) / 100
                    confidence = min(1.0, abs(avg_deviation) / threshold_pct * 0.5 + 0.5)
                    deviation_pct_value = abs(avg_deviation)

                pattern = DetectedPattern(
                    pattern_id=self._generate_pattern_id(),
                    pattern_type=PatternType.DRIFT,
                    timestamp=current_group_start,
                    duration_ms=int(duration_h * 3600 * 1000),
                    confidence=confidence,
                    metrics={
                        "baseline": baseline,
                        "drift_amount": drift_amount,
                        "deviation_pct": deviation_pct_value,
                        "duration_hours": duration_h,
                        "detection_mode": "absolute" if use_absolute_mode else "percentage",
                    },
                )
                patterns.append(pattern)

        logger.info(f"드리프트 패턴 {len(patterns)}개 감지")
        return patterns

    def detect_vibration(
        self,
        axis: str = "Fz",
        window_seconds: Optional[float] = None,
        std_multiplier: Optional[float] = None
    ) -> List[DetectedPattern]:
        """진동 패턴 감지

        표준편차가 급격히 증가하는 구간을 감지합니다.

        Args:
            axis: 분석할 축
            window_seconds: 분석 윈도우 (초)
            std_multiplier: 표준편차 증가 배수

        Returns:
            진동 패턴 목록
        """
        window_seconds = window_seconds or self.VIBRATION_WINDOW_SECONDS
        std_multiplier = std_multiplier or self.VIBRATION_STD_MULTIPLIER

        data = self._store.data

        # 전체 표준편차
        global_std = float(data[axis].std())

        # Rolling 표준편차 계산
        # 125Hz 샘플링 기준 윈도우 크기
        window_size = int(window_seconds * 125)
        rolling_std = data[axis].rolling(window=window_size, min_periods=window_size // 2).std()

        # 임계값 초과 구간
        threshold = global_std * std_multiplier
        vibration_mask = rolling_std > threshold
        vibration_indices = data[vibration_mask].index.tolist()

        if not vibration_indices:
            return []

        # 연속 구간 그룹핑
        groups = self._group_continuous_indices(vibration_indices, max_gap=window_size)
        patterns = []

        for group in groups:
            group_data = data.loc[group]

            start_time = group_data["timestamp"].min()
            end_time = group_data["timestamp"].max()
            duration_s = (end_time - start_time).total_seconds()

            max_std = float(rolling_std.loc[group].max())
            mean_std = float(rolling_std.loc[group].mean())

            pattern = DetectedPattern(
                pattern_id=self._generate_pattern_id(),
                pattern_type=PatternType.VIBRATION,
                timestamp=start_time,
                duration_ms=int(duration_s * 1000),
                confidence=min(1.0, mean_std / threshold),
                metrics={
                    "axis": axis,
                    "global_std": global_std,
                    "max_std": max_std,
                    "mean_std": mean_std,
                    "std_multiplier": max_std / global_std,
                    "duration_s": duration_s,
                },
            )
            patterns.append(pattern)

        logger.info(f"진동 패턴 {len(patterns)}개 감지")
        return patterns

    def load_existing_patterns(self) -> List[DetectedPattern]:
        """기존 감지 패턴 로드

        Returns:
            기존 패턴 목록
        """
        if self._existing_patterns:
            return self._existing_patterns

        if not self.PATTERNS_PATH.exists():
            logger.warning(f"패턴 파일 없음: {self.PATTERNS_PATH}")
            return []

        with open(self.PATTERNS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        patterns = [DetectedPattern.from_dict(p) for p in data]
        self._existing_patterns = patterns

        # 패턴 카운터 업데이트
        for p in patterns:
            try:
                num = int(p.pattern_id.split("-")[1])
                self._pattern_counter = max(self._pattern_counter, num)
            except (IndexError, ValueError):
                pass

        logger.info(f"기존 패턴 {len(patterns)}개 로드")
        return patterns

    def save_patterns(
        self,
        patterns: List[DetectedPattern],
        path: Optional[Path] = None
    ) -> None:
        """패턴 저장

        Args:
            patterns: 저장할 패턴 목록
            path: 저장 경로 (기본: PATTERNS_PATH)
        """
        path = path or self.PATTERNS_PATH
        path.parent.mkdir(parents=True, exist_ok=True)

        data = [p.to_dict() for p in patterns]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"패턴 {len(patterns)}개 저장: {path}")

    def get_patterns_by_type(
        self,
        pattern_type: PatternType,
        patterns: Optional[List[DetectedPattern]] = None
    ) -> List[DetectedPattern]:
        """타입별 패턴 필터

        Args:
            pattern_type: 패턴 타입
            patterns: 패턴 목록 (없으면 기존 패턴 사용)

        Returns:
            필터된 패턴 목록
        """
        if patterns is None:
            patterns = self.load_existing_patterns()

        return [p for p in patterns if p.pattern_type == pattern_type]

    def get_patterns_in_range(
        self,
        start: datetime,
        end: datetime,
        patterns: Optional[List[DetectedPattern]] = None
    ) -> List[DetectedPattern]:
        """시간 범위별 패턴 필터

        Args:
            start: 시작 시각
            end: 종료 시각
            patterns: 패턴 목록 (없으면 기존 패턴 사용)

        Returns:
            필터된 패턴 목록
        """
        if patterns is None:
            patterns = self.load_existing_patterns()

        return [p for p in patterns if start <= p.timestamp <= end]

    def get_summary(self) -> dict:
        """패턴 요약 통계

        Returns:
            요약 딕셔너리
        """
        patterns = self.load_existing_patterns()

        summary = {
            "total_patterns": len(patterns),
            "by_type": {},
        }

        for pt in PatternType:
            type_patterns = self.get_patterns_by_type(pt, patterns)
            if type_patterns:
                summary["by_type"][pt.value] = {
                    "count": len(type_patterns),
                    "avg_confidence": np.mean([p.confidence for p in type_patterns]),
                }

        return summary

    def _generate_pattern_id(self) -> str:
        """패턴 ID 생성"""
        self._pattern_counter += 1
        return f"PAT-{self._pattern_counter:03d}"

    def _group_continuous_indices(
        self,
        indices: List[int],
        max_gap: int = 1
    ) -> List[List[int]]:
        """연속 인덱스 그룹핑

        Args:
            indices: 인덱스 목록
            max_gap: 최대 허용 갭

        Returns:
            그룹 목록
        """
        if not indices:
            return []

        groups = []
        current_group = [indices[0]]

        for idx in indices[1:]:
            if idx - current_group[-1] <= max_gap:
                current_group.append(idx)
            else:
                groups.append(current_group)
                current_group = [idx]

        groups.append(current_group)
        return groups


# 편의 함수
def create_pattern_detector(sensor_store: Optional[SensorStore] = None) -> PatternDetector:
    """PatternDetector 인스턴스 생성"""
    return PatternDetector(sensor_store)
