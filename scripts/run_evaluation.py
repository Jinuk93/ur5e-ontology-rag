#!/usr/bin/env python
# ============================================================
# scripts/run_evaluation.py - 평가 시스템 실행 스크립트
# ============================================================
# 온톨로지 RAG 시스템 자동 평가
#
# 사용법:
#   # 전체 평가 실행
#   python scripts/run_evaluation.py
#
#   # 특정 카테고리만 평가
#   python scripts/run_evaluation.py --category ontology
#
#   # 특정 난이도만 평가
#   python scripts/run_evaluation.py --difficulty easy
#
#   # 빠른 평가 (규칙 기반, LLM 없이)
#   python scripts/run_evaluation.py --fast
#
#   # 리포트만 생성 (이전 결과 사용)
#   python scripts/run_evaluation.py --report-only
# ============================================================

import os
import sys
import argparse
import json
from pathlib import Path

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def main():
    parser = argparse.ArgumentParser(
        description="온톨로지 RAG 시스템 평가",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/run_evaluation.py                           # 전체 평가
  python scripts/run_evaluation.py --category ontology       # 온톨로지 질문만
  python scripts/run_evaluation.py --category error_resolution  # 에러 해결 질문만
  python scripts/run_evaluation.py --fast                    # 빠른 평가 (LLM 없이)
  python scripts/run_evaluation.py --report-only             # 리포트만 생성
        """,
    )

    parser.add_argument(
        "--category",
        type=str,
        choices=["ontology", "sensor_analysis", "error_resolution", "pattern_history", "specification", "invalid"],
        help="특정 카테고리만 평가",
    )

    parser.add_argument(
        "--difficulty",
        type=str,
        choices=["easy", "medium", "hard"],
        help="특정 난이도만 평가",
    )

    parser.add_argument(
        "--query-type",
        type=str,
        choices=["ONTOLOGY", "HYBRID", "RAG"],
        help="특정 쿼리 타입만 평가",
    )

    parser.add_argument(
        "--fast",
        action="store_true",
        help="빠른 평가 모드 (규칙 기반, LLM Judge 사용 안 함)",
    )

    parser.add_argument(
        "--report-only",
        action="store_true",
        help="리포트만 생성 (최근 평가 결과 사용)",
    )

    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="API 서버 URL (기본값: http://localhost:8000)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/evaluation/results",
        help="결과 저장 디렉토리",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="상세 출력 비활성화",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("온톨로지 RAG 평가 시스템")
    print("=" * 60)

    if args.report_only:
        # 최근 결과로 리포트만 생성
        generate_report_only(args.output_dir)
    else:
        # 평가 실행
        run_evaluation(
            category=args.category,
            difficulty=args.difficulty,
            query_type=args.query_type,
            use_llm_judge=not args.fast,
            api_url=args.api_url,
            output_dir=args.output_dir,
            verbose=not args.quiet,
        )


def run_evaluation(
    category: str = None,
    difficulty: str = None,
    query_type: str = None,
    use_llm_judge: bool = True,
    api_url: str = "http://localhost:8000",
    output_dir: str = "data/evaluation/results",
    verbose: bool = True,
):
    """평가 실행"""
    from src.evaluation.evaluator import Evaluator
    from src.evaluation.report import ReportGenerator

    # 평가기 초기화
    if verbose:
        mode = "LLM Judge" if use_llm_judge else "Rule-based (Fast)"
        print(f"\n[*] 평가 모드: {mode}")
        print(f"[*] API URL: {api_url}")
        if category:
            print(f"[*] 카테고리 필터: {category}")
        if difficulty:
            print(f"[*] 난이도 필터: {difficulty}")
        if query_type:
            print(f"[*] 쿼리 타입 필터: {query_type}")

    evaluator = Evaluator(
        api_url=api_url,
        use_llm_judge=use_llm_judge,
        verbose=verbose,
    )

    # 벤치마크 통계 출력
    try:
        stats = evaluator.benchmark.get_statistics()
        if verbose:
            print(f"\n[*] 벤치마크 데이터셋:")
            print(f"  총 항목: {stats['total']}")
            print(f"  카테고리: {stats['by_category']}")
            print(f"  난이도: {stats['by_difficulty']}")
            print(f"  ABSTAIN 예상: {stats['by_abstain']}")
    except Exception as e:
        print(f"\n[!] 벤치마크 로드 실패: {e}")
        print("[!] data/benchmark/benchmark.json 파일을 확인하세요.")
        return

    # 평가 실행
    print("\n" + "-" * 60)
    print("평가 실행 중...")
    print("-" * 60)

    try:
        summary = evaluator.evaluate_all(
            category=category,
            difficulty=difficulty,
            query_type=query_type,
        )
    except Exception as e:
        print(f"\n[ERROR] 평가 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 결과 저장
    print("\n" + "-" * 60)
    print("결과 저장 중...")
    result_path = evaluator.save_results(summary, output_dir=output_dir)

    # 리포트 생성
    report_generator = ReportGenerator()
    report_path = "docs/평가결과.md"
    report_generator.generate_markdown(summary, report_path)

    # 결과 요약 출력
    print("\n" + "=" * 60)
    print("평가 완료!")
    print("=" * 60)
    print(f"\n결과 요약:")
    print(f"  통과율: {summary.pass_rate:.1%} ({summary.passed_items}/{summary.total_items})")
    print(f"  평균 정확도: {summary.avg_answer_metrics.accuracy:.1%}")
    print(f"  환각 방지율: {(1 - summary.verification_metrics.hallucination_rate):.1%}")
    print(f"  평균 신뢰도: {summary.avg_confidence:.1%}")
    print(f"  평균 응답 시간: {summary.avg_latency_ms:.0f}ms")

    print(f"\n저장된 파일:")
    print(f"  결과 JSON: {result_path}")
    print(f"  리포트 MD: {report_path}")

    # 카테고리별 요약
    print(f"\n카테고리별 성능:")
    for cat, data in sorted(summary.by_category.items()):
        print(f"  {cat}: {data['pass_rate']:.0%} ({data['passed']}/{data['total']})")

    return summary


def generate_report_only(output_dir: str):
    """최근 결과로 리포트만 생성"""
    from src.evaluation.report import ReportGenerator
    from src.evaluation.evaluator import EvaluationSummary
    from src.evaluation.metrics import RetrievalMetrics, AnswerMetrics, VerificationMetrics

    latest_path = Path(output_dir) / "latest.json"

    if not latest_path.exists():
        print(f"[ERROR] 최근 평가 결과를 찾을 수 없습니다: {latest_path}")
        print("[INFO] 먼저 평가를 실행하세요: python scripts/run_evaluation.py")
        return

    # JSON 로드
    with open(latest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary_data = data.get("summary", data)  # 호환성

    # EvaluationSummary 재구성
    summary = EvaluationSummary(
        total_items=summary_data["total_items"],
        passed_items=summary_data["passed_items"],
        pass_rate=summary_data["pass_rate"],
        avg_retrieval_metrics=RetrievalMetrics(**summary_data["avg_retrieval_metrics"]),
        avg_answer_metrics=AnswerMetrics(**summary_data["avg_answer_metrics"]),
        verification_metrics=VerificationMetrics(**summary_data["verification_metrics"]),
        avg_latency_ms=summary_data["avg_latency_ms"],
        avg_confidence=summary_data.get("avg_confidence", 0.0),
        by_category=summary_data["by_category"],
        by_difficulty=summary_data["by_difficulty"],
        by_query_type=summary_data.get("by_query_type", {}),
        timestamp=summary_data.get("timestamp", ""),
        version=summary_data.get("version", "unknown"),
    )

    # 리포트 생성
    report_generator = ReportGenerator()
    report_path = "docs/평가결과.md"
    report_generator.generate_markdown(summary, report_path)

    print(f"\n[OK] 리포트 생성 완료: {report_path}")


if __name__ == "__main__":
    main()
