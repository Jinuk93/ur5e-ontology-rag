# ============================================================
# scripts/run_rag.py - RAG 파이프라인 실행 및 테스트
# ============================================================
# 실행 방법: python scripts/run_rag.py
#
# RAG 파이프라인:
#   1. Retriever: VectorDB에서 유사 청크 검색
#   2. PromptBuilder: 프롬프트 구성
#   3. Generator: LLM 답변 생성
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

from src.rag.retriever import Retriever
from src.rag.prompt_builder import PromptBuilder
from src.rag.generator import Generator


# ============================================================
# [1] RAG Pipeline 클래스
# ============================================================

class RAGPipeline:
    """
    RAG (Retrieval-Augmented Generation) 파이프라인

    사용 예시:
        rag = RAGPipeline()
        answer = rag.query("C4A15 에러가 발생했어요")
        print(answer)
    """

    def __init__(self, top_k: int = 5, verbose: bool = True):
        """
        RAG 파이프라인 초기화

        Args:
            top_k: 검색할 청크 수
            verbose: 상세 로그 출력 여부
        """
        self.top_k = top_k
        self.verbose = verbose

        print("=" * 60)
        print("[*] Initializing RAG Pipeline")
        print("=" * 60)

        # 컴포넌트 초기화
        self.retriever = Retriever()
        self.prompt_builder = PromptBuilder()
        self.generator = Generator()

        print("\n[OK] RAG Pipeline ready!")
        print("=" * 60)

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
            top_k: 검색할 청크 수 (None이면 기본값)
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
        # Step 1: 검색 (Retrieval)
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 1] Retrieving relevant chunks (top_k={top_k})...")

        contexts = self.retriever.retrieve(question, top_k=top_k)

        if self.verbose:
            print(f"    Found {len(contexts)} chunks:")
            for i, ctx in enumerate(contexts, 1):
                doc_type = ctx.metadata.get('doc_type', 'unknown')
                print(f"    {i}. [{ctx.score:.3f}] {ctx.chunk_id} ({doc_type})")

        # ─────────────────────────────────────────────────────
        # Step 2: 프롬프트 구성 (Augmentation)
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 2] Building prompt...")

        messages = self.prompt_builder.build(question, contexts)

        if self.verbose:
            # 컨텍스트 길이 계산
            total_chars = sum(len(m['content']) for m in messages)
            print(f"    Prompt length: {total_chars} chars")

        # ─────────────────────────────────────────────────────
        # Step 3: 생성 (Generation)
        # ─────────────────────────────────────────────────────
        if self.verbose:
            print(f"\n[Step 3] Generating answer...")

        result = self.generator.generate(messages)

        elapsed = time.time() - start_time

        if self.verbose:
            print(f"    Model: {result.model}")
            print(f"    Tokens: {result.usage['total_tokens']} (prompt: {result.usage['prompt_tokens']}, completion: {result.usage['completion_tokens']})")
            print(f"    Time: {elapsed:.2f}s")

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
                for i, ctx in enumerate(contexts[:3], 1):
                    doc_type = ctx.metadata.get('doc_type', 'unknown')
                    source = ctx.metadata.get('source', 'unknown')
                    page = ctx.metadata.get('page', '')
                    print(f"  {i}. {source} (page {page}) - {doc_type}")

        return result.answer


# ============================================================
# [2] 테스트 실행
# ============================================================

def run_tests():
    """RAG 테스트 시나리오 실행"""

    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "       RAG Pipeline Test - Phase 5 기본 RAG 구현".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    # RAG 파이프라인 초기화
    rag = RAGPipeline(top_k=5, verbose=True)

    # ─────────────────────────────────────────────────────
    # 테스트 시나리오
    # ─────────────────────────────────────────────────────
    test_questions = [
        # 1. 에러 코드 질문
        "C4A15 에러가 발생했어요. 어떻게 해결하나요?",

        # 2. 일반 에러 질문
        "통신 에러가 자주 발생하는데 원인이 뭐예요?",

        # 3. 사용법 질문
        "로봇 팔 캘리브레이션은 어떻게 하나요?",
    ]

    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "                   테스트 시작".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    for i, question in enumerate(test_questions, 1):
        print(f"\n\n{'█' * 60}")
        print(f"█ 테스트 {i}/{len(test_questions)}")
        print(f"{'█' * 60}")

        try:
            answer = rag.query(question)
        except Exception as e:
            print(f"\n[ERROR] {e}")

        print("\n" + "─" * 60)
        input("Press Enter to continue to next test...")

    # ─────────────────────────────────────────────────────
    # 완료
    # ─────────────────────────────────────────────────────
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
    print("║" + "        UR5e RAG Assistant - Interactive Mode".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n  질문을 입력하세요. 종료하려면 'quit' 또는 'exit'을 입력하세요.\n")

    # RAG 파이프라인 초기화
    rag = RAGPipeline(top_k=5, verbose=True)

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


# ============================================================
# [4] 메인 실행
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UR5e RAG Pipeline")
    parser.add_argument(
        "--mode",
        choices=["test", "interactive"],
        default="test",
        help="실행 모드: test (테스트 시나리오) 또는 interactive (대화형)"
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        help="단일 질문 실행"
    )

    args = parser.parse_args()

    if args.question:
        # 단일 질문 모드
        rag = RAGPipeline(top_k=5, verbose=True)
        rag.query(args.question)
    elif args.mode == "interactive":
        # 인터랙티브 모드
        interactive_mode()
    else:
        # 테스트 모드
        run_tests()
