"""
센서 데이터 로더

Parquet 파일에서 센서 데이터를 로드하고 전처리합니다.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

import pandas as pd

logger = logging.getLogger(__name__)


class DataLoader:
    """센서 데이터 로더"""

    DEFAULT_PATH = Path("data/sensor/raw/axia80_week_01.parquet")

    # 센서 축 컬럼
    SENSOR_AXES = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]

    # 컨텍스트 컬럼
    CONTEXT_COLUMNS = [
        "task_mode", "work_order_id", "product_id", "shift",
        "operator_id", "gripper_state", "payload_kg", "payload_class",
        "tool_id", "status", "event_id", "error_code"
    ]

    # path별 캐시 (다른 파일 로드 시 구분)
    _cache: dict = {}

    @classmethod
    def load(
        cls,
        path: Optional[Path] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """Parquet 파일 로드

        Args:
            path: Parquet 파일 경로 (기본: DEFAULT_PATH)
            use_cache: 캐시 사용 여부

        Returns:
            센서 데이터 DataFrame
        """
        path = path or cls.DEFAULT_PATH
        cache_key = str(path.resolve()) if isinstance(path, Path) else str(Path(path).resolve())

        if use_cache and cache_key in cls._cache:
            return cls._cache[cache_key]

        logger.info(f"센서 데이터 로드: {path}")

        df = pd.read_parquet(path)
        df = cls.preprocess(df)

        if use_cache:
            cls._cache[cache_key] = df

        logger.info(f"센서 데이터 로드 완료: {len(df)} 레코드")
        return df

    @classmethod
    def preprocess(cls, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 전처리

        Args:
            df: 원본 DataFrame

        Returns:
            전처리된 DataFrame
        """
        # 타임스탬프를 datetime으로 변환 (이미 datetime인 경우 스킵)
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # 타임스탬프 기준 정렬
        df = df.sort_values("timestamp").reset_index(drop=True)

        # 결측치 처리 (센서 축만)
        for axis in cls.SENSOR_AXES:
            if axis in df.columns:
                # 선형 보간
                df[axis] = df[axis].interpolate(method="linear")
                # 남은 결측치는 0으로
                df[axis] = df[axis].fillna(0)

        return df

    @classmethod
    def get_time_range(cls, df: pd.DataFrame) -> Tuple[datetime, datetime]:
        """데이터 시간 범위 반환

        Args:
            df: 센서 데이터 DataFrame

        Returns:
            (시작 시각, 종료 시각) 튜플
        """
        start = df["timestamp"].min()
        end = df["timestamp"].max()
        return start.to_pydatetime(), end.to_pydatetime()

    @classmethod
    def get_axes(cls) -> List[str]:
        """센서 축 목록 반환"""
        return cls.SENSOR_AXES.copy()

    @classmethod
    def get_context_columns(cls) -> List[str]:
        """컨텍스트 컬럼 목록 반환"""
        return cls.CONTEXT_COLUMNS.copy()

    @classmethod
    def clear_cache(cls, path: Optional[Path] = None) -> None:
        """캐시 초기화

        Args:
            path: 특정 경로만 초기화 (None이면 전체 초기화)
        """
        if path is not None:
            cache_key = str(path.resolve()) if isinstance(path, Path) else str(Path(path).resolve())
            if cache_key in cls._cache:
                del cls._cache[cache_key]
                logger.info(f"센서 데이터 캐시 초기화: {path}")
        else:
            cls._cache.clear()
            logger.info("센서 데이터 캐시 전체 초기화")


# 편의 함수
def load_sensor_data(path: Optional[Path] = None) -> pd.DataFrame:
    """센서 데이터 로드 (편의 함수)"""
    return DataLoader.load(path)
