# ============================================================
# scripts/run_rag_v3.py - Phase 7 RAG 파이프라인 (Verifier 적용)
# ============================================================
# 실행 방법: python scripts/run_rag_v3.py
#
# Phase 6와의 차이점:
#   - Verifier: 생성 전/후 검증
#   - SafeResponse: 정보 부족 시 안전 응답
#   - Citation: 답변에 출처 및 신뢰도 표시
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
from src.rag.verifier import Verifier, VerificationStatus


# ============================================================
# [1] RAG Pipeline V3 클래스
# ============================================================

class RAGPipelineV3:
    """
    Phase 7 RAG 파이프라인 (Verifier 적용)

    Phase 6와의 차이점:
        - 생성 전 컨텍스트 검증 (Hallucination 방지)
        - 생성 후 답변 검증
        - 정보 부족 시 안전 응답 반환
        - 답변에 출처 및 신뢰도 표시

    사용 예시:
        rag = RAGPipelineV3()
        answer = rag.query("C4A15 에러가 발생했어요")
        print(answer)
    """

    def __init__(self, top_k: int = 5, verbose: bool = True):
        """
        RAG 파이프라인 V3 초기화

        Args:
            top_k: 검색할 결과 수
            verbose: 상세 로그 출력 여부
        """
        self.top_k = top_k
        self.verbose = verbose

        print("=" * 60)
        print("[*] Initializing RAG Pipeline V3 (Phase 7)")
        print("=" * 60)

        # 컴포넌트 초기화
        self.hybrid_retriever = HybridRetriever(verbose=False)
        self.verifier = Verifier()
        self.prompt_builder = PromptBuilder()
        self.generator = Generator()

        print("\n[OK] RAG Pipeline V3 ready!")
        print("=" * 60)

    def close(self):
        """연결 종료"""
        self.hybrid_retriever.close()

    def query(
        self,
        question: str,
        top_k: int = None,
        show_sources: bool = True,
        add_citation: bool = True,
    ) -> str:
        """
        검증된 RAG 질의 실행

        Args:
            question: 사용자 질문
            top_k: 검색할 결과 수 (None이면 기본값)
            show_sources: 출처 정보 표시 여부
            add_citation: 답변에 출처 추가 여부

        Returns:
            str: 검증된 답변 (또는 안전 응답)
        """
        top_k = top_k or self.top_k
        start_time = time.time()

        if self.verbose:
            print(f"\n{'─' * 60}")
            print(f"[Question] {question}")
            print(f"{'─' * 60}")

        # ─────────────────────────────────────────────────────
        # Step 1: 하이브리드 검색
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
        # Step 2: 생성 전 검증 (Context Verification)
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 2] Pre-generation verification...")

        pre_verification = self.verifier.verify_before_generation(analysis, hybrid_results)

        if self.verbose:
            print(f"  Status: {pre_verification.status.value}")
            print(f"  Confidence: {pre_verification.confidence:.2f}")
            print(f"  Evidence count: {pre_verification.evidence_count}")
            if pre_verification.warnings:
                print(f"  Warnings: {pre_verification.warnings}")

        # 검증 실패 시 안전 응답 반환
        if not pre_verification.is_safe_to_answer:
            if self.verbose:
                print(f"\n[!] Verification FAILED - Returning safe response")

            safe_response = self.verifier.get_safe_response(pre_verification, analysis)

            elapsed = time.time() - start_time

            if self.verbose:
                print(f"\n{'─' * 60}")
                print("[Answer] (Safe Response)")
                print(f"{'─' * 60}")
                print(safe_response)
                print(f"\n  Time: {elapsed:.2f}s")

            return safe_response

        # ─────────────────────────────────────────────────────
        # Step 3: 컨텍스트 변환 (HybridResult → RetrievalResult)
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 3] Building context...")

        contexts = []
        for hr in hybrid_results:
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
        # Step 4: LLM 생성
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 4] Generating answer...")

        result = self.generator.generate(messages)
        answer = result.answer

        if self.verbose:
            print(f"  Model: {result.model}")
            print(f"  Tokens: {result.usage['total_tokens']}")

        # ─────────────────────────────────────────────────────
        # Step 5: 생성 후 검증 (Answer Verification)
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 5] Post-generation verification...")

        post_verification = self.verifier.verify_after_generation(
            answer, hybrid_results, analysis
        )

        if self.verbose:
            print(f"  Status: {post_verification.status.value}")
            print(f"  Confidence: {post_verification.confidence:.2f}")
            print(f"  Evidence sources: {post_verification.evidence_sources[:3]}")
            if post_verification.warnings:
                print(f"  Warnings: {post_verification.warnings}")

        # ─────────────────────────────────────────────────────
        # Step 6: 경고/출처 추가
        # ─────────────────────────────────────────────────────
        final_answer = answer

        # PARTIAL일 때 경고 추가
        if post_verification.status == VerificationStatus.PARTIAL and post_verification.warnings:
            final_answer = self.verifier.add_warning(final_answer, post_verification)

        # 출처 추가
        if add_citation:
            final_answer = self.verifier.add_citation(final_answer, post_verification)

        elapsed = time.time() - start_time

        # ─────────────────────────────────────────────────────
        # 결과 출력
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n{'─' * 60}")
            print("[Answer]")
            print(f"{'─' * 60}")
            print(final_answer)

            if show_sources:
                print(f"\n{'─' * 60}")
                print("[Sources Detail]")
                print(f"{'─' * 60}")
                for i, ctx in enumerate(contexts[:3], 1):
                    source_type = "GRAPH" if "graph" in ctx.metadata.get("doc_type", "") else "VECTOR"
                    source = ctx.metadata.get("source", "Unknown")
                    entity = ctx.metadata.get("entity_name", ctx.chunk_id)
                    print(f"  {i}. [{source_type}] {entity}")
                    print(f"     Source: {source}")

            print(f"\n  Total time: {elapsed:.2f}s")

        return final_answer


# ============================================================
# [2] 테스트 실행
# ============================================================

def run_verification_tests():
    """Phase 7 검증 테스트"""

    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "     Phase 7 RAG - Verifier 테스트".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    # Phase 7 RAG 초기화
    rag_v3 = RAGPipelineV3(top_k=5, verbose=True)

    # ─────────────────────────────────────────────────────
    # 테스트 시나리오
    # ─────────────────────────────────────────────────────
    test_cases = [
        {
            "question": "C4A15 에러가 발생했어요. 어떻게 해결하나요?",
            "expected_status": "VERIFIED 또는 PARTIAL",
            "description": "정상 에러 코드 (검증 통과 예상)",
        },
        {
            "question": "C999 에러 해결법 알려줘",
            "expected_status": "INSUFFICIENT",
            "description": "존재하지 않는 에러 코드 (안전 응답 예상)",
        },
        {
            "question": "C100 에러가 뭐야?",
            "expected_status": "INSUFFICIENT",
            "description": "범위 밖 에러 코드 (안전 응답 예상)",
        },
        {
            "question": "Control Box 관련 에러 목록 알려줘",
            "expected_status": "VERIFIED 또는 PARTIAL",
            "description": "부품 에러 목록 (검증 통과 예상)",
        },
        {
            "question": "로봇이 갑자기 멈췄어요",
            "expected_status": "PARTIAL",
            "description": "일반 질문 (컨텍스트 기반 답변)",
        },
    ]

    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "                   테스트 시작".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n\n{'█' * 60}")
        print(f"█ 테스트 {i}/{len(test_cases)}: {test['description']}")
        print(f"█ 예상 상태: {test['expected_status']}")
        print(f"{'█' * 60}")

        try:
            answer = rag_v3.query(test["question"])
            results.append({
                "test": test["description"],
                "status": "PASS",
                "answer_preview": answer[:100] + "..." if len(answer) > 100 else answer
            })
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test": test["description"],
                "status": "FAIL",
                "error": str(e)
            })

        print("\n" + "─" * 60)
        input("Press Enter to continue to next test...")

    # ─────────────────────────────────────────────────────
    # 결과 요약
    # ─────────────────────────────────────────────────────
    rag_v3.close()

    print("\n\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "               테스트 결과 요약".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    for i, r in enumerate(results, 1):
        status_icon = "✓" if r["status"] == "PASS" else "✗"
        print(f"  {i}. [{status_icon}] {r['test']}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"\n  통과: {passed}/{len(results)}")

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
    print("║" + "    UR5e RAG Assistant V3 - Interactive Mode".center(58) + "║")
    print("║" + "      (Phase 7: Verifier - Hallucination 방지)".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n  질문을 입력하세요. 종료하려면 'quit' 또는 'exit'을 입력하세요.\n")

    # RAG 파이프라인 초기화
    rag = RAGPipelineV3(top_k=5, verbose=True)

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

    parser = argparse.ArgumentParser(description="UR5e RAG Pipeline V3 (Phase 7 - Verifier)")
    parser.add_argument(
        "--mode",
        choices=["test", "interactive"],
        default="test",
        help="실행 모드: test (검증 테스트) 또는 interactive (대화형)"
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        help="단일 질문 실행"
    )

    args = parser.parse_args()

    if args.question:
        # 단일 질문 모드
        rag = RAGPipelineV3(top_k=5, verbose=True)
        rag.query(args.question)
        rag.close()
    elif args.mode == "interactive":
        # 인터랙티브 모드
        interactive_mode()
    else:
        # 검증 테스트 모드
        run_verification_tests()
