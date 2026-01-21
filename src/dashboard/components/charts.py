# ============================================================
# src/dashboard/components/charts.py - Chart Components
# ============================================================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any


def render_bar_chart(
    data: List[Dict],
    x: str,
    y: str,
    title: str = None,
    color: str = None,
    orientation: str = "v",
    height: int = 400,
):
    """
    Render a bar chart using Plotly

    Args:
        data: List of dicts with data
        x: X-axis column name
        y: Y-axis column name
        title: Chart title
        color: Column for color encoding
        orientation: "v" for vertical, "h" for horizontal
        height: Chart height in pixels
    """
    import pandas as pd
    df = pd.DataFrame(data)

    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        orientation=orientation,
        title=title,
    )

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_line_chart(
    data: List[Dict],
    x: str,
    y: str,
    title: str = None,
    color: str = None,
    height: int = 400,
):
    """
    Render a line chart using Plotly
    """
    import pandas as pd
    df = pd.DataFrame(data)

    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        markers=True,
    )

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_pie_chart(
    data: List[Dict],
    names: str,
    values: str,
    title: str = None,
    height: int = 400,
    hole: float = 0.3,
):
    """
    Render a pie/donut chart using Plotly
    """
    import pandas as pd
    df = pd.DataFrame(data)

    fig = px.pie(
        df,
        names=names,
        values=values,
        title=title,
        hole=hole,
    )

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_gauge_chart(
    value: float,
    title: str = None,
    min_val: float = 0,
    max_val: float = 100,
    thresholds: Dict[str, float] = None,
    height: int = 250,
):
    """
    Render a gauge chart for showing progress/scores
    """
    if thresholds is None:
        thresholds = {"red": 40, "yellow": 70, "green": 100}

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title},
        gauge={
            "axis": {"range": [min_val, max_val]},
            "bar": {"color": "#2196F3"},
            "steps": [
                {"range": [min_val, thresholds.get("red", 40)], "color": "#ffcdd2"},
                {"range": [thresholds.get("red", 40), thresholds.get("yellow", 70)], "color": "#fff9c4"},
                {"range": [thresholds.get("yellow", 70), max_val], "color": "#c8e6c9"},
            ],
        }
    ))

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_comparison_table(
    data: List[Dict],
    columns: List[str],
    highlight_column: str = None,
    title: str = None,
):
    """
    Render a comparison table with optional highlighting
    """
    import pandas as pd

    if title:
        st.subheader(title)

    df = pd.DataFrame(data)

    if highlight_column and highlight_column in df.columns:
        # Apply styling to highlight best values
        def highlight_max(s):
            is_max = s == s.max()
            return ['background-color: #c8e6c9' if v else '' for v in is_max]

        styled_df = df.style.apply(highlight_max, subset=[highlight_column])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)


def render_latency_histogram(
    latencies: List[float],
    title: str = "Latency Distribution",
    height: int = 300,
):
    """
    Render a histogram of latency values
    """
    fig = px.histogram(
        x=latencies,
        nbins=20,
        title=title,
        labels={"x": "Latency (ms)", "y": "Count"},
    )

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)
