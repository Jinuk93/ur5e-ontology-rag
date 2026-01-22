# Phase 5: 기본 RAG 구현

> **목표:** 최소 동작하는 RAG 시스템(MVP)을 구현한다. 질문 → 검색 → LLM 답변 흐름.
>
> **핵심 학습:** OpenAI API 사용법, 프롬프트 엔지니어링 기초
>
> **난이도:** ★★★☆☆

---

## 1. 현재 상태 (Phase 4 완료 후)

```
┌─────────────────────────────────────────────────────────────┐
│                    구축 완료된 시스템                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [VectorDB - ChromaDB]           [GraphDB - Neo4j]          │
│  ─────────────────────           ─────────────────          │
│  • 722개 청크 저장                • 325개 노드               │
│  • 의미 기반 유사도 검색          • 201개 관계               │
│                                  • RESOLVED_BY: 144개       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**아직 없는 것:** 질문을 받아서 답변을 생성하는 시스템

---

## 2. Phase 5 목표

### 2.1 최종 목표

```
[사용자 질문]
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                     기본 RAG Pipeline                        │
│                                                              │
│  Step 1: 검색 (Retrieval)                                   │
│  ────────────────────────                                   │
│  • VectorDB에서 유사한 청크 검색                            │
│  • 상위 k개 결과 반환                                        │
│                                                              │
│  Step 2: 컨텍스트 구성 (Augmentation)                       │
│  ────────────────────────────────────                       │
│  • 검색된 청크들을 프롬프트에 포함                          │
│  • 토큰 제한 고려                                           │
│                                                              │
│  Step 3: 생성 (Generation)                                  │
│  ────────────────────────                                   │
│  • LLM에게 컨텍스트 + 질문 전달                             │
│  • 답변 생성                                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
[최종 답변]
```

### 2.2 핵심 요구사항

| 항목 | 설명 |
|------|------|
| **검색** | VectorDB에서 유사한 청크 top-k 검색 |
| **프롬프트** | 컨텍스트 + 질문을 조합한 프롬프트 |
| **LLM 호출** | OpenAI GPT-4o-mini 사용 |
| **답변 형식** | 한글 답변 + 출처 표시 |

---

## 3. 파일 구조 (계획)

```
src/rag/
├── __init__.py
├── retriever.py           ← VectorDB 검색
├── prompt_builder.py      ← 프롬프트 구성
└── generator.py           ← LLM 답변 생성

scripts/
└── run_rag.py             ← RAG 파이프라인 테스트
```

---

## 4. 상세 구현 계획

### 4.1 Retriever (`retriever.py`)

**목적:** VectorDB에서 질문과 유사한 청크 검색

```python
class Retriever:
    """VectorDB 검색기"""

    def __init__(self):
        self.vector_store = VectorStore()

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """
        질문과 유사한 청크 검색

        Args:
            query: 사용자 질문
            top_k: 반환할 결과 수

        Returns:
            List[RetrievalResult]:
                - chunk_id: str
                - content: str
                - metadata: dict
                - score: float (유사도)
        """
```

**예시:**
```
질문: "C4A15 에러가 발생했어요"

검색 결과:
1. [score: 0.92] error_codes_C4_004: "C4A15 Communication with joint 3 lost..."
2. [score: 0.85] error_codes_C4_003: "C4A14 Communication with joint 2 lost..."
3. [score: 0.78] service_manual_007: "Joint communication troubleshooting..."
```

### 4.2 Prompt Builder (`prompt_builder.py`)

**목적:** 검색 결과와 질문을 조합하여 LLM 프롬프트 생성

```python
class PromptBuilder:
    """프롬프트 구성기"""

    def build(self, query: str, contexts: List[RetrievalResult]) -> str:
        """
        LLM 입력용 프롬프트 생성

        Args:
            query: 사용자 질문
            contexts: 검색된 청크들

        Returns:
            str: 완성된 프롬프트
        """
```

**프롬프트 템플릿:**
```
당신은 UR5e 로봇 전문 기술 지원 엔지니어입니다.
아래 제공된 정보를 바탕으로 사용자의 질문에 정확하게 답변하세요.

## 규칙
1. 제공된 정보만 사용하세요.
2. 모르면 "제공된 정보에서 찾을 수 없습니다"라고 답변하세요.
3. 한글로 답변하세요.
4. 구체적인 해결 단계가 있으면 번호를 매겨 나열하세요.

## 제공된 정보
{context}

## 사용자 질문
{query}

## 답변
```

### 4.3 Generator (`generator.py`)

**목적:** LLM을 사용하여 최종 답변 생성

```python
class Generator:
    """LLM 답변 생성기"""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI()
        self.model = model

    def generate(self, prompt: str) -> str:
        """
        LLM으로 답변 생성

        Args:
            prompt: 완성된 프롬프트

        Returns:
            str: 생성된 답변
        """
```

### 4.4 RAG Pipeline 통합 (`run_rag.py`)

```python
def rag_query(question: str) -> str:
    """
    RAG 파이프라인 실행

    1. Retriever: 유사 청크 검색
    2. PromptBuilder: 프롬프트 구성
    3. Generator: LLM 답변 생성
    """
    # Step 1: 검색
    retriever = Retriever()
    contexts = retriever.retrieve(question, top_k=5)

    # Step 2: 프롬프트 구성
    builder = PromptBuilder()
    prompt = builder.build(question, contexts)

    # Step 3: LLM 답변 생성
    generator = Generator()
    answer = generator.generate(prompt)

    return answer
```

---

## 5. 테스트 시나리오

### 5.1 에러 코드 질문

| # | 질문 | 예상 동작 |
|---|------|----------|
| 1 | "C4A15 에러가 발생했어요" | 에러 설명 + 해결 방법 |
| 2 | "통신 에러가 자주 발생해요" | 관련 에러 코드들 설명 |
| 3 | "조인트 3에서 문제가 생겼어요" | 조인트 3 관련 에러/절차 |

### 5.2 사용법 질문

| # | 질문 | 예상 동작 |
|---|------|----------|
| 4 | "로봇 팔 캘리브레이션 방법" | 캘리브레이션 절차 설명 |
| 5 | "안전 설정 어떻게 해요?" | 안전 설정 관련 정보 |
| 6 | "티치 펜던트 사용법" | 티치 펜던트 조작 설명 |

### 5.3 범위 밖 질문

| # | 질문 | 예상 동작 |
|---|------|----------|
| 7 | "오늘 날씨 어때요?" | "제공된 정보에서 찾을 수 없습니다" |
| 8 | "다른 로봇 추천해줘" | "제공된 정보에서 찾을 수 없습니다" |

---

## 6. 예상 비용

```
LLM 비용 (GPT-4o-mini):
├── 입력: ~2000 토큰/질문 (컨텍스트 포함)
├── 출력: ~500 토큰/질문
├── 단가: $0.15/1M input, $0.60/1M output
└── 예상: ~$0.001/질문 (약 1.5원)

테스트 10회 기준: ~$0.01 (약 15원)
```

---

## 7. 체크리스트

- [ ] `src/rag/__init__.py` 생성
- [ ] `src/rag/retriever.py` 구현 (VectorDB 검색)
- [ ] `src/rag/prompt_builder.py` 구현 (프롬프트 구성)
- [ ] `src/rag/generator.py` 구현 (LLM 답변 생성)
- [ ] `scripts/run_rag.py` 구현 (통합 테스트)
- [ ] 테스트 시나리오 검증

---

## 8. 다음 단계 (Phase 6 예정)

Phase 5에서는 **VectorDB 검색만** 사용합니다.

Phase 6 (온톨로지 추론)에서 **GraphDB를 활용한 지능적 검색**을 추가합니다:
- 에러 코드 감지 → RESOLVED_BY 관계 탐색
- 부품명 감지 → HAS_ERROR 관계 탐색
- 검색어 확장 (Query Expansion)

```
Phase 5 (기본 RAG):
    질문 → VectorDB 검색 → LLM 답변

Phase 6 (온톨로지 추론):
    질문 → 엔티티 추출 → GraphDB 탐색 → 확장 검색 → LLM 답변
```

---

## 9. 참고: RAG란?

### 9.1 RAG = Retrieval-Augmented Generation

```
┌─────────────────────────────────────────────────────────────┐
│  기존 LLM                                                    │
│  ─────────                                                   │
│  질문 → LLM → 답변                                          │
│                                                              │
│  문제: LLM이 학습하지 않은 정보는 모름 (hallucination)       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  RAG                                                         │
│  ───                                                         │
│  질문 → [검색] → 관련 문서 → LLM → 답변                     │
│                                                              │
│  장점: 검색된 문서를 근거로 답변 (정확도 향상)              │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 왜 RAG인가?

| 방식 | 장점 | 단점 |
|------|------|------|
| **Fine-tuning** | 모델에 지식 내재화 | 비용 높음, 업데이트 어려움 |
| **RAG** | 비용 낮음, 실시간 업데이트 | 검색 품질에 의존 |

UR5e 매뉴얼처럼 **자주 업데이트되는 문서**에는 RAG가 적합합니다.

---

**작성일:** 2026-01-20
