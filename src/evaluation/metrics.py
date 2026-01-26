# ============================================================
# src/evaluation/metrics.py - Evaluation Metrics Calculator
# ============================================================
# 온톨로지 RAG 시스템 평가 지표 계산기
# ============================================================

from dataclasses import dataclass
from typing import List, Set, Optional


@dataclass
class RetrievalMetrics:
    """검색/엔티티 추출 품질 지표"""
    precision: float    # |추출 ∩ 정답| / |추출|
    recall: float       # |추출 ∩ 정답| / |정답|
    f1_score: float     # 2 * P * R / (P + R)
    entity_accuracy: float  # 엔티티 추출 정확도
    hit_rate: float     # 적어도 하나 맞춘 비율

    def to_dict(self) -> dict:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "entity_accuracy": round(self.entity_accuracy, 4),
            "hit_rate": round(self.hit_rate, 4),
        }


@dataclass
class AnswerMetrics:
    """답변 품질 지표 (LLM-as-Judge)"""
    accuracy: float      # 예상 정답과의 일치도
    completeness: float  # 핵심 정보 포함 여부
    relevance: float     # 질문과의 관련성
    faithfulness: float  # 온톨로지 기반 여부 (환각 없음)

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
    """ABSTAIN 검증 품질 지표"""
    abstain_accuracy: float       # ABSTAIN 판단 정확도
    hallucination_rate: float     # 환각 발생률 (낮을수록 좋음)
    safe_response_rate: float     # 안전 응답률 (invalid 질문에 ABSTAIN)
    false_abstain_rate: float     # 잘못된 ABSTAIN 비율

    def to_dict(self) -> dict:
        return {
            "abstain_accuracy": round(self.abstain_accuracy, 4),
            "hallucination_rate": round(self.hallucination_rate, 4),
            "safe_response_rate": round(self.safe_response_rate, 4),
            "false_abstain_rate": round(self.false_abstain_rate, 4),
        }


class MetricsCalculator:
    """평가 지표 계산기"""

    def calculate_retrieval_metrics(
        self,
        extracted: List[str],
        expected: List[str],
    ) -> RetrievalMetrics:
        """
        엔티티 추출 품질 지표 계산

        Args:
            extracted: 추출된 엔티티 ID 목록
            expected: 예상 엔티티 ID 목록
        """
        extracted_set = set(self._normalize(extracted))
        expected_set = set(self._normalize(expected))

        precision = self.calculate_precision(extracted_set, expected_set)
        recall = self.calculate_recall(extracted_set, expected_set)
        f1 = self.calculate_f1(precision, recall)
        hit_rate = 1.0 if extracted_set.intersection(expected_set) else 0.0

        # 엔티티 정확도 (완전 일치)
        entity_accuracy = 1.0 if extracted_set == expected_set else (
            len(extracted_set.intersection(expected_set)) / max(len(expected_set), 1)
        )

        return RetrievalMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1,
            entity_accuracy=entity_accuracy,
            hit_rate=hit_rate,
        )

    def _normalize(self, items: List[str]) -> List[str]:
        """정규화 (대문자, 공백 제거)"""
        return [i.upper().strip() for i in items if i]

    def calculate_precision(self, extracted: Set[str], expected: Set[str]) -> float:
        """Precision = |추출 ∩ 정답| / |추출|"""
        if len(extracted) == 0:
            return 1.0 if len(expected) == 0 else 0.0
        intersection = extracted.intersection(expected)
        return len(intersection) / len(extracted)

    def calculate_recall(self, extracted: Set[str], expected: Set[str]) -> float:
        """Recall = |추출 ∩ 정답| / |정답|"""
        if len(expected) == 0:
            return 1.0
        intersection = extracted.intersection(expected)
        return len(intersection) / len(expected)

    def calculate_f1(self, precision: float, recall: float) -> float:
        """F1 Score = 2 * Precision * Recall / (Precision + Recall)"""
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def calculate_verification_metrics(
        self,
        results: List[dict],
    ) -> VerificationMetrics:
        """
        ABSTAIN 검증 품질 지표 계산

        Args:
            results: 평가 결과 목록, 각 항목은 다음 키를 포함:
                - actual_abstain: 실제 ABSTAIN 여부
                - expected_abstain: 예상 ABSTAIN 여부
                - category: 카테고리
        """
        if not results:
            return VerificationMetrics(
                abstain_accuracy=0.0,
                hallucination_rate=0.0,
                safe_response_rate=0.0,
                false_abstain_rate=0.0,
            )

        total = len(results)
        correct_abstain = 0
        hallucination_count = 0
        safe_response_correct = 0
        false_abstain_count = 0
        invalid_count = 0
        valid_count = 0

        for result in results:
            actual_abstain = result.get("actual_abstain", False)
            expected_abstain = result.get("expected_abstain", False)
            category = result.get("category", "")

            # ABSTAIN 정확도
            if actual_abstain == expected_abstain:
                correct_abstain += 1

            # invalid 카테고리 처리 (ABSTAIN 필수)
            if category == "invalid":
                invalid_count += 1
                if actual_abstain:
                    safe_response_correct += 1
                else:
                    hallucination_count += 1
            else:
                valid_count += 1
                # 유효한 질문에 대해 잘못된 ABSTAIN
                if actual_abstain and not expected_abstain:
                    false_abstain_count += 1
                # 유효한 질문에 답변해야 하는데 환각 응답
                if not actual_abstain and expected_abstain:
                    hallucination_count += 1

        abstain_accuracy = correct_abstain / total if total > 0 else 0.0
        hallucination_rate = hallucination_count / total if total > 0 else 0.0
        safe_response_rate = safe_response_correct / invalid_count if invalid_count > 0 else 1.0
        false_abstain_rate = false_abstain_count / valid_count if valid_count > 0 else 0.0

        return VerificationMetrics(
            abstain_accuracy=abstain_accuracy,
            hallucination_rate=hallucination_rate,
            safe_response_rate=safe_response_rate,
            false_abstain_rate=false_abstain_rate,
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
            entity_accuracy=sum(m.entity_accuracy for m in metrics_list) / n,
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

    # 엔티티 추출 품질 테스트
    extracted = ["C153", "Fz", "UR5e"]
    expected = ["C153", "Fz"]

    metrics = calc.calculate_retrieval_metrics(extracted, expected)
    print("Retrieval Metrics:")
    print(f"  Precision: {metrics.precision:.4f}")
    print(f"  Recall: {metrics.recall:.4f}")
    print(f"  F1 Score: {metrics.f1_score:.4f}")
    print(f"  Entity Accuracy: {metrics.entity_accuracy:.4f}")
    print(f"  Hit Rate: {metrics.hit_rate:.4f}")

    # ABSTAIN 검증 품질 테스트
    test_results = [
        {"actual_abstain": False, "expected_abstain": False, "category": "ontology"},
        {"actual_abstain": True, "expected_abstain": True, "category": "invalid"},
        {"actual_abstain": False, "expected_abstain": True, "category": "invalid"},  # 환각
        {"actual_abstain": True, "expected_abstain": False, "category": "ontology"},  # 잘못된 ABSTAIN
    ]

    v_metrics = calc.calculate_verification_metrics(test_results)
    print("\nVerification Metrics:")
    print(f"  Abstain Accuracy: {v_metrics.abstain_accuracy:.4f}")
    print(f"  Hallucination Rate: {v_metrics.hallucination_rate:.4f}")
    print(f"  Safe Response Rate: {v_metrics.safe_response_rate:.4f}")
    print(f"  False Abstain Rate: {v_metrics.false_abstain_rate:.4f}")
