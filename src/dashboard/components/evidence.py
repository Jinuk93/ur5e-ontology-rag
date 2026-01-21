# ============================================================
# src/dashboard/components/evidence.py - Evidence Panel Component
# ============================================================
# UX 개선: 한글화 및 설명 보강
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
    단일 근거 카드 렌더링

    Args:
        evidence: 근거 정보 (content, source_type, score, metadata)
        index: 근거 번호
        expanded: 전체 내용 표시 여부
    """
    source_type = evidence.get("source_type", "unknown")
    score = evidence.get("score", 0)
    content = evidence.get("content", "")
    metadata = evidence.get("metadata", {})

    # 출처 유형별 아이콘과 색상
    source_icons = {
        "graph": ("🔷", "#2196F3", "지식그래프"),
        "vector": ("📄", "#4CAF50", "문서DB"),
    }
    icon, color, type_name = source_icons.get(source_type, ("📌", "#9E9E9E", "기타"))

    # 엔티티 이름 또는 청크 ID
    entity_name = metadata.get("entity_name", metadata.get("chunk_id", "알 수 없음"))

    # 신뢰도에 따른 표시
    if score >= 0.8:
        score_badge = f"🟢 높음 ({score*100:.0f}%)"
    elif score >= 0.5:
        score_badge = f"🟡 보통 ({score*100:.0f}%)"
    else:
        score_badge = f"🔴 낮음 ({score*100:.0f}%)"

    # 헤더
    header = f"[{index}] {type_name} - {entity_name}"

    with st.expander(f"{icon} {header} — 신뢰도: {score_badge}", expanded=expanded):
        # 출처 정보
        if source_type == "graph":
            st.caption(f"📍 출처: 지식그래프 (Neo4j) - {metadata.get('entity_type', '노드')}")
            st.info("💡 **지식그래프란?** 에러코드, 부품, 원인, 해결책 간의 관계를 저장한 데이터베이스입니다.")
        else:
            source_doc = metadata.get("source", "문서DB")
            page = metadata.get("page", "")
            page_info = f" ({page}페이지)" if page else ""
            st.caption(f"📍 출처: 문서DB (VectorDB) - {source_doc}{page_info}")
            st.info("💡 **문서DB란?** UR5e 매뉴얼, 가이드 등 텍스트 문서를 저장한 데이터베이스입니다.")

        st.divider()

        # 내용
        st.markdown("**📝 내용:**")
        st.markdown(content if expanded else truncate_text(content, 500))

        # 신뢰도 상세 설명
        st.markdown("**📊 신뢰도 점수 설명:**")
        st.markdown(f"""
        | 항목 | 값 |
        |------|-----|
        | 점수 | {score*100:.1f}% |
        | 의미 | 이 정보가 질문과 **{score*100:.0f}%** 관련이 있습니다 |
        | 등급 | {score_badge} |
        """)

        # 메타데이터
        if metadata:
            with st.expander("📋 상세 정보 (개발자용)", expanded=False):
                for key, value in metadata.items():
                    if key not in ["content", "chunk_id"]:
                        # 키 이름 한글화
                        key_korean = {
                            "entity_name": "엔티티명",
                            "entity_type": "엔티티 유형",
                            "source": "원본 문서",
                            "page": "페이지",
                        }.get(key, key)
                        st.text(f"• {key_korean}: {value}")

        # 액션 버튼
        col1, col2, col3 = st.columns(3)
        with col1:
            if source_type == "graph":
                if st.button(f"🕸️ 그래프에서 보기", key=f"graph_{index}"):
                    st.session_state["selected_node"] = entity_name
                    st.session_state["navigate_to"] = "Knowledge_Graph"
                    st.toast("지식 그래프 페이지로 이동합니다")
        with col2:
            if st.button(f"📋 복사", key=f"copy_{index}"):
                st.toast(f"근거 [{index}] 복사됨")
        with col3:
            if st.button(f"🔍 상세보기", key=f"detail_{index}"):
                st.session_state[f"evidence_detail_{index}"] = True


def render_evidence_panel(
    answer: str,
    evidences: List[Dict[str, Any]],
    verification: Dict[str, Any] = None,
):
    """
    전체 근거 패널 렌더링

    Args:
        answer: 생성된 답변
        evidences: 근거 목록
        verification: 검증 정보
    """
    st.markdown("### 📚 답변 근거 패널")
    st.caption("AI가 답변을 생성할 때 참고한 정보들을 보여줍니다.")

    # 용어 설명
    with st.expander("❓ 용어 설명 (처음 사용자용)", expanded=False):
        st.markdown("""
        | 용어 | 설명 |
        |------|------|
        | **신뢰도 (Confidence)** | AI가 답변에 얼마나 확신하는지를 나타내는 점수 (0~100%) |
        | **근거 개수 (Evidence Count)** | AI가 참고한 정보의 개수 |
        | **검증 상태 (Status)** | 답변이 근거에 의해 뒷받침되는 정도 |
        | **지식그래프 (GraphDB)** | 에러-원인-해결책 관계를 저장한 DB |
        | **문서DB (VectorDB)** | 매뉴얼/가이드 문서를 저장한 DB |
        """)

    # 답변 섹션
    st.markdown("#### 🤖 AI 답변")
    with st.container():
        st.markdown(answer)

        if verification:
            status = verification.get("status", "unknown")
            confidence = verification.get("confidence", 0)
            evidence_count = verification.get("evidence_count", 0)

            icon, color, conf_str = format_confidence(confidence)

            # 상태 한글화
            status_korean = {
                "verified": ("✅", "검증됨", "모든 내용이 근거로 뒷받침됩니다"),
                "partial": ("⚠️", "부분 검증", "일부 내용만 근거로 뒷받침됩니다"),
                "unverified": ("❌", "미검증", "근거가 충분하지 않습니다"),
                "insufficient": ("❓", "정보 부족", "관련 정보를 찾지 못했습니다"),
            }
            status_icon, status_text, status_desc = status_korean.get(
                status, ("❓", "알 수 없음", "상태를 확인할 수 없습니다")
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"{icon} **신뢰도:** {conf_str}")
                st.caption("AI가 답변에 얼마나 확신하는지")
            with col2:
                st.markdown(f"📊 **참고 근거:** {evidence_count}개")
                st.caption("AI가 참고한 정보 개수")
            with col3:
                st.markdown(f"{status_icon} **검증 상태:** {status_text}")
                st.caption(status_desc)

    st.divider()

    # 근거 섹션
    st.markdown("#### 📖 검색된 근거")
    st.caption("AI가 답변을 생성할 때 참고한 정보들입니다.")

    # 필터 옵션
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        source_filter = st.multiselect(
            "출처 유형 필터",
            options=["graph", "vector"],
            default=["graph", "vector"],
            format_func=lambda x: "🔷 지식그래프" if x == "graph" else "📄 문서DB",
            key="evidence_source_filter",
            help="특정 출처 유형만 보려면 선택하세요",
        )
    with col2:
        min_score = st.slider(
            "최소 신뢰도",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1,
            key="evidence_min_score",
            help="이 점수 이상의 근거만 표시합니다",
        )
    with col3:
        show_all = st.checkbox("전체 펼치기", value=False, key="evidence_show_all")

    # 근거 필터링
    filtered_evidences = [
        e for e in evidences
        if e.get("source_type", "unknown") in source_filter
        and e.get("score", 0) >= min_score
    ]

    if not filtered_evidences:
        st.warning("⚠️ 선택한 필터 조건에 맞는 근거가 없습니다. 필터 조건을 조정해보세요.")
        return

    # 근거 카드 렌더링
    for i, evidence in enumerate(filtered_evidences, 1):
        render_evidence_card(evidence, i, expanded=show_all)

    # 요약
    st.divider()
    st.markdown("#### 📊 근거 요약")
    st.caption("""
    **이 섹션이 보여주는 것:**
    - **총 검색 결과**: AI가 데이터베이스에서 찾은 관련 정보의 총 개수
    - **지식그래프 출처**: 에러-원인-해결책 관계 데이터에서 가져온 정보 수
    - **문서DB 출처**: 매뉴얼/가이드 문서에서 가져온 정보 수
    """)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "총 검색 결과",
            len(evidences),
            help="AI가 찾은 관련 정보의 총 개수"
        )
    with col2:
        graph_count = len([e for e in evidences if e.get("source_type") == "graph"])
        st.metric(
            "지식그래프 출처",
            graph_count,
            help="에러-원인-해결책 관계 데이터"
        )
    with col3:
        vector_count = len([e for e in evidences if e.get("source_type") == "vector"])
        st.metric(
            "문서DB 출처",
            vector_count,
            help="매뉴얼/가이드 문서"
        )

    # 내보내기 옵션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 JSON으로 내보내기", key="export_evidence_json"):
            import json
            st.download_button(
                "📥 다운로드",
                data=json.dumps(evidences, ensure_ascii=False, indent=2),
                file_name="근거_데이터.json",
                mime="application/json",
            )
    with col2:
        if st.button("📋 전체 복사", key="copy_all_evidence"):
            st.toast("모든 근거가 클립보드에 복사되었습니다")


def render_answer_evidence_linking(
    answer: str,
    evidences: List[Dict[str, Any]],
):
    """
    답변-근거 연결 분석 렌더링

    답변의 어느 부분이 어떤 근거로 뒷받침되는지 보여줍니다
    """
    st.markdown("### 🔗 답변-근거 연결 분석")
    st.caption("AI 답변의 각 부분이 어떤 근거로 뒷받침되는지 분석합니다.")

    st.markdown(answer)

    st.divider()

    st.markdown("#### 📊 근거 매칭 분석")
    st.caption("각 근거가 답변에 얼마나 기여했는지 보여줍니다.")

    # 매칭 테이블 생성
    matching_data = []
    for i, evidence in enumerate(evidences[:5], 1):
        score = evidence.get("score", 0)
        source_type = evidence.get("source_type", "unknown")
        type_name = "지식그래프" if source_type == "graph" else "문서DB"

        # 상태 결정
        if score > 0.7:
            status = "✅ 높은 기여"
        elif score > 0.5:
            status = "⚠️ 보통 기여"
        else:
            status = "🔴 낮은 기여"

        matching_data.append({
            "번호": f"[{i}]",
            "출처 유형": type_name,
            "엔티티": evidence.get("metadata", {}).get("entity_name", "N/A"),
            "신뢰도": f"{score*100:.0f}%",
            "기여도": status,
        })

    if matching_data:
        import pandas as pd
        df = pd.DataFrame(matching_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # 환각 검사
    st.markdown("#### ⚠️ 환각(Hallucination) 검사")
    st.caption("AI가 근거 없이 만들어낸 정보가 있는지 확인합니다.")
    with st.container():
        if evidences and any(e.get("score", 0) > 0.5 for e in evidences):
            st.success("✅ 답변의 모든 내용이 근거로 뒷받침됩니다")
        else:
            st.warning("⚠️ 일부 내용은 근거가 부족할 수 있습니다. 추가 확인을 권장합니다.")
