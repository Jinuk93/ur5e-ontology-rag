"""
센서 라우트

센서 데이터, 패턴, 이벤트, SSE 스트림 관련 엔드포인트
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    SensorReading,
    SensorReadingsResponse,
    PatternInfo,
    PatternsResponse,
    EventInfo,
    EventsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sensors", tags=["Sensors"])

# 센서 데이터 경로
SENSOR_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "sensor"

# 센서 데이터 캐시
_sensor_df: Optional[pd.DataFrame] = None
_patterns_data: Optional[List[Dict]] = None
_events_data: Optional[List[Dict]] = None

# SSE 스트리밍 커서
_sse_cursor: int = 0


def load_sensor_data() -> pd.DataFrame:
    """센서 데이터 로드 (캐싱)"""
    global _sensor_df
    if _sensor_df is None:
        parquet_path = SENSOR_DATA_DIR / "raw" / "axia80_week_01.parquet"
        if parquet_path.exists():
            try:
                _sensor_df = pd.read_parquet(parquet_path)
            except Exception as e:
                logger.warning(f"Failed to read sensor parquet: {parquet_path} ({e})")
                _sensor_df = pd.DataFrame()

            if not _sensor_df.empty:
                required_cols = {"timestamp", "Fx", "Fy", "Fz", "Tx", "Ty", "Tz"}
                missing = required_cols - set(_sensor_df.columns)
                if missing:
                    logger.warning(f"Sensor parquet missing required columns: {sorted(missing)}")
                    _sensor_df = pd.DataFrame()
                else:
                    logger.info(f"Loaded sensor data: {len(_sensor_df)} records")
        else:
            logger.warning(f"Sensor data not found: {parquet_path}")
            _sensor_df = pd.DataFrame()
    return _sensor_df


def load_patterns() -> List[Dict]:
    """패턴 데이터 로드"""
    global _patterns_data
    if _patterns_data is None:
        patterns_path = SENSOR_DATA_DIR / "processed" / "detected_patterns.json"
        if patterns_path.exists():
            with open(patterns_path, 'r', encoding='utf-8') as f:
                _patterns_data = json.load(f)
            logger.info(f"Loaded patterns: {len(_patterns_data)} patterns")
        else:
            _patterns_data = []
    return _patterns_data


def load_events() -> List[Dict]:
    """이상 이벤트 데이터 로드"""
    global _events_data
    if _events_data is None:
        events_path = SENSOR_DATA_DIR / "processed" / "anomaly_events.json"
        if events_path.exists():
            with open(events_path, 'r', encoding='utf-8') as f:
                _events_data = json.load(f)
            logger.info(f"Loaded events: {len(_events_data)} events")
        else:
            _events_data = []
    return _events_data


@router.get("/readings", response_model=SensorReadingsResponse)
async def get_sensor_readings(
    limit: int = Query(default=60, ge=1, le=1000, description="반환할 레코드 수"),
    offset: int = Query(default=0, ge=0, description="시작 오프셋 (최신 데이터 기준)"),
):
    """
    센서 측정값 조회

    최신 데이터부터 limit 개수만큼 반환합니다.
    프론트엔드 LiveView에서 실시간 차트 데이터로 사용합니다.
    """
    try:
        df = load_sensor_data()

        if df.empty:
            return SensorReadingsResponse(
                readings=[],
                total=0,
                time_range={"start": "", "end": ""},
            )

        total = len(df)
        start_idx = max(0, total - offset - limit)
        end_idx = total - offset

        subset = df.iloc[start_idx:end_idx].copy()

        readings = []
        for _, row in subset.iterrows():
            readings.append(SensorReading(
                timestamp=str(row['timestamp']),
                Fx=float(row['Fx']) if pd.notna(row['Fx']) else 0.0,
                Fy=float(row['Fy']) if pd.notna(row['Fy']) else 0.0,
                Fz=float(row['Fz']) if pd.notna(row['Fz']) else 0.0,
                Tx=float(row['Tx']) if pd.notna(row['Tx']) else 0.0,
                Ty=float(row['Ty']) if pd.notna(row['Ty']) else 0.0,
                Tz=float(row['Tz']) if pd.notna(row['Tz']) else 0.0,
                status=str(row.get('status', 'normal')),
                task_mode=str(row.get('task_mode', 'idle')),
            ))

        time_range = {
            "start": str(subset['timestamp'].min()) if not subset.empty else "",
            "end": str(subset['timestamp'].max()) if not subset.empty else "",
        }

        return SensorReadingsResponse(
            readings=readings,
            total=total,
            time_range=time_range,
        )

    except Exception as e:
        logger.error(f"Sensor readings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/readings/range")
async def get_sensor_readings_range(
    hours: int = Query(default=1, ge=1, le=168, description="조회할 시간 범위 (최대 168시간=7일)"),
    samples: int = Query(default=200, ge=10, le=500, description="반환할 샘플 수"),
):
    """
    시간 범위 기반 센서 데이터 조회 (샘플링)

    7일치 데이터를 효율적으로 조회하기 위해 샘플링합니다.
    - hours: 최근 N시간 데이터 조회
    - samples: 반환할 데이터 포인트 수 (균등 샘플링)
    """
    try:
        df = load_sensor_data()

        if df.empty:
            return {"readings": [], "total": 0, "time_range": {"start": "", "end": ""}}

        total = len(df)
        # 1초당 1샘플 기준, hours 시간에 해당하는 레코드 수
        records_needed = hours * 3600
        records_needed = min(records_needed, total)

        # 최근 N시간 데이터 선택
        subset = df.iloc[-records_needed:].copy()

        # 균등 샘플링
        if len(subset) > samples:
            indices = [int(i * len(subset) / samples) for i in range(samples)]
            subset = subset.iloc[indices]

        readings = []
        for _, row in subset.iterrows():
            readings.append({
                "timestamp": str(row['timestamp']),
                "Fx": float(row['Fx']) if pd.notna(row['Fx']) else 0.0,
                "Fy": float(row['Fy']) if pd.notna(row['Fy']) else 0.0,
                "Fz": float(row['Fz']) if pd.notna(row['Fz']) else 0.0,
                "Tx": float(row['Tx']) if pd.notna(row['Tx']) else 0.0,
                "Ty": float(row['Ty']) if pd.notna(row['Ty']) else 0.0,
                "Tz": float(row['Tz']) if pd.notna(row['Tz']) else 0.0,
            })

        time_range = {
            "start": str(subset['timestamp'].min()) if not subset.empty else "",
            "end": str(subset['timestamp'].max()) if not subset.empty else "",
        }

        return {
            "readings": readings,
            "total": records_needed,
            "sampled": len(readings),
            "hours": hours,
            "time_range": time_range,
        }

    except Exception as e:
        logger.error(f"Sensor readings range error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns", response_model=PatternsResponse)
async def get_sensor_patterns(
    limit: int = Query(default=10, ge=1, le=100, description="반환할 패턴 수"),
):
    """
    감지된 패턴 목록 조회

    충돌, 과부하, 드리프트 등 감지된 패턴 목록을 반환합니다.
    프론트엔드 HistoryView에서 패턴 테이블로 사용합니다.
    """
    try:
        patterns_raw = load_patterns()

        patterns = []
        for p in patterns_raw[:limit]:
            patterns.append(PatternInfo(
                id=p.get('pattern_id', p.get('id', '')),
                type=p.get('pattern_type', p.get('type', '')),
                timestamp=p.get('timestamp', p.get('start_time', '')),
                confidence=float(p.get('confidence', 0.0)),
                metrics=p.get('metrics', {}),
                related_error_codes=p.get('related_error_codes', p.get('error_codes', [])),
            ))

        return PatternsResponse(
            patterns=patterns,
            total=len(patterns_raw),
        )

    except Exception as e:
        logger.error(f"Patterns error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events", response_model=EventsResponse)
async def get_sensor_events(
    limit: int = Query(default=20, ge=1, le=100, description="반환할 이벤트 수"),
):
    """
    이상 이벤트 목록 조회

    시나리오 A/B/C에서 발생한 이상 이벤트 목록을 반환합니다.
    """
    try:
        events_raw = load_events()

        events = []
        for e in events_raw[:limit]:
            events.append(EventInfo(
                event_id=e.get('event_id', ''),
                scenario=e.get('scenario', ''),
                event_type=e.get('event_type', ''),
                start_time=e.get('start_time', ''),
                end_time=e.get('end_time', ''),
                duration_s=float(e.get('duration_s', 0)),
                error_code=e.get('error_code'),
                description=e.get('description', ''),
            ))

        return EventsResponse(
            events=events,
            total=len(events_raw),
        )

    except Exception as e:
        logger.error(f"Events error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def sensor_stream_generator(request: Request, interval: float = 1.0):
    """
    센서 데이터 SSE 스트림 생성기

    실제 운영에서는 실시간 센서 데이터를 받아 전송하지만,
    현재는 저장된 데이터를 순차적으로 재생합니다.
    """
    global _sse_cursor
    df = load_sensor_data()

    if df.empty:
        yield f"data: {json.dumps({'error': 'No sensor data available'})}\n\n"
        return

    total = len(df)

    while True:
        if await request.is_disconnected():
            logger.info("SSE client disconnected")
            break

        row = df.iloc[_sse_cursor % total]

        reading = {
            "timestamp": str(row['timestamp']),
            "Fx": float(row['Fx']) if pd.notna(row['Fx']) else 0.0,
            "Fy": float(row['Fy']) if pd.notna(row['Fy']) else 0.0,
            "Fz": float(row['Fz']) if pd.notna(row['Fz']) else 0.0,
            "Tx": float(row['Tx']) if pd.notna(row['Tx']) else 0.0,
            "Ty": float(row['Ty']) if pd.notna(row['Ty']) else 0.0,
            "Tz": float(row['Tz']) if pd.notna(row['Tz']) else 0.0,
            "cursor": _sse_cursor,
            "total": total,
        }

        yield f"data: {json.dumps(reading)}\n\n"

        _sse_cursor = (_sse_cursor + 1) % total

        await asyncio.sleep(interval)


@router.get("/stream")
async def stream_sensor_data(
    request: Request,
    interval: float = Query(default=1.0, ge=0.1, le=10.0, description="전송 간격 (초)"),
):
    """
    센서 데이터 SSE 스트림

    Server-Sent Events를 통해 실시간 센서 데이터를 스트리밍합니다.
    프론트엔드 LiveView에서 EventSource로 구독합니다.

    - interval: 데이터 전송 간격 (기본 1초)
    """
    return StreamingResponse(
        sensor_stream_generator(request, interval),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
