# ============================================================
# src/dashboard/pages/sensor_analysis.py - 센서 분석 페이지
# ============================================================
# Main-S6: 센서 데이터 시각화
# ============================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import json

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


# ============================================================
# [1] 데이터 로드 함수
# ============================================================

def load_sensor_data() -> Optional[pd.DataFrame]:
    """센서 데이터 로드"""
    data_path = Path(project_root) / "data" / "sensor" / "raw" / "axia80_week_01.parquet"

    if not data_path.exists():
        return None

    try:
        df = pd.read_parquet(data_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None


def load_detected_patterns() -> List[Dict]:
    """감지된 패턴 로드"""
    patterns_path = Path(project_root) / "data" / "sensor" / "processed" / "detected_patterns.json"

    if not patterns_path.exists():
        return []

    try:
        with open(patterns_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ============================================================
# [2] 시각화 컴포넌트
# ============================================================

# 패턴별 색상
PATTERN_COLORS = {
    "collision": "#FF5252",     # 빨강
    "vibration": "#FF9800",     # 주황
    "overload": "#9C27B0",      # 보라
    "drift": "#2196F3",         # 파랑
    "unknown": "#9E9E9E",       # 회색
}


def plot_sensor_timeseries(
    df: pd.DataFrame,
    axes: List[str] = ["Fz", "Tx", "Ty"],
    patterns: List[Dict] = None,
    time_range: tuple = None
) -> go.Figure:
    """센서 시계열 차트"""

    # 시간 필터링
    if time_range:
        mask = (df["timestamp"] >= time_range[0]) & (df["timestamp"] <= time_range[1])
        df = df[mask]

    # 데이터 샘플링 (성능 최적화)
    if len(df) > 10000:
        df = df.iloc[::len(df)//10000]

    fig = make_subplots(
        rows=len(axes), cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=axes
    )

    for i, axis in enumerate(axes, 1):
        if axis in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df[axis],
                    name=axis,
                    mode="lines",
                    line=dict(width=1),
                ),
                row=i, col=1
            )

    # 패턴 구간 하이라이트
    if patterns:
        for pattern in patterns:
            ts = pattern.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)

            duration_ms = pattern.get("duration_ms", 1000)
            end_ts = ts + timedelta(milliseconds=duration_ms)

            pattern_type = pattern.get("pattern_type", "unknown")
            color = PATTERN_COLORS.get(pattern_type, PATTERN_COLORS["unknown"])

            for i in range(1, len(axes) + 1):
                fig.add_vrect(
                    x0=ts, x1=end_ts,
                    fillcolor=color,
                    opacity=0.2,
                    layer="below",
                    line_width=0,
                    row=i, col=1,
                    annotation_text=pattern_type if i == 1 else None,
                    annotation_position="top left"
                )

    fig.update_layout(
        height=150 * len(axes),
        margin=dict(l=50, r=20, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified"
    )

    return fig


def plot_pattern_timeline(patterns: List[Dict]) -> go.Figure:
    """패턴 이벤트 타임라인"""

    if not patterns:
        return go.Figure()

    # 데이터 준비
    timestamps = []
    types = []
    confidences = []
    colors = []
    hover_texts = []

    for p in patterns:
        ts = p.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        pattern_type = p.get("pattern_type", "unknown")
        confidence = p.get("confidence", 0)

        timestamps.append(ts)
        types.append(pattern_type)
        confidences.append(confidence)
        colors.append(PATTERN_COLORS.get(pattern_type, PATTERN_COLORS["unknown"]))

        hover_texts.append(
            f"패턴: {pattern_type}<br>"
            f"시간: {ts}<br>"
            f"신뢰도: {confidence:.0%}"
        )

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=types,
        mode="markers",
        marker=dict(
            size=15,
            color=colors,
            line=dict(width=1, color="white")
        ),
        hovertext=hover_texts,
        hoverinfo="text"
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=100, r=20, t=30, b=30),
        yaxis=dict(title="패턴 유형"),
        xaxis=dict(title="시간"),
    )

    return fig


def plot_pattern_distribution(patterns: List[Dict]) -> go.Figure:
    """패턴 유형별 분포"""

    if not patterns:
        return go.Figure()

    # 유형별 카운트
    counts = {}
    for p in patterns:
        pt = p.get("pattern_type", "unknown")
        counts[pt] = counts.get(pt, 0) + 1

    fig = go.Figure(data=[
        go.Bar(
            x=list(counts.keys()),
            y=list(counts.values()),
            marker_color=[PATTERN_COLORS.get(k, "#9E9E9E") for k in counts.keys()],
            text=list(counts.values()),
            textposition="auto"
        )
    ])

    fig.update_layout(
        height=250,
        margin=dict(l=50, r=20, t=30, b=30),
        xaxis=dict(title="패턴 유형"),
        yaxis=dict(title="감지 횟수"),
    )

    return fig


# ============================================================
# [3] 메인 렌더 함수
# ============================================================

def render_sensor_analysis():
    """센서 분석 페이지 렌더링"""

    st.title("📊 센서 분석")
    st.caption("Main-S6: 센서 데이터 시각화 및 패턴 분석")

    # 데이터 로드
    with st.spinner("센서 데이터 로드 중..."):
        df = load_sensor_data()
        patterns = load_detected_patterns()

    # ─────────────────────────────────────────────────────
    # 데이터 없음 처리
    # ─────────────────────────────────────────────────────
    if df is None:
        st.warning("⚠️ 센서 데이터가 없습니다.")
        st.info("""
        센서 데이터를 생성하려면:
        ```bash
        python scripts/run_sensor_s1.py
        ```
        를 실행하세요.
        """)
        return

    # ─────────────────────────────────────────────────────
    # 1. 데이터 요약
    # ─────────────────────────────────────────────────────
    st.header("📋 데이터 요약")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("총 레코드", f"{len(df):,}")

    with col2:
        time_range = (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 3600
        st.metric("시간 범위", f"{time_range:.1f}시간")

    with col3:
        st.metric("감지 패턴", len(patterns))

    with col4:
        avg_fz = df["Fz"].mean() if "Fz" in df.columns else 0
        st.metric("평균 Fz", f"{avg_fz:.1f}N")

    # ─────────────────────────────────────────────────────
    # 2. 패턴 요약 카드
    # ─────────────────────────────────────────────────────
    st.header("🎯 감지된 패턴")

    if patterns:
        # 유형별 카운트
        pattern_counts = {}
        for p in patterns:
            pt = p.get("pattern_type", "unknown")
            pattern_counts[pt] = pattern_counts.get(pt, 0) + 1

        cols = st.columns(4)
        pattern_types = ["collision", "vibration", "overload", "drift"]

        for i, pt in enumerate(pattern_types):
            with cols[i]:
                count = pattern_counts.get(pt, 0)
                color = PATTERN_COLORS.get(pt, "#9E9E9E")
                st.markdown(f"""
                <div style="
                    background-color: {color}20;
                    border-left: 4px solid {color};
                    padding: 10px;
                    border-radius: 4px;
                ">
                    <b>{pt.upper()}</b><br>
                    <span style="font-size: 24px;">{count}</span>
                </div>
                """, unsafe_allow_html=True)

        # 분포 차트
        st.plotly_chart(plot_pattern_distribution(patterns), use_container_width=True)
    else:
        st.info("감지된 패턴이 없습니다.")

    # ─────────────────────────────────────────────────────
    # 3. 시계열 차트
    # ─────────────────────────────────────────────────────
    st.header("📈 센서 시계열")

    # 시간 범위 선택
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "시작일",
            value=df["timestamp"].min().date()
        )
    with col2:
        end_date = st.date_input(
            "종료일",
            value=df["timestamp"].max().date()
        )

    # 축 선택
    available_axes = [c for c in df.columns if c != "timestamp"]
    selected_axes = st.multiselect(
        "표시할 축",
        options=available_axes,
        default=["Fz", "Tx", "Ty"] if all(a in available_axes for a in ["Fz", "Tx", "Ty"]) else available_axes[:3]
    )

    # 패턴 하이라이트 옵션
    show_patterns = st.checkbox("패턴 구간 표시", value=True)

    if selected_axes:
        time_range = (
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.max.time())
        )

        fig = plot_sensor_timeseries(
            df,
            axes=selected_axes,
            patterns=patterns if show_patterns else None,
            time_range=time_range
        )
        st.plotly_chart(fig, use_container_width=True)

    # ─────────────────────────────────────────────────────
    # 4. 패턴 이벤트 타임라인
    # ─────────────────────────────────────────────────────
    if patterns:
        st.header("🕐 패턴 이벤트 타임라인")
        st.plotly_chart(plot_pattern_timeline(patterns), use_container_width=True)

    # ─────────────────────────────────────────────────────
    # 5. 패턴 상세 목록
    # ─────────────────────────────────────────────────────
    if patterns:
        st.header("📋 패턴 상세 목록")

        # DataFrame으로 변환
        pattern_df = pd.DataFrame(patterns)

        if "timestamp" in pattern_df.columns:
            pattern_df["timestamp"] = pd.to_datetime(pattern_df["timestamp"])

        # 테이블 표시
        st.dataframe(
            pattern_df[[c for c in ["pattern_id", "pattern_type", "timestamp", "confidence", "related_error_codes"] if c in pattern_df.columns]],
            use_container_width=True
        )

    # ─────────────────────────────────────────────────────
    # 6. 에러코드 연관 분석
    # ─────────────────────────────────────────────────────
    if patterns:
        st.header("🔗 에러코드 연관 분석")

        # 패턴-에러 매핑 추출
        pattern_error_map = {}
        for p in patterns:
            pt = p.get("pattern_type", "unknown")
            errors = p.get("related_error_codes", [])

            if pt not in pattern_error_map:
                pattern_error_map[pt] = set()
            pattern_error_map[pt].update(errors)

        # 표시
        for pt, errors in pattern_error_map.items():
            if errors:
                color = PATTERN_COLORS.get(pt, "#9E9E9E")
                st.markdown(f"""
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-bottom: 5px;
                ">
                    <span style="
                        background-color: {color};
                        color: white;
                        padding: 2px 8px;
                        border-radius: 4px;
                    ">{pt}</span>
                    <span>→</span>
                    <span>{', '.join(errors)}</span>
                </div>
                """, unsafe_allow_html=True)


# ============================================================
# 직접 실행 시 테스트
# ============================================================

if __name__ == "__main__":
    # Streamlit 실행 필요
    print("Run with: streamlit run src/dashboard/pages/sensor_analysis.py")
