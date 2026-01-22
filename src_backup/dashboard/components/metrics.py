# ============================================================
# src/dashboard/components/metrics.py - Metric Display Components
# ============================================================

import streamlit as st


def render_metric_card(
    label: str,
    value: str,
    delta: str = None,
    delta_color: str = "normal",
    icon: str = None,
    help_text: str = None,
):
    """
    Render a metric card with optional delta and icon

    Args:
        label: Metric label
        value: Metric value
        delta: Change from previous value
        delta_color: "normal", "inverse", or "off"
        icon: Emoji icon to display
        help_text: Tooltip text
    """
    if icon:
        label = f"{icon} {label}"

    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text,
    )


def render_metric_row(metrics: list, columns: int = 4):
    """
    Render a row of metric cards

    Args:
        metrics: List of metric dicts with keys: label, value, delta, icon
        columns: Number of columns
    """
    cols = st.columns(columns)

    for i, metric in enumerate(metrics):
        with cols[i % columns]:
            render_metric_card(
                label=metric.get("label", ""),
                value=metric.get("value", ""),
                delta=metric.get("delta"),
                delta_color=metric.get("delta_color", "normal"),
                icon=metric.get("icon"),
                help_text=metric.get("help"),
            )


def render_status_indicator(status: str, label: str = None):
    """
    Render a status indicator (online/offline/warning)

    Args:
        status: "online", "offline", "warning", "error"
        label: Optional label text
    """
    status_config = {
        "online": ("🟢", "green", "Online"),
        "offline": ("🔴", "red", "Offline"),
        "warning": ("🟡", "orange", "Warning"),
        "error": ("🔴", "red", "Error"),
        "healthy": ("✅", "green", "Healthy"),
    }

    icon, color, default_label = status_config.get(
        status.lower(), ("⚪", "gray", status)
    )

    display_label = label or default_label
    st.markdown(f"{icon} **{display_label}**")


def render_kpi_dashboard(kpis: dict):
    """
    Render a KPI dashboard with multiple metrics

    Args:
        kpis: Dict with KPI categories and their metrics
    """
    for category, metrics in kpis.items():
        st.subheader(category)
        render_metric_row(metrics)
        st.divider()
