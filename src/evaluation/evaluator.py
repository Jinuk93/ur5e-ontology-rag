# ============================================================
# src/evaluation/evaluator.py - RAG Evaluation Runner
# ============================================================
# RAG 파이프라인 평가 실행기
# ============================================================

import os
import sys
import time
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.evaluation.benchmark import BenchmarkItem, BenchmarkDataset
from src.evaluation.metrics import MetricsCalculator, RetrievalMetrics, AnswerMetrics, VerificationMetrics
from src.evaluation.llm_judge import LLMJudge, RuleBasedJudge


# ============================================================
# [1] 데이터 클래스
# ============================================================

@dataclass
class EvaluationResult:
    """단일 항목 평가 결과"""
    benchmark_id: str
    question: str
    generated_answer: str
    expected_answer: str
    retrieved_contexts: List[str]
    expected_contexts: List[str]
    retrieval_metrics: RetrievalMetrics
    answer_metrics: AnswerMetrics
    verification_status: str
    expected_verification: str
    latency_ms: float
    passed: bool
    category: str
    difficulty: str

    def to_dict(self) -> dict:
        return {
            "benchmark_id": self.benchmark_id,
            "question": self.question,
            "generated_answer": self.generated_answer,
            "expected_answer": self.expected_answer,
            "retrieved_contexts": self.retrieved_contexts,
            "expected_contexts": self.expected_contexts,
            "retrieval_metrics": self.retrieval_metrics.to_dict(),
            "answer_metrics": self.answer_metrics.to_dict(),
            "verification_status": self.verification_status,
            "expected_verification": self.expected_verification,
            "latency_ms": round(self.latency_ms, 2),
            "passed": self.passed,
            "category": self.category,
            "difficulty": self.difficulty,
        }


@dataclass
class EvaluationSummary:
    """전체 평가 요약"""
    total_items: int
    passed_items: int
    pass_rate: float
    avg_retrieval_metrics: RetrievalMetrics
    avg_answer_metrics: AnswerMetrics
    verification_metrics: VerificationMetrics
    avg_latency_ms: float
    by_category: Dict[str, Dict[str, float]]
    by_difficulty: Dict[str, Dict[str, float]]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "v3"  # Phase 7

    def to_dict(self) -> dict:
        return {
            "total_items": self.total_items,
            "passed_items": self.passed_items,
            "pass_rate": round(self.pass_rate, 4),
            "avg_retrieval_metrics": self.avg_retrieval_metrics.to_dict(),
            "avg_answer_metrics": self.avg_answer_metrics.to_dict(),
            "verification_metrics": self.verification_metrics.to_dict(),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "by_category": self.by_category,
            "by_difficulty": self.by_difficulty,
            "timestamp": self.timestamp,
            "version": self.version,
        }


# ============================================================
# [2] Evaluator 클래스
# ============================================================

class Evaluator:
    """
    RAG 평가기

    벤치마크 데이터셋을 사용하여 RAG 파이프라인의 성능을 평가합니다.

    사용 예시:
        evaluator = Evaluator()
        summary = evaluator.evaluate_all()
        print(f"Pass Rate: {summary.pass_rate:.2%}")
    """

    def __init__(
        self,
        benchmark_dir: str = "data/benchmark",
        use_llm_judge: bool = True,
        verbose: bool = True,
    ):
        """
        Evaluator 초기화

        Args:
            benchmark_dir: 벤치마크 데이터 디렉토리
            use_llm_judge: LLM 기반 평가 사용 여부 (False면 규칙 기반)
            verbose: 상세 출력 여부
        """
        self.benchmark = BenchmarkDataset(benchmark_dir)
        self.metrics_calculator = MetricsCalculator()
        self.judge = LLMJudge() if use_llm_judge else RuleBasedJudge()
        self.verbose = verbose

        # RAG 서비스 지연 로드
        self._rag_service = None

    @property
    def rag_service(self):
        """RAG 서비스 지연 로드"""
        if self._rag_service is None:
            from src.api.services.rag_service import RAGService
            self._rag_service = RAGService()
        return self._rag_service

    def evaluate_all(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> EvaluationSummary:
        """
        전체 벤치마크 평가 실행

        Args:
            category: 특정 카테고리만 평가 (옵션)
            difficulty: 특정 난이도만 평가 (옵션)

        Returns:
            EvaluationSummary: 평가 요약
        """
        # 벤치마크 로드 및 필터링
        items = self.benchmark.load()

        if category:
            items = [i for i in items if i.category == category]
        if difficulty:
            items = [i for i in items if i.difficulty == difficulty]

        if not items:
            raise ValueError("No benchmark items found matching the criteria")

        if self.verbose:
            print(f"\n[*] Evaluating {len(items)} benchmark items...")

        # 개별 평가 실행
        results: List[EvaluationResult] = []
        for i, item in enumerate(items, 1):
            if self.verbose:
                print(f"  [{i}/{len(items)}] {item.id}: {item.question[:50]}...")

            result = self.evaluate_item(item)
            results.append(result)

            if self.verbose:
                status = "✓" if result.passed else "✗"
                print(f"    {status} Answer: {result.answer_metrics.accuracy:.2f}, Verification: {result.verification_status}")

        # 요약 계산
        summary = self._calculate_summary(results)

        if self.verbose:
            print(f"\n[OK] Evaluation complete!")
            print(f"  Pass Rate: {summary.pass_rate:.2%}")
            print(f"  Avg Accuracy: {summary.avg_answer_metrics.accuracy:.2f}")
            print(f"  Hallucination Rate: {summary.verification_metrics.hallucination_rate:.2%}")

        return summary

    def evaluate_item(self, item: BenchmarkItem) -> EvaluationResult:
        """
        단일 항목 평가

        Args:
            item: 벤치마크 항목

        Returns:
            EvaluationResult: 평가 결과
        """
        start_time = time.time()

        # RAG 질의 실행
        response = self.rag_service.query(
            question=item.question,
            top_k=5,
            include_sources=True,
            include_citation=False,  # 평가 시에는 인용 제외
        )

        latency_ms = (time.time() - start_time) * 1000

        # 검색된 컨텍스트 추출
        retrieved_contexts = []
        if response.sources:
            retrieved_contexts = [s.name for s in response.sources]

        # 검색 품질 평가
        retrieval_metrics = self.metrics_calculator.calculate_retrieval_metrics(
            retrieved=retrieved_contexts,
            expected=item.expected_contexts,
        )

        # 답변 품질 평가 (LLM Judge)
        answer_metrics = self.judge.evaluate(
            question=item.question,
            generated_answer=response.answer,
            expected_answer=item.expected_answer,
        )

        # 검증 상태
        verification_status = response.verification.status.value if response.verification else "unknown"

        # 통과 여부 판정
        passed = self._check_passed(
            answer_metrics=answer_metrics,
            verification_status=verification_status,
            expected_verification=item.expected_verification,
            category=item.category,
        )

        return EvaluationResult(
            benchmark_id=item.id,
            question=item.question,
            generated_answer=response.answer,
            expected_answer=item.expected_answer,
            retrieved_contexts=retrieved_contexts,
            expected_contexts=item.expected_contexts,
            retrieval_metrics=retrieval_metrics,
            answer_metrics=answer_metrics,
            verification_status=verification_status,
            expected_verification=item.expected_verification,
            latency_ms=latency_ms,
            passed=passed,
            category=item.category,
            difficulty=item.difficulty,
        )

    def _check_passed(
        self,
        answer_metrics: AnswerMetrics,
        verification_status: str,
        expected_verification: str,
        category: str,
    ) -> bool:
        """
        평가 항목 통과 여부 판정

        기준:
        - 일반 질문: accuracy >= 0.6 AND relevance >= 0.6
        - invalid 질문: verification_status == "insufficient"
        """
        if category == "invalid":
            # invalid 카테고리는 insufficient 응답이어야 통과
            return verification_status.lower() == "insufficient"
        else:
            # 일반 질문은 정확도와 관련성 기준
            return (
                answer_metrics.accuracy >= 0.6 and
                answer_metrics.relevance >= 0.6
            )

    def _calculate_summary(self, results: List[EvaluationResult]) -> EvaluationSummary:
        """평가 결과 요약 계산"""

        total = len(results)
        passed = sum(1 for r in results if r.passed)

        # 메트릭 평균
        retrieval_metrics_list = [r.retrieval_metrics for r in results]
        answer_metrics_list = [r.answer_metrics for r in results]

        avg_retrieval = self.metrics_calculator.aggregate_retrieval_metrics(retrieval_metrics_list)
        avg_answer = self.metrics_calculator.aggregate_answer_metrics(answer_metrics_list)

        # 검증 메트릭
        verification_data = [
            {
                "verification_status": r.verification_status,
                "expected_verification": r.expected_verification,
                "category": r.category,
            }
            for r in results
        ]
        verification_metrics = self.metrics_calculator.calculate_verification_metrics(verification_data)

        # 평균 지연 시간
        avg_latency = sum(r.latency_ms for r in results) / total if total > 0 else 0

        # 카테고리별 통계
        by_category = {}
        for cat in set(r.category for r in results):
            cat_results = [r for r in results if r.category == cat]
            cat_passed = sum(1 for r in cat_results if r.passed)
            cat_answer_metrics = [r.answer_metrics for r in cat_results]
            avg_accuracy = sum(m.accuracy for m in cat_answer_metrics) / len(cat_answer_metrics)
            by_category[cat] = {
                "total": len(cat_results),
                "passed": cat_passed,
                "pass_rate": cat_passed / len(cat_results),
                "avg_accuracy": avg_accuracy,
            }

        # 난이도별 통계
        by_difficulty = {}
        for diff in set(r.difficulty for r in results):
            diff_results = [r for r in results if r.difficulty == diff]
            diff_passed = sum(1 for r in diff_results if r.passed)
            diff_answer_metrics = [r.answer_metrics for r in diff_results]
            avg_accuracy = sum(m.accuracy for m in diff_answer_metrics) / len(diff_answer_metrics)
            by_difficulty[diff] = {
                "total": len(diff_results),
                "passed": diff_passed,
                "pass_rate": diff_passed / len(diff_results),
                "avg_accuracy": avg_accuracy,
            }

        return EvaluationSummary(
            total_items=total,
            passed_items=passed,
            pass_rate=passed / total if total > 0 else 0,
            avg_retrieval_metrics=avg_retrieval,
            avg_answer_metrics=avg_answer,
            verification_metrics=verification_metrics,
            avg_latency_ms=avg_latency,
            by_category=by_category,
            by_difficulty=by_difficulty,
        )

    def compare_pipelines(
        self,
        pipelines: Dict[str, Any],
        items: Optional[List[BenchmarkItem]] = None,
    ) -> Dict[str, EvaluationSummary]:
        """
        여러 파이프라인 비교 평가 (A/B 테스트)

        Args:
            pipelines: {"v1": service1, "v2": service2, ...}
            items: 평가할 벤치마크 항목 (None이면 전체)

        Returns:
            Dict[str, EvaluationSummary]: 버전별 평가 결과
        """
        if items is None:
            items = self.benchmark.load()

        results = {}
        for version, service in pipelines.items():
            if self.verbose:
                print(f"\n[*] Evaluating pipeline: {version}")

            # RAG 서비스 교체
            original_service = self._rag_service
            self._rag_service = service

            try:
                summary = self.evaluate_all()
                summary.version = version
                results[version] = summary
            finally:
                # 원래 서비스로 복원
                self._rag_service = original_service

        return results

    def save_results(
        self,
        summary: EvaluationSummary,
        output_dir: str = "data/evaluation/results",
    ) -> str:
        """
        평가 결과 JSON 저장

        Args:
            summary: 평가 요약
            output_dir: 출력 디렉토리

        Returns:
            str: 저장된 파일 경로
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_{timestamp}_{summary.version}.json"
        filepath = output_path / filename

        # JSON 저장
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, ensure_ascii=False, indent=2)

        # latest.json 링크
        latest_path = output_path / "latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, ensure_ascii=False, indent=2)

        if self.verbose:
            print(f"\n[OK] Results saved to: {filepath}")

        return str(filepath)


# ============================================================
# 모듈 테스트
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("RAG Evaluator Test")
    print("=" * 60)

    # 벤치마크 통계 확인
    benchmark = BenchmarkDataset()
    benchmark.load()
    stats = benchmark.get_statistics()
    print(f"\nBenchmark Statistics:")
    print(f"  Total: {stats['total']}")
    print(f"  By Category: {stats['by_category']}")
    print(f"  By Difficulty: {stats['by_difficulty']}")

    # 평가 실행 (테스트용으로 5개만)
    print("\n" + "-" * 60)
    print("Running evaluation (first 5 items)...")

    evaluator = Evaluator(use_llm_judge=True, verbose=True)

    # 첫 5개만 테스트
    items = evaluator.benchmark.load()[:5]
    results = []

    for item in items:
        result = evaluator.evaluate_item(item)
        results.append(result)

    print("\n" + "-" * 60)
    print("Results:")
    for r in results:
        status = "✓" if r.passed else "✗"
        print(f"  {status} {r.benchmark_id}: accuracy={r.answer_metrics.accuracy:.2f}, verification={r.verification_status}")
