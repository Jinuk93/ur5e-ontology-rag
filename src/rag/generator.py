# ============================================================
# src/rag/generator.py - LLM 답변 생성기
# ============================================================
# OpenAI GPT-4o-mini를 사용하여 최종 답변을 생성합니다.
#
# 사용 예시:
#   generator = Generator()
#   answer = generator.generate(messages)
# ============================================================

import os
import sys
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# .env 파일 로드
load_dotenv()

from openai import OpenAI


# ============================================================
# [1] GenerationResult 데이터 클래스
# ============================================================

@dataclass
class GenerationResult:
    """
    생성 결과를 담는 데이터 클래스

    Attributes:
        answer: 생성된 답변 텍스트
        model: 사용된 모델 이름
        usage: 토큰 사용량 정보
    """
    answer: str
    model: str
    usage: dict

    def __repr__(self):
        preview = self.answer[:100] + "..." if len(self.answer) > 100 else self.answer
        return f"GenerationResult(model={self.model}, answer='{preview}')"


# ============================================================
# [2] Generator 클래스
# ============================================================

class Generator:
    """
    LLM 기반 답변 생성기

    OpenAI GPT-4o-mini를 사용하여 컨텍스트 기반 답변을 생성합니다.

    사용 예시:
        generator = Generator()
        result = generator.generate(messages)
        print(result.answer)
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ):
        """
        Generator 초기화

        Args:
            model: OpenAI 모델 이름 (기본값: gpt-4o-mini)
            temperature: 생성 다양성 (0~1, 낮을수록 일관성)
            max_tokens: 최대 출력 토큰 수
        """
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        print(f"[OK] Generator initialized")
        print(f"     Model: {model}")
        print(f"     Temperature: {temperature}")

    # --------------------------------------------------------
    # [2.1] 답변 생성
    # --------------------------------------------------------

    def generate(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> GenerationResult:
        """
        LLM으로 답변 생성

        Args:
            messages: OpenAI Chat API 형식의 메시지 리스트
                [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            temperature: 생성 다양성 (None이면 기본값 사용)
            max_tokens: 최대 출력 토큰 (None이면 기본값 사용)

        Returns:
            GenerationResult: 생성된 답변과 메타데이터
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )

        # 결과 추출
        answer = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return GenerationResult(
            answer=answer,
            model=self.model,
            usage=usage,
        )

    # --------------------------------------------------------
    # [2.2] 단순 질문 응답 (프롬프트 직접 전달)
    # --------------------------------------------------------

    def generate_simple(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        단순 프롬프트로 답변 생성

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택)

        Returns:
            str: 생성된 답변
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        result = self.generate(messages)
        return result.answer


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("[*] Generator Test")
    print("=" * 60)

    # Generator 초기화
    generator = Generator()

    # 테스트 메시지
    test_messages = [
        {
            "role": "system",
            "content": "당신은 UR5e 로봇 전문 기술 지원 엔지니어입니다. 한글로 답변하세요."
        },
        {
            "role": "user",
            "content": """## 제공된 정보

### 정보 1 [출처: 에러 코드 문서]
C4A15 Communication with joint 3 lost
EXPLANATION
More than 1 package lost
SUGGESTION
(A) Verify the communication cables are connected properly,
(B) Conduct a complete rebooting sequence

---

## 사용자 질문

C4A15 에러가 발생했어요. 어떻게 해결하나요?

---

위 정보를 바탕으로 답변하세요."""
        }
    ]

    print("\n[Input]")
    print("-" * 40)
    print(f"Query: C4A15 에러가 발생했어요. 어떻게 해결하나요?")

    print("\n[Generating...]")
    result = generator.generate(test_messages)

    print("\n[Output]")
    print("-" * 40)
    print(result.answer)

    print("\n[Usage]")
    print(f"  Prompt tokens: {result.usage['prompt_tokens']}")
    print(f"  Completion tokens: {result.usage['completion_tokens']}")
    print(f"  Total tokens: {result.usage['total_tokens']}")

    print("\n" + "=" * 60)
    print("[OK] Generator test completed!")
    print("=" * 60)
