# ============================================================
# src/evaluation/report.py - Evaluation Report Generator
# ============================================================
# 평가 결과 리포트 생성기
# ============================================================

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.evaluation.evaluator import EvaluationSummary, EvaluationResult


class ReportGenerator:
    """
    평가 리포트 생성기

    평가 결과를 Markdown 형식의 리포트로 생성합니다.

    사용 예시:
        generator = ReportGenerator()
        generator.generate_markdown(summary, "docs/Phase10_평가결과.md")
    """

    def generate_markdown(
        self,
        summary: EvaluationSummary,
        output_path: str = "docs/Phase10_평가결과.md",
        results: Optional[List[EvaluationResult]] = None,
    ) -> str:
        """
        Markdown 리포트 생성

        Args:
            summary: 평가 요약
            output_path: 출력 파일 경로
            results: 개별 결과 목록 (선택, 상세 보고서용)

        Returns:
            str: 생성된 리포트 내용
        """
        report = self._build_report(summary, results)

        # 파일 저장
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[OK] Report saved to: {output_path}")
        return report

    def _build_report(
        self,
        summary: EvaluationSummary,
        results: Optional[List[EvaluationResult]] = None,
    ) -> str:
        """리포트 내용 생성"""

        sections = [
            self._header(summary),
            self._overview(summary),
            self._retrieval_metrics(summary),
            self._answer_metrics(summary),
            self._verification_metrics(summary),
            self._category_breakdown(summary),
            self._difficulty_breakdown(summary),
        ]

        if results:
            sections.append(self._detailed_results(results))

        sections.append(self._conclusion(summary))
        sections.append(self._footer())

        return "\n\n".join(sections)

    def _header(self, summary: EvaluationSummary) -> str:
        return f"""# Phase 10: 평가 결과 리포트

> **평가 일시:** {summary.timestamp}
>
> **평가 버전:** {summary.version}
>
> **총 평가 항목:** {summary.total_items}개

---"""

    def _overview(self, summary: EvaluationSummary) -> str:
        pass_rate_pct = summary.pass_rate * 100
        hallucination_pct = summary.verification_metrics.hallucination_rate * 100
        safe_response_pct = summary.verification_metrics.safe_response_rate * 100

        # 성능 등급 결정
        if pass_rate_pct >= 80:
            grade = "🏆 우수"
        elif pass_rate_pct >= 60:
            grade = "✅ 양호"
        elif pass_rate_pct >= 40:
            grade = "⚠️ 보통"
        else:
            grade = "❌ 미흡"

        return f"""## 1. 요약

### 종합 성능

| 지표 | 값 | 평가 |
|------|------|------|
| **통과율** | {pass_rate_pct:.1f}% ({summary.passed_items}/{summary.total_items}) | {grade} |
| **환각 방지율** | {100 - hallucination_pct:.1f}% | {"✅" if hallucination_pct < 10 else "⚠️"} |
| **안전 응답률** | {safe_response_pct:.1f}% | {"✅" if safe_response_pct >= 90 else "⚠️"} |
| **평균 응답 시간** | {summary.avg_latency_ms:.0f}ms | {"✅" if summary.avg_latency_ms < 5000 else "⚠️"} |

### 핵심 지표 (KPI)

```
┌────────────────────────────────────────────────────────┐
│  정확도(Accuracy)     [{self._progress_bar(summary.avg_answer_metrics.accuracy)}] {summary.avg_answer_metrics.accuracy:.0%}  │
│  환각방지율           [{self._progress_bar(1 - summary.verification_metrics.hallucination_rate)}] {(1 - summary.verification_metrics.hallucination_rate):.0%}  │
│  검색 재현율(Recall)  [{self._progress_bar(summary.avg_retrieval_metrics.recall)}] {summary.avg_retrieval_metrics.recall:.0%}  │
│  관련성(Relevance)    [{self._progress_bar(summary.avg_answer_metrics.relevance)}] {summary.avg_answer_metrics.relevance:.0%}  │
└────────────────────────────────────────────────────────┘
```"""

    def _progress_bar(self, value: float, width: int = 20) -> str:
        """ASCII 프로그레스 바 생성"""
        filled = int(value * width)
        empty = width - filled
        return "█" * filled + "░" * empty

    def _retrieval_metrics(self, summary: EvaluationSummary) -> str:
        m = summary.avg_retrieval_metrics
        return f"""## 2. 검색 품질 (Retrieval Metrics)

| 지표 | 값 | 목표 | 달성 |
|------|------|------|------|
| **Precision** | {m.precision:.2%} | 80%+ | {"✅" if m.precision >= 0.8 else "❌"} |
| **Recall** | {m.recall:.2%} | 85%+ | {"✅" if m.recall >= 0.85 else "❌"} |
| **F1 Score** | {m.f1_score:.2%} | 80%+ | {"✅" if m.f1_score >= 0.8 else "❌"} |
| **MRR** | {m.mrr:.2%} | 70%+ | {"✅" if m.mrr >= 0.7 else "❌"} |
| **Hit Rate** | {m.hit_rate:.2%} | 90%+ | {"✅" if m.hit_rate >= 0.9 else "❌"} |

### 설명
- **Precision**: 검색된 결과 중 정답이 포함된 비율
- **Recall**: 정답 중 검색된 비율 (검색 완전성)
- **F1 Score**: Precision과 Recall의 조화 평균
- **MRR**: 첫 번째 정답의 평균 역순위
- **Hit Rate**: 하나라도 정답을 찾은 비율"""

    def _answer_metrics(self, summary: EvaluationSummary) -> str:
        m = summary.avg_answer_metrics
        return f"""## 3. 답변 품질 (Answer Metrics - LLM Judge)

| 지표 | 값 | 목표 | 달성 |
|------|------|------|------|
| **Accuracy** | {m.accuracy:.2%} | 85%+ | {"✅" if m.accuracy >= 0.85 else "❌"} |
| **Completeness** | {m.completeness:.2%} | 80%+ | {"✅" if m.completeness >= 0.8 else "❌"} |
| **Relevance** | {m.relevance:.2%} | 90%+ | {"✅" if m.relevance >= 0.9 else "❌"} |
| **Faithfulness** | {m.faithfulness:.2%} | 95%+ | {"✅" if m.faithfulness >= 0.95 else "❌"} |

### 설명
- **Accuracy**: 예상 정답과의 일치도
- **Completeness**: 핵심 정보 포함 여부
- **Relevance**: 질문에 대한 답변 적절성
- **Faithfulness**: 사실 기반 여부 (환각 없음)"""

    def _verification_metrics(self, summary: EvaluationSummary) -> str:
        m = summary.verification_metrics
        return f"""## 4. 검증 품질 (Verification Metrics)

| 지표 | 값 | 목표 | 달성 |
|------|------|------|------|
| **Hallucination Rate** | {m.hallucination_rate:.2%} | <5% | {"✅" if m.hallucination_rate < 0.05 else "❌"} |
| **Safe Response Rate** | {m.safe_response_rate:.2%} | 100% | {"✅" if m.safe_response_rate >= 1.0 else "❌"} |
| **Verification Accuracy** | {m.verification_accuracy:.2%} | 95%+ | {"✅" if m.verification_accuracy >= 0.95 else "❌"} |

### 설명
- **Hallucination Rate**: 잘못된 정보를 생성한 비율 (낮을수록 좋음)
- **Safe Response Rate**: 존재하지 않는 에러 코드에 대해 "정보 없음"으로 응답한 비율
- **Verification Accuracy**: 검증 결과가 예상과 일치한 비율"""

    def _category_breakdown(self, summary: EvaluationSummary) -> str:
        rows = []
        for cat, data in sorted(summary.by_category.items()):
            rows.append(
                f"| **{cat}** | {data['passed']}/{data['total']} | "
                f"{data['pass_rate']:.0%} | {data['avg_accuracy']:.2%} |"
            )

        return f"""## 5. 카테고리별 성능

| 카테고리 | 통과 | 통과율 | 평균 정확도 |
|----------|------|--------|------------|
{chr(10).join(rows)}

### 카테고리 설명
- **error_code**: 특정 에러 코드에 대한 질문 (예: "C103 에러 해결법")
- **component**: 부품 관련 질문 (예: "Control Box 에러 목록")
- **general**: 일반 질문 (예: "로봇이 멈췄어요")
- **invalid**: 존재하지 않는 에러 코드 질문 (환각 테스트)"""

    def _difficulty_breakdown(self, summary: EvaluationSummary) -> str:
        rows = []
        difficulty_order = ["easy", "medium", "hard"]
        for diff in difficulty_order:
            if diff in summary.by_difficulty:
                data = summary.by_difficulty[diff]
                rows.append(
                    f"| **{diff}** | {data['passed']}/{data['total']} | "
                    f"{data['pass_rate']:.0%} | {data['avg_accuracy']:.2%} |"
                )

        return f"""## 6. 난이도별 성능

| 난이도 | 통과 | 통과율 | 평균 정확도 |
|--------|------|--------|------------|
{chr(10).join(rows)}

### 난이도 설명
- **easy**: 단일 에러 코드 직접 질문
- **medium**: 부품 관련 복합 질문
- **hard**: 증상 기반 추론 필요"""

    def _detailed_results(self, results: List[EvaluationResult]) -> str:
        rows = []
        for r in results[:20]:  # 상위 20개만
            status = "✅" if r.passed else "❌"
            rows.append(
                f"| {status} | {r.benchmark_id} | {r.question[:30]}... | "
                f"{r.answer_metrics.accuracy:.0%} | {r.verification_status} |"
            )

        return f"""## 7. 상세 결과 (상위 20개)

| 상태 | ID | 질문 | 정확도 | 검증 |
|------|-----|------|--------|------|
{chr(10).join(rows)}"""

    def _conclusion(self, summary: EvaluationSummary) -> str:
        # 개선 필요 영역 식별
        improvements = []

        if summary.avg_retrieval_metrics.precision < 0.8:
            improvements.append("- 검색 Precision 향상 필요 (현재: {:.0%})".format(summary.avg_retrieval_metrics.precision))

        if summary.avg_answer_metrics.accuracy < 0.85:
            improvements.append("- 답변 정확도 향상 필요 (현재: {:.0%})".format(summary.avg_answer_metrics.accuracy))

        if summary.verification_metrics.hallucination_rate > 0.05:
            improvements.append("- 환각 방지율 개선 필요 (현재 환각률: {:.0%})".format(summary.verification_metrics.hallucination_rate))

        if not improvements:
            improvements.append("- 모든 목표 지표 달성! 🎉")

        return f"""## 8. 결론 및 개선 방향

### 현재 성능 평가
- 전체 통과율: **{summary.pass_rate:.0%}**
- 평균 정확도: **{summary.avg_answer_metrics.accuracy:.0%}**
- 환각 방지율: **{(1 - summary.verification_metrics.hallucination_rate):.0%}**

### 개선 필요 영역
{chr(10).join(improvements)}

### Phase별 비교 (예상)

| Phase | Precision | Recall | Accuracy | Hallucination |
|-------|-----------|--------|----------|---------------|
| Phase 5 (Vector) | 45% | 40% | 50% | 100% |
| Phase 6 (Hybrid) | 80% | 85% | 82% | 55% |
| **Phase 7 (Verifier)** | **{summary.avg_retrieval_metrics.precision:.0%}** | **{summary.avg_retrieval_metrics.recall:.0%}** | **{summary.avg_answer_metrics.accuracy:.0%}** | **{summary.verification_metrics.hallucination_rate:.0%}** |"""

    def _footer(self) -> str:
        return f"""---

*이 리포트는 Phase 10 자동 평가 시스템에 의해 생성되었습니다.*

*생성 시각: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*"""

    def generate_comparison_report(
        self,
        results: Dict[str, EvaluationSummary],
        output_path: str = "docs/Phase10_버전비교.md",
    ) -> str:
        """
        버전 비교 리포트 생성

        Args:
            results: {"v1": summary1, "v2": summary2, ...}
            output_path: 출력 파일 경로

        Returns:
            str: 생성된 리포트 내용
        """
        report = self._build_comparison_report(results)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[OK] Comparison report saved to: {output_path}")
        return report

    def _build_comparison_report(self, results: Dict[str, EvaluationSummary]) -> str:
        """버전 비교 리포트 생성"""

        # 테이블 행 생성
        rows = []
        for version, summary in sorted(results.items()):
            rows.append(
                f"| **{version}** | "
                f"{summary.pass_rate:.0%} | "
                f"{summary.avg_retrieval_metrics.precision:.0%} | "
                f"{summary.avg_retrieval_metrics.recall:.0%} | "
                f"{summary.avg_answer_metrics.accuracy:.0%} | "
                f"{summary.verification_metrics.hallucination_rate:.0%} | "
                f"{summary.avg_latency_ms:.0f}ms |"
            )

        return f"""# Phase 10: 버전 비교 리포트

> **비교 일시:** {datetime.now().isoformat()}
>
> **비교 버전:** {', '.join(results.keys())}

---

## 버전별 성능 비교

| 버전 | 통과율 | Precision | Recall | Accuracy | Hallucination | Latency |
|------|--------|-----------|--------|----------|---------------|---------|
{chr(10).join(rows)}

## 분석

### 최고 성능 버전
- 통과율 최고: **{max(results.items(), key=lambda x: x[1].pass_rate)[0]}**
- 정확도 최고: **{max(results.items(), key=lambda x: x[1].avg_answer_metrics.accuracy)[0]}**
- 환각률 최저: **{min(results.items(), key=lambda x: x[1].verification_metrics.hallucination_rate)[0]}**

---

*이 리포트는 Phase 10 자동 평가 시스템에 의해 생성되었습니다.*
"""


# ============================================================
# 모듈 테스트
# ============================================================

if __name__ == "__main__":
    from src.evaluation.metrics import RetrievalMetrics, AnswerMetrics, VerificationMetrics

    # 테스트용 더미 데이터
    summary = EvaluationSummary(
        total_items=40,
        passed_items=35,
        pass_rate=0.875,
        avg_retrieval_metrics=RetrievalMetrics(
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            mrr=0.75,
            hit_rate=0.92,
        ),
        avg_answer_metrics=AnswerMetrics(
            accuracy=0.86,
            completeness=0.83,
            relevance=0.91,
            faithfulness=0.94,
        ),
        verification_metrics=VerificationMetrics(
            hallucination_rate=0.03,
            safe_response_rate=1.0,
            verification_accuracy=0.95,
        ),
        avg_latency_ms=3500,
        by_category={
            "error_code": {"total": 15, "passed": 14, "pass_rate": 0.93, "avg_accuracy": 0.90},
            "component": {"total": 10, "passed": 9, "pass_rate": 0.90, "avg_accuracy": 0.85},
            "general": {"total": 10, "passed": 8, "pass_rate": 0.80, "avg_accuracy": 0.78},
            "invalid": {"total": 5, "passed": 4, "pass_rate": 0.80, "avg_accuracy": 1.0},
        },
        by_difficulty={
            "easy": {"total": 20, "passed": 19, "pass_rate": 0.95, "avg_accuracy": 0.92},
            "medium": {"total": 15, "passed": 13, "pass_rate": 0.87, "avg_accuracy": 0.82},
            "hard": {"total": 5, "passed": 3, "pass_rate": 0.60, "avg_accuracy": 0.70},
        },
    )

    generator = ReportGenerator()
    report = generator.generate_markdown(summary, "docs/Phase10_평가결과_테스트.md")
    print("\nGenerated report preview:")
    print(report[:2000])
