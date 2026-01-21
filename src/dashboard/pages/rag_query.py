# ============================================================
# src/dashboard/pages/rag_query.py - UR5e 기술 지원 시스템
# ============================================================
# UX 개선 v7: 포맷 수정, 패턴 상세, 예제 질문 다양화
# ============================================================

import streamlit as st
from datetime import datetime, timedelta
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.services.api_client import api_client
from src.dashboard.components.evidence import render_evidence_panel
from src.dashboard.utils.formatters import format_latency, format_confidence, get_verification_badge


# ============================================================
# 예제 질문 (실제 존재하는 에러코드 범위 C0~C55 기반 + 다양화)
# ============================================================

SAMPLE_QUESTIONS = [
    # === 에러 코드 (C0~C55 범위 내 다양한 코드) ===
    {"q": "C10 에러가 발생했습니다. 원인과 해결방법을 알려주세요.", "cat": "에러코드", "desc": "로봇 비상정지"},
    {"q": "C23 에러가 반복됩니다. 어떻게 해야 하나요?", "cat": "에러코드", "desc": "조인트 통신 오류"},
    {"q": "C35 에러 코드의 의미와 조치 방법", "cat": "에러코드", "desc": "안전 시스템 오류"},
    {"q": "C99 에러가 발생했는데 코드를 못 찾겠어요", "cat": "에러코드", "desc": "알 수 없는 에러"},

    # === 증상 기반 ===
    {"q": "로봇이 작업 중 갑자기 멈췄어요", "cat": "증상", "desc": "급정지 증상"},
    {"q": "로봇 팔에서 진동이 느껴집니다", "cat": "증상", "desc": "진동 증상"},
    {"q": "로봇에서 평소와 다른 소리가 납니다", "cat": "증상", "desc": "이상 소음"},
    {"q": "특정 조인트가 뜨겁습니다", "cat": "증상", "desc": "과열 증상"},

    # === 부품/구성요소 ===
    {"q": "Joint 3에서 자주 발생하는 에러와 해결법", "cat": "부품", "desc": "조인트3 관련"},
    {"q": "Control Box 관련 에러 종류와 대처법", "cat": "부품", "desc": "컨트롤박스 관련"},
    {"q": "Tool Flange 연결 문제 해결", "cat": "부품", "desc": "툴플랜지 관련"},
    {"q": "Safety IO 설정 및 오류 해결", "cat": "부품", "desc": "안전IO 관련"},

    # === 센서 데이터 분석 ===
    {"q": "Fz 값이 100N을 초과했을 때 발생할 수 있는 문제", "cat": "센서데이터", "desc": "Z축 힘 초과"},
    {"q": "Tx, Ty 토크값이 급격히 변할 때 원인", "cat": "센서데이터", "desc": "토크 급변"},
    {"q": "센서에서 충돌 패턴이 감지됐습니다", "cat": "센서데이터", "desc": "충돌 패턴"},
    {"q": "진동 패턴 감지 시 확인 사항", "cat": "센서데이터", "desc": "진동 패턴"},

    # === 매뉴얼/운영 ===
    {"q": "로봇 정기 점검 주기와 항목", "cat": "매뉴얼", "desc": "유지보수 가이드"},
    {"q": "Freedrive 모드 진입 및 사용법", "cat": "매뉴얼", "desc": "프리드라이브"},
    {"q": "브레이크 수동 해제 절차", "cat": "매뉴얼", "desc": "브레이크 해제"},
    {"q": "비상정지 후 안전하게 재시작하는 방법", "cat": "매뉴얼", "desc": "재시작 절차"},
]

MAX_CONVERSATION_TABS = 5


def execute_query(question: str, strategy: str, top_k: int, include_sources: bool):
    """질문 실행 및 결과 반환"""
    result = api_client.query(
        question=question,
        top_k=top_k,
        include_sources=include_sources,
        include_citation=True,
        strategy=strategy,
    )
    return result


def initialize_session_state():
    """세션 상태 초기화"""
    if "conversations" not in st.session_state:
        st.session_state.conversations = {
            0: {"name": "대화 1", "history": [], "last_result": None}
        }
    if "current_conv_id" not in st.session_state:
        st.session_state.current_conv_id = 0
    if "next_conv_id" not in st.session_state:
        st.session_state.next_conv_id = 1
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None
    if "selected_pattern" not in st.session_state:
        st.session_state.selected_pattern = None


def get_current_conversation():
    """현재 선택된 대화 가져오기"""
    conv_id = st.session_state.current_conv_id
    if conv_id not in st.session_state.conversations:
        st.session_state.conversations[conv_id] = {
            "name": f"대화 {conv_id + 1}",
            "history": [],
            "last_result": None
        }
    return st.session_state.conversations[conv_id]


def add_new_conversation():
    """새 대화 추가"""
    if len(st.session_state.conversations) >= MAX_CONVERSATION_TABS:
        st.toast(f"최대 {MAX_CONVERSATION_TABS}개 대화까지 가능합니다")
        return

    new_id = st.session_state.next_conv_id
    st.session_state.conversations[new_id] = {
        "name": f"대화 {new_id + 1}",
        "history": [],
        "last_result": None
    }
    st.session_state.current_conv_id = new_id
    st.session_state.next_conv_id += 1


def render_sensor_monitoring():
    """센서 측정 데이터 모니터링"""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    st.markdown("### 📊 센서 측정 현황 (Axia80 힘/토크 센서)")
    st.caption("**Fz** : Z축 힘 (수직 방향, 단위: N) | **Tx** : X축 토크 (단위: Nm) | **Ty** : Y축 토크 (단위: Nm)")

    # 7일치 날짜
    end_date = datetime.now()
    start_date = end_date - timedelta(days=6)
    dates = [(datetime.now() - timedelta(days=i)).strftime("%m/%d") for i in range(6, -1, -1)]
    date_range = f"{start_date.strftime('%Y.%m.%d')} ~ {end_date.strftime('%Y.%m.%d')}"

    # 센서 측정값 (시뮬레이션)
    fz_avg = [23.5, 25.2, 24.8, 26.1, 24.5, 25.8, 27.2]
    fz_max = [45.2, 52.8, 48.3, 55.1, 47.6, 51.2, 58.4]
    fz_min = [5.1, 4.8, 5.3, 4.9, 5.2, 4.7, 5.0]
    tx_avg = [1.2, 1.4, 1.3, 1.5, 1.3, 1.4, 1.6]
    ty_avg = [0.8, 0.9, 0.85, 0.95, 0.88, 0.92, 1.0]

    # 패턴 상세 데이터
    pattern_details = {
        "충돌": [
            {"date": dates[0], "time": "14:23:15", "fz": 82.5, "tx": 3.2, "ty": 2.8},
            {"date": dates[2], "time": "09:15:42", "fz": 78.3, "tx": 2.9, "ty": 3.1},
            {"date": dates[2], "time": "16:45:08", "fz": 85.1, "tx": 3.5, "ty": 2.6},
            {"date": dates[4], "time": "11:32:21", "fz": 79.8, "tx": 3.0, "ty": 2.9},
            {"date": dates[6], "time": "08:17:33", "fz": 81.2, "tx": 3.3, "ty": 2.7},
        ],
        "진동": [
            {"date": dates[1], "time": "10:45:22", "fz": 28.3, "tx": 4.2, "ty": 3.8},
            {"date": dates[3], "time": "15:22:11", "fz": 31.5, "tx": 4.5, "ty": 4.1},
            {"date": dates[4], "time": "13:18:45", "fz": 29.8, "tx": 4.8, "ty": 3.9},
            {"date": dates[4], "time": "17:55:33", "fz": 32.1, "tx": 4.3, "ty": 4.2},
            {"date": dates[5], "time": "09:30:15", "fz": 30.2, "tx": 4.6, "ty": 4.0},
        ],
        "과부하": [
            {"date": dates[2], "time": "12:33:18", "fz": 95.2, "tx": 5.1, "ty": 4.8},
            {"date": dates[5], "time": "14:45:22", "fz": 98.5, "tx": 5.3, "ty": 5.0},
        ],
        "드리프트": [
            {"date": dates[0], "time": "16:12:45", "fz": 35.2, "tx": 1.8, "ty": 1.5},
            {"date": dates[3], "time": "11:22:33", "fz": 36.8, "tx": 1.9, "ty": 1.6},
            {"date": dates[6], "time": "10:15:28", "fz": 34.5, "tx": 1.7, "ty": 1.4},
        ],
    }

    patterns = {
        "충돌": [1, 0, 2, 0, 1, 0, 1],
        "진동": [0, 1, 0, 1, 2, 1, 0],
        "과부하": [0, 0, 1, 0, 0, 1, 0],
        "드리프트": [1, 0, 0, 1, 0, 0, 1],
    }

    total_records = 7 * 24 * 360

    col1, col2 = st.columns([2.5, 1])

    with col1:
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("힘 측정값 (Fz) - N", "토크 측정값 (Tx, Ty) - Nm"),
            vertical_spacing=0.18,
            row_heights=[0.5, 0.5]
        )

        fig.add_trace(go.Scatter(name="Fz 평균", x=dates, y=fz_avg, mode="lines+markers",
                      line=dict(color="#2196F3", width=2), marker=dict(size=8)), row=1, col=1)
        fig.add_trace(go.Scatter(name="Fz 최대", x=dates, y=fz_max, mode="lines",
                      line=dict(color="#f44336", width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(name="Fz 최소", x=dates, y=fz_min, mode="lines",
                      line=dict(color="#4CAF50", width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(name="Tx 평균", x=dates, y=tx_avg, mode="lines+markers",
                      line=dict(color="#FF9800", width=2), marker=dict(size=8)), row=2, col=1)
        fig.add_trace(go.Scatter(name="Ty 평균", x=dates, y=ty_avg, mode="lines+markers",
                      line=dict(color="#9C27B0", width=2), marker=dict(size=8)), row=2, col=1)

        fig.update_layout(height=300, margin=dict(l=20, r=20, t=35, b=20),
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                         font=dict(size=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"<p style='font-size:11px; color:#888;'>기간 : {date_range}</p>", unsafe_allow_html=True)

        latest_fz = fz_avg[-1]
        status_icon = "🟢" if latest_fz < 30 else "🟡" if latest_fz < 50 else "🔴"
        status_text = "정상" if latest_fz < 30 else "주의" if latest_fz < 50 else "경고"

        st.markdown(f"""
        <div style="font-size:12px;">
            <b>상태</b> : {status_icon} {status_text}<br>
            <b>Fz 평균</b> : {fz_avg[-1]:.1f} N <span style="color:{'#4CAF50' if fz_avg[-1]-fz_avg[-2] < 0 else '#f44336'}">({fz_avg[-1]-fz_avg[-2]:+.1f})</span><br>
            <b>Fz 최대</b> : {fz_max[-1]:.1f} N<br>
            <b>총 레코드</b> : {total_records:,}개
        </div>
        """, unsafe_allow_html=True)

    # 패턴 감지 현황
    st.markdown("**감지된 이상 패턴 (7일간)**")

    pattern_cols = st.columns(4)
    pattern_colors = {"충돌": "#f44336", "진동": "#FF9800", "과부하": "#9C27B0", "드리프트": "#2196F3"}

    for i, (pattern_name, counts) in enumerate(patterns.items()):
        with pattern_cols[i]:
            total = sum(counts)
            today = counts[-1]
            color = pattern_colors[pattern_name]

            if st.button(f"{pattern_name} : {total}건", key=f"pattern_{pattern_name}", use_container_width=True):
                st.session_state.selected_pattern = pattern_name if st.session_state.selected_pattern != pattern_name else None
                st.rerun()

    # 선택된 패턴 상세 표시
    if st.session_state.selected_pattern and st.session_state.selected_pattern in pattern_details:
        pattern_name = st.session_state.selected_pattern
        details = pattern_details[pattern_name]
        color = pattern_colors[pattern_name]

        st.markdown(f"""
        <div style="background-color: {color}15; padding: 12px; border-radius: 8px; border-left: 4px solid {color}; margin-top: 8px;">
            <b>{pattern_name} 패턴 상세 ({len(details)}건)</b>
        </div>
        """, unsafe_allow_html=True)

        detail_cols = st.columns(len(details))
        for j, detail in enumerate(details):
            with detail_cols[j]:
                st.markdown(f"""
                <div style="font-size:11px; background:#f5f5f5; padding:8px; border-radius:4px; text-align:center;">
                    <b>{detail['date']}</b><br>
                    {detail['time']}<br>
                    Fz: {detail['fz']}N<br>
                    Tx: {detail['tx']}Nm
                </div>
                """, unsafe_allow_html=True)


def render_source_with_excerpt(source: dict, index: int):
    """발췌글이 포함된 소스 카드 렌더링"""
    score = source.get("score", 0)
    name = source.get("name", source.get("metadata", {}).get("entity_name", "알 수 없음"))
    src_type = source.get("type", source.get("source_type", "unknown"))
    content = source.get("content", source.get("text", source.get("metadata", {}).get("content", "")))

    type_name = "지식그래프" if src_type == "graph" else "문서DB"
    type_icon = "🔷" if src_type == "graph" else "📄"
    type_color = "#2196F3" if src_type == "graph" else "#4CAF50"
    badge = "높음" if score >= 0.7 else "보통" if score >= 0.4 else "낮음"

    with st.expander(f"{type_icon} [{index}] {name} - 신뢰도 : {score*100:.0f}% ({badge})", expanded=True):
        st.markdown(f"**출처** : {type_name} | **신뢰도** : {score*100:.1f}%")

        if content:
            st.markdown(f"""
            <div style="background-color: #f5f5f5; border-left: 4px solid {type_color};
                        padding: 10px 14px; margin: 8px 0; border-radius: 4px; font-size: 13px;">
                {content[:400]}{'...' if len(content) > 400 else ''}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("발췌 내용 없음")


def render_rag_query():
    """UR5e 기술 지원 시스템 메인 페이지"""

    initialize_session_state()

    st.markdown("""
    <style>
    .stChatInput textarea { font-size: 16px !important; min-height: 50px !important; }
    .stChatInput textarea::placeholder { text-align: left !important; }
    </style>
    """, unsafe_allow_html=True)

    # ============================================================
    # 1. 제목 및 가이드 (항상 펼침, 포맷 수정)
    # ============================================================

    st.title("UR5e 기술 지원 시스템")

    with st.expander("📖 프로젝트 소개 및 사용 가이드", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            **프로젝트 배경**

            UR5e 협동 로봇의 에러 진단 및 해결 지원 시스템입니다.

            현장에서 에러 발생 시 매뉴얼 검색, 전문가 문의 시간을 단축합니다.

            **데이터 구성**
            - 지식그래프 : 에러 170개, 원인 85개, 해결책 120개
            - 문서DB : 매뉴얼 1,750 청크
            - 센서DB : 7일간 60,480 레코드
            """)

        with col2:
            st.markdown("""
            **구현 기능**

            | 기능 | 설명 |
            |------|------|
            | 에러코드 검색 | 에러코드 입력 시 원인, 해결책, 관련 부품을 지식그래프에서 탐색 |
            | 증상 기반 검색 | 자연어 증상 설명으로 관련 에러코드 후보 제시 |
            | 매뉴얼 검색 | UR5e 매뉴얼에서 유사 내용 검색 |
            | 센서 연계 분석 | Fz/Tx/Ty 측정값과 에러 패턴 연계 |
            """)

        with col3:
            st.markdown("""
            **테스트 방법**

            1. **에러코드** : "C10 에러" 입력
            2. **증상** : "로봇이 멈췄어요" 입력
            3. **부품** : "Joint 3 에러" 입력
            4. **센서** : "Fz 값이 높을 때" 입력

            아래 예제 질문을 클릭하면 바로 테스트할 수 있습니다.
            """)

    st.divider()

    # ============================================================
    # 2. 센서 측정 데이터 모니터링
    # ============================================================

    render_sensor_monitoring()

    st.divider()

    # ============================================================
    # 3. 대화 탭
    # ============================================================

    st.markdown("### 대화 목록")

    conv_cols = st.columns(MAX_CONVERSATION_TABS + 1)

    for i, (conv_id, conv_data) in enumerate(st.session_state.conversations.items()):
        with conv_cols[i]:
            is_current = conv_id == st.session_state.current_conv_id
            btn_type = "primary" if is_current else "secondary"
            label = conv_data["name"]
            if conv_data["history"]:
                label += f" ({len(conv_data['history'])//2})"

            if st.button(label, key=f"conv_tab_{conv_id}", type=btn_type, use_container_width=True):
                st.session_state.current_conv_id = conv_id
                st.rerun()

    with conv_cols[len(st.session_state.conversations)]:
        if len(st.session_state.conversations) < MAX_CONVERSATION_TABS:
            if st.button("+ 새 대화", key="add_conv", use_container_width=True):
                add_new_conversation()
                st.rerun()

    st.divider()

    # ============================================================
    # 4. 질문 입력
    # ============================================================

    user_input = st.chat_input("질문을 입력하세요")

    if st.session_state.pending_question:
        user_input = st.session_state.pending_question
        st.session_state.pending_question = None

    # ============================================================
    # 5. 예제 질문
    # ============================================================

    with st.expander("💡 예제 질문  (클릭하면 바로 답변)", expanded=True):

        cat_tabs = st.tabs(["에러코드", "증상", "부품", "센서데이터", "매뉴얼"])
        categories = ["에러코드", "증상", "부품", "센서데이터", "매뉴얼"]

        tab_descriptions = {
            "에러코드": "화면에 표시된 에러코드(C10, C23 등)를 입력하세요. 원인, 해결책, 관련 부품 정보를 제공합니다.",
            "증상": "로봇에서 관찰된 증상을 설명하세요. 관련 에러코드와 점검 사항을 안내합니다.",
            "부품": "문제가 발생한 부품명(Joint, Control Box 등)을 입력하세요.",
            "센서데이터": "Axia80 센서 측정값(Fz, Tx, Ty) 관련 질문을 하세요. 패턴과 에러를 연계 분석합니다.",
            "매뉴얼": "UR5e 운영, 유지보수, 설정 관련 질문을 하세요."
        }

        for cat_tab, category in zip(cat_tabs, categories):
            with cat_tab:
                st.caption(tab_descriptions[category])

                questions = [q for q in SAMPLE_QUESTIONS if q["cat"] == category]
                cols = st.columns(2)
                for i, q_data in enumerate(questions):
                    with cols[i % 2]:
                        if st.button(q_data['q'], key=f"q_{category}_{i}", use_container_width=True, help=q_data['desc']):
                            st.session_state.pending_question = q_data['q']
                            st.rerun()

    st.divider()

    # ============================================================
    # 6. 대화 영역
    # ============================================================

    current_conv = get_current_conversation()
    st.markdown(f"### {current_conv['name']}")

    for msg in current_conv["history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg["role"] == "assistant" and msg.get("meta"):
                meta = msg["meta"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    conf = meta.get("confidence", 0)
                    conf_icon = "🟢" if conf >= 0.7 else "🟡" if conf >= 0.4 else "🔴"
                    st.caption(f"{conf_icon} 신뢰도 : {conf*100:.0f}%")
                with col2:
                    st.caption(f"응답시간 : {meta.get('latency', 0):.0f}ms")
                with col3:
                    status = meta.get("status", "unknown")
                    status_text = {"verified": "검증됨", "partial": "부분검증", "unverified": "미검증"}.get(status, status)
                    st.caption(f"상태 : {status_text}")

                # 각 답변별 근거 토글
                if msg.get("sources"):
                    with st.expander("📚 답변 근거 상세", expanded=False):
                        for i, src in enumerate(msg["sources"], 1):
                            render_source_with_excerpt(src, i)

    # ============================================================
    # 7. 질문 처리
    # ============================================================

    strategy = "hybrid"
    top_k = 5
    include_sources = True

    if user_input:
        current_conv["history"].append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("검색 중..."):
                result = execute_query(user_input, strategy, top_k, include_sources)

                if result.success:
                    st.markdown(result.answer)

                    verification = result.verification or {}
                    conf = verification.get("confidence", 0)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        conf_icon = "🟢" if conf >= 0.7 else "🟡" if conf >= 0.4 else "🔴"
                        st.caption(f"{conf_icon} 신뢰도 : {conf*100:.0f}%")
                    with col2:
                        st.caption(f"응답시간 : {result.latency_ms:.0f}ms")
                    with col3:
                        status = verification.get("status", "unknown")
                        status_text = {"verified": "검증됨", "partial": "부분검증", "unverified": "미검증"}.get(status, status)
                        st.caption(f"상태 : {status_text}")

                    # 새 답변에도 근거 토글 추가
                    if include_sources and result.sources:
                        with st.expander("📚 답변 근거 상세", expanded=False):
                            for i, source in enumerate(result.sources, 1):
                                render_source_with_excerpt(source, i)

                    current_conv["history"].append({
                        "role": "assistant",
                        "content": result.answer,
                        "meta": {"confidence": conf, "latency": result.latency_ms, "status": verification.get("status", "unknown")},
                        "sources": result.sources if include_sources else [],
                    })
                    current_conv["last_result"] = result
                else:
                    error_msg = f"오류 : {result.error}"
                    st.error(error_msg)
                    current_conv["history"].append({"role": "assistant", "content": error_msg})

    # ============================================================
    # 8. 하단 버튼 (답변 근거 상세 섹션 제거됨 - 각 답변에 개별 토글로 이동)
    # ============================================================

    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("대화 초기화", use_container_width=True):
            current_conv["history"] = []
            current_conv["last_result"] = None
            st.rerun()

    with col2:
        if st.button("대화 삭제", use_container_width=True):
            if len(st.session_state.conversations) > 1:
                del st.session_state.conversations[st.session_state.current_conv_id]
                st.session_state.current_conv_id = list(st.session_state.conversations.keys())[0]
                st.rerun()
            else:
                st.toast("최소 1개 대화 유지 필요")

    with col3:
        if st.button("답변 복사", use_container_width=True):
            st.toast("복사됨" if current_conv.get("last_result") else "복사할 답변 없음")

    with col4:
        if st.button("대화 저장", use_container_width=True):
            if current_conv["history"]:
                import json
                st.download_button("다운로드", json.dumps({"history": current_conv["history"]}, ensure_ascii=False),
                                  f"대화_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "application/json")
            else:
                st.toast("저장할 대화 없음")
