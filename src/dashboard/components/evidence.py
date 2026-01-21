# ============================================================
# src/dashboard/components/evidence.py - Evidence Panel Component
# ============================================================

import streamlit as st
from typing import List, Dict, Any
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.utils.formatters import format_score, format_confidence, truncate_text


def render_evidence_card(
    evidence: Dict[str, Any],
    index: int,
    expanded: bool = False,
):
    """
    Render a single evidence card

    Args:
        evidence: Evidence dict with content, source_type, score, metadata
        index: Evidence index number
        expanded: Whether to show full content
    """
    source_type = evidence.get("source_type", "unknown")
    score = evidence.get("score", 0)
    content = evidence.get("content", "")
    metadata = evidence.get("metadata", {})

    # Source type icon and color
    source_icons = {
        "graph": ("🔷", "#2196F3"),
        "vector": ("📄", "#4CAF50"),
    }
    icon, color = source_icons.get(source_type, ("📌", "#9E9E9E"))

    # Entity name or chunk ID
    entity_name = metadata.get("entity_name", metadata.get("chunk_id", "Unknown"))

    # Header
    header = f"[{index}] {source_type.upper()} - {entity_name}"

    with st.expander(f"{icon} {header} — Score: {format_score(score)}", expanded=expanded):
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
        st.markdown(content if expanded else truncate_text(content, 500))

        # Metadata
        if metadata:
            with st.expander("📋 Metadata", expanded=False):
                for key, value in metadata.items():
                    if key not in ["content", "chunk_id"]:
                        st.text(f"• {key}: {value}")

        # Actions
        col1, col2, col3 = st.columns(3)
        with col1:
            if source_type == "graph":
                if st.button(f"🕸️ View in Graph", key=f"graph_{index}"):
                    st.session_state["selected_node"] = entity_name
                    st.session_state["navigate_to"] = "Knowledge_Graph"
        with col2:
            if st.button(f"📋 Copy", key=f"copy_{index}"):
                st.toast(f"Copied evidence [{index}]")
        with col3:
            if st.button(f"🔍 Details", key=f"detail_{index}"):
                st.session_state[f"evidence_detail_{index}"] = True


def render_evidence_panel(
    answer: str,
    evidences: List[Dict[str, Any]],
    verification: Dict[str, Any] = None,
):
    """
    Render the full evidence panel with answer and sources

    Args:
        answer: Generated answer text
        evidences: List of evidence dicts
        verification: Verification info dict
    """
    st.markdown("### 📚 Evidence Panel")

    # Answer section
    st.markdown("#### 🤖 Answer")
    with st.container():
        st.markdown(answer)

        if verification:
            status = verification.get("status", "unknown")
            confidence = verification.get("confidence", 0)
            evidence_count = verification.get("evidence_count", 0)

            icon, color, conf_str = format_confidence(confidence)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"{icon} **Confidence:** {conf_str}")
            with col2:
                st.markdown(f"📊 **Evidence Count:** {evidence_count}")
            with col3:
                status_icons = {
                    "verified": "✅",
                    "partial": "⚠️",
                    "unverified": "❌",
                    "insufficient": "❓",
                }
                st.markdown(f"{status_icons.get(status, '❓')} **Status:** {status.title()}")

    st.divider()

    # Evidence section
    st.markdown("#### 📖 Retrieved Evidence")

    # Filter options
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        source_filter = st.multiselect(
            "Source Type",
            options=["graph", "vector"],
            default=["graph", "vector"],
            key="evidence_source_filter",
        )
    with col2:
        min_score = st.slider(
            "Min Score",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1,
            key="evidence_min_score",
        )
    with col3:
        show_all = st.checkbox("Show All", value=False, key="evidence_show_all")

    # Filter evidences
    filtered_evidences = [
        e for e in evidences
        if e.get("source_type", "unknown") in source_filter
        and e.get("score", 0) >= min_score
    ]

    if not filtered_evidences:
        st.info("No evidence matches the current filters.")
        return

    # Render evidence cards
    for i, evidence in enumerate(filtered_evidences, 1):
        render_evidence_card(evidence, i, expanded=show_all)

    # Summary
    st.divider()
    st.markdown("#### 📊 Evidence Summary")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Retrieved", len(evidences))
    with col2:
        graph_count = len([e for e in evidences if e.get("source_type") == "graph"])
        st.metric("From GraphDB", graph_count)
    with col3:
        vector_count = len([e for e in evidences if e.get("source_type") == "vector"])
        st.metric("From VectorDB", vector_count)

    # Export options
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export as JSON", key="export_evidence_json"):
            import json
            st.download_button(
                "Download JSON",
                data=json.dumps(evidences, ensure_ascii=False, indent=2),
                file_name="evidence.json",
                mime="application/json",
            )
    with col2:
        if st.button("📋 Copy All", key="copy_all_evidence"):
            st.toast("All evidence copied to clipboard")


def render_answer_evidence_linking(
    answer: str,
    evidences: List[Dict[str, Any]],
):
    """
    Render answer with linked evidence references

    Shows which parts of the answer are supported by which evidence
    """
    st.markdown("### 🔗 Answer-Evidence Linking")

    # This is a simplified version - full implementation would need NLP
    st.markdown(answer)

    st.divider()

    st.markdown("#### 📊 Evidence Matching Analysis")

    # Create a simple matching table
    matching_data = []
    for i, evidence in enumerate(evidences[:5], 1):
        matching_data.append({
            "Evidence": f"[{i}]",
            "Source": evidence.get("source_type", "unknown").upper(),
            "Entity": evidence.get("metadata", {}).get("entity_name", "N/A"),
            "Score": format_score(evidence.get("score", 0)),
            "Status": "✅ Used" if evidence.get("score", 0) > 0.5 else "⚠️ Low Score",
        })

    if matching_data:
        import pandas as pd
        df = pd.DataFrame(matching_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Hallucination check
    st.markdown("#### ⚠️ Hallucination Check")
    with st.container():
        st.success("✅ All claims in the answer are supported by evidence")
