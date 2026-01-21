# ============================================================
# src/evaluation/llm_judge.py - LLM-based Answer Evaluation
# ============================================================
# LLM을 활용한 답변 품질 평가 (LLM-as-Judge)
# ============================================================

import os
import sys
import json
import re
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# .env 파일 로드
load_dotenv()

from openai import OpenAI

from src.evaluation.metrics import AnswerMetrics


# ============================================================
# [1] LLMJudge 클래스
# ============================================================

class LLMJudge:
    """
    LLM 기반 답변 품질 평가기

    OpenAI GPT-4o-mini를 사용하여 생성된 답변의 품질을 평가합니다.
    평가 기준:
        - accuracy: 예상 정답과의 일치도
        - completeness: 핵심 정보 포함 여부
        - relevance: 질문과의 관련성
        - faithfulness: 컨텍스트 기반 여부

    사용 예시:
        judge = LLMJudge()
        metrics = judge.evaluate(question, generated_answer, expected_answer)
        print(f"Accuracy: {metrics.accuracy}")
    """

    EVALUATION_PROMPT = """당신은 AI 답변의 품질을 평가하는 전문 평가자입니다.
다음 질문에 대한 생성된 답변과 예상 정답을 비교하여 평가해주세요.

## 질문
{question}

## 생성된 답변
{generated_answer}

## 예상 정답
{expected_answer}

## 평가 기준 (각 0.0 ~ 1.0 점수)
1. **accuracy** (정확도): 생성된 답변이 예상 정답의 핵심 내용과 얼마나 일치하는가?
   - 1.0: 완벽하게 일치하거나 더 상세함
   - 0.7-0.9: 대부분 일치, 사소한 차이
   - 0.4-0.6: 일부만 일치
   - 0.0-0.3: 거의 일치하지 않음

2. **completeness** (완전성): 예상 정답의 핵심 정보가 모두 포함되어 있는가?
   - 1.0: 모든 핵심 정보 포함
   - 0.7-0.9: 대부분의 핵심 정보 포함
   - 0.4-0.6: 일부 핵심 정보만 포함
   - 0.0-0.3: 핵심 정보 대부분 누락

3. **relevance** (관련성): 질문에 대한 적절한 답변인가?
   - 1.0: 질문에 정확히 맞는 답변
   - 0.7-0.9: 대체로 적절한 답변
   - 0.4-0.6: 부분적으로 관련됨
   - 0.0-0.3: 관련 없는 답변

4. **faithfulness** (신뢰성): 답변이 사실에 기반하고 있는가? (환각이 없는가?)
   - 1.0: 모든 정보가 사실에 기반
   - 0.7-0.9: 대부분 사실에 기반
   - 0.4-0.6: 일부 불확실한 정보 포함
   - 0.0-0.3: 많은 부분이 사실과 다름

## 주의사항
- "정보를 찾을 수 없습니다" 등의 응답은 질문에 답변할 정보가 없을 때 적절한 응답입니다.
- 존재하지 않는 에러 코드에 대해 "정보를 찾을 수 없습니다"라고 답하면 높은 점수를 줍니다.
- 추측이나 허위 정보를 제공하면 낮은 점수를 줍니다.

## 출력 형식
반드시 다음 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요:
{{"accuracy": 0.0, "completeness": 0.0, "relevance": 0.0, "faithfulness": 0.0}}"""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
    ):
        """
        LLMJudge 초기화

        Args:
            model: OpenAI 모델 이름 (기본값: gpt-4o-mini)
            temperature: 생성 다양성 (평가는 일관성을 위해 0 권장)
        """
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature

    def evaluate(
        self,
        question: str,
        generated_answer: str,
        expected_answer: str,
        context: Optional[str] = None,
    ) -> AnswerMetrics:
        """
        LLM을 활용한 답변 품질 평가

        Args:
            question: 원본 질문
            generated_answer: RAG 시스템이 생성한 답변
            expected_answer: 벤치마크의 예상 정답
            context: (선택) 참고 컨텍스트

        Returns:
            AnswerMetrics: 평가 결과
        """
        # 프롬프트 구성
        prompt = self.EVALUATION_PROMPT.format(
            question=question,
            generated_answer=generated_answer,
            expected_answer=expected_answer,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 AI 답변 품질을 평가하는 전문가입니다. JSON 형식으로만 응답하세요."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=200,
            )

            # 응답 파싱
            content = response.choices[0].message.content.strip()
            metrics = self._parse_response(content)

            return metrics

        except Exception as e:
            print(f"LLMJudge error: {e}")
            # 오류 시 기본값 반환
            return AnswerMetrics(
                accuracy=0.0,
                completeness=0.0,
                relevance=0.0,
                faithfulness=0.0,
            )

    def _parse_response(self, content: str) -> AnswerMetrics:
        """
        LLM 응답을 AnswerMetrics로 파싱

        Args:
            content: LLM 응답 텍스트

        Returns:
            AnswerMetrics: 파싱된 평가 결과
        """
        try:
            # JSON 추출 시도
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)

                return AnswerMetrics(
                    accuracy=float(data.get("accuracy", 0.0)),
                    completeness=float(data.get("completeness", 0.0)),
                    relevance=float(data.get("relevance", 0.0)),
                    faithfulness=float(data.get("faithfulness", 0.0)),
                )
            else:
                # JSON을 찾지 못한 경우
                print(f"Could not find JSON in response: {content[:100]}")
                return AnswerMetrics(0.0, 0.0, 0.0, 0.0)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}, content: {content[:100]}")
            return AnswerMetrics(0.0, 0.0, 0.0, 0.0)
        except Exception as e:
            print(f"Parse error: {e}")
            return AnswerMetrics(0.0, 0.0, 0.0, 0.0)

    def evaluate_batch(
        self,
        items: list,
    ) -> list:
        """
        여러 항목 일괄 평가

        Args:
            items: 평가할 항목 목록 (각 항목은 dict: question, generated_answer, expected_answer)

        Returns:
            list[AnswerMetrics]: 평가 결과 목록
        """
        results = []
        for item in items:
            metrics = self.evaluate(
                question=item["question"],
                generated_answer=item["generated_answer"],
                expected_answer=item["expected_answer"],
            )
            results.append(metrics)
        return results


# ============================================================
# [2] 규칙 기반 평가 (LLM 없이 빠른 평가)
# ============================================================

class RuleBasedJudge:
    """
    규칙 기반 빠른 평가기

    LLM 없이 간단한 규칙으로 답변 품질을 평가합니다.
    LLMJudge 대비 빠르지만 정확도가 낮습니다.
    """

    def evaluate(
        self,
        question: str,
        generated_answer: str,
        expected_answer: str,
    ) -> AnswerMetrics:
        """규칙 기반 답변 품질 평가"""

        # 정규화
        gen_lower = generated_answer.lower()
        exp_lower = expected_answer.lower()
        q_lower = question.lower()

        # 1. 정확도: 예상 답변의 키워드가 생성 답변에 포함된 비율
        exp_keywords = set(exp_lower.split())
        gen_words = set(gen_lower.split())
        common_keywords = exp_keywords.intersection(gen_words)
        accuracy = len(common_keywords) / len(exp_keywords) if exp_keywords else 0.0

        # 2. 완전성: 예상 답변 길이 대비 생성 답변 길이
        completeness = min(1.0, len(generated_answer) / max(len(expected_answer), 1))

        # 3. 관련성: 질문 키워드가 답변에 포함된 비율
        q_keywords = set(q_lower.split()) - {"해결", "방법", "알려주세요", "입니다", "에러", "발생"}
        gen_has_q_keywords = sum(1 for k in q_keywords if k in gen_lower)
        relevance = gen_has_q_keywords / len(q_keywords) if q_keywords else 0.5

        # 4. 신뢰성: "정보를 찾을 수 없습니다" 패턴 확인
        insufficient_patterns = ["찾을 수 없", "확인되지 않", "알 수 없", "정보가 없"]
        is_insufficient = any(p in gen_lower for p in insufficient_patterns)

        # 에러 코드가 없는 질문에 insufficient 응답이면 높은 신뢰성
        # 에러 코드가 있는 질문에 insufficient 응답이면 낮은 신뢰성
        error_code_match = re.search(r'[cC]\d+|[eE]\d+', question)
        if is_insufficient:
            # 유효하지 않은 에러 코드에 대한 insufficient 응답
            faithfulness = 1.0
        else:
            faithfulness = 0.7  # 기본값

        return AnswerMetrics(
            accuracy=min(1.0, accuracy),
            completeness=min(1.0, completeness),
            relevance=min(1.0, relevance),
            faithfulness=faithfulness,
        )


# ============================================================
# 모듈 테스트
# ============================================================

if __name__ == "__main__":
    # LLMJudge 테스트
    print("Testing LLMJudge...")

    judge = LLMJudge()

    # 테스트 케이스 1: 정상 답변
    metrics = judge.evaluate(
        question="C103 에러가 발생했습니다. 해결 방법을 알려주세요.",
        generated_answer="C103 에러는 Joint 관련 통신 문제입니다. 케이블 연결 상태를 확인하고 필요 시 재부팅을 수행하세요.",
        expected_answer="C103 에러는 Joint 관련 통신 문제입니다. 케이블 연결 상태를 확인하고 필요 시 재부팅을 수행하세요.",
    )
    print(f"\nTest 1 (정확한 답변):")
    print(f"  Accuracy: {metrics.accuracy:.2f}")
    print(f"  Completeness: {metrics.completeness:.2f}")
    print(f"  Relevance: {metrics.relevance:.2f}")
    print(f"  Faithfulness: {metrics.faithfulness:.2f}")

    # 테스트 케이스 2: 존재하지 않는 에러 코드에 대한 적절한 응답
    metrics = judge.evaluate(
        question="C999 에러 해결법",
        generated_answer="C999 에러 코드에 대한 정보를 찾을 수 없습니다. 정확한 에러 코드를 확인해 주세요.",
        expected_answer="C999 에러 코드에 대한 정보를 찾을 수 없습니다. 정확한 에러 코드를 확인해 주세요.",
    )
    print(f"\nTest 2 (존재하지 않는 에러 코드):")
    print(f"  Accuracy: {metrics.accuracy:.2f}")
    print(f"  Completeness: {metrics.completeness:.2f}")
    print(f"  Relevance: {metrics.relevance:.2f}")
    print(f"  Faithfulness: {metrics.faithfulness:.2f}")

    # RuleBasedJudge 테스트
    print("\n\nTesting RuleBasedJudge...")
    rule_judge = RuleBasedJudge()
    metrics = rule_judge.evaluate(
        question="C103 에러가 발생했습니다. 해결 방법을 알려주세요.",
        generated_answer="C103 에러는 통신 문제입니다. 케이블을 확인하세요.",
        expected_answer="C103 에러는 Joint 관련 통신 문제입니다. 케이블 연결 상태를 확인하고 필요 시 재부팅을 수행하세요.",
    )
    print(f"\nRule-based Test:")
    print(f"  Accuracy: {metrics.accuracy:.2f}")
    print(f"  Completeness: {metrics.completeness:.2f}")
    print(f"  Relevance: {metrics.relevance:.2f}")
    print(f"  Faithfulness: {metrics.faithfulness:.2f}")
