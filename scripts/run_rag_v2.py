# ============================================================
# scripts/run_rag_v2.py - Phase 6 RAG 파이프라인 (온톨로지 추론)
# ============================================================
# 실행 방법: python scripts/run_rag_v2.py
#
# Phase 5와의 차이점:
#   - QueryAnalyzer: 에러 코드/부품명 감지
#   - GraphRetriever: GraphDB 관계 기반 검색
#   - HybridRetriever: Vector + Graph 결합
# ============================================================

import sys
import os
import time

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.rag.hybrid_retriever import HybridRetriever, HybridResult
from src.rag.prompt_builder import PromptBuilder
from src.rag.generator import Generator
from src.rag.retriever import RetrievalResult


# ============================================================
# [1] RAG Pipeline V2 클래스
# ============================================================

class RAGPipelineV2:
    """
    Phase 6 RAG 파이프라인 (온톨로지 추론)

    Phase 5와의 차이점:
        - 질문 분석을 통한 에러 코드/부품명 감지
        - GraphDB 우선 검색 (관계 기반)
        - VectorDB 보충 검색 (의미 기반)

    사용 예시:
        rag = RAGPipelineV2()
        answer = rag.query("C4A15 에러가 발생했어요")
        print(answer)
    """

    def __init__(self, top_k: int = 5, verbose: bool = True):
        """
        RAG 파이프라인 V2 초기화

        Args:
            top_k: 검색할 결과 수
            verbose: 상세 로그 출력 여부
        """
        self.top_k = top_k
        self.verbose = verbose

        print("=" * 60)
        print("[*] Initializing RAG Pipeline V2 (Phase 6)")
        print("=" * 60)

        # 컴포넌트 초기화
        self.hybrid_retriever = HybridRetriever(verbose=False)
        self.prompt_builder = PromptBuilder()
        self.generator = Generator()

        print("\n[OK] RAG Pipeline V2 ready!")
        print("=" * 60)

    def close(self):
        """연결 종료"""
        self.hybrid_retriever.close()

    def query(
        self,
        question: str,
        top_k: int = None,
        show_sources: bool = True,
    ) -> str:
        """
        RAG 질의 실행

        Args:
            question: 사용자 질문
            top_k: 검색할 결과 수 (None이면 기본값)
            show_sources: 출처 정보 표시 여부

        Returns:
            str: 생성된 답변
        """
        top_k = top_k or self.top_k
        start_time = time.time()

        if self.verbose:
            print(f"\n{'─' * 60}")
            print(f"[Question] {question}")
            print(f"{'─' * 60}")

        # ─────────────────────────────────────────────────────
        # Step 1: 하이브리드 검색 (Query Analysis + Retrieval)
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 1] Hybrid Retrieval (top_k={top_k})...")

        hybrid_results, analysis = self.hybrid_retriever.retrieve(question, top_k=top_k)

        if self.verbose:
            print(f"\n[Query Analysis]")
            print(f"  Error codes: {analysis.error_codes}")
            print(f"  Components: {analysis.components}")
            print(f"  Query type: {analysis.query_type}")
            print(f"  Strategy: {analysis.search_strategy}")

            print(f"\n[Retrieval Results] {len(hybrid_results)} items")
            for i, r in enumerate(hybrid_results, 1):
                source_label = "GRAPH" if r.source_type == "graph" else "VECTOR"
                print(f"  {i}. [{source_label}] score={r.score:.3f}")

        # ─────────────────────────────────────────────────────
        # Step 2: 컨텍스트 변환 (HybridResult → RetrievalResult)
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 2] Building context...")

        # HybridResult를 RetrievalResult로 변환 (PromptBuilder 호환)
        contexts = []
        for hr in hybrid_results:
            # metadata 구성
            metadata = hr.metadata.copy()
            if hr.source_type == "graph":
                metadata["doc_type"] = "graph_result"
                metadata["source"] = "GraphDB (Neo4j)"
            else:
                metadata.setdefault("doc_type", "vector_result")
                metadata.setdefault("source", "VectorDB (ChromaDB)")

            contexts.append(RetrievalResult(
                chunk_id=metadata.get("chunk_id", f"graph_{hr.metadata.get('entity_name', 'unknown')}"),
                content=hr.content,
                metadata=metadata,
                score=hr.score,
            ))

        messages = self.prompt_builder.build(question, contexts)

        if self.verbose:
            total_chars = sum(len(m['content']) for m in messages)
            print(f"  Context length: {total_chars} chars")

        # ─────────────────────────────────────────────────────
        # Step 3: 생성 (Generation)
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 3] Generating answer...")

        result = self.generator.generate(messages)

        elapsed = time.time() - start_time

        if self.verbose:
            print(f"  Model: {result.model}")
            print(f"  Tokens: {result.usage['total_tokens']} (prompt: {result.usage['prompt_tokens']}, completion: {result.usage['completion_tokens']})")
            print(f"  Time: {elapsed:.2f}s")

        # ─────────────────────────────────────────────────────
        # 결과 출력
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n{'─' * 60}")
            print("[Answer]")
            print(f"{'─' * 60}")
            print(result.answer)

            if show_sources:
                print(f"\n{'─' * 60}")
                print("[Sources]")
                print(f"{'─' * 60}")
                for i, ctx in enumerate(contexts[:5], 1):
                    source_type = "GRAPH" if "graph" in ctx.metadata.get("doc_type", "") else "VECTOR"
                    source = ctx.metadata.get("source", "Unknown")
                    entity = ctx.metadata.get("entity_name", ctx.chunk_id)
                    print(f"  {i}. [{source_type}] {entity} - {source}")

        return result.answer


# ============================================================
# [2] 테스트 실행
# ============================================================

def run_comparison_tests():
    """Phase 5 vs Phase 6 비교 테스트"""

    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "     Phase 6 RAG - 온톨로지 추론 비교 테스트".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    # Phase 6 RAG 초기화
    rag_v2 = RAGPipelineV2(top_k=5, verbose=True)

    # ─────────────────────────────────────────────────────
    # 테스트 시나리오
    # ─────────────────────────────────────────────────────
    test_cases = [
        {
            "question": "C4A15 에러가 발생했어요. 어떻게 해결하나요?",
            "expected": "graph_first",
            "description": "에러 코드 해결 (Phase 5에서 실패했던 케이스)",
        },
        {
            "question": "Control Box 관련 에러 목록 알려줘",
            "expected": "graph_first",
            "description": "부품 에러 목록",
        },
        {
            "question": "Safety Control Board에서 어떤 에러가 발생할 수 있나요?",
            "expected": "graph_first",
            "description": "Safety Board 에러 (Phase 5에서 성공했던 케이스)",
        },
    ]

    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "                   테스트 시작".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    for i, test in enumerate(test_cases, 1):
        print(f"\n\n{'█' * 60}")
        print(f"█ 테스트 {i}/{len(test_cases)}: {test['description']}")
        print(f"█ 예상 전략: {test['expected']}")
        print(f"{'█' * 60}")

        try:
            answer = rag_v2.query(test["question"])
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "─" * 60)
        input("Press Enter to continue to next test...")

    # ─────────────────────────────────────────────────────
    # 완료
    # ─────────────────────────────────────────────────────
    rag_v2.close()

    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "               테스트 완료!".center(58) + "║")
    print("╚" + "═" * 58 + "╝")


# ============================================================
# [3] 인터랙티브 모드
# ============================================================

def interactive_mode():
    """인터랙티브 질문/답변 모드"""

    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "    UR5e RAG Assistant V2 - Interactive Mode".center(58) + "║")
    print("║" + "         (Phase 6: 온톨로지 추론)".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n  질문을 입력하세요. 종료하려면 'quit' 또는 'exit'을 입력하세요.\n")

    # RAG 파이프라인 초기화
    rag = RAGPipelineV2(top_k=5, verbose=True)

    while True:
        print("\n" + "─" * 60)
        question = input("질문: ").strip()

        if not question:
            continue

        if question.lower() in ['quit', 'exit', 'q']:
            print("\n종료합니다. 감사합니다!")
            break

        try:
            rag.query(question)
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()

    rag.close()


# ============================================================
# [4] 메인 실행
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UR5e RAG Pipeline V2 (Phase 6)")
    parser.add_argument(
        "--mode",
        choices=["test", "interactive"],
        default="test",
        help="실행 모드: test (비교 테스트) 또는 interactive (대화형)"
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        help="단일 질문 실행"
    )

    args = parser.parse_args()

    if args.question:
        # 단일 질문 모드
        rag = RAGPipelineV2(top_k=5, verbose=True)
        rag.query(args.question)
        rag.close()
    elif args.mode == "interactive":
        # 인터랙티브 모드
        interactive_mode()
    else:
        # 비교 테스트 모드
        run_comparison_tests()
