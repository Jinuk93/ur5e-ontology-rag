# ============================================================
# src/rag/prompt_builder.py - 프롬프트 구성기
# ============================================================
# 검색 결과와 질문을 조합하여 LLM 입력용 프롬프트를 생성합니다.
#
# 프롬프트 엔지니어링 핵심 원칙:
#   1. 명확한 역할 부여 (UR5e 전문 엔지니어)
#   2. 규칙 명시 (제공된 정보만 사용, 모르면 모른다고 답변)
#   3. 컨텍스트 + 질문 구조화
# ============================================================

import os
import sys
from typing import List

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.rag.retriever import RetrievalResult


# ============================================================
# [1] 프롬프트 템플릿
# ============================================================

SYSTEM_PROMPT = """당신은 UR5e 협동 로봇 전문 기술 지원 엔지니어입니다.
사용자의 질문에 정확하고 친절하게 답변하세요.

## 규칙
1. **제공된 정보만 사용하세요.** 추측하거나 외부 지식을 사용하지 마세요.
2. **모르면 모른다고 답변하세요.** "제공된 정보에서 찾을 수 없습니다"라고 솔직하게 말하세요.
3. **한글로 답변하세요.** 전문 용어는 영어를 병기할 수 있습니다.
4. **구체적인 단계가 있으면 번호를 매겨 나열하세요.**
5. **출처를 명시하세요.** 어떤 문서에서 정보를 가져왔는지 언급하세요."""

USER_PROMPT_TEMPLATE = """## 제공된 정보

{context}

---

## 사용자 질문

{query}

---

## 답변

위 정보를 바탕으로 사용자의 질문에 답변하세요."""


# ============================================================
# [2] PromptBuilder 클래스
# ============================================================

class PromptBuilder:
    """
    프롬프트 구성기

    검색 결과(컨텍스트)와 사용자 질문을 조합하여
    LLM 입력용 프롬프트를 생성합니다.

    사용 예시:
        builder = PromptBuilder()
        messages = builder.build(query, contexts)
        # messages는 OpenAI Chat API 형식의 리스트
    """

    def __init__(
        self,
        max_context_chars: int = 6000,
        include_metadata: bool = True,
    ):
        """
        PromptBuilder 초기화

        Args:
            max_context_chars: 컨텍스트 최대 문자 수 (토큰 제한 고려)
            include_metadata: 메타데이터(출처) 포함 여부
        """
        self.max_context_chars = max_context_chars
        self.include_metadata = include_metadata

    # --------------------------------------------------------
    # [2.1] 프롬프트 빌드
    # --------------------------------------------------------

    def build(
        self,
        query: str,
        contexts: List[RetrievalResult],
    ) -> List[dict]:
        """
        OpenAI Chat API 형식의 메시지 리스트 생성

        Args:
            query: 사용자 질문
            contexts: 검색된 청크 리스트

        Returns:
            List[dict]: OpenAI Chat API messages 형식
                [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."}
                ]
        """
        # 컨텍스트 텍스트 구성
        context_text = self._build_context(contexts)

        # 사용자 프롬프트 구성
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context_text,
            query=query,
        )

        # OpenAI Chat API 형식
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        return messages

    # --------------------------------------------------------
    # [2.2] 컨텍스트 구성
    # --------------------------------------------------------

    def _build_context(self, contexts: List[RetrievalResult]) -> str:
        """
        검색 결과를 컨텍스트 텍스트로 변환

        Args:
            contexts: 검색된 청크 리스트

        Returns:
            str: 포맷팅된 컨텍스트 텍스트
        """
        if not contexts:
            return "(검색된 정보가 없습니다)"

        context_parts = []
        total_chars = 0

        for i, ctx in enumerate(contexts, 1):
            # 출처 정보
            source_info = ""
            if self.include_metadata:
                doc_type = ctx.metadata.get('doc_type', 'unknown')
                source = ctx.metadata.get('source', 'unknown')
                page = ctx.metadata.get('page', '')

                # 문서 타입을 한글로
                doc_type_kr = {
                    'error_code': '에러 코드 문서',
                    'service_manual': '서비스 매뉴얼',
                    'user_manual': '사용자 매뉴얼',
                }.get(doc_type, doc_type)

                source_info = f"[출처: {doc_type_kr}"
                if page:
                    source_info += f", 페이지 {page}"
                source_info += f", 유사도: {ctx.score:.2f}]"

            # 컨텍스트 항목 구성
            part = f"### 정보 {i} {source_info}\n{ctx.content}\n"

            # 문자 수 제한 확인
            if total_chars + len(part) > self.max_context_chars:
                # 제한 초과 시 중단
                context_parts.append(f"\n(... 추가 {len(contexts) - i + 1}개 결과 생략)")
                break

            context_parts.append(part)
            total_chars += len(part)

        return "\n".join(context_parts)

    # --------------------------------------------------------
    # [2.3] 단순 프롬프트 (디버깅용)
    # --------------------------------------------------------

    def build_simple(
        self,
        query: str,
        contexts: List[RetrievalResult],
    ) -> str:
        """
        단일 문자열 프롬프트 생성 (디버깅용)

        Args:
            query: 사용자 질문
            contexts: 검색된 청크 리스트

        Returns:
            str: 전체 프롬프트 문자열
        """
        messages = self.build(query, contexts)
        return f"[SYSTEM]\n{messages[0]['content']}\n\n[USER]\n{messages[1]['content']}"


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("[*] PromptBuilder Test")
    print("=" * 60)

    # 테스트용 검색 결과 생성
    test_contexts = [
        RetrievalResult(
            chunk_id="error_codes_C4_001",
            content="C4A15 Communication with joint 3 lost\nEXPLANATION\nMore than 1 package lost\nSUGGESTION\n(A) Verify the communication cables are connected properly, (B) Conduct a complete rebooting sequence",
            metadata={
                "doc_type": "error_code",
                "source": "ErrorCodes.pdf",
                "page": 45,
            },
            score=0.92,
        ),
        RetrievalResult(
            chunk_id="service_manual_007",
            content="Joint Communication Troubleshooting\n\nWhen experiencing communication errors with joints:\n1. Check all cable connections\n2. Verify power supply\n3. Reboot the system",
            metadata={
                "doc_type": "service_manual",
                "source": "ServiceManual.pdf",
                "page": 78,
            },
            score=0.85,
        ),
    ]

    # PromptBuilder 테스트
    builder = PromptBuilder()

    query = "C4A15 에러가 발생했어요. 어떻게 해결하나요?"
    messages = builder.build(query, test_contexts)

    print("\n[Messages for OpenAI API]")
    print("-" * 40)
    for msg in messages:
        print(f"\n[{msg['role'].upper()}]")
        print(msg['content'][:500] + "..." if len(msg['content']) > 500 else msg['content'])

    print("\n" + "=" * 60)
    print("[OK] PromptBuilder test completed!")
    print("=" * 60)
