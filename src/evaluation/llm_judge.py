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
        - faithfulness: 온톨로지 기반 여부 (환각 없음)
    """

    EVALUATION_PROMPT = """당신은 산업용 로봇(UR5e) 및 힘 센서(Axia80) 관련 AI 답변의 품질을 평가하는 전문 평가자입니다.
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
   - 1.0: 모든 핵심 정보 포함 (에러코드, 원인, 해결책 등)
   - 0.7-0.9: 대부분의 핵심 정보 포함
   - 0.4-0.6: 일부 핵심 정보만 포함
   - 0.0-0.3: 핵심 정보 대부분 누락

3. **relevance** (관련성): 질문에 대한 적절한 답변인가?
   - 1.0: 질문에 정확히 맞는 답변
   - 0.7-0.9: 대체로 적절한 답변
   - 0.4-0.6: 부분적으로 관련됨
   - 0.0-0.3: 관련 없는 답변

4. **faithfulness** (신뢰성): 답변이 사실에 기반하고 있는가? (환각이 없는가?)
   - 1.0: 모든 정보가 사실에 기반 (온톨로지/매뉴얼 정보)
   - 0.7-0.9: 대부분 사실에 기반
   - 0.4-0.6: 일부 불확실한 정보 포함
   - 0.0-0.3: 많은 부분이 사실과 다름 (환각)

## 주의사항
- "해당 질문에 대한 충분한 근거를 찾지 못했습니다" 등의 ABSTAIN 응답은 정보가 없을 때 적절한 응답입니다.
- 존재하지 않는 에러 코드나 잘못된 질문에 ABSTAIN으로 답하면 높은 점수를 줍니다.
- 추측이나 허위 정보를 제공하면 낮은 점수를 줍니다.
- "안녕?" 같은 도메인 외 질문에 ABSTAIN 응답은 적절합니다.

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
            generated_answer: 시스템이 생성한 답변
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
                    {"role": "system", "content": "당신은 산업용 로봇 AI 답변 품질을 평가하는 전문가입니다. JSON 형식으로만 응답하세요."},
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
        """LLM 응답을 AnswerMetrics로 파싱"""
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
                print(f"Could not find JSON in response: {content[:100]}")
                return AnswerMetrics(0.0, 0.0, 0.0, 0.0)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}, content: {content[:100]}")
            return AnswerMetrics(0.0, 0.0, 0.0, 0.0)
        except Exception as e:
            print(f"Parse error: {e}")
            return AnswerMetrics(0.0, 0.0, 0.0, 0.0)

    def evaluate_batch(self, items: list) -> list:
        """여러 항목 일괄 평가"""
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

    # ABSTAIN 패턴
    ABSTAIN_PATTERNS = [
        "충분한 근거를 찾지 못했습니다",
        "정보를 찾을 수 없",
        "확인되지 않",
        "알 수 없",
        "정보가 없",
        "abstain",
    ]

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

        # ABSTAIN 응답 감지
        is_abstain_response = any(p in gen_lower for p in self.ABSTAIN_PATTERNS)
        is_expected_abstain = any(p in exp_lower for p in self.ABSTAIN_PATTERNS)

        # ABSTAIN 응답이 예상되는 경우
        if is_expected_abstain and is_abstain_response:
            return AnswerMetrics(
                accuracy=1.0,
                completeness=1.0,
                relevance=1.0,
                faithfulness=1.0,
            )

        # ABSTAIN 응답이 예상되지 않는데 ABSTAIN한 경우
        if not is_expected_abstain and is_abstain_response:
            return AnswerMetrics(
                accuracy=0.2,
                completeness=0.0,
                relevance=0.3,
                faithfulness=1.0,  # 적어도 환각은 없음
            )

        # ABSTAIN이 예상되는데 답변한 경우 (환각)
        if is_expected_abstain and not is_abstain_response:
            return AnswerMetrics(
                accuracy=0.0,
                completeness=0.0,
                relevance=0.2,
                faithfulness=0.0,  # 환각
            )

        # 1. 정확도: 예상 답변의 키워드가 생성 답변에 포함된 비율
        exp_keywords = set(exp_lower.split())
        gen_words = set(gen_lower.split())
        # 불용어 제거
        stopwords = {"해결", "방법", "알려주세요", "입니다", "에러", "발생", "가", "이", "의", "을", "를", "은", "는"}
        exp_keywords = exp_keywords - stopwords
        common_keywords = exp_keywords.intersection(gen_words)
        accuracy = len(common_keywords) / len(exp_keywords) if exp_keywords else 0.5

        # 2. 완전성: 예상 답변 길이 대비 생성 답변 길이
        completeness = min(1.0, len(generated_answer) / max(len(expected_answer), 1))

        # 3. 관련성: 질문 키워드가 답변에 포함된 비율
        q_keywords = set(q_lower.split()) - stopwords
        gen_has_q_keywords = sum(1 for k in q_keywords if k in gen_lower)
        relevance = gen_has_q_keywords / len(q_keywords) if q_keywords else 0.5

        # 4. 신뢰성: 기본 0.7 (규칙 기반으로는 정확히 평가 어려움)
        faithfulness = 0.7

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
    # RuleBasedJudge 테스트 (LLM 없이 빠른 테스트)
    print("Testing RuleBasedJudge...")

    rule_judge = RuleBasedJudge()

    # 테스트 1: 정상 답변
    metrics = rule_judge.evaluate(
        question="C153 에러가 발생했습니다. 해결 방법을 알려주세요.",
        generated_answer="C153 에러는 Joint 관련 통신 문제입니다. 케이블 연결 상태를 확인하고 필요 시 재부팅을 수행하세요.",
        expected_answer="C153 에러는 Joint 관련 통신 문제입니다. 케이블 연결 상태를 확인하고 필요 시 재부팅을 수행하세요.",
    )
    print(f"\nTest 1 (정확한 답변):")
    print(f"  Accuracy: {metrics.accuracy:.2f}")
    print(f"  Completeness: {metrics.completeness:.2f}")
    print(f"  Relevance: {metrics.relevance:.2f}")
    print(f"  Faithfulness: {metrics.faithfulness:.2f}")

    # 테스트 2: 적절한 ABSTAIN
    metrics = rule_judge.evaluate(
        question="안녕?",
        generated_answer="해당 질문에 대한 충분한 근거를 찾지 못했습니다.",
        expected_answer="해당 질문에 대한 충분한 근거를 찾지 못했습니다.",
    )
    print(f"\nTest 2 (적절한 ABSTAIN):")
    print(f"  Accuracy: {metrics.accuracy:.2f}")
    print(f"  Completeness: {metrics.completeness:.2f}")
    print(f"  Relevance: {metrics.relevance:.2f}")
    print(f"  Faithfulness: {metrics.faithfulness:.2f}")

    # 테스트 3: 환각 응답
    metrics = rule_judge.evaluate(
        question="C999 에러 해결법",
        generated_answer="C999 에러는 시스템 오류입니다. 재부팅하세요.",  # 존재하지 않는 에러 코드에 답변
        expected_answer="해당 질문에 대한 충분한 근거를 찾지 못했습니다.",
    )
    print(f"\nTest 3 (환각 응답):")
    print(f"  Accuracy: {metrics.accuracy:.2f}")
    print(f"  Completeness: {metrics.completeness:.2f}")
    print(f"  Relevance: {metrics.relevance:.2f}")
    print(f"  Faithfulness: {metrics.faithfulness:.2f}")
