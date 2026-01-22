# ============================================================
# src/dashboard/pages/overview.py - Dashboard Overview Page
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
from src.dashboard.services.graph_service import graph_service
from src.dashboard.components.metrics import render_metric_row, render_status_indicator
from src.dashboard.components.charts import render_bar_chart, render_pie_chart


def render_overview():
    """Render the overview/home page"""

    st.title("📊 시스템 현황")
    st.markdown("""
    **UR5e 에러 해결 도우미 시스템의 전체 상태를 한눈에 확인할 수 있습니다.**

    이 시스템은 로봇 매뉴얼과 에러 정보를 AI가 학습하여
    현장 엔지니어분들이 에러를 빠르게 해결할 수 있도록 도와줍니다.
    """)

    # ============================================================
    # 시스템 연결 상태
    # ============================================================

    st.subheader("🔌 시스템 연결 상태")
    st.caption("모든 항목이 '연결됨' 또는 '정상' 상태여야 시스템이 정상 작동합니다.")

    col1, col2, col3, col4 = st.columns(4)

    # API Health
    health = api_client.health_check()
    components = health.get("components", {})

    with col1:
        status = "online" if health.get("status") == "healthy" else "offline"
        st.metric(
            label="API 서버",
            value="연결됨" if status == "online" else "연결 안됨",
            delta="정상" if status == "online" else "오류",
            delta_color="normal" if status == "online" else "inverse",
            help="질의응답 서비스를 제공하는 서버입니다.",
        )

    with col2:
        vectordb_status = components.get("vectordb", "unknown")
        st.metric(
            label="문서DB (ChromaDB)",
            value="연결됨" if vectordb_status == "connected" else "연결 안됨",
            delta="정상" if vectordb_status == "connected" else "오류",
            delta_color="normal" if vectordb_status == "connected" else "inverse",
            help="매뉴얼 문서를 저장하고 검색하는 데이터베이스입니다.",
        )

    with col3:
        graphdb_status = components.get("graphdb", "unknown")
        st.metric(
            label="지식DB (Neo4j)",
            value="연결됨" if graphdb_status == "connected" else "연결 안됨",
            delta="정상" if graphdb_status == "connected" else "오류",
            delta_color="normal" if graphdb_status == "connected" else "inverse",
            help="에러 코드와 부품 간의 관계를 저장하는 데이터베이스입니다.",
        )

    with col4:
        llm_status = components.get("llm", "unknown")
        st.metric(
            label="AI 모델 (GPT-4o)",
            value="사용 가능" if llm_status == "available" else "사용 불가",
            delta="정상" if llm_status == "available" else "오류",
            delta_color="normal" if llm_status == "available" else "inverse",
            help="질문에 대한 답변을 생성하는 AI 모델입니다.",
        )

    st.divider()

    # ============================================================
    # 시스템 구조도
    # ============================================================

    with st.expander("🏗️ 시스템 구조도 (전문가용)", expanded=False):
        st.caption("이 시스템이 어떻게 동작하는지 보여주는 다이어그램입니다.")

        st.markdown("""
        ```
        ┌─────────────────────────────────────────────────────────────────────┐
        │                    AI 기반 에러 해결 시스템                           │
        │                                                                      │
        │   ┌─────────┐    ┌──────────────┐    ┌────────────┐    ┌─────────┐ │
        │   │  질문   │ ─► │  질문 분석   │ ─► │  정보 검색 │ ─► │  검증   │ │
        │   │  입력   │    │ (에러/부품)  │    │  (복합)    │    │ (확인)  │ │
        │   └─────────┘    └──────────────┘    └─────┬──────┘    └────┬────┘ │
        │                                            │                 │      │
        │                         ┌──────────────────┼─────────────────┘      │
        │                         │                  │                        │
        │                         ▼                  ▼                        │
        │                  ┌───────────┐      ┌───────────┐                  │
        │                  │ AI 답변   │      │  지식DB   │                  │
        │                  │ 생성기    │      │  문서DB   │                  │
        │                  └─────┬─────┘      └───────────┘                  │
        │                        │                                            │
        │                        ▼                                            │
        │                  ┌───────────┐                                      │
        │                  │  답변     │                                      │
        │                  │ + 근거   │                                      │
        │                  └───────────┘                                      │
        └─────────────────────────────────────────────────────────────────────┘
        ```
        """)

    st.divider()

    # ============================================================
    # 저장된 정보 현황
    # ============================================================

    st.subheader("📚 저장된 정보 현황")
    st.caption("현재 시스템에 저장되어 있는 에러 코드와 부품 정보입니다.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 에러 코드")
        errors = api_client.get_errors()
        st.info(f"📌 **{len(errors)}개**의 에러 코드가 등록되어 있습니다")

        with st.expander("에러 코드 범위 보기"):
            st.markdown("""
            | 범위 | 분류 | 설명 |
            |------|------|------|
            | C0-C9 | 시스템 에러 | 시스템 전체 관련 에러 |
            | C10-C19 | 통신 에러 | 네트워크/통신 관련 에러 |
            | C20-C29 | 조인트 에러 | 로봇 관절 관련 에러 |
            | C30-C39 | 안전 에러 | 안전 시스템 관련 에러 |
            | C40-C49 | 하드웨어 에러 | 하드웨어 고장 관련 에러 |
            | C50-C55 | 기타 에러 | 기타 분류 에러 |
            """)

    with col2:
        st.markdown("##### 부품 정보")
        components_list = api_client.get_components()
        st.info(f"🔧 **{len(components_list)}개**의 부품이 등록되어 있습니다")

        with st.expander("주요 부품 목록 보기"):
            for comp in components_list[:10]:
                st.text(f"• {comp}")
            if len(components_list) > 10:
                st.caption(f"... 외 {len(components_list) - 10}개")

    st.divider()

    # ============================================================
    # 지식그래프 통계
    # ============================================================

    st.subheader("🕸️ 지식 그래프 통계")
    st.caption("에러 코드와 부품, 해결방법 간의 연결 관계 정보입니다.")

    stats = graph_service.get_statistics()

    if "error" not in stats:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "전체 노드 수",
                f"{stats.get('total_nodes', 0):,}개",
                help="에러 코드, 부품, 해결방법 등의 총 개수",
            )
        with col2:
            st.metric(
                "전체 관계 수",
                f"{stats.get('total_edges', 0):,}개",
                help="노드 간의 연결 관계 총 개수",
            )
        with col3:
            st.metric(
                "노드 종류",
                f"{stats.get('node_types', 0)}가지",
                help="에러코드, 부품, 해결방법 등의 종류 수",
            )
        with col4:
            st.metric(
                "관계 종류",
                f"{stats.get('edge_types', 0)}가지",
                help="발생원인, 해결방법 등의 관계 종류 수",
            )

        # 차트 표시
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### 노드 종류별 분포")
            node_counts = stats.get("node_counts", {})
            if node_counts:
                # 한글 레이블로 변환
                korean_labels = {
                    "ErrorCode": "에러코드",
                    "Component": "부품",
                    "Solution": "해결방법",
                    "Symptom": "증상",
                    "Cause": "원인",
                }
                chart_data = [
                    {"종류": korean_labels.get(k, k), "개수": v}
                    for k, v in node_counts.items()
                ]
                render_bar_chart(chart_data, x="종류", y="개수", height=300)

        with col2:
            st.markdown("##### 관계 종류별 분포")
            edge_counts = stats.get("edge_counts", {})
            if edge_counts:
                korean_labels = {
                    "CAUSED_BY": "원인",
                    "RESOLVED_BY": "해결방법",
                    "HAS_SYMPTOM": "증상",
                    "RELATED_TO": "관련항목",
                }
                chart_data = [
                    {"종류": korean_labels.get(k, k), "개수": v}
                    for k, v in list(edge_counts.items())[:6]
                ]
                render_pie_chart(chart_data, names="종류", values="개수", height=300)

    else:
        st.warning(f"지식그래프 통계를 불러올 수 없습니다: {stats.get('error')}")
        st.caption("지식DB(Neo4j) 연결 상태를 확인해 주세요.")

    st.divider()

    # ============================================================
    # 사용 방법 안내
    # ============================================================

    st.subheader("💡 사용 방법")

    st.markdown("""
    **1. 질문하기 (권장)**
    - 왼쪽 메뉴에서 **"질문하기"**를 선택하세요
    - 에러 코드나 증상을 입력하면 AI가 해결방법을 안내합니다
    - 예: "C4A15 에러 해결법", "로봇이 갑자기 멈췄어요"

    **2. 검색 탐색기**
    - 다양한 검색 방식을 비교해볼 수 있습니다
    - 전문가용 기능입니다

    **3. 지식 그래프**
    - 에러와 부품, 해결방법의 관계를 시각적으로 볼 수 있습니다

    **4. 성능 평가**
    - 시스템의 정확도와 신뢰도를 확인할 수 있습니다

    **5. 운영 모니터**
    - 시스템 사용량과 비용을 확인할 수 있습니다 (관리자용)
    """)

    st.divider()

    # Footer
    st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
