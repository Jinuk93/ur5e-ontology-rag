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
    PredictionItem,
    RealtimePrediction,
    PredictionsResponse,
    IntegratedStreamData,
)
from src.ontology import OntologyEngine, load_ontology
from src.simulation.correlation_engine import get_correlation_engine, reset_correlation_engine
from src.simulation.scenario_sequencer import ScenarioType, get_scenario_sequencer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sensors", tags=["Sensors"])

# 센서 데이터 경로 (절대 경로 사용)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SENSOR_DATA_DIR = _PROJECT_ROOT / "data" / "sensor"

# 센서 데이터 캐시
_sensor_df: Optional[pd.DataFrame] = None
_patterns_data: Optional[List[Dict]] = None
_events_data: Optional[List[Dict]] = None

# SSE 스트리밍 커서
_sse_cursor: int = 0

# OntologyEngine 캐시
_ontology_engine: Optional[OntologyEngine] = None


def get_ontology_engine() -> OntologyEngine:
    """OntologyEngine 싱글톤"""
    global _ontology_engine
    if _ontology_engine is None:
        _ontology_engine = OntologyEngine()
    return _ontology_engine


def load_sensor_data() -> pd.DataFrame:
    """센서 데이터 로드 (캐싱)"""
    global _sensor_df
    if _sensor_df is None:
        parquet_path = SENSOR_DATA_DIR / "raw" / "axia80_week_01.parquet"
        logger.info(f"Attempting to load sensor data from: {parquet_path}")
        logger.info(f"Path exists: {parquet_path.exists()}")
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


@router.get("/predictions", response_model=PredictionsResponse)
async def get_realtime_predictions(
    limit: int = Query(default=10, ge=1, le=50, description="분석할 최근 이벤트 수"),
):
    """
    이기종 결합 기반 실시간 예측

    Axia80 센서 데이터의 패턴과 온톨로지를 결합하여
    에러 발생을 사전 예측합니다.

    예측 경로:
    - Axia80 센서 → 패턴 감지 (PAT_COLLISION, PAT_OVERLOAD 등)
    - 패턴 → 온톨로지 추론 (TRIGGERS 관계)
    - 추론 → 에러 코드 예측 (C153, C189 등)
    """
    try:
        engine = get_ontology_engine()
        patterns_raw = load_patterns()
        events_raw = load_events()

        predictions_list = []
        high_risk_count = 0

        # 패턴별로 온톨로지 기반 예측 수행
        for pattern in patterns_raw[:limit]:
            pattern_type = pattern.get('pattern_type', '')
            pattern_id = f"PAT_{pattern_type.upper()}" if pattern_type else None
            timestamp = pattern.get('timestamp', '')
            confidence = pattern.get('confidence', 0.0)
            metrics = pattern.get('metrics', {})

            # 센서 값 추출
            sensor_value = metrics.get('peak_value', metrics.get('max_value', 0))

            # 상태 결정
            state = "normal"
            if abs(sensor_value) > 300:
                state = "critical"
            elif abs(sensor_value) > 100:
                state = "warning"

            prediction_items = []
            ontology_path = None

            if pattern_id:
                # 온톨로지 추론 경로 탐색
                traverser = engine.traverser
                reasoning_result = traverser.get_reasoning_path(pattern_id)

                if reasoning_result:
                    # 에러 예측 추출
                    for error_path in reasoning_result.get('error_paths', []):
                        error_code = error_path.get('error_id', '')
                        prob = error_path.get('confidence', 0) * confidence

                        # 원인 추출
                        cause = None
                        for cause_path in reasoning_result.get('cause_paths', []):
                            cause = cause_path.get('cause_id', '')
                            break

                        # 권장 조치
                        recommendation = _get_recommendation_for_pattern(pattern_type)

                        prediction_items.append(PredictionItem(
                            error_code=error_code,
                            probability=round(prob, 2),
                            pattern=pattern_id,
                            cause=cause,
                            timeframe="수초 내" if prob > 0.8 else "수분 내",
                            recommendation=recommendation,
                        ))

                        if prob > 0.7:
                            high_risk_count += 1

                    # 온톨로지 경로 생성
                    if reasoning_result.get('error_paths'):
                        first_error = reasoning_result['error_paths'][0]
                        ontology_path = first_error.get('path', '')

            # 예측이 없으면 기본 예측 추가
            if not prediction_items and pattern_type:
                default_errors = _get_default_errors_for_pattern(pattern_type)
                for err_code, prob in default_errors:
                    prediction_items.append(PredictionItem(
                        error_code=err_code,
                        probability=round(prob * confidence, 2),
                        pattern=pattern_id or f"PAT_{pattern_type.upper()}",
                        cause=_get_cause_for_pattern(pattern_type),
                        timeframe="모니터링 중",
                        recommendation=_get_recommendation_for_pattern(pattern_type),
                    ))

            predictions_list.append(RealtimePrediction(
                timestamp=timestamp,
                sensor_value=round(sensor_value, 2),
                state=state,
                pattern_detected=pattern_id,
                predictions=prediction_items,
                ontology_path=ontology_path,
            ))

        return PredictionsResponse(
            predictions=predictions_list,
            total_patterns=len(patterns_raw),
            high_risk_count=high_risk_count,
        )

    except Exception as e:
        logger.error(f"Predictions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _get_default_errors_for_pattern(pattern_type: str) -> List[tuple]:
    """패턴 타입별 기본 에러 코드 매핑"""
    mapping = {
        "collision": [("C153", 0.95), ("C119", 0.8)],
        "overload": [("C189", 0.9)],
        "drift": [],
        "vibration": [("C204", 0.75)],
    }
    return mapping.get(pattern_type.lower(), [])


def _get_cause_for_pattern(pattern_type: str) -> str:
    """패턴 타입별 원인 매핑"""
    mapping = {
        "collision": "CAUSE_COLLISION",
        "overload": "CAUSE_OVERLOAD",
        "drift": "CAUSE_CALIBRATION",
        "vibration": "CAUSE_JOINT_WEAR",
    }
    return mapping.get(pattern_type.lower(), "CAUSE_UNKNOWN")


def _get_recommendation_for_pattern(pattern_type: str) -> str:
    """패턴 타입별 권장 조치"""
    mapping = {
        "collision": "작업 영역 장애물 확인 및 제거",
        "overload": "페이로드 무게 확인 및 감량",
        "drift": "센서 캘리브레이션 수행",
        "vibration": "조인트 볼트 토크 점검",
    }
    return mapping.get(pattern_type.lower(), "상황 점검 필요")


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
    센서 데이터 SSE 스트림 (Axia80 only - 레거시)

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


# ============================================================
# Phase 2: 통합 실시간 스트림 (UR5e + Axia80 상관분석)
# ============================================================

async def integrated_stream_generator(request: Request, interval: float = 0.5):
    """
    통합 센서 데이터 SSE 스트림 생성기

    CorrelationEngine을 사용하여 UR5e + Axia80 상관 데이터를 생성합니다.
    시나리오 기반 시뮬레이션으로 물리적 상관관계가 있는 데이터를 제공합니다.
    """
    engine = get_correlation_engine()

    while True:
        if await request.is_disconnected():
            logger.info("Integrated SSE client disconnected")
            break

        try:
            # CorrelationEngine에서 통합 데이터 생성
            reading = engine.tick()

            # JSON 직렬화
            data = reading.to_dict()
            data["data_source"] = "simulated"

            yield f"data: {json.dumps(data)}\n\n"

        except Exception as e:
            logger.error(f"Integrated stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        await asyncio.sleep(interval)


@router.get("/stream/integrated")
async def stream_integrated_data(
    request: Request,
    interval: float = Query(default=0.5, ge=0.1, le=5.0, description="전송 간격 (초)"),
):
    """
    통합 실시간 스트림 (UR5e + Axia80)

    ⚠️ 시뮬레이션 데이터: UR5e 텔레메트리는 시나리오 기반으로 생성됩니다.

    Server-Sent Events를 통해 다음 데이터를 실시간 스트리밍합니다:
    - Axia80: 힘/토크 센서 데이터
    - UR5e: TCP 속도, 조인트 토크, 전류, 안전 모드 (시뮬레이션)
    - Correlation: 토크/힘 비율, 속도-힘 상관계수
    - Risk: 접촉/충돌 위험 점수, 권장 조치

    시나리오 종류:
    - normal (70%): 정상 작업 사이클
    - collision (10%): 충돌 → 스파이크 → 보호정지
    - overload (10%): 과부하 지속
    - wear (5%): 마모 징후 (토크/힘 불일치)
    - risk_approach (5%): 위험 접근

    - interval: 데이터 전송 간격 (기본 0.5초)
    """
    return StreamingResponse(
        integrated_stream_generator(request, interval),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream/scenario")
async def force_scenario(
    scenario: str = Query(description="강제 시나리오 (normal/collision/overload/wear/risk_approach)"),
    duration: Optional[int] = Query(default=None, description="시나리오 지속 시간 (초)"),
):
    """
    시나리오 강제 전환 (테스트/데모용)

    현재 시나리오를 강제로 특정 시나리오로 전환합니다.
    """
    try:
        scenario_type = ScenarioType(scenario)
        sequencer = get_scenario_sequencer()
        sequencer.force_scenario(scenario_type, duration)

        return {
            "success": True,
            "scenario": scenario,
            "duration": duration or sequencer.scenario_config.duration_range[1],
            "message": f"시나리오를 '{scenario}'로 전환했습니다.",
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 시나리오: {scenario}. "
                   f"가능한 값: {[s.value for s in ScenarioType]}"
        )


@router.get("/stream/statistics")
async def get_stream_statistics():
    """
    스트림 통계 조회

    최근 60개 데이터의 통계를 반환합니다.
    """
    engine = get_correlation_engine()
    stats = engine.get_statistics()

    if not stats:
        return {"message": "아직 데이터가 수집되지 않았습니다.", "statistics": {}}

    return {
        "message": "통계 조회 성공",
        "statistics": stats,
    }


@router.post("/stream/reset")
async def reset_stream():
    """
    스트림 리셋

    CorrelationEngine과 ScenarioSequencer를 리셋합니다.
    """
    from src.simulation.scenario_sequencer import reset_scenario_sequencer

    reset_correlation_engine()
    reset_scenario_sequencer()

    return {
        "success": True,
        "message": "스트림이 리셋되었습니다.",
    }
