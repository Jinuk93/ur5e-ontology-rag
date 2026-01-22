# ============================================================
# src/dashboard/app.py - Streamlit Dashboard Main App
# ============================================================
# UR5e RAG System Dashboard
#
# Run with:
#   streamlit run src/dashboard/app.py
#   or
#   python scripts/run_dashboard.py
# ============================================================

import streamlit as st
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.dashboard.utils.config import config


# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT,
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/your-repo/ur5e-rag",
        "Report a bug": "https://github.com/your-repo/ur5e-rag/issues",
        "About": "# UR5e RAG Dashboard\nAI-powered error resolution system for UR5e robots."
    }
)


# ============================================================
# Custom CSS
# ============================================================

st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 1rem;
    }

    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1a2e;
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: white;
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-weight: 600;
    }

    /* Evidence cards */
    .evidence-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }

    /* Graph container */
    .graph-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden;
    }

    /* Status badges */
    .badge-verified {
        background-color: #4CAF50;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
    }

    .badge-partial {
        background-color: #FF9800;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
    }

    .badge-unverified {
        background-color: #F44336;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Sidebar Navigation
# ============================================================

with st.sidebar:
    st.image("https://img.icons8.com/color/96/robot-2.png", width=80)
    st.title("UR5e 에러 해결 도우미")
    st.caption("AI 기반 로봇 에러 진단 시스템")

    st.divider()

    # Navigation - 한글 우선, 영어는 괄호
    st.subheader("📌 메뉴 선택")

    page = st.radio(
        "페이지 선택",
        options=[
            "💬 질문하기 (RAG Query)",
            "📊 시스템 현황 (Overview)",
            "🔍 검색 탐색기 (Search Explorer)",
            "🕸️ 지식 그래프 (Knowledge Graph)",
            "📉 센서 분석 (Sensor Analysis)",
            "📈 성능 평가 (Performance)",
            "🔧 운영 모니터 (LLMOps Monitor)",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # System Status - 한글화
    st.subheader("🔌 시스템 연결 상태")

    from src.dashboard.services.api_client import api_client

    try:
        health = api_client.health_check()
        if health.get("status") == "healthy":
            st.success("✅ 서버 연결됨")
        else:
            st.warning("⚠️ 서버 연결 불안정")

        components = health.get("components", {})
        col1, col2 = st.columns(2)
        with col1:
            if components.get("vectordb") == "connected":
                st.caption("🟢 문서DB")
            else:
                st.caption("🔴 문서DB")
        with col2:
            if components.get("graphdb") == "connected":
                st.caption("🟢 지식DB")
            else:
                st.caption("🔴 지식DB")

    except Exception as e:
        st.error("🔴 서버 연결 안됨")
        st.caption("관리자에게 문의하세요")

    st.divider()

    # Help section
    st.subheader("💡 도움말")
    st.markdown("""
    **질문하기**: 에러 코드나 증상을 입력하면 AI가 해결방법을 알려드립니다.

    **예시 질문**:
    - "C4A15 에러 해결법"
    - "로봇이 갑자기 멈췄어요"
    """)

    st.divider()

    st.caption("UR5e RAG v1.0 | 문의: 관리자")


# ============================================================
# Page Routing - 한글 메뉴에 맞게 수정
# ============================================================

if page == "💬 질문하기 (RAG Query)":
    from src.dashboard.pages.rag_query import render_rag_query
    render_rag_query()

elif page == "📊 시스템 현황 (Overview)":
    from src.dashboard.pages.overview import render_overview
    render_overview()

elif page == "🔍 검색 탐색기 (Search Explorer)":
    from src.dashboard.pages.search_explorer import render_search_explorer
    render_search_explorer()

elif page == "🕸️ 지식 그래프 (Knowledge Graph)":
    from src.dashboard.pages.knowledge_graph import render_knowledge_graph
    render_knowledge_graph()

elif page == "📉 센서 분석 (Sensor Analysis)":
    from src.dashboard.pages.sensor_analysis import render_sensor_analysis
    render_sensor_analysis()

elif page == "📈 성능 평가 (Performance)":
    from src.dashboard.pages.performance import render_performance
    render_performance()

elif page == "🔧 운영 모니터 (LLMOps Monitor)":
    from src.dashboard.pages.llmops_monitor import render_llmops_monitor
    render_llmops_monitor()
