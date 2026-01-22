"""
프롬프트 구성기

LLM 호출을 위한 프롬프트를 구성합니다.
"""

import logging
from typing import Dict, List, Optional, Any

from .evidence_schema import QueryType, ClassificationResult

logger = logging.getLogger(__name__)


class PromptBuilder:
    """LLM 프롬프트 구성기

    질문 유형과 추론 결과에 따라 적절한 프롬프트를 구성합니다.
    """

    # 시스템 프롬프트 템플릿
    SYSTEM_PROMPT_BASE = """당신은 UR5e 협동로봇과 ATI Axia80 힘/토크 센서 전문가입니다.
온톨로지 기반 추론 결과를 사용자에게 명확하게 설명합니다.

## 장비 개요
- UR5e: 6축 협동로봇 (가반하중 5kg, 작업반경 850mm)
- Axia80: 6축 힘/토크 센서 (Fz: ±235N, Fx/Fy: ±75N, Tx/Ty/Tz: ±4Nm)

## 센서 정상 범위
- Fz (수직력): -60N ~ 0N (IDLE 상태)
- Fx, Fy (수평력): -10N ~ 10N
- Tx, Ty, Tz (토크): -0.5Nm ~ 0.5Nm

## 응답 원칙
1. 추론 결과를 근거로 명확하게 설명
2. 기술 용어는 쉽게 풀어서 설명
3. 권장 조치를 구체적으로 제시
4. 불확실한 내용은 신뢰도와 함께 표시
"""

    SYSTEM_PROMPT_ONTOLOGY = """
## 온톨로지 질문 응답 지침
- 센서 값의 상태와 의미를 분석합니다.
- 감지된 패턴과 예상 원인을 설명합니다.
- 에러 예측이 있다면 확률과 함께 제시합니다.
- 온톨로지 경로를 근거로 제시합니다.
"""

    SYSTEM_PROMPT_HYBRID = """
## 하이브리드 질문 응답 지침
- 온톨로지 추론과 문서 정보를 통합합니다.
- 에러코드의 원인과 해결책을 설명합니다.
- 관련 문서 출처를 명시합니다.
"""

    SYSTEM_PROMPT_RAG = """
## 일반 질문 응답 지침
- 문서에서 찾은 정보를 정확하게 전달합니다.
- 사양, 절차, 정의를 명확하게 설명합니다.
- 출처를 명시합니다.
"""

    def __init__(self):
        """초기화"""
        logger.info("PromptBuilder 초기화 완료")

    def build_system_prompt(self, query_type: QueryType) -> str:
        """시스템 프롬프트 구성

        Args:
            query_type: 질문 유형

        Returns:
            시스템 프롬프트
        """
        prompt = self.SYSTEM_PROMPT_BASE

        if query_type == QueryType.ONTOLOGY:
            prompt += self.SYSTEM_PROMPT_ONTOLOGY
        elif query_type == QueryType.HYBRID:
            prompt += self.SYSTEM_PROMPT_HYBRID
        else:
            prompt += self.SYSTEM_PROMPT_RAG

        return prompt

    def build_prompt(
        self,
        classification: ClassificationResult,
        reasoning: Any,  # ReasoningResult
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """전체 프롬프트 구성

        Args:
            classification: 질문 분류 결과
            reasoning: 추론 결과
            context: 추가 컨텍스트

        Returns:
            완성된 프롬프트
        """
        sections = []

        # 1. 질문 섹션
        sections.append(self._build_query_section(classification))

        # 2. 엔티티 섹션
        sections.append(self._build_entity_section(classification))

        # 3. 추론 결과 섹션
        if reasoning:
            sections.append(self._build_reasoning_section(reasoning))

        # 4. 컨텍스트 섹션 (있는 경우)
        if context:
            sections.append(self._build_context_section(context))

        # 5. 지시 섹션
        sections.append(self._build_instruction_section(classification.query_type))

        return "\n\n".join(sections)

    def _build_query_section(self, classification: ClassificationResult) -> str:
        """질문 섹션 구성"""
        return f"""## 사용자 질문
{classification.query}

- 질문 유형: {classification.query_type.value}
- 분류 신뢰도: {classification.confidence:.0%}"""

    def _build_entity_section(self, classification: ClassificationResult) -> str:
        """엔티티 섹션 구성"""
        if not classification.entities:
            return "## 추출된 엔티티\n없음"

        lines = ["## 추출된 엔티티"]
        for entity in classification.entities:
            props = ""
            if entity.properties:
                props = f" (속성: {entity.properties})"
            lines.append(f"- {entity.text}: {entity.entity_type} [{entity.entity_id}]{props}")

        return "\n".join(lines)

    def _build_reasoning_section(self, reasoning: Any) -> str:
        """추론 결과 섹션 구성"""
        lines = ["## 추론 결과"]

        # 추론 체인
        if reasoning.reasoning_chain:
            lines.append("\n### 추론 과정")
            for i, step in enumerate(reasoning.reasoning_chain, 1):
                desc = step.get("description", step.get("step", ""))
                lines.append(f"{i}. {desc}")

        # 결론
        if reasoning.conclusions:
            lines.append("\n### 결론")
            for conclusion in reasoning.conclusions:
                c_type = conclusion.get("type", "")
                if c_type == "state":
                    lines.append(f"- 상태: {conclusion.get('entity', '')} → {conclusion.get('state', '')}")
                elif c_type == "pattern":
                    lines.append(f"- 패턴: {conclusion.get('pattern', '')} (신뢰도: {conclusion.get('confidence', 0):.0%})")
                elif c_type == "cause":
                    lines.append(f"- 원인: {conclusion.get('cause', '')} (신뢰도: {conclusion.get('confidence', 0):.0%})")
                elif c_type == "triggered_error":
                    lines.append(f"- 예상 에러: {conclusion.get('error', '')} (신뢰도: {conclusion.get('confidence', 0):.0%})")
                else:
                    lines.append(f"- {conclusion}")

        # 예측
        if reasoning.predictions:
            lines.append("\n### 예측")
            for pred in reasoning.predictions:
                error = pred.get("error_code", pred.get("error", ""))
                prob = pred.get("probability", 0)
                timeframe = pred.get("timeframe", "")
                lines.append(f"- {error}: {prob:.0%} 확률{f' ({timeframe})' if timeframe else ''}")

        # 권장사항
        if reasoning.recommendations:
            lines.append("\n### 권장사항")
            for rec in reasoning.recommendations:
                action = rec.get("action", rec.get("resolution", ""))
                ref = rec.get("reference", "")
                lines.append(f"- {action}{f' (참고: {ref})' if ref else ''}")

        # 온톨로지 경로
        if reasoning.ontology_paths:
            lines.append("\n### 온톨로지 경로")
            for path in reasoning.ontology_paths[:3]:  # 최대 3개
                lines.append(f"- {path}")

        lines.append(f"\n추론 신뢰도: {reasoning.confidence:.0%}")

        return "\n".join(lines)

    def _build_context_section(self, context: Dict[str, Any]) -> str:
        """컨텍스트 섹션 구성"""
        lines = ["## 현재 컨텍스트"]

        if "shift" in context:
            lines.append(f"- 근무조: {context['shift']}")
        if "product" in context:
            lines.append(f"- 제품: {context['product']}")
        if "work_phase" in context:
            lines.append(f"- 작업 단계: {context['work_phase']}")
        if "current_time" in context:
            lines.append(f"- 현재 시간: {context['current_time']}")

        return "\n".join(lines)

    def _build_instruction_section(self, query_type: QueryType) -> str:
        """지시 섹션 구성"""
        base_instruction = """## 응답 지시
위의 추론 결과를 바탕으로 사용자에게 명확하고 유용한 답변을 제공하세요.

1. 핵심 내용을 먼저 요약
2. 기술적 분석 결과 설명
3. 권장 조치 제시
4. 불확실한 내용은 신뢰도와 함께 표시"""

        if query_type == QueryType.ONTOLOGY:
            base_instruction += """
5. 온톨로지 추론 경로를 근거로 제시
6. 예측이 있다면 확률과 함께 설명"""
        elif query_type == QueryType.HYBRID:
            base_instruction += """
5. 문서 출처를 명시
6. 온톨로지와 문서 정보를 통합하여 설명"""

        return base_instruction


# 편의 함수
def create_prompt_builder() -> PromptBuilder:
    """PromptBuilder 인스턴스 생성"""
    return PromptBuilder()
