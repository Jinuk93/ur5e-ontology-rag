# ============================================================
# src/evaluation/__init__.py - Evaluation Module
# ============================================================
# Phase 10: 자동화된 품질 평가 및 성능 측정
# ============================================================

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == "BenchmarkItem":
        from src.evaluation.benchmark import BenchmarkItem
        return BenchmarkItem
    elif name == "BenchmarkDataset":
        from src.evaluation.benchmark import BenchmarkDataset
        return BenchmarkDataset
    elif name == "MetricsCalculator":
        from src.evaluation.metrics import MetricsCalculator
        return MetricsCalculator
    elif name == "RetrievalMetrics":
        from src.evaluation.metrics import RetrievalMetrics
        return RetrievalMetrics
    elif name == "AnswerMetrics":
        from src.evaluation.metrics import AnswerMetrics
        return AnswerMetrics
    elif name == "VerificationMetrics":
        from src.evaluation.metrics import VerificationMetrics
        return VerificationMetrics
    elif name == "LLMJudge":
        from src.evaluation.llm_judge import LLMJudge
        return LLMJudge
    elif name == "RuleBasedJudge":
        from src.evaluation.llm_judge import RuleBasedJudge
        return RuleBasedJudge
    elif name == "Evaluator":
        from src.evaluation.evaluator import Evaluator
        return Evaluator
    elif name == "EvaluationResult":
        from src.evaluation.evaluator import EvaluationResult
        return EvaluationResult
    elif name == "EvaluationSummary":
        from src.evaluation.evaluator import EvaluationSummary
        return EvaluationSummary
    elif name == "ReportGenerator":
        from src.evaluation.report import ReportGenerator
        return ReportGenerator
    raise AttributeError(f"module 'src.evaluation' has no attribute '{name}'")

__all__ = [
    "BenchmarkItem",
    "BenchmarkDataset",
    "MetricsCalculator",
    "RetrievalMetrics",
    "AnswerMetrics",
    "VerificationMetrics",
    "LLMJudge",
    "RuleBasedJudge",
    "Evaluator",
    "EvaluationResult",
    "EvaluationSummary",
    "ReportGenerator",
]
