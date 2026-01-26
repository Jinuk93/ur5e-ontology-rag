# ============================================================
# src/evaluation/evaluator.py - RAG Evaluation Runner
# ============================================================
# 온톨로지 RAG 파이프라인 평가 실행기
# ============================================================

import os
import sys
import time
import json
import requests
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
    extracted_entities: List[str]
    expected_entities: List[str]
    retrieval_metrics: RetrievalMetrics
    answer_metrics: AnswerMetrics
    actual_abstain: bool
    expected_abstain: bool
    query_type: str
    actual_query_type: str
    latency_ms: float
    passed: bool
    category: str
    difficulty: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "benchmark_id": self.benchmark_id,
            "question": self.question,
            "generated_answer": self.generated_answer[:200] + "..." if len(self.generated_answer) > 200 else self.generated_answer,
            "expected_answer": self.expected_answer[:200] + "..." if len(self.expected_answer) > 200 else self.expected_answer,
            "extracted_entities": self.extracted_entities,
            "expected_entities": self.expected_entities,
            "retrieval_metrics": self.retrieval_metrics.to_dict(),
            "answer_metrics": self.answer_metrics.to_dict(),
            "actual_abstain": self.actual_abstain,
            "expected_abstain": self.expected_abstain,
            "query_type": self.query_type,
            "actual_query_type": self.actual_query_type,
            "latency_ms": round(self.latency_ms, 2),
            "passed": self.passed,
            "category": self.category,
            "difficulty": self.difficulty,
            "confidence": round(self.confidence, 2),
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
    avg_confidence: float
    by_category: Dict[str, Dict[str, float]]
    by_difficulty: Dict[str, Dict[str, float]]
    by_query_type: Dict[str, Dict[str, float]]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "ontology_rag_v1"

    def to_dict(self) -> dict:
        return {
            "total_items": self.total_items,
            "passed_items": self.passed_items,
            "pass_rate": round(self.pass_rate, 4),
            "avg_retrieval_metrics": self.avg_retrieval_metrics.to_dict(),
            "avg_answer_metrics": self.avg_answer_metrics.to_dict(),
            "verification_metrics": self.verification_metrics.to_dict(),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "avg_confidence": round(self.avg_confidence, 4),
            "by_category": self.by_category,
            "by_difficulty": self.by_difficulty,
            "by_query_type": self.by_query_type,
            "timestamp": self.timestamp,
            "version": self.version,
        }


# ============================================================
# [2] Evaluator 클래스
# ============================================================

class Evaluator:
    """
    온톨로지 RAG 평가기

    벤치마크 데이터셋을 사용하여 RAG 파이프라인의 성능을 평가합니다.

    사용 예시:
        evaluator = Evaluator()
        summary = evaluator.evaluate_all()
        print(f"Pass Rate: {summary.pass_rate:.2%}")
    """

    def __init__(
        self,
        benchmark_dir: str = "data/benchmark",
        api_url: str = "http://localhost:8000",
        use_llm_judge: bool = True,
        verbose: bool = True,
    ):
        """
        Evaluator 초기화

        Args:
            benchmark_dir: 벤치마크 데이터 디렉토리
            api_url: API 서버 URL
            use_llm_judge: LLM 기반 평가 사용 여부 (False면 규칙 기반)
            verbose: 상세 출력 여부
        """
        self.benchmark = BenchmarkDataset(benchmark_dir)
        self.metrics_calculator = MetricsCalculator()
        self.judge = LLMJudge() if use_llm_judge else RuleBasedJudge()
        self.api_url = api_url
        self.verbose = verbose

    def evaluate_all(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        query_type: Optional[str] = None,
    ) -> EvaluationSummary:
        """
        전체 벤치마크 평가 실행

        Args:
            category: 특정 카테고리만 평가 (옵션)
            difficulty: 특정 난이도만 평가 (옵션)
            query_type: 특정 쿼리 타입만 평가 (옵션)

        Returns:
            EvaluationSummary: 평가 요약
        """
        # 벤치마크 로드 및 필터링
        items = self.benchmark.load()

        if category:
            items = [i for i in items if i.category == category]
        if difficulty:
            items = [i for i in items if i.difficulty == difficulty]
        if query_type:
            items = [i for i in items if i.query_type == query_type]

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
                abstain_str = "ABSTAIN" if result.actual_abstain else "ANSWER"
                print(f"    {status} {abstain_str} | Accuracy: {result.answer_metrics.accuracy:.2f} | Confidence: {result.confidence:.2f}")

        # 요약 계산
        summary = self._calculate_summary(results)

        if self.verbose:
            print(f"\n[OK] Evaluation complete!")
            print(f"  Pass Rate: {summary.pass_rate:.2%}")
            print(f"  Avg Accuracy: {summary.avg_answer_metrics.accuracy:.2%}")
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

        # Chat API 호출
        response = self._call_chat_api(item.question)
        latency_ms = (time.time() - start_time) * 1000

        # 응답 파싱
        generated_answer = response.get("answer", "")
        actual_abstain = response.get("abstain", False)
        confidence = response.get("confidence", 0.0)
        actual_query_type = response.get("query_type", "UNKNOWN")

        # 추출된 엔티티
        extracted_entities = []
        classification = response.get("classification", {})
        if classification.get("entities"):
            extracted_entities = [e.get("entity_id", "") for e in classification["entities"]]

        # 엔티티 추출 품질 평가
        retrieval_metrics = self.metrics_calculator.calculate_retrieval_metrics(
            extracted=extracted_entities,
            expected=item.expected_entities,
        )

        # 답변 품질 평가 (LLM Judge)
        answer_metrics = self.judge.evaluate(
            question=item.question,
            generated_answer=generated_answer,
            expected_answer=item.expected_answer,
        )

        # 통과 여부 판정
        passed = self._check_passed(
            answer_metrics=answer_metrics,
            actual_abstain=actual_abstain,
            expected_abstain=item.expected_abstain,
            category=item.category,
        )

        return EvaluationResult(
            benchmark_id=item.id,
            question=item.question,
            generated_answer=generated_answer,
            expected_answer=item.expected_answer,
            extracted_entities=extracted_entities,
            expected_entities=item.expected_entities,
            retrieval_metrics=retrieval_metrics,
            answer_metrics=answer_metrics,
            actual_abstain=actual_abstain,
            expected_abstain=item.expected_abstain,
            query_type=item.query_type,
            actual_query_type=actual_query_type,
            latency_ms=latency_ms,
            passed=passed,
            category=item.category,
            difficulty=item.difficulty,
            confidence=confidence,
        )

    def _call_chat_api(self, question: str) -> Dict[str, Any]:
        """Chat API 호출"""
        try:
            response = requests.post(
                f"{self.api_url}/api/chat/query",
                json={"question": question},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API call error: {e}")
            return {
                "answer": "",
                "abstain": True,
                "confidence": 0.0,
                "query_type": "ERROR",
            }

    def _check_passed(
        self,
        answer_metrics: AnswerMetrics,
        actual_abstain: bool,
        expected_abstain: bool,
        category: str,
    ) -> bool:
        """
        평가 항목 통과 여부 판정

        기준:
        - invalid 카테고리: ABSTAIN이어야 통과
        - 일반 질문: accuracy >= 0.6 AND relevance >= 0.6
        - ABSTAIN이 예상되는 경우: ABSTAIN 여부로 판정
        """
        # invalid 카테고리는 ABSTAIN 응답이어야 통과
        if category == "invalid":
            return actual_abstain

        # ABSTAIN이 예상되는 경우
        if expected_abstain:
            return actual_abstain

        # 일반 질문은 정확도와 관련성 기준
        return (
            answer_metrics.accuracy >= 0.6 and
            answer_metrics.relevance >= 0.6 and
            not actual_abstain  # 답변해야 하는데 ABSTAIN하면 실패
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
                "actual_abstain": r.actual_abstain,
                "expected_abstain": r.expected_abstain,
                "category": r.category,
            }
            for r in results
        ]
        verification_metrics = self.metrics_calculator.calculate_verification_metrics(verification_data)

        # 평균 지연 시간 및 신뢰도
        avg_latency = sum(r.latency_ms for r in results) / total if total > 0 else 0
        avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 0

        # 카테고리별 통계
        by_category = self._calculate_group_stats(results, "category")

        # 난이도별 통계
        by_difficulty = self._calculate_group_stats(results, "difficulty")

        # 쿼리 타입별 통계
        by_query_type = self._calculate_group_stats(results, "query_type")

        return EvaluationSummary(
            total_items=total,
            passed_items=passed,
            pass_rate=passed / total if total > 0 else 0,
            avg_retrieval_metrics=avg_retrieval,
            avg_answer_metrics=avg_answer,
            verification_metrics=verification_metrics,
            avg_latency_ms=avg_latency,
            avg_confidence=avg_confidence,
            by_category=by_category,
            by_difficulty=by_difficulty,
            by_query_type=by_query_type,
        )

    def _calculate_group_stats(
        self,
        results: List[EvaluationResult],
        group_key: str
    ) -> Dict[str, Dict[str, float]]:
        """그룹별 통계 계산"""
        groups = {}
        for r in results:
            group_value = getattr(r, group_key)
            if group_value not in groups:
                groups[group_value] = []
            groups[group_value].append(r)

        stats = {}
        for group_value, group_results in groups.items():
            group_passed = sum(1 for r in group_results if r.passed)
            group_answer_metrics = [r.answer_metrics for r in group_results]
            avg_accuracy = sum(m.accuracy for m in group_answer_metrics) / len(group_answer_metrics)
            avg_confidence = sum(r.confidence for r in group_results) / len(group_results)

            stats[group_value] = {
                "total": len(group_results),
                "passed": group_passed,
                "pass_rate": group_passed / len(group_results),
                "avg_accuracy": avg_accuracy,
                "avg_confidence": avg_confidence,
            }

        return stats

    def save_results(
        self,
        summary: EvaluationSummary,
        results: Optional[List[EvaluationResult]] = None,
        output_dir: str = "data/evaluation/results",
    ) -> str:
        """
        평가 결과 JSON 저장

        Args:
            summary: 평가 요약
            results: 개별 결과 목록 (선택)
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

        # 저장할 데이터
        data = {
            "summary": summary.to_dict(),
            "results": [r.to_dict() for r in results] if results else [],
        }

        # JSON 저장
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # latest.json 링크
        latest_path = output_path / "latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if self.verbose:
            print(f"\n[OK] Results saved to: {filepath}")

        return str(filepath)


# ============================================================
# 모듈 테스트
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Ontology RAG Evaluator Test")
    print("=" * 60)

    # 벤치마크 통계 확인
    benchmark = BenchmarkDataset()
    try:
        benchmark.load()
        stats = benchmark.get_statistics()
        print(f"\nBenchmark Statistics:")
        print(f"  Total: {stats['total']}")
        print(f"  By Category: {stats['by_category']}")
        print(f"  By Difficulty: {stats['by_difficulty']}")
        print(f"  By Query Type: {stats['by_query_type']}")
    except Exception as e:
        print(f"\nNo benchmark data found: {e}")
        print("Creating sample benchmark data...")

    print("\n" + "=" * 60)
    print("To run full evaluation:")
    print("  python scripts/run_evaluation.py")
    print("=" * 60)
