# ============================================================
# src/dashboard/pages/rag_query.py - RAG Query Page with Evidence Panel
# ============================================================

import streamlit as st
from datetime import datetime
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.services.api_client import api_client
from src.dashboard.components.evidence import render_evidence_panel
from src.dashboard.utils.formatters import format_latency, format_confidence, get_verification_badge


def render_rag_query():
    """Render the RAG Query page with chat interface and evidence panel"""

    st.title("💬 에러 해결 도우미")
    st.markdown("""
    **UR5e 로봇에서 발생한 에러나 문제를 입력해 주세요.**
    AI가 관련 정보를 검색하여 해결 방법을 안내해 드립니다.
    """)

    # ============================================================
    # 사용 안내 (처음 사용자를 위한 친절한 설명)
    # ============================================================

    if "chat_history" not in st.session_state or len(st.session_state.chat_history) == 0:
        st.info("""
        **💡 이렇게 질문해 보세요:**
        - 에러 코드를 알고 있다면: "C4A15 에러 해결법"
        - 증상만 알고 있다면: "로봇이 갑자기 멈췄어요"
        - 특정 부품 문제: "Joint 3 통신 에러"
        """)

    # ============================================================
    # 고급 설정 (전문가용 - 기본적으로 접혀있음)
    # ============================================================

    with st.expander("⚙️ 고급 설정 (전문가용)", expanded=False):
        st.caption("일반 사용자는 기본 설정으로 사용하시면 됩니다.")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            strategy = st.selectbox(
                "검색 방식",
                options=["hybrid", "graph_first", "vector_first"],
                index=0,
                help="hybrid: 지식그래프와 문서 검색을 함께 사용 (권장)\ngraph_first: 지식그래프 우선\nvector_first: 문서 검색 우선",
            )

        with col2:
            top_k = st.slider(
                "검색 결과 수",
                min_value=1,
                max_value=20,
                value=5,
                help="더 많은 결과를 가져오면 정확도가 올라갈 수 있지만, 응답 시간이 길어집니다.",
            )

        with col3:
            include_sources = st.checkbox(
                "출처 표시",
                value=True,
                help="답변의 근거가 되는 출처를 표시합니다.",
            )

        with col4:
            include_citation = st.checkbox(
                "인용 포함",
                value=True,
                help="답변에 인용 정보를 포함합니다.",
            )

    st.divider()

    # ============================================================
    # Initialize Session State
    # ============================================================

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "last_query_result" not in st.session_state:
        st.session_state.last_query_result = None

    # ============================================================
    # 채팅 인터페이스
    # ============================================================

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg["role"] == "assistant" and msg.get("metadata"):
                # Show quick stats in Korean
                meta = msg["metadata"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    icon, _, conf = format_confidence(meta.get("confidence", 0))
                    st.caption(f"{icon} 신뢰도: {conf}")
                with col2:
                    st.caption(f"⏱️ 응답시간: {format_latency(meta.get('latency_ms', 0))}")
                with col3:
                    badge_icon, _, badge_text = get_verification_badge(meta.get("status", "unknown"))
                    st.caption(f"{badge_icon} {badge_text}")

    # Chat input
    user_input = st.chat_input("에러 코드나 증상을 입력하세요... (예: C4A15, 로봇이 멈췄어요)")

    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input,
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Query API
        with st.chat_message("assistant"):
            with st.spinner("🔍 관련 정보를 검색하고 있습니다..."):
                result = api_client.query(
                    question=user_input,
                    top_k=top_k,
                    include_sources=include_sources,
                    include_citation=include_citation,
                )

                if result.success:
                    # Display answer
                    st.markdown(result.answer)

                    # Show quick stats in Korean
                    verification = result.verification
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        conf = verification.get("confidence", 0)
                        icon, _, conf_str = format_confidence(conf)
                        st.caption(f"{icon} 신뢰도: {conf_str}")
                    with col2:
                        st.caption(f"⏱️ 응답시간: {format_latency(result.latency_ms)}")
                    with col3:
                        status = verification.get("status", "unknown")
                        badge_icon, _, badge_text = get_verification_badge(status)
                        st.caption(f"{badge_icon} {badge_text}")

                    # Save to session state
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result.answer,
                        "metadata": {
                            "confidence": verification.get("confidence", 0),
                            "latency_ms": result.latency_ms,
                            "status": verification.get("status", "unknown"),
                        }
                    })

                    st.session_state.last_query_result = result

                else:
                    error_msg = f"❌ 오류가 발생했습니다: {result.error}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": error_msg,
                    })

    # ============================================================
    # 근거 패널 (Evidence Panel)
    # ============================================================

    if st.session_state.last_query_result:
        result = st.session_state.last_query_result

        st.divider()
        st.subheader("📚 답변 근거")
        st.caption("AI가 어떤 정보를 바탕으로 답변했는지 확인할 수 있습니다.")

        # Tabs for different views - Korean
        tab1, tab2, tab3 = st.tabs(["📖 참고 자료", "🔍 질문 분석", "📊 출처 분포"])

        with tab1:
            if result.sources:
                st.markdown("**AI가 참고한 정보들:**")

                # Convert sources to evidence format
                evidences = []
                for source in result.sources:
                    evidences.append({
                        "content": f"출처: {source.get('name', '알 수 없음')}",
                        "source_type": source.get("type", "unknown"),
                        "score": source.get("score", 0),
                        "metadata": {
                            "entity_name": source.get("name", "알 수 없음"),
                        }
                    })

                render_evidence_panel(
                    answer=result.answer,
                    evidences=evidences,
                    verification=result.verification,
                )
            else:
                st.info("참고 자료 정보가 없습니다.")

        with tab2:
            st.markdown("#### 질문 분석 결과")
            st.caption("AI가 질문을 어떻게 이해했는지 보여줍니다.")
            analysis = result.query_analysis

            if analysis:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**감지된 에러 코드:**")
                    error_codes = analysis.get("error_codes", [])
                    if error_codes:
                        for code in error_codes:
                            st.code(code)
                    else:
                        st.caption("에러 코드가 감지되지 않았습니다")

                    st.markdown("**감지된 부품:**")
                    components = analysis.get("components", [])
                    if components:
                        for comp in components:
                            st.code(comp)
                    else:
                        st.caption("특정 부품이 감지되지 않았습니다")

                with col2:
                    st.markdown("**질문 유형:**")
                    query_type = analysis.get("query_type", "unknown")
                    type_korean = {
                        "error_resolution": "에러 해결",
                        "component_info": "부품 정보",
                        "general": "일반 질문",
                    }
                    st.info(type_korean.get(query_type, query_type))

                    st.markdown("**사용된 검색 방식:**")
                    strategy = analysis.get("search_strategy", "unknown")
                    strategy_korean = {
                        "graph_first": "🔷 지식그래프 우선",
                        "vector_first": "📄 문서 검색 우선",
                        "hybrid": "🔀 복합 검색 (권장)",
                    }
                    st.info(strategy_korean.get(strategy, strategy))
            else:
                st.info("질문 분석 정보가 없습니다.")

        with tab3:
            st.markdown("#### 정보 출처 분포")
            st.caption("답변에 사용된 정보의 출처를 보여줍니다.")

            if result.sources:
                # Count by type
                graph_count = len([s for s in result.sources if s.get("type") == "graph"])
                vector_count = len([s for s in result.sources if s.get("type") == "vector"])

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("전체 출처", len(result.sources))
                with col2:
                    st.metric("지식그래프", graph_count)
                with col3:
                    st.metric("문서DB", vector_count)

                # Visual distribution
                st.markdown("**출처 비율:**")
                total = len(result.sources)
                if total > 0:
                    graph_pct = int((graph_count / total) * 100)
                    vector_pct = 100 - graph_pct

                    st.progress(graph_pct / 100, text=f"지식그래프: {graph_pct}%")
                    st.progress(vector_pct / 100, text=f"문서DB: {vector_pct}%")

                # Score distribution
                st.markdown("**관련도 점수:**")
                for i, source in enumerate(result.sources, 1):
                    score = source.get("score", 0)
                    st.progress(score, text=f"[{i}] {source.get('name', '알 수 없음')}: {score:.2f}")
            else:
                st.info("출처 정보가 없습니다.")

    # ============================================================
    # 빠른 작업 버튼
    # ============================================================

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🗑️ 대화 지우기", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.last_query_result = None
            st.rerun()

    with col2:
        if st.button("📋 답변 복사", use_container_width=True):
            if st.session_state.last_query_result:
                st.toast("답변이 클립보드에 복사되었습니다!")
            else:
                st.toast("복사할 답변이 없습니다")

    with col3:
        if st.button("📥 대화 저장", use_container_width=True):
            if st.session_state.chat_history:
                import json
                export_data = {
                    "timestamp": datetime.now().isoformat(),
                    "conversation": st.session_state.chat_history,
                }
                st.download_button(
                    "JSON 다운로드",
                    data=json.dumps(export_data, ensure_ascii=False, indent=2),
                    file_name=f"rag_대화_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )
            else:
                st.toast("저장할 대화가 없습니다")

    # ============================================================
    # 자주 묻는 질문 예시
    # ============================================================

    with st.expander("💡 자주 묻는 질문 (클릭하면 바로 질문됩니다)"):
        st.caption("아래 버튼을 클릭하면 해당 질문이 바로 전송됩니다.")

        sample_questions = [
            ("C4A15 에러가 발생했습니다. 해결 방법을 알려주세요.", "에러 코드 질문 예시"),
            ("Control Box에서 발생할 수 있는 에러들은 무엇인가요?", "부품별 에러 조회"),
            ("Joint 3 통신 문제 해결법", "통신 문제"),
            ("로봇이 갑자기 멈췄어요. 어떻게 해야 하나요?", "증상 기반 질문"),
            ("C999 에러 해결법", "존재하지 않는 에러 테스트"),
        ]

        for q, desc in sample_questions:
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(f"📝 {q}", key=f"sample_{q[:20]}", use_container_width=True):
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": q,
                    })
                    st.rerun()
            with col2:
                st.caption(desc)
