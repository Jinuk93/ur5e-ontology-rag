# ============================================================
# src/dashboard/pages/llmops_monitor.py - LLMOps Monitoring Page
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.components.charts import render_line_chart, render_bar_chart, render_pie_chart
from src.dashboard.utils.formatters import format_tokens, format_cost, format_latency


def render_llmops_monitor():
    """Render the LLMOps Monitoring page"""

    st.title("🔧 LLMOps Monitor")
    st.caption("Real-time monitoring of LLM usage, costs, and system performance")

    # ============================================================
    # Real-time Metrics
    # ============================================================

    st.subheader("📊 Real-time Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Active Queries",
            value="0",
            delta="Idle",
            delta_color="off",
        )

    with col2:
        st.metric(
            "Queue Length",
            value="0",
            delta="No waiting",
            delta_color="normal",
        )

    with col3:
        st.metric(
            "Error Rate",
            value="0.2%",
            delta="-0.1%",
            delta_color="normal",
        )

    with col4:
        st.metric(
            "Uptime",
            value="99.9%",
            delta="+0.1%",
            delta_color="normal",
        )

    st.divider()

    # ============================================================
    # Token Usage
    # ============================================================

    st.subheader("🎫 Token Usage")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Generate sample data for visualization
        hours = list(range(24))
        token_data = [
            {"Hour": f"{h:02d}:00", "Input Tokens": random.randint(1000, 5000), "Output Tokens": random.randint(500, 2000)}
            for h in hours
        ]

        st.markdown("##### Token Usage Over Time (24h)")
        render_line_chart(
            token_data,
            x="Hour",
            y="Input Tokens",
            title="",
            height=300,
        )

    with col2:
        st.markdown("##### Today's Summary")

        total_input = 32450
        total_output = 12780
        total_tokens = total_input + total_output

        st.metric("Input Tokens", format_tokens(total_input))
        st.metric("Output Tokens", format_tokens(total_output))
        st.metric("Total Tokens", format_tokens(total_tokens))

        # Progress bar
        st.markdown("**Daily Limit Usage:**")
        daily_limit = 100000
        usage_pct = total_tokens / daily_limit
        st.progress(usage_pct, text=f"{usage_pct * 100:.1f}% of {format_tokens(daily_limit)}")

    st.divider()

    # ============================================================
    # Cost Tracking
    # ============================================================

    st.subheader("💰 Cost Tracking")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Today's Cost",
            format_cost(0.12),
            delta="-$0.02",
            delta_color="normal",
        )

    with col2:
        st.metric(
            "This Week",
            format_cost(0.83),
            delta="-$0.15",
            delta_color="normal",
        )

    with col3:
        st.metric(
            "This Month",
            format_cost(3.21),
            delta="+$0.45",
            delta_color="inverse",
        )

    # Cost breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Cost by Period")
        cost_data = [
            {"Period": "Today", "Cost": 0.12},
            {"Period": "Yesterday", "Cost": 0.14},
            {"Period": "2 Days Ago", "Cost": 0.11},
            {"Period": "3 Days Ago", "Cost": 0.15},
            {"Period": "4 Days Ago", "Cost": 0.13},
        ]
        render_bar_chart(cost_data, x="Period", y="Cost", height=250)

    with col2:
        st.markdown("##### Cost Distribution")
        distribution_data = [
            {"Category": "RAG Queries", "Percentage": 65},
            {"Category": "Embeddings", "Percentage": 20},
            {"Category": "Analysis", "Percentage": 15},
        ]
        render_pie_chart(distribution_data, names="Category", values="Percentage", height=250)

    # Budget tracking
    st.markdown("##### Monthly Budget")
    monthly_budget = 10.00
    monthly_spent = 3.21
    budget_pct = monthly_spent / monthly_budget

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.progress(budget_pct, text=f"{format_cost(monthly_spent)} / {format_cost(monthly_budget)}")
    with col2:
        st.metric("Remaining", format_cost(monthly_budget - monthly_spent))
    with col3:
        days_left = 10  # Days until month end
        daily_budget = (monthly_budget - monthly_spent) / days_left
        st.metric("Daily Budget", format_cost(daily_budget))

    st.divider()

    # ============================================================
    # Latency Distribution
    # ============================================================

    st.subheader("⏱️ Latency Distribution")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Response Time Distribution")

        latency_ranges = [
            {"Range": "< 1s", "Count": 8, "Percentage": 8},
            {"Range": "1-2s", "Count": 35, "Percentage": 35},
            {"Range": "2-3s", "Count": 42, "Percentage": 42},
            {"Range": "3-5s", "Count": 12, "Percentage": 12},
            {"Range": "> 5s", "Count": 3, "Percentage": 3},
        ]

        for item in latency_ranges:
            st.progress(item["Percentage"] / 100, text=f"{item['Range']}: {item['Percentage']}%")

    with col2:
        st.markdown("##### Latency Percentiles")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("P50", "2.1s")
        with col_b:
            st.metric("P95", "4.2s")
        with col_c:
            st.metric("P99", "5.8s")

        st.markdown("##### By Component")
        components_latency = [
            {"Component": "Query Analysis", "Time": "0.05s", "Percentage": 2},
            {"Component": "Graph Retrieval", "Time": "0.82s", "Percentage": 24},
            {"Component": "Vector Retrieval", "Time": "0.45s", "Percentage": 13},
            {"Component": "LLM Generation", "Time": "1.95s", "Percentage": 58},
            {"Component": "Verification", "Time": "0.12s", "Percentage": 3},
        ]

        for comp in components_latency:
            st.progress(comp["Percentage"] / 100, text=f"{comp['Component']}: {comp['Time']} ({comp['Percentage']}%)")

    st.divider()

    # ============================================================
    # Error Log
    # ============================================================

    st.subheader("📋 Recent Logs")

    log_entries = [
        {"Time": "14:32:15", "Level": "WARN", "Message": "Neo4j connection timeout - retrying", "Component": "GraphDB"},
        {"Time": "14:28:03", "Level": "ERROR", "Message": "OpenAI rate limit exceeded", "Component": "LLM"},
        {"Time": "14:15:22", "Level": "INFO", "Message": "Service recovered from rate limit", "Component": "LLM"},
        {"Time": "14:10:45", "Level": "INFO", "Message": "Cache cleared successfully", "Component": "System"},
        {"Time": "14:05:18", "Level": "WARN", "Message": "High latency detected (>5s)", "Component": "RAG"},
    ]

    for log in log_entries:
        level = log["Level"]
        if level == "ERROR":
            icon = "🔴"
        elif level == "WARN":
            icon = "🟡"
        else:
            icon = "🟢"

        st.text(f"[{log['Time']}] {icon} {level:5} | {log['Component']:8} | {log['Message']}")

    # Log filters
    with st.expander("🔍 Log Filters"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.multiselect("Level", options=["INFO", "WARN", "ERROR"], default=["WARN", "ERROR"])
        with col2:
            st.multiselect("Component", options=["System", "LLM", "GraphDB", "VectorDB", "RAG"])
        with col3:
            st.date_input("Date Range", value=datetime.now())

    st.divider()

    # ============================================================
    # Model Configuration
    # ============================================================

    st.subheader("⚙️ Model Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Current Configuration")
        config_data = {
            "LLM Model": "gpt-4o-mini",
            "Embedding Model": "text-embedding-3-small",
            "Max Tokens": "4096",
            "Temperature": "0.0",
            "Top-K Default": "5",
        }

        for key, value in config_data.items():
            st.text(f"• {key}: {value}")

    with col2:
        st.markdown("##### Model Pricing")
        pricing_data = {
            "Input (GPT-4o-mini)": "$0.15 / 1M tokens",
            "Output (GPT-4o-mini)": "$0.60 / 1M tokens",
            "Embedding": "$0.02 / 1M tokens",
        }

        for key, value in pricing_data.items():
            st.text(f"• {key}: {value}")

    # ============================================================
    # Export & Actions
    # ============================================================

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📥 Export Metrics", use_container_width=True):
            st.toast("Metrics exported to CSV")

    with col2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    with col3:
        if st.button("⚠️ Clear Cache", use_container_width=True):
            st.toast("Cache cleared successfully")

    # Footer
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
