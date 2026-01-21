# Phase 7: Verifier 구현

> **목표:** 근거 없는 답변 방지 - 안전장치
>
> **핵심 학습:** 답변 검증, Hallucination 방지, 출처 기반 응답
>
> **난이도:** ★★★☆☆

---

## 1. Phase 6 한계 및 Phase 7 필요성

### 1.1 Phase 6에서 발견된 문제

```
[질문] "C999 에러 해결법 알려줘"

[Phase 6 - 하이브리드 검색]
  GraphDB: C999 없음
  VectorDB: 유사한 에러 문서 반환

  LLM 답변: "C999 에러는 전원 문제로 인해 발생합니다.
             해결 방법: 1) 전원 케이블 확인 2) 재시작"

  문제: C999는 존재하지 않는 에러 코드!
        LLM이 '추측'으로 답변을 생성함 ❌
```

**원인:** LLM은 컨텍스트에 없는 정보도 '그럴듯하게' 생성 (Hallucination)

### 1.2 Phase 7 해결 방향

```
[질문] "C999 에러 해결법 알려줘"

[Phase 7 - Verifier 적용]
  1. 검색: C999 관련 정보 없음
  2. 검증: 에러 코드 C999가 컨텍스트에 존재하는가? → NO
  3. 판정: "근거 없음" (UNVERIFIED)

  답변: "죄송합니다. C999 에러 코드에 대한 정보를
        데이터베이스에서 찾을 수 없습니다.
        유효한 에러 코드 범위는 C0~C55입니다." ✅
```

---

## 2. Phase 7 목표

### 2.1 Verifier 역할

```
┌─────────────────────────────────────────────────────────────┐
│                    Phase 7 RAG Pipeline                      │
│                                                              │
│  [사용자 질문]                                               │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────┐        │
│  │            Query Analyzer (Phase 6)              │        │
│  └─────────────────────────────────────────────────┘        │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────┐        │
│  │            Hybrid Retriever (Phase 6)            │        │
│  └─────────────────────────────────────────────────┘        │
│       │                                                      │
│       ├─────────────────────────────────────────┐           │
│       ▼                                         │           │
│  ┌──────────────────────────────┐               │           │
│  │     Context Verifier (신규)  │               │           │
│  │  • 컨텍스트 충분성 검증      │               │           │
│  │  • 엔티티 존재 확인          │               │           │
│  │  • 답변 가능 여부 판정       │               │           │
│  └──────────────────────────────┘               │           │
│       │                                         │           │
│       ├────YES────┐      NO─────────────────────┤           │
│       ▼           │                             ▼           │
│  ┌────────────┐   │                    ┌────────────────┐   │
│  │  LLM 생성  │   │                    │ 안전 응답 생성  │   │
│  └────────────┘   │                    │ "정보 없음"     │   │
│       │           │                    └────────────────┘   │
│       ▼           │                             │           │
│  ┌──────────────────────────────┐               │           │
│  │    Answer Verifier (신규)    │               │           │
│  │  • 답변-컨텍스트 일치 검증   │               │           │
│  │  • 출처 태깅                 │               │           │
│  │  • 신뢰도 점수               │               │           │
│  └──────────────────────────────┘               │           │
│       │                                         │           │
│       └─────────────────────────────────────────┘           │
│                           │                                  │
│                           ▼                                  │
│                    [검증된 답변 반환]                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 핵심 컴포넌트

| 컴포넌트 | 역할 | 신규/확장 |
|---------|------|----------|
| **Context Verifier** | 컨텍스트 충분성 사전 검증 | 신규 |
| **Answer Verifier** | 답변-컨텍스트 일치 검증 | 신규 |
| **SafeResponse** | 정보 부족 시 안전 응답 | 신규 |

---

## 3. 파일 구조 (계획)

```
src/rag/
├── __init__.py
├── retriever.py              ← 기존
├── query_analyzer.py         ← Phase 6
├── graph_retriever.py        ← Phase 6
├── hybrid_retriever.py       ← Phase 6
├── prompt_builder.py         ← 기존
├── generator.py              ← 기존
└── verifier.py               ← 신규: 검증 로직

scripts/
├── run_rag.py                ← Phase 5
├── run_rag_v2.py             ← Phase 6
└── run_rag_v3.py             ← 신규: Phase 7 버전
```

---

## 4. 상세 구현 계획

### 4.1 검증 결과 데이터 클래스

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class VerificationStatus(Enum):
    """검증 상태"""
    VERIFIED = "verified"           # 검증됨 (근거 있음)
    PARTIAL = "partial"             # 부분 검증 (일부 근거)
    UNVERIFIED = "unverified"       # 미검증 (근거 없음)
    INSUFFICIENT = "insufficient"   # 컨텍스트 부족

@dataclass
class VerificationResult:
    """검증 결과"""
    status: VerificationStatus
    confidence: float              # 신뢰도 점수 (0.0 ~ 1.0)
    evidence_count: int            # 근거 수
    evidence_sources: List[str]    # 근거 출처
    warnings: List[str]            # 경고 메시지

    @property
    def is_safe_to_answer(self) -> bool:
        """답변해도 안전한지 여부"""
        return self.status in [VerificationStatus.VERIFIED, VerificationStatus.PARTIAL]
```

### 4.2 Context Verifier

**목적:** 검색된 컨텍스트가 질문에 답변하기 충분한지 사전 검증

```python
class ContextVerifier:
    """
    컨텍스트 사전 검증기

    검증 항목:
        1. 에러 코드 존재 여부
        2. 부품명 존재 여부
        3. 컨텍스트 관련성 점수
        4. 최소 컨텍스트 수
    """

    def __init__(
        self,
        min_contexts: int = 1,
        min_relevance_score: float = 0.3,
    ):
        self.min_contexts = min_contexts
        self.min_relevance_score = min_relevance_score

    def verify_context(
        self,
        query_analysis: QueryAnalysis,
        contexts: List[HybridResult],
    ) -> VerificationResult:
        """
        컨텍스트 검증 수행

        Args:
            query_analysis: 질문 분석 결과
            contexts: 검색된 컨텍스트

        Returns:
            VerificationResult: 검증 결과
        """
        warnings = []
        evidence_sources = []

        # 1. 컨텍스트 수 확인
        if len(contexts) < self.min_contexts:
            return VerificationResult(
                status=VerificationStatus.INSUFFICIENT,
                confidence=0.0,
                evidence_count=0,
                evidence_sources=[],
                warnings=["검색된 컨텍스트가 부족합니다"]
            )

        # 2. 에러 코드 검증
        if query_analysis.error_codes:
            found_codes = self._check_error_codes_in_context(
                query_analysis.error_codes,
                contexts
            )
            if not found_codes:
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    confidence=0.0,
                    evidence_count=0,
                    evidence_sources=[],
                    warnings=[f"에러 코드 {query_analysis.error_codes}를 찾을 수 없습니다"]
                )
            evidence_sources.extend(found_codes)

        # 3. 부품명 검증
        if query_analysis.components:
            found_components = self._check_components_in_context(
                query_analysis.components,
                contexts
            )
            if not found_components:
                warnings.append(f"부품 {query_analysis.components} 정보가 제한적입니다")
            evidence_sources.extend(found_components)

        # 4. 관련성 점수 검증
        avg_score = sum(c.score for c in contexts) / len(contexts)
        if avg_score < self.min_relevance_score:
            warnings.append(f"컨텍스트 관련성이 낮습니다 (score={avg_score:.2f})")

        # 5. 최종 판정
        evidence_count = len(evidence_sources)
        confidence = min(1.0, evidence_count * 0.2 + avg_score)

        if evidence_count >= 2 and not warnings:
            status = VerificationStatus.VERIFIED
        elif evidence_count >= 1:
            status = VerificationStatus.PARTIAL
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
        """에러 코드가 컨텍스트에 존재하는지 확인"""
        found = []
        for code in error_codes:
            for ctx in contexts:
                if code.lower() in ctx.content.lower():
                    source = ctx.metadata.get("entity_name", ctx.metadata.get("chunk_id", "unknown"))
                    found.append(f"{code} (from {source})")
                    break
        return found

    def _check_components_in_context(
        self,
        components: List[str],
        contexts: List[HybridResult],
    ) -> List[str]:
        """부품명이 컨텍스트에 존재하는지 확인"""
        found = []
        for component in components:
            for ctx in contexts:
                if component.lower() in ctx.content.lower():
                    source = ctx.metadata.get("entity_name", ctx.metadata.get("chunk_id", "unknown"))
                    found.append(f"{component} (from {source})")
                    break
        return found
```

### 4.3 Answer Verifier

**목적:** LLM 답변이 컨텍스트에 기반하는지 사후 검증

```python
class AnswerVerifier:
    """
    답변 사후 검증기

    검증 항목:
        1. 답변에 언급된 정보가 컨텍스트에 있는지
        2. 에러 코드 정확성
        3. 해결 방법 출처 확인
    """

    def __init__(self):
        # 검증용 에러 코드 패턴
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
            answer: LLM 생성 답변
            contexts: 사용된 컨텍스트
            query_analysis: 질문 분석 결과

        Returns:
            VerificationResult: 검증 결과
        """
        warnings = []
        evidence_sources = []

        # 1. 답변에서 에러 코드 추출
        answer_error_codes = self.error_code_pattern.findall(answer)
        answer_error_codes = [c.upper() for c in answer_error_codes]

        # 2. 컨텍스트에 없는 에러 코드 감지 (Hallucination)
        context_text = " ".join([c.content for c in contexts])
        for code in answer_error_codes:
            if code not in context_text.upper():
                # 질문에 있던 코드인지 확인
                if code not in query_analysis.error_codes:
                    warnings.append(f"답변에 근거 없는 에러 코드: {code}")

        # 3. 출처 태깅
        for ctx in contexts:
            if any(phrase in answer.lower() for phrase in self._extract_key_phrases(ctx.content)):
                source = ctx.metadata.get("entity_name", ctx.metadata.get("chunk_id", "unknown"))
                evidence_sources.append(source)

        # 4. 신뢰도 계산
        if warnings:
            confidence = max(0.0, 0.5 - len(warnings) * 0.2)
            status = VerificationStatus.PARTIAL if confidence > 0.2 else VerificationStatus.UNVERIFIED
        else:
            confidence = min(1.0, len(evidence_sources) * 0.25)
            status = VerificationStatus.VERIFIED if confidence > 0.5 else VerificationStatus.PARTIAL

        return VerificationResult(
            status=status,
            confidence=confidence,
            evidence_count=len(evidence_sources),
            evidence_sources=list(set(evidence_sources)),
            warnings=warnings
        )

    def _extract_key_phrases(self, text: str, max_phrases: int = 5) -> List[str]:
        """컨텍스트에서 핵심 구문 추출 (간단 버전)"""
        # 영문/한글 핵심 단어 추출 (4글자 이상)
        words = re.findall(r'\b\w{4,}\b', text.lower())
        # 상위 빈도 단어 반환
        from collections import Counter
        common = Counter(words).most_common(max_phrases)
        return [word for word, _ in common]
```

### 4.4 Safe Response Generator

**목적:** 검증 실패 시 안전한 응답 생성

```python
class SafeResponseGenerator:
    """
    안전 응답 생성기

    상황별 응답:
        - INSUFFICIENT: 컨텍스트 부족
        - UNVERIFIED: 근거 없음
        - PARTIAL: 부분 정보
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
            return self._insufficient_response(query_analysis)

        elif verification.status == VerificationStatus.UNVERIFIED:
            return self._unverified_response(query_analysis, verification.warnings)

        else:  # PARTIAL
            return self._partial_response(verification.warnings)

    def _insufficient_response(self, query_analysis: QueryAnalysis) -> str:
        """컨텍스트 부족 응답"""
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
        warning_text = "\n".join(f"- {w}" for w in warnings)

        return (
            f"죄송합니다. 요청하신 정보에 대한 신뢰할 수 있는 "
            f"근거를 찾을 수 없습니다.\n\n"
            f"**확인된 문제:**\n{warning_text}\n\n"
            f"정확한 정보를 위해 UR5e 공식 매뉴얼이나 "
            f"Universal Robots 기술지원팀에 문의해 주세요."
        )

    def _partial_response(self, warnings: List[str]) -> str:
        """부분 정보 경고"""
        warning_text = "\n".join(f"- {w}" for w in warnings)

        return (
            f"\n\n---\n"
            f"⚠️ **주의:** 이 답변은 제한된 정보를 기반으로 합니다.\n"
            f"{warning_text}\n"
            f"정확한 정보는 공식 매뉴얼을 참조해 주세요."
        )
```

### 4.5 통합 Verifier 클래스

```python
class Verifier:
    """
    통합 검증기

    Context Verifier + Answer Verifier + Safe Response
    """

    def __init__(
        self,
        min_contexts: int = 1,
        min_relevance_score: float = 0.3,
    ):
        self.context_verifier = ContextVerifier(
            min_contexts=min_contexts,
            min_relevance_score=min_relevance_score,
        )
        self.answer_verifier = AnswerVerifier()
        self.safe_response = SafeResponseGenerator()

    def verify_before_generation(
        self,
        query_analysis: QueryAnalysis,
        contexts: List[HybridResult],
    ) -> VerificationResult:
        """생성 전 컨텍스트 검증"""
        return self.context_verifier.verify_context(query_analysis, contexts)

    def verify_after_generation(
        self,
        answer: str,
        contexts: List[HybridResult],
        query_analysis: QueryAnalysis,
    ) -> VerificationResult:
        """생성 후 답변 검증"""
        return self.answer_verifier.verify_answer(answer, contexts, query_analysis)

    def get_safe_response(
        self,
        verification: VerificationResult,
        query_analysis: QueryAnalysis,
    ) -> str:
        """안전 응답 생성"""
        return self.safe_response.generate_safe_response(verification, query_analysis)

    def add_citation(
        self,
        answer: str,
        verification: VerificationResult,
    ) -> str:
        """답변에 출처 정보 추가"""
        if not verification.evidence_sources:
            return answer

        sources = "\n".join(f"  - {s}" for s in verification.evidence_sources[:3])
        citation = (
            f"\n\n---\n"
            f"📚 **출처:**\n{sources}\n"
            f"🔒 신뢰도: {verification.confidence:.0%}"
        )

        return answer + citation
```

---

## 5. RAG Pipeline V3 통합

### 5.1 run_rag_v3.py 구조

```python
class RAGPipelineV3:
    """
    Phase 7 RAG 파이프라인 (Verifier 적용)

    Phase 6와의 차이점:
        - 생성 전 컨텍스트 검증
        - 생성 후 답변 검증
        - 안전 응답 생성
        - 출처 태깅
    """

    def __init__(self, ...):
        self.hybrid_retriever = HybridRetriever()
        self.verifier = Verifier()
        self.prompt_builder = PromptBuilder()
        self.generator = Generator()

    def query(self, question: str) -> str:
        """
        검증된 RAG 질의

        흐름:
            1. 하이브리드 검색
            2. [검증] 컨텍스트 충분성
            3. LLM 생성 (또는 안전 응답)
            4. [검증] 답변 정확성
            5. 출처 태깅
        """
        # 1. 검색
        contexts, analysis = self.hybrid_retriever.retrieve(question)

        # 2. 생성 전 검증
        pre_verification = self.verifier.verify_before_generation(analysis, contexts)

        if not pre_verification.is_safe_to_answer:
            # 안전 응답 반환
            return self.verifier.get_safe_response(pre_verification, analysis)

        # 3. LLM 생성
        messages = self.prompt_builder.build(question, contexts)
        result = self.generator.generate(messages)
        answer = result.answer

        # 4. 생성 후 검증
        post_verification = self.verifier.verify_after_generation(
            answer, contexts, analysis
        )

        # 5. 부분 검증 시 경고 추가
        if post_verification.status == VerificationStatus.PARTIAL:
            warning = self.verifier.get_safe_response(post_verification, analysis)
            answer = answer + warning

        # 6. 출처 태깅
        answer = self.verifier.add_citation(answer, post_verification)

        return answer
```

---

## 6. 예상 테스트 시나리오

### 6.1 컨텍스트 검증 테스트

| # | 질문 | 예상 검증 결과 | 예상 응답 |
|---|------|---------------|----------|
| 1 | "C999 에러 해결법" | INSUFFICIENT | "C999 정보 없음, 범위: C0~C55" |
| 2 | "C100 에러" | INSUFFICIENT | "C100 정보 없음" |
| 3 | "XYZ 부품 에러" | INSUFFICIENT | "XYZ 정보 없음" |

### 6.2 답변 검증 테스트

| # | 상황 | 예상 검증 결과 | 예상 동작 |
|---|------|---------------|----------|
| 4 | LLM이 없는 에러 코드 언급 | UNVERIFIED | 경고 메시지 추가 |
| 5 | 컨텍스트 기반 답변 | VERIFIED | 출처 태깅 |
| 6 | 부분 정보 답변 | PARTIAL | 주의 메시지 추가 |

### 6.3 정상 동작 테스트

| # | 질문 | 예상 검증 결과 | 예상 응답 |
|---|------|---------------|----------|
| 7 | "C4A15 에러 해결법" | VERIFIED | 정상 답변 + 출처 |
| 8 | "Control Box 에러 목록" | VERIFIED | 정상 답변 + 출처 |
| 9 | "Joint 3 문제 해결" | PARTIAL | 답변 + 주의 메시지 |

---

## 7. Before vs After 예상

### 7.1 존재하지 않는 에러 코드

**Before (Phase 6):**
```
질문: "C999 에러 해결법"

검색: VectorDB에서 유사 문서 반환
LLM: "C999 에러는 전원 문제입니다..." (추측)

문제: Hallucination! ❌
```

**After (Phase 7):**
```
질문: "C999 에러 해결법"

검색: 관련 정보 없음
검증: INSUFFICIENT (에러 코드 미발견)
응답: "죄송합니다. C999 에러 코드에 대한 정보를
       데이터베이스에서 찾을 수 없습니다.
       유효한 에러 코드 범위는 C0~C55입니다." ✅
```

### 7.2 정상적인 에러 코드

**Before (Phase 6):**
```
질문: "C4A15 에러 해결법"

검색: GraphDB에서 해결 방법 검색
LLM: "C4A15 에러 해결: 케이블 확인, 재부팅"

문제: 출처가 없음
```

**After (Phase 7):**
```
질문: "C4A15 에러 해결법"

검색: GraphDB에서 해결 방법 검색
검증: VERIFIED (에러 코드 발견, 해결 방법 존재)
LLM: "C4A15 에러 해결: 케이블 확인, 재부팅"

출처 추가:
---
📚 출처:
  - C4A15 (from error_C4A15)
  - Procedure_P001
🔒 신뢰도: 85% ✅
```

---

## 8. 구현 순서

### Step 1: 데이터 클래스 정의
1. VerificationStatus Enum
2. VerificationResult dataclass

### Step 2: Context Verifier
1. 컨텍스트 수 확인
2. 에러 코드 존재 확인
3. 부품명 존재 확인
4. 관련성 점수 검증

### Step 3: Answer Verifier
1. 답변 내 에러 코드 추출
2. 컨텍스트와 비교
3. Hallucination 감지

### Step 4: Safe Response Generator
1. 상황별 응답 템플릿
2. 경고 메시지 포맷팅

### Step 5: 통합 Verifier
1. 검증 흐름 통합
2. 출처 태깅 기능

### Step 6: RAG Pipeline V3
1. 검증 흐름 통합
2. 테스트

---

## 9. 체크리스트

- [ ] `src/rag/verifier.py` 구현
  - [ ] VerificationStatus, VerificationResult 정의
  - [ ] ContextVerifier 구현
  - [ ] AnswerVerifier 구현
  - [ ] SafeResponseGenerator 구현
  - [ ] Verifier 통합 클래스
- [ ] `src/rag/__init__.py` 업데이트
- [ ] `scripts/run_rag_v3.py` 구현
- [ ] 테스트 시나리오 검증 (9개)

---

## 10. 예상 비용

```
LLM 비용 변화:
├── 검증 로직: 추가 LLM 호출 없음 (규칙 기반)
├── 안전 응답: LLM 호출 생략 → 비용 절감
└── 총 비용: 동일 또는 감소

검증 오버헤드:
├── Context Verifier: ~10ms
├── Answer Verifier: ~20ms
└── 총 추가 시간: ~30ms (무시 가능)

예상 개선:
├── Hallucination 방지: 90%+
├── 잘못된 답변 감소: 80%+
└── 사용자 신뢰도 향상: +++
```

---

## 11. 참고: Hallucination이란?

### 11.1 정의

```
Hallucination (환각):
  LLM이 학습 데이터나 제공된 컨텍스트에 없는
  정보를 마치 사실인 것처럼 생성하는 현상

예시:
  컨텍스트: "C4A15는 통신 에러입니다"

  [정상 답변]
  "C4A15는 통신 에러입니다"

  [Hallucination]
  "C4A15는 통신 에러이며, C4A16은 전원 에러입니다"
                            ↑
                  컨텍스트에 없는 정보 생성!
```

### 11.2 RAG에서 Hallucination 방지 전략

```
1. 컨텍스트 기반 제약
   - 프롬프트: "제공된 정보만 사용하세요"
   - 한계: LLM이 무시할 수 있음

2. 사후 검증 (이 프로젝트)
   - 답변에서 정보 추출
   - 컨텍스트와 비교
   - 불일치 시 경고

3. 신뢰도 점수
   - 근거 수 기반 점수
   - 사용자에게 투명하게 제공
```

---

## 12. Phase 8 Preview

Phase 7 완료 후, Phase 8에서는:

```
Phase 8: 평가 시스템 (Evaluation)
├── 자동화된 품질 평가
├── 정확도/재현율 측정
├── A/B 테스트 프레임워크
└── 지속적 개선 파이프라인
```
