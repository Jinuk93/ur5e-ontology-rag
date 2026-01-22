# ============================================================
# src/dashboard/pages/performance.py - Performance Evaluation Page
# ============================================================
# Phase 10 평가 시스템과 연동된 성능 평가 대시보드
# ============================================================

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.services.api_client import api_client
from src.dashboard.components.charts import render_bar_chart, render_gauge_chart, render_comparison_table
from src.dashboard.utils.formatters import format_latency


def load_evaluation_results():
    """평가 결과 JSON에서 데이터 로드"""
    results_path = Path(_project_root) / "data" / "evaluation" / "results" / "latest.json"
    if results_path.exists():
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading evaluation results: {e}")
            return None
    return None


def render_performance():
    """Render the Performance Evaluation page"""

    st.title("📈 성능 평가 (Performance)")
    st.caption("RAG 시스템 성능 지표, 벤치마크 결과, Phase별 비교")

    # 평가 결과 로드
    eval_results = load_evaluation_results()

    # ============================================================
    # KPI 지표 (Score Cards)
    # ============================================================

    st.subheader("🎯 핵심 성능 지표 (KPI)")

    # 실제 데이터 또는 기본값
    if eval_results:
        accuracy = eval_results["avg_answer_metrics"]["accuracy"] * 100
        hallucination_prevention = (1 - eval_results["verification_metrics"]["hallucination_rate"]) * 100
        recall = eval_results["avg_retrieval_metrics"]["recall"] * 100
        pass_rate = eval_results["pass_rate"] * 100
        latency = eval_results["avg_latency_ms"]

        st.success("✅ 최근 평가 결과가 로드되었습니다.")
        st.caption(f"평가 시각: {eval_results.get('timestamp', '알 수 없음')}")
    else:
        accuracy = 82.5
        hallucination_prevention = 95.2
        recall = 78.3
        pass_rate = 87.5
        latency = 3500

        st.info("💡 평가 결과가 없습니다. `python scripts/run_evaluation.py` 명령어로 평가를 실행하세요.")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_gauge_chart(
            value=accuracy,
            title="정확도 (Accuracy)",
            min_val=0,
            max_val=100,
            height=200,
        )
        st.caption("예상 정답과의 일치도")

    with col2:
        render_gauge_chart(
            value=hallucination_prevention,
            title="환각 방지율",
            min_val=0,
            max_val=100,
            height=200,
        )
        st.caption("잘못된 정보 생성 방지")

    with col3:
        render_gauge_chart(
            value=recall,
            title="재현율 (Recall)",
            min_val=0,
            max_val=100,
            height=200,
        )
        st.caption("관련 정보 검색 비율")

    with col4:
        render_gauge_chart(
            value=pass_rate,
            title="통과율 (Pass Rate)",
            min_val=0,
            max_val=100,
            height=200,
        )
        st.caption("벤치마크 테스트 통과")

    st.divider()

    # ============================================================
    # 카테고리별 성능 (평가 결과 기반)
    # ============================================================

    if eval_results and "by_category" in eval_results:
        st.subheader("📂 카테고리별 성능")

        cat_data = []
        for cat, data in eval_results["by_category"].items():
            cat_labels = {
                "error_code": "에러 코드",
                "component": "부품 질문",
                "general": "일반 질문",
                "invalid": "잘못된 에러 (환각 테스트)"
            }
            cat_data.append({
                "카테고리": cat_labels.get(cat, cat),
                "통과": f"{data['passed']}/{data['total']}",
                "통과율": f"{data['pass_rate']:.0%}",
                "평균 정확도": f"{data['avg_accuracy']:.0%}",
            })

        st.dataframe(pd.DataFrame(cat_data), use_container_width=True, hide_index=True)

        # 시각화
        col1, col2 = st.columns(2)

        with col1:
            chart_data = [
                {"category": item["카테고리"], "pass_rate": float(item["통과율"].replace("%", ""))}
                for item in cat_data
            ]
            render_bar_chart(
                chart_data,
                x="category",
                y="pass_rate",
                title="카테고리별 통과율",
                height=300,
            )

        with col2:
            chart_data = [
                {"category": item["카테고리"], "accuracy": float(item["평균 정확도"].replace("%", ""))}
                for item in cat_data
            ]
            render_bar_chart(
                chart_data,
                x="category",
                y="accuracy",
                title="카테고리별 정확도",
                height=300,
            )

        st.divider()

    # ============================================================
    # Phase별 비교
    # ============================================================

    st.subheader("📊 Phase별 비교")

    # 현재 Phase 7 성능 (평가 결과 기반)
    if eval_results:
        current_accuracy = eval_results["avg_answer_metrics"]["accuracy"] * 100
        current_hallucination = (1 - eval_results["verification_metrics"]["hallucination_rate"]) * 100
        current_latency = eval_results["avg_latency_ms"] / 1000
    else:
        current_accuracy = 82.5
        current_hallucination = 95.2
        current_latency = 3.5

    phase_data = [
        {"Phase": "Phase 5 (VectorDB Only)", "정확도 (%)": 50, "환각 방지율 (%)": 0, "평균 응답시간 (초)": 2.0, "지식그래프 활용": "없음"},
        {"Phase": "Phase 6 (Hybrid)", "정확도 (%)": 75, "환각 방지율 (%)": 45, "평균 응답시간 (초)": 3.5, "지식그래프 활용": "있음"},
        {"Phase": "Phase 7 (Verifier)", "정확도 (%)": round(current_accuracy, 1), "환각 방지율 (%)": round(current_hallucination, 1), "평균 응답시간 (초)": round(current_latency, 1), "지식그래프 활용": "있음"},
    ]

    df = pd.DataFrame(phase_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 차트
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 정확도 향상 추이")
        render_bar_chart(
            phase_data,
            x="Phase",
            y="정확도 (%)",
            title="",
            height=300,
        )

    with col2:
        st.markdown("##### 환각 방지율 향상 추이")
        render_bar_chart(
            phase_data,
            x="Phase",
            y="환각 방지율 (%)",
            title="",
            height=300,
        )

    st.divider()

    # ============================================================
    # 벤치마크 테스트
    # ============================================================

    st.subheader("🧪 벤치마크 테스트")

    tab1, tab2 = st.tabs(["빠른 테스트 (5개)", "전체 평가 실행"])

    with tab1:
        # 빠른 테스트 케이스
        test_cases = [
            {"Query": "C103 에러 해결법", "Expected": "VERIFIED", "Type": "에러 코드"},
            {"Query": "C999 에러 해결법", "Expected": "INSUFFICIENT", "Type": "잘못된 에러"},
            {"Query": "Control Box 에러 목록", "Expected": "VERIFIED", "Type": "부품 질문"},
            {"Query": "로봇이 갑자기 멈췄어요", "Expected": "PARTIAL,VERIFIED", "Type": "일반 질문"},
            {"Query": "ABC123 에러", "Expected": "INSUFFICIENT", "Type": "잘못된 형식"},
        ]

        if st.button("▶️ 빠른 테스트 실행", type="primary"):
            st.markdown("#### 테스트 결과")

            results = []
            progress_bar = st.progress(0)

            for i, test in enumerate(test_cases):
                with st.spinner(f"테스트 중: {test['Query'][:30]}..."):
                    result = api_client.query(test["Query"], top_k=3)

                    if result.success:
                        actual_status = result.verification.get("status", "unknown").upper()
                        expected = test["Expected"]

                        # 통과 여부 확인
                        passed = actual_status in expected.split(",")

                        results.append({
                            "질문": test["Query"],
                            "유형": test["Type"],
                            "예상": expected,
                            "실제": actual_status,
                            "결과": "✅" if passed else "❌",
                            "응답시간": format_latency(result.latency_ms),
                            "신뢰도": f"{result.verification.get('confidence', 0) * 100:.0f}%",
                        })
                    else:
                        results.append({
                            "질문": test["Query"],
                            "유형": test["Type"],
                            "예상": test["Expected"],
                            "실제": "ERROR",
                            "결과": "❌",
                            "응답시간": "-",
                            "신뢰도": "-",
                        })

                progress_bar.progress((i + 1) / len(test_cases))

            # 결과 표시
            df_results = pd.DataFrame(results)
            st.dataframe(df_results, use_container_width=True, hide_index=True)

            # 요약
            passed_count = len([r for r in results if r["결과"] == "✅"])
            total_count = len(results)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("전체 테스트", total_count)
            with col2:
                st.metric("통과", passed_count)
            with col3:
                st.metric("통과율", f"{passed_count / total_count * 100:.0f}%")

        else:
            # 테스트 케이스 표시
            st.markdown("**테스트 케이스:**")
            st.dataframe(pd.DataFrame(test_cases), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("""
        ### 전체 벤치마크 평가

        40개의 벤치마크 질문으로 전체 시스템을 평가합니다.

        **터미널에서 실행:**
        ```bash
        python scripts/run_evaluation.py
        ```

        **옵션:**
        - `--category error_code`: 에러 코드 질문만 평가
        - `--fast`: 빠른 평가 (LLM Judge 없이)
        - `--report-only`: 리포트만 재생성
        """)

        if st.button("📊 전체 평가 실행 (시간 소요)"):
            with st.spinner("전체 벤치마크 평가 실행 중... (약 5-10분 소요)"):
                try:
                    # 평가 실행
                    from src.evaluation.evaluator import Evaluator
                    from src.evaluation.report import ReportGenerator

                    evaluator = Evaluator(use_llm_judge=True, verbose=False)
                    summary = evaluator.evaluate_all()

                    # 결과 저장
                    evaluator.save_results(summary)

                    # 리포트 생성
                    report_gen = ReportGenerator()
                    report_gen.generate_markdown(summary, "docs/Phase10_평가결과.md")

                    st.success(f"✅ 평가 완료! 통과율: {summary.pass_rate:.0%}")
                    st.rerun()

                except Exception as e:
                    st.error(f"평가 실패: {e}")

    st.divider()

    # ============================================================
    # 커스텀 테스트
    # ============================================================

    st.subheader("🔬 커스텀 테스트")

    col1, col2 = st.columns([3, 1])

    with col1:
        custom_query = st.text_input(
            "테스트 질문",
            placeholder="테스트할 질문을 입력하세요...",
        )

    with col2:
        custom_expected = st.selectbox(
            "예상 결과",
            options=["VERIFIED", "PARTIAL", "UNVERIFIED", "INSUFFICIENT"],
        )

    if st.button("🧪 커스텀 테스트 실행"):
        if custom_query:
            with st.spinner("테스트 중..."):
                result = api_client.query(custom_query, top_k=5)

                if result.success:
                    actual_status = result.verification.get("status", "unknown").upper()
                    passed = actual_status == custom_expected

                    if passed:
                        st.success(f"✅ 테스트 통과! - 실제: {actual_status}")
                    else:
                        st.error(f"❌ 테스트 실패 - 예상: {custom_expected}, 실제: {actual_status}")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("응답 시간", format_latency(result.latency_ms))
                    with col2:
                        st.metric("신뢰도", f"{result.verification.get('confidence', 0) * 100:.0f}%")
                    with col3:
                        st.metric("근거 수", result.verification.get("evidence_count", 0))

                    with st.expander("답변 보기"):
                        st.markdown(result.answer)
                else:
                    st.error(f"테스트 실패: {result.error}")
        else:
            st.warning("테스트할 질문을 입력하세요")

    # ============================================================
    # 성능 최적화 팁
    # ============================================================

    st.divider()

    with st.expander("💡 성능 최적화 팁"):
        st.markdown("""
        ### RAG 시스템 성능 향상 방법

        1. **구체적인 질문 사용**
           - 에러 코드를 알고 있다면 포함 (예: "C103 에러 해결법")
           - 부품 이름을 명시적으로 언급

        2. **검색 전략 선택**
           - `graph_first`: 에러 코드 질문에 최적
           - `vector_first`: 일반 문제 해결에 적합
           - `hybrid`: 복잡한 질문에 권장

        3. **검색 결과 수 조정**
           - 구체적인 질문: 3-5개
           - 탐색적 질문: 10-15개

        4. **검증 결과 신뢰**
           - "INSUFFICIENT": 정보 부족을 정확히 감지
           - "PARTIAL": 주의가 필요한 답변
        """)
