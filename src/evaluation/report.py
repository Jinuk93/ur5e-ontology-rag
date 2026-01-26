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
    """

    def generate_markdown(
        self,
        summary: EvaluationSummary,
        output_path: str = "docs/평가결과.md",
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
            self._query_type_breakdown(summary),
        ]

        if results:
            sections.append(self._detailed_results(results))

        sections.append(self._conclusion(summary))
        sections.append(self._footer())

        return "\n\n".join(sections)

    def _header(self, summary: EvaluationSummary) -> str:
        return f"""# 온톨로지 RAG 평가 결과 리포트

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
            grade = "우수"
        elif pass_rate_pct >= 60:
            grade = "양호"
        elif pass_rate_pct >= 40:
            grade = "보통"
        else:
            grade = "미흡"

        return f"""## 1. 요약

### 종합 성능

| 지표 | 값 | 평가 |
|------|------|------|
| **통과율** | {pass_rate_pct:.1f}% ({summary.passed_items}/{summary.total_items}) | {grade} |
| **환각 방지율** | {100 - hallucination_pct:.1f}% | {"달성" if hallucination_pct < 10 else "개선 필요"} |
| **안전 응답률** | {safe_response_pct:.1f}% | {"달성" if safe_response_pct >= 90 else "개선 필요"} |
| **평균 신뢰도** | {summary.avg_confidence:.1%} | {"달성" if summary.avg_confidence >= 0.7 else "개선 필요"} |
| **평균 응답 시간** | {summary.avg_latency_ms:.0f}ms | {"달성" if summary.avg_latency_ms < 5000 else "개선 필요"} |

### 핵심 지표 (KPI)

```
정확도(Accuracy)     [{self._progress_bar(summary.avg_answer_metrics.accuracy)}] {summary.avg_answer_metrics.accuracy:.0%}
환각방지율           [{self._progress_bar(1 - summary.verification_metrics.hallucination_rate)}] {(1 - summary.verification_metrics.hallucination_rate):.0%}
엔티티 추출 정확도   [{self._progress_bar(summary.avg_retrieval_metrics.entity_accuracy)}] {summary.avg_retrieval_metrics.entity_accuracy:.0%}
관련성(Relevance)    [{self._progress_bar(summary.avg_answer_metrics.relevance)}] {summary.avg_answer_metrics.relevance:.0%}
```"""

    def _progress_bar(self, value: float, width: int = 20) -> str:
        """ASCII 프로그레스 바 생성"""
        filled = int(value * width)
        empty = width - filled
        return "#" * filled + "-" * empty

    def _retrieval_metrics(self, summary: EvaluationSummary) -> str:
        m = summary.avg_retrieval_metrics
        return f"""## 2. 엔티티 추출 품질 (Retrieval Metrics)

| 지표 | 값 | 목표 | 달성 |
|------|------|------|------|
| **Precision** | {m.precision:.2%} | 80%+ | {"O" if m.precision >= 0.8 else "X"} |
| **Recall** | {m.recall:.2%} | 85%+ | {"O" if m.recall >= 0.85 else "X"} |
| **F1 Score** | {m.f1_score:.2%} | 80%+ | {"O" if m.f1_score >= 0.8 else "X"} |
| **Entity Accuracy** | {m.entity_accuracy:.2%} | 75%+ | {"O" if m.entity_accuracy >= 0.75 else "X"} |
| **Hit Rate** | {m.hit_rate:.2%} | 90%+ | {"O" if m.hit_rate >= 0.9 else "X"} |

### 설명
- **Precision**: 추출된 엔티티 중 정답 비율
- **Recall**: 예상 엔티티 중 추출된 비율
- **F1 Score**: Precision과 Recall의 조화 평균
- **Entity Accuracy**: 엔티티 추출 완전 일치율
- **Hit Rate**: 하나라도 정답 엔티티를 추출한 비율"""

    def _answer_metrics(self, summary: EvaluationSummary) -> str:
        m = summary.avg_answer_metrics
        return f"""## 3. 답변 품질 (Answer Metrics - LLM Judge)

| 지표 | 값 | 목표 | 달성 |
|------|------|------|------|
| **Accuracy** | {m.accuracy:.2%} | 85%+ | {"O" if m.accuracy >= 0.85 else "X"} |
| **Completeness** | {m.completeness:.2%} | 80%+ | {"O" if m.completeness >= 0.8 else "X"} |
| **Relevance** | {m.relevance:.2%} | 90%+ | {"O" if m.relevance >= 0.9 else "X"} |
| **Faithfulness** | {m.faithfulness:.2%} | 95%+ | {"O" if m.faithfulness >= 0.95 else "X"} |

### 설명
- **Accuracy**: 예상 정답과의 일치도
- **Completeness**: 핵심 정보 포함 여부
- **Relevance**: 질문에 대한 답변 적절성
- **Faithfulness**: 온톨로지 기반 여부 (환각 없음)"""

    def _verification_metrics(self, summary: EvaluationSummary) -> str:
        m = summary.verification_metrics
        return f"""## 4. ABSTAIN 검증 품질 (Verification Metrics)

| 지표 | 값 | 목표 | 달성 |
|------|------|------|------|
| **ABSTAIN Accuracy** | {m.abstain_accuracy:.2%} | 95%+ | {"O" if m.abstain_accuracy >= 0.95 else "X"} |
| **Hallucination Rate** | {m.hallucination_rate:.2%} | <5% | {"O" if m.hallucination_rate < 0.05 else "X"} |
| **Safe Response Rate** | {m.safe_response_rate:.2%} | 100% | {"O" if m.safe_response_rate >= 1.0 else "X"} |
| **False ABSTAIN Rate** | {m.false_abstain_rate:.2%} | <10% | {"O" if m.false_abstain_rate < 0.1 else "X"} |

### 설명
- **ABSTAIN Accuracy**: ABSTAIN 판단 정확도
- **Hallucination Rate**: 잘못된 정보를 생성한 비율 (낮을수록 좋음)
- **Safe Response Rate**: 도메인 외 질문에 ABSTAIN 응답 비율
- **False ABSTAIN Rate**: 답변해야 하는데 ABSTAIN한 비율 (낮을수록 좋음)"""

    def _category_breakdown(self, summary: EvaluationSummary) -> str:
        rows = []
        for cat, data in sorted(summary.by_category.items()):
            rows.append(
                f"| **{cat}** | {data['passed']}/{data['total']} | "
                f"{data['pass_rate']:.0%} | {data['avg_accuracy']:.2%} | {data['avg_confidence']:.2%} |"
            )

        return f"""## 5. 카테고리별 성능

| 카테고리 | 통과 | 통과율 | 평균 정확도 | 평균 신뢰도 |
|----------|------|--------|------------|------------|
{chr(10).join(rows)}

### 카테고리 설명
- **ontology**: 온톨로지 정의 질문 (Fz가 뭐야?, Fx와 Fz 차이)
- **sensor_analysis**: 센서값 분석 질문 (Fz가 -350N인데 뭐야?)
- **error_resolution**: 에러 해결 질문 (C153 에러 해결법)
- **pattern_history**: 패턴/이력 질문 (최근 충돌 패턴 있나요?)
- **specification**: 사양 질문 (UR5e 페이로드 몇 kg?)
- **invalid**: 도메인 외 질문 (안녕?, 날씨 어때?)"""

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
- **easy**: 단일 엔티티 직접 질문
- **medium**: 복합 엔티티 또는 맥락 필요
- **hard**: 추론 및 패턴 분석 필요"""

    def _query_type_breakdown(self, summary: EvaluationSummary) -> str:
        rows = []
        for qt, data in sorted(summary.by_query_type.items()):
            rows.append(
                f"| **{qt}** | {data['passed']}/{data['total']} | "
                f"{data['pass_rate']:.0%} | {data['avg_accuracy']:.2%} |"
            )

        return f"""## 7. 쿼리 타입별 성능

| 쿼리 타입 | 통과 | 통과율 | 평균 정확도 |
|-----------|------|--------|------------|
{chr(10).join(rows)}

### 쿼리 타입 설명
- **ONTOLOGY**: 온톨로지 추론 필요 (관계 탐색, 패턴 분석)
- **HYBRID**: 온톨로지 + 문서 검색 결합
- **RAG**: 일반 문서 검색"""

    def _detailed_results(self, results: List[EvaluationResult]) -> str:
        rows = []
        for r in results[:30]:  # 상위 30개만
            status = "O" if r.passed else "X"
            abstain = "ABSTAIN" if r.actual_abstain else "ANSWER"
            rows.append(
                f"| {status} | {r.benchmark_id} | {r.question[:30]}... | "
                f"{abstain} | {r.answer_metrics.accuracy:.0%} | {r.confidence:.0%} |"
            )

        return f"""## 8. 상세 결과 (상위 30개)

| 상태 | ID | 질문 | 응답 | 정확도 | 신뢰도 |
|------|-----|------|------|--------|--------|
{chr(10).join(rows)}"""

    def _conclusion(self, summary: EvaluationSummary) -> str:
        # 개선 필요 영역 식별
        improvements = []

        if summary.avg_retrieval_metrics.entity_accuracy < 0.75:
            improvements.append(f"- 엔티티 추출 정확도 향상 필요 (현재: {summary.avg_retrieval_metrics.entity_accuracy:.0%})")

        if summary.avg_answer_metrics.accuracy < 0.85:
            improvements.append(f"- 답변 정확도 향상 필요 (현재: {summary.avg_answer_metrics.accuracy:.0%})")

        if summary.verification_metrics.hallucination_rate > 0.05:
            improvements.append(f"- 환각 방지율 개선 필요 (현재 환각률: {summary.verification_metrics.hallucination_rate:.0%})")

        if summary.verification_metrics.false_abstain_rate > 0.1:
            improvements.append(f"- 잘못된 ABSTAIN 감소 필요 (현재: {summary.verification_metrics.false_abstain_rate:.0%})")

        if not improvements:
            improvements.append("- 모든 목표 지표 달성!")

        return f"""## 9. 결론 및 개선 방향

### 현재 성능 평가
- 전체 통과율: **{summary.pass_rate:.0%}**
- 평균 정확도: **{summary.avg_answer_metrics.accuracy:.0%}**
- 환각 방지율: **{(1 - summary.verification_metrics.hallucination_rate):.0%}**
- 평균 신뢰도: **{summary.avg_confidence:.0%}**

### 개선 필요 영역
{chr(10).join(improvements)}"""

    def _footer(self) -> str:
        return f"""---

*이 리포트는 온톨로지 RAG 평가 시스템에 의해 자동 생성되었습니다.*

*생성 시각: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*"""


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
            entity_accuracy=0.78,
            hit_rate=0.92,
        ),
        avg_answer_metrics=AnswerMetrics(
            accuracy=0.86,
            completeness=0.83,
            relevance=0.91,
            faithfulness=0.94,
        ),
        verification_metrics=VerificationMetrics(
            abstain_accuracy=0.95,
            hallucination_rate=0.03,
            safe_response_rate=1.0,
            false_abstain_rate=0.05,
        ),
        avg_latency_ms=3500,
        avg_confidence=0.85,
        by_category={
            "ontology": {"total": 10, "passed": 9, "pass_rate": 0.90, "avg_accuracy": 0.88, "avg_confidence": 0.90},
            "sensor_analysis": {"total": 8, "passed": 7, "pass_rate": 0.875, "avg_accuracy": 0.85, "avg_confidence": 0.88},
            "error_resolution": {"total": 8, "passed": 7, "pass_rate": 0.875, "avg_accuracy": 0.87, "avg_confidence": 0.86},
            "pattern_history": {"total": 6, "passed": 5, "pass_rate": 0.833, "avg_accuracy": 0.82, "avg_confidence": 0.84},
            "specification": {"total": 4, "passed": 4, "pass_rate": 1.0, "avg_accuracy": 0.95, "avg_confidence": 0.92},
            "invalid": {"total": 4, "passed": 3, "pass_rate": 0.75, "avg_accuracy": 1.0, "avg_confidence": 0.95},
        },
        by_difficulty={
            "easy": {"total": 20, "passed": 19, "pass_rate": 0.95, "avg_accuracy": 0.92, "avg_confidence": 0.90},
            "medium": {"total": 15, "passed": 13, "pass_rate": 0.87, "avg_accuracy": 0.82, "avg_confidence": 0.85},
            "hard": {"total": 5, "passed": 3, "pass_rate": 0.60, "avg_accuracy": 0.70, "avg_confidence": 0.75},
        },
        by_query_type={
            "ONTOLOGY": {"total": 25, "passed": 22, "pass_rate": 0.88, "avg_accuracy": 0.87, "avg_confidence": 0.88},
            "HYBRID": {"total": 10, "passed": 9, "pass_rate": 0.90, "avg_accuracy": 0.85, "avg_confidence": 0.86},
            "RAG": {"total": 5, "passed": 4, "pass_rate": 0.80, "avg_accuracy": 0.80, "avg_confidence": 0.82},
        },
    )

    generator = ReportGenerator()
    report = generator.generate_markdown(summary, "docs/평가결과_테스트.md")
    print("\nGenerated report preview:")
    print(report[:2000])
