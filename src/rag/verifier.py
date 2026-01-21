# ============================================================
# src/rag/verifier.py - 답변 검증기
# ============================================================
# 근거 없는 답변(Hallucination)을 방지하고 신뢰할 수 있는 응답만
# 반환하도록 검증합니다.
#
# 주요 기능:
#   - Context Verifier: 컨텍스트 충분성 사전 검증
#   - Answer Verifier: 답변-컨텍스트 일치 사후 검증
#   - Safe Response: 검증 실패 시 안전 응답 생성
# ============================================================

import re
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.rag.query_analyzer import QueryAnalysis
from src.rag.hybrid_retriever import HybridResult


# ============================================================
# [1] 검증 상태 Enum
# ============================================================

class VerificationStatus(Enum):
    """
    검증 상태

    Values:
        VERIFIED: 검증됨 (충분한 근거 있음)
        PARTIAL: 부분 검증 (일부 근거만 있음)
        UNVERIFIED: 미검증 (근거 없음)
        INSUFFICIENT: 컨텍스트 부족
    """
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    INSUFFICIENT = "insufficient"


# ============================================================
# [2] 검증 결과 데이터 클래스
# ============================================================

@dataclass
class VerificationResult:
    """
    검증 결과

    Attributes:
        status: 검증 상태
        confidence: 신뢰도 점수 (0.0 ~ 1.0)
        evidence_count: 근거 수
        evidence_sources: 근거 출처 리스트
        warnings: 경고 메시지 리스트
    """
    status: VerificationStatus
    confidence: float
    evidence_count: int
    evidence_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_safe_to_answer(self) -> bool:
        """답변해도 안전한지 여부"""
        return self.status in [VerificationStatus.VERIFIED, VerificationStatus.PARTIAL]

    def __repr__(self):
        return (
            f"VerificationResult(\n"
            f"  status={self.status.value}\n"
            f"  confidence={self.confidence:.2f}\n"
            f"  evidence_count={self.evidence_count}\n"
            f"  warnings={self.warnings}\n"
            f")"
        )


# ============================================================
# [3] Context Verifier - 컨텍스트 사전 검증
# ============================================================

class ContextVerifier:
    """
    컨텍스트 사전 검증기

    검색된 컨텍스트가 질문에 답변하기 충분한지 검증합니다.

    검증 항목:
        1. 컨텍스트 수 확인
        2. 에러 코드 존재 여부
        3. 부품명 존재 여부
        4. 관련성 점수 검증

    사용 예시:
        verifier = ContextVerifier()
        result = verifier.verify_context(analysis, contexts)
        if result.is_safe_to_answer:
            # LLM 생성 진행
        else:
            # 안전 응답 반환
    """

    def __init__(
        self,
        min_contexts: int = 1,
        min_relevance_score: float = 0.3,
    ):
        """
        ContextVerifier 초기화

        Args:
            min_contexts: 최소 필요 컨텍스트 수
            min_relevance_score: 최소 관련성 점수
        """
        self.min_contexts = min_contexts
        self.min_relevance_score = min_relevance_score

        # 에러 코드 패턴 (유효/무효 모두 감지용)
        self.error_code_pattern = re.compile(r'\b(C\d+(?:A\d+)?)\b', re.IGNORECASE)
        self.valid_error_bases = set(range(0, 56))  # C0 ~ C55

    def _detect_invalid_error_codes(self, query: str) -> List[str]:
        """
        질문에서 유효하지 않은 에러 코드 감지

        Args:
            query: 원본 질문

        Returns:
            List[str]: 유효하지 않은 에러 코드 리스트
        """
        matches = self.error_code_pattern.findall(query)
        invalid_codes = []

        for code in matches:
            code_upper = code.upper()
            base_match = re.match(r'C(\d+)', code_upper)
            if base_match:
                base_num = int(base_match.group(1))
                if base_num not in self.valid_error_bases:
                    invalid_codes.append(code_upper)

        return invalid_codes

    def verify_context(
        self,
        query_analysis: QueryAnalysis,
        contexts: List[HybridResult],
    ) -> VerificationResult:
        """
        컨텍스트 검증 수행

        Args:
            query_analysis: 질문 분석 결과
            contexts: 검색된 컨텍스트 리스트

        Returns:
            VerificationResult: 검증 결과
        """
        warnings = []
        evidence_sources = []

        # ─────────────────────────────────────────────────────
        # 0. 유효하지 않은 에러 코드 감지 (C56 이상)
        # ─────────────────────────────────────────────────────
        invalid_codes = self._detect_invalid_error_codes(query_analysis.original_query)
        if invalid_codes:
            return VerificationResult(
                status=VerificationStatus.INSUFFICIENT,
                confidence=0.0,
                evidence_count=0,
                evidence_sources=[],
                warnings=[f"유효하지 않은 에러 코드: {invalid_codes}. 유효 범위는 C0~C55입니다."]
            )

        # ─────────────────────────────────────────────────────
        # 1. 컨텍스트 수 확인
        # ─────────────────────────────────────────────────────
        if len(contexts) < self.min_contexts:
            return VerificationResult(
                status=VerificationStatus.INSUFFICIENT,
                confidence=0.0,
                evidence_count=0,
                evidence_sources=[],
                warnings=["검색된 컨텍스트가 부족합니다"]
            )

        # ─────────────────────────────────────────────────────
        # 2. 에러 코드 검증 (있을 경우)
        # ─────────────────────────────────────────────────────
        if query_analysis.error_codes:
            found_codes = self._check_error_codes_in_context(
                query_analysis.error_codes,
                contexts
            )
            if not found_codes:
                return VerificationResult(
                    status=VerificationStatus.INSUFFICIENT,
                    confidence=0.0,
                    evidence_count=0,
                    evidence_sources=[],
                    warnings=[f"에러 코드 {query_analysis.error_codes}에 대한 정보를 찾을 수 없습니다"]
                )
            evidence_sources.extend(found_codes)

        # ─────────────────────────────────────────────────────
        # 3. 부품명 검증 (있을 경우)
        # ─────────────────────────────────────────────────────
        if query_analysis.components:
            found_components = self._check_components_in_context(
                query_analysis.components,
                contexts
            )
            if not found_components:
                warnings.append(f"부품 {query_analysis.components} 정보가 제한적입니다")
            else:
                evidence_sources.extend(found_components)

        # ─────────────────────────────────────────────────────
        # 4. 관련성 점수 검증
        # ─────────────────────────────────────────────────────
        avg_score = sum(c.score for c in contexts) / len(contexts)
        if avg_score < self.min_relevance_score:
            warnings.append(f"컨텍스트 관련성이 낮습니다 (score={avg_score:.2f})")

        # ─────────────────────────────────────────────────────
        # 5. 최종 판정
        # ─────────────────────────────────────────────────────
        evidence_count = len(evidence_sources)
        confidence = min(1.0, evidence_count * 0.2 + avg_score)

        if evidence_count >= 2 and not warnings:
            status = VerificationStatus.VERIFIED
        elif evidence_count >= 1:
            status = VerificationStatus.PARTIAL
        else:
            # 에러 코드/부품명이 없는 일반 질문
            if not query_analysis.error_codes and not query_analysis.components:
                # 일반 질문은 컨텍스트가 있으면 PARTIAL
                status = VerificationStatus.PARTIAL
                evidence_sources = [f"vector_result_{i}" for i in range(min(3, len(contexts)))]
                evidence_count = len(evidence_sources)
                confidence = avg_score
            else:
                status = VerificationStatus.UNVERIFIED

        return VerificationResult(
            status=status,
            confidence=confidence,
            evidence_count=evidence_count,
            evidence_sources=evidence_sources,
            warnings=warnings
        )

    def _check_error_codes_in_context(
        self,
        error_codes: List[str],
        contexts: List[HybridResult],
    ) -> List[str]:
        """
        에러 코드가 컨텍스트에 존재하는지 확인

        Args:
            error_codes: 검색할 에러 코드 리스트
            contexts: 컨텍스트 리스트

        Returns:
            List[str]: 발견된 에러 코드와 출처
        """
        found = []

        for code in error_codes:
            code_lower = code.lower()

            for ctx in contexts:
                content_lower = ctx.content.lower()

                # 에러 코드가 컨텍스트에 있는지 확인
                if code_lower in content_lower:
                    source = ctx.metadata.get(
                        "entity_name",
                        ctx.metadata.get("chunk_id", "unknown")
                    )
                    found.append(f"{code} (from {source})")
                    break

        return found

    def _check_components_in_context(
        self,
        components: List[str],
        contexts: List[HybridResult],
    ) -> List[str]:
        """
        부품명이 컨텍스트에 존재하는지 확인

        Args:
            components: 검색할 부품명 리스트
            contexts: 컨텍스트 리스트

        Returns:
            List[str]: 발견된 부품명과 출처
        """
        found = []

        for component in components:
            component_lower = component.lower()

            for ctx in contexts:
                content_lower = ctx.content.lower()

                if component_lower in content_lower:
                    source = ctx.metadata.get(
                        "entity_name",
                        ctx.metadata.get("chunk_id", "unknown")
                    )
                    found.append(f"{component} (from {source})")
                    break

        return found


# ============================================================
# [4] Answer Verifier - 답변 사후 검증
# ============================================================

class AnswerVerifier:
    """
    답변 사후 검증기

    LLM이 생성한 답변이 컨텍스트에 기반하는지 검증합니다.

    검증 항목:
        1. 답변에 언급된 에러 코드가 컨텍스트에 있는지
        2. Hallucination 감지
        3. 출처 확인

    사용 예시:
        verifier = AnswerVerifier()
        result = verifier.verify_answer(answer, contexts, analysis)
        if result.warnings:
            print("경고:", result.warnings)
    """

    def __init__(self):
        """AnswerVerifier 초기화"""
        # 에러 코드 감지 패턴
        self.error_code_pattern = re.compile(r'\b(C\d+(?:A\d+)?)\b', re.IGNORECASE)

    def verify_answer(
        self,
        answer: str,
        contexts: List[HybridResult],
        query_analysis: QueryAnalysis,
    ) -> VerificationResult:
        """
        답변 검증 수행

        Args:
            answer: LLM이 생성한 답변
            contexts: 사용된 컨텍스트 리스트
            query_analysis: 질문 분석 결과

        Returns:
            VerificationResult: 검증 결과
        """
        warnings = []
        evidence_sources = []

        # ─────────────────────────────────────────────────────
        # 1. 답변에서 에러 코드 추출
        # ─────────────────────────────────────────────────────
        answer_error_codes = self.error_code_pattern.findall(answer)
        answer_error_codes = list(set([c.upper() for c in answer_error_codes]))

        # ─────────────────────────────────────────────────────
        # 2. 컨텍스트에 없는 에러 코드 감지 (Hallucination)
        # ─────────────────────────────────────────────────────
        context_text = " ".join([c.content for c in contexts]).upper()

        for code in answer_error_codes:
            if code not in context_text:
                # 질문에 원래 있던 코드인지 확인
                if code not in query_analysis.error_codes:
                    warnings.append(f"답변에 근거 없는 에러 코드가 포함됨: {code}")

        # ─────────────────────────────────────────────────────
        # 3. 출처 매칭 (답변 내용이 컨텍스트에서 왔는지)
        # ─────────────────────────────────────────────────────
        for ctx in contexts:
            key_phrases = self._extract_key_phrases(ctx.content)

            # 핵심 구문이 답변에 포함되어 있으면 출처로 인정
            for phrase in key_phrases:
                if phrase.lower() in answer.lower():
                    source = ctx.metadata.get(
                        "entity_name",
                        ctx.metadata.get("chunk_id", "unknown")
                    )
                    if source not in evidence_sources:
                        evidence_sources.append(source)
                    break

        # ─────────────────────────────────────────────────────
        # 4. 신뢰도 및 상태 결정
        # ─────────────────────────────────────────────────────
        if warnings:
            confidence = max(0.0, 0.5 - len(warnings) * 0.2)
            if confidence > 0.2:
                status = VerificationStatus.PARTIAL
            else:
                status = VerificationStatus.UNVERIFIED
        else:
            confidence = min(1.0, len(evidence_sources) * 0.25 + 0.3)
            if confidence > 0.6:
                status = VerificationStatus.VERIFIED
            else:
                status = VerificationStatus.PARTIAL

        return VerificationResult(
            status=status,
            confidence=confidence,
            evidence_count=len(evidence_sources),
            evidence_sources=evidence_sources,
            warnings=warnings
        )

    def _extract_key_phrases(self, text: str, max_phrases: int = 5) -> List[str]:
        """
        컨텍스트에서 핵심 구문 추출

        Args:
            text: 텍스트
            max_phrases: 추출할 최대 구문 수

        Returns:
            List[str]: 핵심 구문 리스트
        """
        # 4글자 이상 단어 추출
        words = re.findall(r'\b\w{4,}\b', text.lower())

        # 빈도순 정렬
        from collections import Counter
        common = Counter(words).most_common(max_phrases)

        return [word for word, _ in common]


# ============================================================
# [5] Safe Response Generator - 안전 응답 생성
# ============================================================

class SafeResponseGenerator:
    """
    안전 응답 생성기

    검증 실패 시 사용자에게 제공할 안전한 응답을 생성합니다.

    응답 유형:
        - INSUFFICIENT: 컨텍스트 부족
        - UNVERIFIED: 근거 없음
        - PARTIAL: 부분 정보 (경고 추가)
    """

    def generate_safe_response(
        self,
        verification: VerificationResult,
        query_analysis: QueryAnalysis,
    ) -> str:
        """
        안전한 응답 생성

        Args:
            verification: 검증 결과
            query_analysis: 질문 분석 결과

        Returns:
            str: 안전한 응답 메시지
        """
        if verification.status == VerificationStatus.INSUFFICIENT:
            return self._insufficient_response(query_analysis, verification.warnings)

        elif verification.status == VerificationStatus.UNVERIFIED:
            return self._unverified_response(query_analysis, verification.warnings)

        else:  # PARTIAL
            return self._partial_response(verification.warnings)

    def _insufficient_response(
        self,
        query_analysis: QueryAnalysis,
        warnings: List[str],
    ) -> str:
        """컨텍스트 부족 응답"""
        # 유효하지 않은 에러 코드 감지 시
        for warning in warnings:
            if "유효하지 않은 에러 코드" in warning:
                return (
                    f"죄송합니다. {warning}\n\n"
                    f"UR5e 에러 코드는 C0부터 C55까지 존재합니다. "
                    f"에러 코드를 다시 확인해 주세요.\n\n"
                    f"예시: C4A15, C50, C17 등"
                )

        if query_analysis.error_codes:
            codes = ", ".join(query_analysis.error_codes)
            return (
                f"죄송합니다. {codes} 에러 코드에 대한 정보를 "
                f"데이터베이스에서 찾을 수 없습니다.\n\n"
                f"유효한 에러 코드 범위는 C0~C55입니다. "
                f"에러 코드를 다시 확인해 주세요."
            )

        if query_analysis.components:
            components = ", ".join(query_analysis.components)
            return (
                f"죄송합니다. {components}에 대한 충분한 정보를 "
                f"찾을 수 없습니다.\n\n"
                f"다른 방식으로 질문해 주시거나, "
                f"UR5e 사용 설명서를 참조해 주세요."
            )

        return (
            "죄송합니다. 질문에 답변할 수 있는 충분한 정보를 "
            "찾을 수 없습니다.\n\n"
            "질문을 더 구체적으로 해주시거나, "
            "에러 코드나 부품명을 포함해 주세요."
        )

    def _unverified_response(
        self,
        query_analysis: QueryAnalysis,
        warnings: List[str],
    ) -> str:
        """근거 없음 응답"""
        warning_text = "\n".join(f"  - {w}" for w in warnings) if warnings else "  - 관련 정보 부족"

        return (
            f"죄송합니다. 요청하신 정보에 대한 신뢰할 수 있는 "
            f"근거를 찾을 수 없습니다.\n\n"
            f"**확인된 문제:**\n{warning_text}\n\n"
            f"정확한 정보를 위해 UR5e 공식 매뉴얼이나 "
            f"Universal Robots 기술지원팀에 문의해 주세요."
        )

    def _partial_response(self, warnings: List[str]) -> str:
        """부분 정보 경고 (답변 뒤에 추가)"""
        if not warnings:
            return ""

        warning_text = "\n".join(f"  - {w}" for w in warnings)

        return (
            f"\n\n---\n"
            f"**주의:** 이 답변은 제한된 정보를 기반으로 합니다.\n"
            f"{warning_text}\n"
            f"정확한 정보는 공식 매뉴얼을 참조해 주세요."
        )


# ============================================================
# [6] 통합 Verifier 클래스
# ============================================================

class Verifier:
    """
    통합 검증기

    Context Verifier + Answer Verifier + Safe Response를 통합합니다.

    사용 예시:
        verifier = Verifier()

        # 생성 전 검증
        pre_result = verifier.verify_before_generation(analysis, contexts)
        if not pre_result.is_safe_to_answer:
            return verifier.get_safe_response(pre_result, analysis)

        # LLM 생성 후 검증
        post_result = verifier.verify_after_generation(answer, contexts, analysis)

        # 출처 추가
        answer = verifier.add_citation(answer, post_result)
    """

    def __init__(
        self,
        min_contexts: int = 1,
        min_relevance_score: float = 0.3,
    ):
        """
        Verifier 초기화

        Args:
            min_contexts: 최소 필요 컨텍스트 수
            min_relevance_score: 최소 관련성 점수
        """
        self.context_verifier = ContextVerifier(
            min_contexts=min_contexts,
            min_relevance_score=min_relevance_score,
        )
        self.answer_verifier = AnswerVerifier()
        self.safe_response_generator = SafeResponseGenerator()

        print("[OK] Verifier initialized")

    def verify_before_generation(
        self,
        query_analysis: QueryAnalysis,
        contexts: List[HybridResult],
    ) -> VerificationResult:
        """
        생성 전 컨텍스트 검증

        Args:
            query_analysis: 질문 분석 결과
            contexts: 검색된 컨텍스트

        Returns:
            VerificationResult: 검증 결과
        """
        return self.context_verifier.verify_context(query_analysis, contexts)

    def verify_after_generation(
        self,
        answer: str,
        contexts: List[HybridResult],
        query_analysis: QueryAnalysis,
    ) -> VerificationResult:
        """
        생성 후 답변 검증

        Args:
            answer: LLM 생성 답변
            contexts: 사용된 컨텍스트
            query_analysis: 질문 분석 결과

        Returns:
            VerificationResult: 검증 결과
        """
        return self.answer_verifier.verify_answer(answer, contexts, query_analysis)

    def get_safe_response(
        self,
        verification: VerificationResult,
        query_analysis: QueryAnalysis,
    ) -> str:
        """
        안전 응답 생성

        Args:
            verification: 검증 결과
            query_analysis: 질문 분석 결과

        Returns:
            str: 안전한 응답 메시지
        """
        return self.safe_response_generator.generate_safe_response(
            verification, query_analysis
        )

    def add_citation(
        self,
        answer: str,
        verification: VerificationResult,
    ) -> str:
        """
        답변에 출처 정보 추가

        Args:
            answer: 원본 답변
            verification: 검증 결과

        Returns:
            str: 출처가 추가된 답변
        """
        if not verification.evidence_sources:
            return answer

        # 상위 3개 출처만 표시
        sources = verification.evidence_sources[:3]
        sources_text = "\n".join(f"  - {s}" for s in sources)

        # 신뢰도 아이콘
        if verification.confidence >= 0.7:
            confidence_icon = "🟢"
        elif verification.confidence >= 0.4:
            confidence_icon = "🟡"
        else:
            confidence_icon = "🔴"

        citation = (
            f"\n\n---\n"
            f"**출처:**\n{sources_text}\n"
            f"{confidence_icon} 신뢰도: {verification.confidence:.0%}"
        )

        return answer + citation

    def add_warning(
        self,
        answer: str,
        verification: VerificationResult,
    ) -> str:
        """
        답변에 경고 메시지 추가 (PARTIAL일 때)

        Args:
            answer: 원본 답변
            verification: 검증 결과

        Returns:
            str: 경고가 추가된 답변
        """
        if verification.status != VerificationStatus.PARTIAL:
            return answer

        if not verification.warnings:
            return answer

        warning = self.safe_response_generator._partial_response(verification.warnings)
        return answer + warning


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("[*] Verifier Test")
    print("=" * 60)

    # 테스트용 mock 데이터
    from dataclasses import dataclass

    # Mock QueryAnalysis
    @dataclass
    class MockAnalysis:
        original_query: str
        error_codes: List[str]
        components: List[str]
        keywords: List[str]
        query_type: str
        search_strategy: str

    # Mock HybridResult
    @dataclass
    class MockContext:
        content: str
        source_type: str
        score: float
        metadata: Dict[str, Any]

    # 테스트 케이스 1: 정상적인 에러 코드 질문
    print("\n" + "─" * 60)
    print("[Test 1] 정상적인 에러 코드 질문")
    print("─" * 60)

    analysis1 = MockAnalysis(
        original_query="C4A15 에러 해결법",
        error_codes=["C4A15"],
        components=[],
        keywords=["에러", "해결"],
        query_type="error_resolution",
        search_strategy="graph_first"
    )

    contexts1 = [
        MockContext(
            content="C4A15: Communication with joint 3 lost. 해결: 케이블 확인, 재부팅",
            source_type="graph",
            score=0.95,
            metadata={"entity_name": "C4A15"}
        ),
        MockContext(
            content="Joint 통신 에러 발생 시 케이블 연결 상태를 먼저 확인하세요.",
            source_type="vector",
            score=0.75,
            metadata={"chunk_id": "manual_ch5_001"}
        )
    ]

    verifier = Verifier()
    result1 = verifier.verify_before_generation(analysis1, contexts1)
    print(f"  Pre-verification: {result1.status.value}")
    print(f"  Safe to answer: {result1.is_safe_to_answer}")
    print(f"  Evidence: {result1.evidence_sources}")

    # 테스트 케이스 2: 존재하지 않는 에러 코드
    print("\n" + "─" * 60)
    print("[Test 2] 존재하지 않는 에러 코드 (C999)")
    print("─" * 60)

    analysis2 = MockAnalysis(
        original_query="C999 에러 해결법",
        error_codes=["C999"],
        components=[],
        keywords=["에러", "해결"],
        query_type="error_resolution",
        search_strategy="graph_first"
    )

    contexts2 = [
        MockContext(
            content="일반적인 에러 해결 방법: 재시작을 시도하세요.",
            source_type="vector",
            score=0.3,
            metadata={"chunk_id": "manual_general"}
        )
    ]

    result2 = verifier.verify_before_generation(analysis2, contexts2)
    print(f"  Pre-verification: {result2.status.value}")
    print(f"  Safe to answer: {result2.is_safe_to_answer}")
    print(f"  Warnings: {result2.warnings}")

    if not result2.is_safe_to_answer:
        safe_response = verifier.get_safe_response(result2, analysis2)
        print(f"\n  Safe Response:")
        print(f"  {safe_response}")

    # 테스트 케이스 3: 답변 검증 (Hallucination 감지)
    print("\n" + "─" * 60)
    print("[Test 3] 답변 검증 - Hallucination 감지")
    print("─" * 60)

    answer3 = "C4A15 에러는 통신 문제입니다. 또한 C999 에러도 비슷한 문제입니다."

    result3 = verifier.verify_after_generation(answer3, contexts1, analysis1)
    print(f"  Post-verification: {result3.status.value}")
    print(f"  Warnings: {result3.warnings}")

    # 테스트 케이스 4: 출처 추가
    print("\n" + "─" * 60)
    print("[Test 4] 출처 추가")
    print("─" * 60)

    answer4 = "C4A15 에러 해결: 케이블을 확인하고 재부팅하세요."
    result4 = verifier.verify_after_generation(answer4, contexts1, analysis1)

    answer_with_citation = verifier.add_citation(answer4, result4)
    print(f"  Original: {answer4}")
    print(f"\n  With citation:")
    print(answer_with_citation)

    print("\n" + "=" * 60)
    print("[OK] Verifier test completed!")
    print("=" * 60)
