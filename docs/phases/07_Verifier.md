# Phase 7: Verifier

> **상태**: ✅ 완료
> **도메인**: 검증 레이어 (Verification)
> **목표**: 근거 기반 검증 시스템 구현

---

## 1. 개요

LLM이 생성한 답변이 실제 문서에 근거하는지 검증하고,
안전 정책을 적용하여 신뢰할 수 있는 답변만 출력하도록 하는 단계.

---

## 2. 태스크

| # | 태스크 | 상태 |
|---|--------|------|
| 1 | VerificationStatus 정의 | ✅ |
| 2 | 문서 citation 검증 로직 | ✅ |
| 3 | Action 안전 정책 구현 | ✅ |
| 4 | Abstain 조건 정의 | ✅ |
| 5 | 통합 테스트 | ✅ |

---

## 3. 검증 정책

### 3.1 VerificationStatus

| 상태 | 설명 | 조건 |
|------|------|------|
| `PASS` | 검증 통과 | 답변이 문서에 근거함 |
| `ABSTAIN` | 답변 보류 | 충분한 근거 없음 |
| `FAIL` | 검증 실패 | 문서와 상충 |

### 3.2 안전 정책

```
┌─────────────────────────────────────────────────────────────┐
│                       Verifier 정책                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  규칙 1: Citation 필수                                       │
│  └─▶ Action(해결 방법)은 반드시 문서 citation 필요            │
│  └─▶ citation 없으면 해당 Action 출력 금지                    │
│                                                             │
│  규칙 2: 안전 관련 주의                                       │
│  └─▶ 안전 경고(S1xxxx) 관련 답변은 공식 매뉴얼 참조 권장       │
│  └─▶ 위험한 조작은 전문가 확인 권장 문구 추가                   │
│                                                             │
│  규칙 3: 근거 불충분시 ABSTAIN                                │
│  └─▶ 관련 문서를 찾지 못하면 "확인되지 않음" 응답               │
│  └─▶ 추측/환각(hallucination) 방지                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 구현

### 4.1 핵심 코드

**Verifier 클래스** (`src/rag/verifier.py`):
```python
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass

class VerificationStatus(Enum):
    PASS = "pass"
    ABSTAIN = "abstain"
    FAIL = "fail"

@dataclass
class VerificationResult:
    status: VerificationStatus
    confidence: float
    citations: List[str]
    warnings: List[str]
    message: Optional[str] = None

class Verifier:
    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence

    def verify(
        self,
        causes: List[str],
        actions: List[str],
        evidence: List[Evidence]
    ) -> VerificationResult:
        """답변 검증"""
        # 1. Citation 검증
        cited_actions = self._verify_citations(actions, evidence)

        # 2. 근거 점수 계산
        confidence = self._calculate_confidence(causes, actions, evidence)

        # 3. 상태 결정
        status = self._determine_status(confidence, cited_actions, actions)

        # 4. 안전 경고 생성
        warnings = self._generate_warnings(causes, actions)

        return VerificationResult(
            status=status,
            confidence=confidence,
            citations=[e.chunk_id for e in evidence if e.is_cited],
            warnings=warnings
        )

    def _verify_citations(
        self, actions: List[str], evidence: List[Evidence]
    ) -> List[str]:
        """Action에 대한 citation 확인"""
        cited_actions = []
        for action in actions:
            if self._find_evidence(action, evidence):
                cited_actions.append(action)
        return cited_actions

    def _determine_status(
        self, confidence: float, cited: List[str], total: List[str]
    ) -> VerificationStatus:
        """검증 상태 결정"""
        if confidence < self.min_confidence:
            return VerificationStatus.ABSTAIN
        if len(cited) < len(total):
            return VerificationStatus.ABSTAIN  # 일부 Action에 근거 없음
        return VerificationStatus.PASS

    def _generate_warnings(
        self, causes: List[str], actions: List[str]
    ) -> List[str]:
        """안전 경고 생성"""
        warnings = []
        for action in actions:
            if self._is_dangerous_action(action):
                warnings.append(
                    "⚠️ 이 조작은 위험할 수 있습니다. 전문가 확인을 권장합니다."
                )
        return warnings
```

### 4.2 검증 흐름

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Generator  │──▶│  Verifier   │──▶│   Output    │
│  (답변 생성) │   │  (검증)      │   │  (최종 답변) │
└─────────────┘   └──────┬──────┘   └─────────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
            ▼            ▼            ▼
        ┌──────┐    ┌──────┐    ┌──────┐
        │ PASS │    │ABSTAIN│   │ FAIL │
        └──────┘    └──────┘    └──────┘
            │            │            │
            ▼            ▼            ▼
       답변 출력     "확인 불가"    답변 차단
                     응답
```

---

## 5. 산출물

### 5.1 파일 목록

| 파일 | 내용 | Lines |
|------|------|-------|
| `src/rag/verifier.py` | 검증 모듈 | ~180 |
| `src/rag/schemas/verification.py` | 스키마 | ~50 |

### 5.2 검증 정책 설정

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| min_confidence | 0.6 | 최소 신뢰도 임계값 |
| require_citation | true | Action에 citation 필수 |
| safety_warning | true | 안전 관련 경고 활성화 |

---

## 6. 테스트 케이스

### 6.1 PASS 케이스

```python
# 답변에 문서 근거가 있는 경우
causes = ["Fan failure"]
actions = ["Check fan operation"]
evidence = [Evidence(text="Check fan operation...", score=0.9)]

result = verifier.verify(causes, actions, evidence)
assert result.status == VerificationStatus.PASS
```

### 6.2 ABSTAIN 케이스

```python
# 답변에 문서 근거가 없는 경우
causes = ["Unknown cause"]
actions = ["Replace motherboard"]
evidence = []  # 근거 없음

result = verifier.verify(causes, actions, evidence)
assert result.status == VerificationStatus.ABSTAIN
```

---

## 7. 검증 체크리스트

- [x] PASS/ABSTAIN/FAIL 상태 구현
- [x] Citation 검증 로직 동작
- [x] 안전 경고 생성 동작
- [x] 근거 없는 Action 차단

---

## 8. 다음 단계

→ [Phase 08: API 서버](08_API서버.md)

---

**Phase**: 7 / 19
**작성일**: 2026-01-22
