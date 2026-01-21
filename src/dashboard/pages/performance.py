# ============================================================
# src/dashboard/pages/performance.py - Performance Evaluation Page
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.services.api_client import api_client
from src.dashboard.components.charts import render_bar_chart, render_gauge_chart, render_comparison_table
from src.dashboard.utils.formatters import format_latency


def render_performance():
    """Render the Performance Evaluation page"""

    st.title("📈 Performance Evaluation")
    st.caption("RAG system performance metrics, benchmarks, and phase comparisons")

    # ============================================================
    # Score Cards
    # ============================================================

    st.subheader("🎯 Key Performance Indicators")

    col1, col2, col3 = st.columns(3)

    with col1:
        render_gauge_chart(
            value=82.5,
            title="Accuracy",
            min_val=0,
            max_val=100,
            height=200,
        )
        st.caption("Based on benchmark test results")

    with col2:
        render_gauge_chart(
            value=95.2,
            title="Hallucination Prevention",
            min_val=0,
            max_val=100,
            height=200,
        )
        st.caption("Invalid error code detection rate")

    with col3:
        render_gauge_chart(
            value=78.3,
            title="Recall",
            min_val=0,
            max_val=100,
            height=200,
        )
        st.caption("Relevant information retrieval rate")

    st.divider()

    # ============================================================
    # Phase Comparison
    # ============================================================

    st.subheader("📊 Phase Comparison")

    phase_data = [
        {"Phase": "Phase 5 (VectorDB Only)", "Accuracy": 65, "Hallucination Prevention": 0, "Avg Latency (s)": 5.2, "Graph Usage": 0},
        {"Phase": "Phase 6 (Hybrid)", "Accuracy": 75, "Hallucination Prevention": 45, "Avg Latency (s)": 4.5, "Graph Usage": 60},
        {"Phase": "Phase 7 (Verifier)", "Accuracy": 82, "Hallucination Prevention": 95, "Avg Latency (s)": 4.2, "Graph Usage": 65},
        {"Phase": "Phase 8 (API)", "Accuracy": 82.5, "Hallucination Prevention": 95.2, "Avg Latency (s)": 3.4, "Graph Usage": 68},
    ]

    df = pd.DataFrame(phase_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Visualization
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Accuracy Improvement")
        render_bar_chart(
            phase_data,
            x="Phase",
            y="Accuracy",
            title="",
            height=300,
        )

    with col2:
        st.markdown("##### Hallucination Prevention")
        render_bar_chart(
            phase_data,
            x="Phase",
            y="Hallucination Prevention",
            title="",
            height=300,
        )

    st.divider()

    # ============================================================
    # Strategy Performance
    # ============================================================

    st.subheader("🔀 Search Strategy Performance")

    strategy_data = [
        {"Strategy": "graph_first", "Accuracy": 85, "Avg Latency (ms)": 800, "Best For": "Error code queries"},
        {"Strategy": "vector_first", "Accuracy": 62, "Avg Latency (ms)": 600, "Best For": "General questions"},
        {"Strategy": "hybrid", "Accuracy": 88, "Avg Latency (ms)": 1200, "Best For": "Complex queries"},
    ]

    col1, col2 = st.columns([2, 1])

    with col1:
        st.dataframe(pd.DataFrame(strategy_data), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("##### Accuracy by Strategy")
        for s in strategy_data:
            pct = s["Accuracy"] / 100
            st.progress(pct, text=f"{s['Strategy']}: {s['Accuracy']}%")

    st.divider()

    # ============================================================
    # Benchmark Tests
    # ============================================================

    st.subheader("🧪 Benchmark Tests")

    # Test cases
    test_cases = [
        {"Query": "C4A15 에러 해결법", "Expected": "VERIFIED", "Type": "Error Resolution"},
        {"Query": "C999 에러 해결법", "Expected": "INSUFFICIENT", "Type": "Invalid Error"},
        {"Query": "C100 에러", "Expected": "INSUFFICIENT", "Type": "Out of Range"},
        {"Query": "Control Box 에러 목록", "Expected": "VERIFIED", "Type": "Component Query"},
        {"Query": "로봇이 갑자기 멈췄어요", "Expected": "PARTIAL/VERIFIED", "Type": "General Question"},
    ]

    # Run tests button
    if st.button("▶️ Run Benchmark Tests", type="primary"):
        st.markdown("#### Test Results")

        results = []
        progress_bar = st.progress(0)

        for i, test in enumerate(test_cases):
            with st.spinner(f"Testing: {test['Query'][:30]}..."):
                result = api_client.query(test["Query"], top_k=3)

                if result.success:
                    actual_status = result.verification.get("status", "unknown").upper()
                    expected = test["Expected"]

                    # Check if passed
                    passed = actual_status in expected.split("/")

                    results.append({
                        "Query": test["Query"],
                        "Type": test["Type"],
                        "Expected": expected,
                        "Actual": actual_status,
                        "Passed": "✅" if passed else "❌",
                        "Latency": format_latency(result.latency_ms),
                        "Confidence": f"{result.verification.get('confidence', 0) * 100:.0f}%",
                    })
                else:
                    results.append({
                        "Query": test["Query"],
                        "Type": test["Type"],
                        "Expected": test["Expected"],
                        "Actual": "ERROR",
                        "Passed": "❌",
                        "Latency": "-",
                        "Confidence": "-",
                    })

            progress_bar.progress((i + 1) / len(test_cases))

        # Display results
        df_results = pd.DataFrame(results)
        st.dataframe(df_results, use_container_width=True, hide_index=True)

        # Summary
        passed_count = len([r for r in results if r["Passed"] == "✅"])
        total_count = len(results)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tests", total_count)
        with col2:
            st.metric("Passed", passed_count)
        with col3:
            st.metric("Pass Rate", f"{passed_count / total_count * 100:.0f}%")

    else:
        # Show test cases
        st.markdown("**Predefined Test Cases:**")
        st.dataframe(pd.DataFrame(test_cases), use_container_width=True, hide_index=True)

    st.divider()

    # ============================================================
    # Custom Test
    # ============================================================

    st.subheader("🔬 Custom Test")

    col1, col2 = st.columns([3, 1])

    with col1:
        custom_query = st.text_input(
            "Test Query",
            placeholder="Enter a test query...",
        )

    with col2:
        custom_expected = st.selectbox(
            "Expected Result",
            options=["VERIFIED", "PARTIAL", "UNVERIFIED", "INSUFFICIENT"],
        )

    if st.button("🧪 Run Custom Test"):
        if custom_query:
            with st.spinner("Testing..."):
                result = api_client.query(custom_query, top_k=5)

                if result.success:
                    actual_status = result.verification.get("status", "unknown").upper()
                    passed = actual_status == custom_expected

                    if passed:
                        st.success(f"✅ Test PASSED - Actual: {actual_status}")
                    else:
                        st.error(f"❌ Test FAILED - Expected: {custom_expected}, Actual: {actual_status}")

                    # Details
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Latency", format_latency(result.latency_ms))
                    with col2:
                        st.metric("Confidence", f"{result.verification.get('confidence', 0) * 100:.0f}%")
                    with col3:
                        st.metric("Evidence Count", result.verification.get("evidence_count", 0))

                    # Answer preview
                    with st.expander("View Answer"):
                        st.markdown(result.answer)
                else:
                    st.error(f"Test failed with error: {result.error}")
        else:
            st.warning("Please enter a query to test")

    # ============================================================
    # Performance Tips
    # ============================================================

    st.divider()

    with st.expander("💡 Performance Optimization Tips"):
        st.markdown("""
        ### How to Improve RAG Performance

        1. **Use Specific Queries**
           - Include error codes when known (e.g., "C4A15 에러")
           - Mention component names explicitly

        2. **Choose the Right Strategy**
           - `graph_first`: Best for error code queries
           - `vector_first`: Best for general troubleshooting
           - `hybrid`: Best for complex, multi-part queries

        3. **Optimize Top-K**
           - Lower values (3-5) for specific queries
           - Higher values (10-15) for exploratory queries

        4. **Trust the Verifier**
           - "INSUFFICIENT" means the system correctly identified missing information
           - Don't ignore "PARTIAL" warnings
        """)
