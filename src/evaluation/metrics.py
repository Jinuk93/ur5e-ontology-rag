# ============================================================
# src/evaluation/metrics.py - Evaluation Metrics Calculator
# ============================================================

from dataclasses import dataclass
from typing import List, Set, Optional


@dataclass
class RetrievalMetrics:
    """검색 품질 지표"""
    precision: float    # |검색 ∩ 정답| / |검색|
    recall: float       # |검색 ∩ 정답| / |정답|
    f1_score: float     # 2 * P * R / (P + R)
    mrr: float          # 1 / (첫 번째 정답 순위)
    hit_rate: float     # 적어도 하나 맞춘 비율

    def to_dict(self) -> dict:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "mrr": round(self.mrr, 4),
            "hit_rate": round(self.hit_rate, 4),
        }


@dataclass
class AnswerMetrics:
    """답변 품질 지표 (LLM-as-Judge)"""
    accuracy: float      # 예상 정답과의 일치도
    completeness: float  # 핵심 정보 포함 여부
    relevance: float     # 질문과의 관련성
    faithfulness: float  # 컨텍스트 기반 여부

    def to_dict(self) -> dict:
        return {
            "accuracy": round(self.accuracy, 4),
            "completeness": round(self.completeness, 4),
            "relevance": round(self.relevance, 4),
            "faithfulness": round(self.faithfulness, 4),
        }

    @property
    def average(self) -> float:
        """평균 점수"""
        return (self.accuracy + self.completeness + self.relevance + self.faithfulness) / 4


@dataclass
class VerificationMetrics:
    """검증 품질 지표"""
    hallucination_rate: float    # 환각 발생률 (낮을수록 좋음)
    safe_response_rate: float    # 안전 응답률 (INSUFFICIENT 정상 반환)
    verification_accuracy: float # 검증 결과 정확도

    def to_dict(self) -> dict:
        return {
            "hallucination_rate": round(self.hallucination_rate, 4),
            "safe_response_rate": round(self.safe_response_rate, 4),
            "verification_accuracy": round(self.verification_accuracy, 4),
        }


class MetricsCalculator:
    """평가 지표 계산기"""

    def calculate_retrieval_metrics(
        self,
        retrieved: List[str],
        expected: List[str],
        retrieved_ranks: Optional[List[int]] = None,
    ) -> RetrievalMetrics:
        """
        검색 품질 지표 계산

        Args:
            retrieved: 검색된 컨텍스트 목록
            expected: 예상 컨텍스트 목록
            retrieved_ranks: 검색된 각 항목의 순위 (MRR 계산용)
        """
        retrieved_set = set(self._normalize_contexts(retrieved))
        expected_set = set(self._normalize_contexts(expected))

        precision = self.calculate_precision(retrieved_set, expected_set)
        recall = self.calculate_recall(retrieved_set, expected_set)
        f1 = self.calculate_f1(precision, recall)
        mrr = self.calculate_mrr(retrieved, expected, retrieved_ranks)
        hit_rate = 1.0 if retrieved_set.intersection(expected_set) else 0.0

        return RetrievalMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1,
            mrr=mrr,
            hit_rate=hit_rate,
        )

    def _normalize_contexts(self, contexts: List[str]) -> List[str]:
        """컨텍스트 정규화 (소문자, 공백 제거)"""
        return [c.lower().strip() for c in contexts if c]

    def calculate_precision(self, retrieved: Set[str], expected: Set[str]) -> float:
        """
        Precision = |검색 ∩ 정답| / |검색|
        검색된 결과 중 정답이 포함된 비율
        """
        if len(retrieved) == 0:
            return 0.0
        intersection = retrieved.intersection(expected)
        return len(intersection) / len(retrieved)

    def calculate_recall(self, retrieved: Set[str], expected: Set[str]) -> float:
        """
        Recall = |검색 ∩ 정답| / |정답|
        정답 중 검색된 비율
        """
        if len(expected) == 0:
            return 1.0  # 정답이 없으면 Recall은 1 (완전히 검색됨)
        intersection = retrieved.intersection(expected)
        return len(intersection) / len(expected)

    def calculate_f1(self, precision: float, recall: float) -> float:
        """
        F1 Score = 2 * Precision * Recall / (Precision + Recall)
        Precision과 Recall의 조화 평균
        """
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def calculate_mrr(
        self,
        retrieved: List[str],
        expected: List[str],
        ranks: Optional[List[int]] = None,
    ) -> float:
        """
        MRR (Mean Reciprocal Rank) = 1 / (첫 번째 정답의 순위)
        첫 번째로 맞은 정답의 역순위
        """
        if not expected:
            return 1.0

        retrieved_normalized = self._normalize_contexts(retrieved)
        expected_normalized = set(self._normalize_contexts(expected))

        # 첫 번째 정답 찾기
        for i, item in enumerate(retrieved_normalized, 1):
            if item in expected_normalized:
                return 1.0 / i

        return 0.0  # 정답을 찾지 못함

    def calculate_verification_metrics(
        self,
        results: List[dict],
    ) -> VerificationMetrics:
        """
        검증 품질 지표 계산

        Args:
            results: 평가 결과 목록, 각 항목은 다음 키를 포함:
                - verification_status: 실제 검증 상태
                - expected_verification: 예상 검증 상태
                - category: 카테고리 (invalid인 경우 환각 테스트)
        """
        if not results:
            return VerificationMetrics(
                hallucination_rate=0.0,
                safe_response_rate=0.0,
                verification_accuracy=0.0,
            )

        total = len(results)
        hallucination_count = 0
        safe_response_correct = 0
        verification_correct = 0
        invalid_count = 0

        for result in results:
            actual_status = result.get("verification_status", "").lower()
            expected_status = result.get("expected_verification", "").lower()
            category = result.get("category", "")

            # 검증 정확도
            if actual_status == expected_status:
                verification_correct += 1

            # invalid 카테고리 처리 (환각 테스트)
            if category == "invalid":
                invalid_count += 1
                # insufficient가 아닌 응답은 환각
                if actual_status != "insufficient":
                    hallucination_count += 1
                else:
                    safe_response_correct += 1
            else:
                # 일반 카테고리에서 verified가 아닌데 verified로 응답하면 환각
                if expected_status != "verified" and actual_status == "verified":
                    hallucination_count += 1

        # 환각 발생률
        hallucination_rate = hallucination_count / total if total > 0 else 0.0

        # 안전 응답률 (invalid 질문에 대해 insufficient 정상 반환)
        safe_response_rate = safe_response_correct / invalid_count if invalid_count > 0 else 1.0

        # 검증 정확도
        verification_accuracy = verification_correct / total if total > 0 else 0.0

        return VerificationMetrics(
            hallucination_rate=hallucination_rate,
            safe_response_rate=safe_response_rate,
            verification_accuracy=verification_accuracy,
        )

    def aggregate_retrieval_metrics(
        self,
        metrics_list: List[RetrievalMetrics],
    ) -> RetrievalMetrics:
        """여러 RetrievalMetrics의 평균 계산"""
        if not metrics_list:
            return RetrievalMetrics(0.0, 0.0, 0.0, 0.0, 0.0)

        n = len(metrics_list)
        return RetrievalMetrics(
            precision=sum(m.precision for m in metrics_list) / n,
            recall=sum(m.recall for m in metrics_list) / n,
            f1_score=sum(m.f1_score for m in metrics_list) / n,
            mrr=sum(m.mrr for m in metrics_list) / n,
            hit_rate=sum(m.hit_rate for m in metrics_list) / n,
        )

    def aggregate_answer_metrics(
        self,
        metrics_list: List[AnswerMetrics],
    ) -> AnswerMetrics:
        """여러 AnswerMetrics의 평균 계산"""
        if not metrics_list:
            return AnswerMetrics(0.0, 0.0, 0.0, 0.0)

        n = len(metrics_list)
        return AnswerMetrics(
            accuracy=sum(m.accuracy for m in metrics_list) / n,
            completeness=sum(m.completeness for m in metrics_list) / n,
            relevance=sum(m.relevance for m in metrics_list) / n,
            faithfulness=sum(m.faithfulness for m in metrics_list) / n,
        )


# 모듈 테스트
if __name__ == "__main__":
    calc = MetricsCalculator()

    # 검색 품질 테스트
    retrieved = ["C103", "Joint", "Control Box"]
    expected = ["C103", "Joint"]

    metrics = calc.calculate_retrieval_metrics(retrieved, expected)
    print("Retrieval Metrics:")
    print(f"  Precision: {metrics.precision:.4f}")
    print(f"  Recall: {metrics.recall:.4f}")
    print(f"  F1 Score: {metrics.f1_score:.4f}")
    print(f"  MRR: {metrics.mrr:.4f}")
    print(f"  Hit Rate: {metrics.hit_rate:.4f}")

    # 검증 품질 테스트
    test_results = [
        {"verification_status": "verified", "expected_verification": "verified", "category": "error_code"},
        {"verification_status": "insufficient", "expected_verification": "insufficient", "category": "invalid"},
        {"verification_status": "verified", "expected_verification": "insufficient", "category": "invalid"},  # 환각
    ]

    v_metrics = calc.calculate_verification_metrics(test_results)
    print("\nVerification Metrics:")
    print(f"  Hallucination Rate: {v_metrics.hallucination_rate:.4f}")
    print(f"  Safe Response Rate: {v_metrics.safe_response_rate:.4f}")
    print(f"  Verification Accuracy: {v_metrics.verification_accuracy:.4f}")
