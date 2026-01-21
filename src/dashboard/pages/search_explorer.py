# ============================================================
# src/dashboard/pages/search_explorer.py - Search Explorer Page
# ============================================================

import streamlit as st
import pandas as pd
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.services.api_client import api_client
from src.dashboard.utils.formatters import format_latency, format_score, truncate_text


def render_search_explorer():
    """Render the Search Explorer page for comparing search strategies"""

    st.title("🔍 Search Explorer")
    st.caption("Compare search strategies and explore retrieval results")

    # ============================================================
    # Search Input
    # ============================================================

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        query = st.text_input(
            "Search Query",
            placeholder="Enter search query (e.g., Joint 3 communication error)",
            label_visibility="collapsed",
        )

    with col2:
        top_k = st.number_input(
            "Top-K",
            min_value=1,
            max_value=20,
            value=5,
            label_visibility="collapsed",
        )

    with col3:
        compare_mode = st.checkbox("Compare All Strategies", value=True)

    search_clicked = st.button("🔍 Search", use_container_width=True, type="primary")

    st.divider()

    # ============================================================
    # Search Results
    # ============================================================

    if search_clicked and query:
        if compare_mode:
            # Compare all strategies
            st.subheader("📊 Strategy Comparison")

            with st.spinner("Searching with all strategies..."):
                results = api_client.compare_strategies(query, top_k)

            # Summary metrics
            col1, col2, col3 = st.columns(3)

            strategies = ["graph_first", "vector_first", "hybrid"]
            strategy_labels = {
                "graph_first": "🔷 Graph First",
                "vector_first": "📄 Vector First",
                "hybrid": "🔀 Hybrid",
            }

            for i, strategy in enumerate(strategies):
                result = results.get(strategy)
                if result and result.success:
                    with [col1, col2, col3][i]:
                        st.markdown(f"### {strategy_labels[strategy]}")
                        st.metric("Results", result.total_count)
                        st.metric("Latency", format_latency(result.latency_ms))

                        if result.results:
                            avg_score = sum(r.get("score", 0) for r in result.results) / len(result.results)
                            st.metric("Avg Score", f"{avg_score:.2f}")
                else:
                    with [col1, col2, col3][i]:
                        st.markdown(f"### {strategy_labels[strategy]}")
                        st.error("Search failed")

            st.divider()

            # Detailed comparison table
            st.subheader("📋 Results Comparison")

            tabs = st.tabs([strategy_labels[s] for s in strategies])

            for i, strategy in enumerate(strategies):
                with tabs[i]:
                    result = results.get(strategy)
                    if result and result.success and result.results:
                        render_search_results(result.results, strategy)
                    else:
                        st.info("No results found")

        else:
            # Single strategy search
            strategy = st.selectbox(
                "Strategy",
                options=["hybrid", "graph_first", "vector_first"],
            )

            with st.spinner(f"Searching with {strategy}..."):
                result = api_client.search(query, top_k, strategy)

            if result.success:
                st.subheader(f"📋 Search Results ({result.total_count} found)")
                st.caption(f"Latency: {format_latency(result.latency_ms)}")

                render_search_results(result.results, strategy)

                # Query Analysis
                with st.expander("🔍 Query Analysis"):
                    analysis = result.query_analysis
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Error Codes:** {', '.join(analysis.get('error_codes', [])) or 'None'}")
                        st.markdown(f"**Components:** {', '.join(analysis.get('components', [])) or 'None'}")
                    with col2:
                        st.markdown(f"**Query Type:** {analysis.get('query_type', 'unknown')}")
                        st.markdown(f"**Strategy:** {analysis.get('search_strategy', 'unknown')}")
            else:
                st.error(f"Search failed: {result.error}")

    elif not query and search_clicked:
        st.warning("Please enter a search query")

    # ============================================================
    # Quick Search Examples
    # ============================================================

    st.divider()

    with st.expander("💡 Quick Search Examples"):
        examples = [
            "C4A15 error",
            "Joint communication lost",
            "Control Box error",
            "Safety system fault",
            "Teach Pendant connection",
        ]

        cols = st.columns(len(examples))
        for i, example in enumerate(examples):
            with cols[i]:
                if st.button(example, key=f"example_{i}", use_container_width=True):
                    st.session_state["search_query"] = example
                    st.rerun()


def render_search_results(results: list, strategy: str):
    """Render search results in a formatted way"""

    for i, result in enumerate(results, 1):
        source_type = result.get("source_type", "unknown")
        score = result.get("score", 0)
        content = result.get("content", "")
        metadata = result.get("metadata", {})

        # Header with score
        source_icon = "🔷" if source_type == "graph" else "📄"
        entity_name = metadata.get("entity_name", metadata.get("chunk_id", "Unknown"))

        with st.expander(f"{source_icon} [{i}] {entity_name} — Score: {format_score(score)}", expanded=(i <= 3)):
            # Source info
            if source_type == "graph":
                st.caption(f"📍 Source: Neo4j ({metadata.get('entity_type', 'Node')})")
            else:
                source_doc = metadata.get("source", "VectorDB")
                page = metadata.get("page", "")
                page_info = f" (Page {page})" if page else ""
                st.caption(f"📍 Source: {source_doc}{page_info}")

            st.divider()

            # Content
            st.markdown(content)

            # Metadata
            if metadata:
                st.divider()
                st.caption("**Metadata:**")
                meta_cols = st.columns(3)
                meta_items = [(k, v) for k, v in metadata.items() if k not in ["content"]]

                for j, (key, value) in enumerate(meta_items[:6]):
                    with meta_cols[j % 3]:
                        st.text(f"• {key}: {value}")

    # Export option
    if results:
        st.divider()
        if st.button("📥 Export Results as JSON"):
            import json
            st.download_button(
                "Download",
                data=json.dumps(results, ensure_ascii=False, indent=2),
                file_name="search_results.json",
                mime="application/json",
            )
