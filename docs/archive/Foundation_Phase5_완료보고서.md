# Phase 5: 기본 RAG 구현 - 완료 보고서

> **목표:** 최소 동작하는 RAG 시스템(MVP)을 구현한다. 질문 → 검색 → LLM 답변 흐름.
>
> **완료일:** 2026-01-20

---

## 1. Before vs After 비교

### 1.1 파일 구조

| 항목 | Before (계획) | After (실제) | 차이점 |
|------|--------------|--------------|--------|
| `retriever.py` | VectorDB 검색 | VectorDB 검색 + RetrievalResult 클래스 | **데이터 클래스 추가** |
| `prompt_builder.py` | 프롬프트 구성 | 프롬프트 구성 + 메타데이터 포함 | **출처 정보 포맷팅** |
| `generator.py` | LLM 답변 생성 | LLM 답변 + GenerationResult + 토큰 통계 | **사용량 추적** |
| `run_rag.py` | 통합 테스트 | RAGPipeline 클래스 + 인터랙티브 모드 | **클래스화 + UI** |

### 1.2 RAG 파이프라인

| 단계 | Before (계획) | After (실제) | 상태 |
|------|--------------|--------------|------|
| Step 1: 검색 | VectorDB top-k | VectorDB top-k + 필터링 | ✅ |
| Step 2: 프롬프트 | 컨텍스트 + 질문 | 시스템 프롬프트 + 컨텍스트 + 질문 | ✅ |
| Step 3: 생성 | GPT-4o-mini | GPT-4o-mini (temperature=0.3) | ✅ |

---

## 2. 생성된 파일 및 코드 분석

### 2.1 파일 구조

```
src/rag/
├── __init__.py           ← 패키지 export
├── retriever.py          ← VectorDB 검색 (120줄)
├── prompt_builder.py     ← 프롬프트 구성 (150줄)
└── generator.py          ← LLM 답변 생성 (130줄)

scripts/
└── run_rag.py            ← RAG 파이프라인 실행 (250줄)
```

### 2.2 코드 분석: retriever.py

```python
class Retriever:
    """VectorDB 기반 검색기"""

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """
        질문과 유사한 청크 검색

        Returns:
            List[RetrievalResult]:
                - chunk_id: str
                - content: str
                - metadata: dict
                - score: float (유사도)
        """
```

### 2.3 코드 분석: prompt_builder.py

```python
SYSTEM_PROMPT = """당신은 UR5e 협동 로봇 전문 기술 지원 엔지니어입니다.

## 규칙
1. 제공된 정보만 사용하세요.
2. 모르면 "제공된 정보에서 찾을 수 없습니다"라고 답변하세요.
3. 한글로 답변하세요.
4. 구체적인 단계가 있으면 번호를 매겨 나열하세요.
5. 출처를 명시하세요."""

class PromptBuilder:
    def build(self, query: str, contexts: List[RetrievalResult]) -> List[dict]:
        """OpenAI Chat API 형식의 메시지 리스트 생성"""
```

### 2.4 코드 분석: generator.py

```python
class Generator:
    """LLM 기반 답변 생성기"""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.3):
        self.client = OpenAI()

    def generate(self, messages: List[dict]) -> GenerationResult:
        """LLM으로 답변 생성"""
```

### 2.5 코드 분석: run_rag.py

```python
class RAGPipeline:
    """RAG 파이프라인"""

    def query(self, question: str) -> str:
        # Step 1: 검색 (Retrieval)
        contexts = self.retriever.retrieve(question, top_k=5)

        # Step 2: 프롬프트 구성 (Augmentation)
        messages = self.prompt_builder.build(question, contexts)

        # Step 3: 생성 (Generation)
        result = self.generator.generate(messages)

        return result.answer
```

---

## 3. 테스트 결과

### 3.1 테스트 시나리오

| # | 질문 | 결과 | 응답 시간 |
|---|------|------|----------|
| 1 | "C4A15 에러가 발생했어요" | ❌ 정보 못 찾음 | 4.0초 |
| 2 | "로봇 캘리브레이션 방법" | ❌ 정보 못 찾음 | 3.5초 |
| 3 | "Safety Control Board 에러" | ✅ 상세 답변 | 22.1초 |

### 3.2 성공 케이스: Safety Control Board 에러

**질문:** "Safety Control Board에서 어떤 에러가 발생할 수 있나요?"

**검색 결과:**
```
1. [0.517] error_codes_C55_037 (error_code)
2. [0.507] error_codes_C51_035 (error_code)
3. [0.502] error_codes_C309_168 (error_code)
```

**생성된 답변 (요약):**
```
Safety Control Board에서 발생할 수 있는 에러:

1. C53 IO overcurrent detected
   - 제안: 모든 외부 연결 제거, 단락 확인

2. C55 Safety system error
   - 제안: (A) 보드 확인 (B) 케이블 확인 (C) 재부팅

3. C55A50 Voltage present at unpowered robot
   - 제안: Safety Control Board 교체

... (10개 이상의 에러 코드 및 해결책)
```

### 3.3 실패 케이스: C4A15 에러

**질문:** "C4A15 에러가 발생했어요. 어떻게 해결하나요?"

**검색 결과:**
```
1. [0.463] error_codes_C305_164 (error_code)  ← C4A15가 아님!
2. [0.462] error_codes_C51_035 (error_code)
3. [0.461] error_codes_C295_154 (error_code)
```

**생성된 답변:**
```
제공된 정보에서 C4A15 에러에 대한 내용은 찾을 수 없습니다.
```

**원인 분석:**
- VectorDB 의미 검색이 "C4A15"를 정확히 매칭하지 못함
- 의미적으로 유사한 다른 에러 코드가 반환됨
- **Phase 6에서 해결 예정**: 에러 코드 감지 → GraphDB 직접 검색

---

## 4. 발견된 한계 및 Phase 6 필요성

### 4.1 VectorDB 검색의 한계

```
[문제]
  질문: "C4A15 에러"
  VectorDB 검색: 의미적 유사도 기반
  결과: 다른 에러 코드 반환 (C305, C51, C295...)

[원인]
  - "C4A15"와 "C305"는 의미적으로 유사 (둘 다 에러 코드)
  - 정확한 에러 코드 매칭이 아닌 유사도 기반 검색
```

### 4.2 Phase 6에서의 해결 방향

```
[Phase 5 - 현재]
  "C4A15 에러"  →  VectorDB 의미 검색  →  ❌ 부정확

[Phase 6 - 예정]
  "C4A15 에러"
       │
       ├─→ 에러 코드 감지: "C4A15"
       │
       ├─→ GraphDB 쿼리:
       │   MATCH (e:ErrorCode {name: 'C4A15'})-[:RESOLVED_BY]->(p)
       │   RETURN e, p
       │
       └─→ ✅ 정확한 해결책 반환
```

---

## 5. 비용 분석

### 5.1 테스트 비용

```
테스트 3회 실행:
├── 테스트 1 (C4A15): 1,792 토큰
├── 테스트 2 (캘리브레이션): 907 토큰
└── 테스트 3 (Safety Board): 2,432 토큰

총 토큰: ~5,131 토큰
예상 비용: ~$0.003 (약 4원)
```

### 5.2 예상 운영 비용

```
질문당 평균:
├── 입력 토큰: ~1,500 (컨텍스트 포함)
├── 출력 토큰: ~300
├── 단가: $0.15/1M input, $0.60/1M output
└── 질문당 비용: ~$0.0004 (약 0.5원)
```

---

## 6. 핵심 개념 정리

### 6.1 RAG (Retrieval-Augmented Generation)

```
┌─────────────────────────────────────────────────────────────┐
│                       RAG 파이프라인                         │
│                                                              │
│  [질문]                                                      │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐                                            │
│  │  Retriever  │  ← VectorDB에서 유사 청크 검색             │
│  └─────────────┘                                            │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐                                            │
│  │ PromptBuilder│ ← 컨텍스트 + 질문 → 프롬프트 구성        │
│  └─────────────┘                                            │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐                                            │
│  │  Generator  │  ← LLM으로 답변 생성                       │
│  └─────────────┘                                            │
│     │                                                        │
│     ▼                                                        │
│  [답변]                                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 프롬프트 엔지니어링 핵심

| 원칙 | 적용 |
|------|------|
| **역할 부여** | "UR5e 전문 기술 지원 엔지니어" |
| **규칙 명시** | "제공된 정보만 사용", "모르면 모른다고" |
| **출력 형식** | "한글", "번호 나열", "출처 명시" |
| **컨텍스트 구조화** | 출처 정보 포함, 유사도 점수 표시 |

---

## 7. 실행 방법

### 7.1 명령어

```bash
# 단일 질문
python scripts/run_rag.py --question "Safety Control Board 에러"

# 인터랙티브 모드
python scripts/run_rag.py --mode interactive

# 테스트 시나리오
python scripts/run_rag.py --mode test
```

### 7.2 코드에서 사용

```python
from src.rag import Retriever, PromptBuilder, Generator

# 개별 컴포넌트 사용
retriever = Retriever()
builder = PromptBuilder()
generator = Generator()

# 검색
contexts = retriever.retrieve("Safety Control Board 에러", top_k=5)

# 프롬프트 구성
messages = builder.build("Safety Control Board 에러", contexts)

# 답변 생성
result = generator.generate(messages)
print(result.answer)
```

---

## 8. 완료 체크리스트

- [x] `src/rag/__init__.py` 생성
- [x] `src/rag/retriever.py` 구현 (VectorDB 검색)
- [x] `src/rag/prompt_builder.py` 구현 (프롬프트 구성)
- [x] `src/rag/generator.py` 구현 (LLM 답변 생성)
- [x] `scripts/run_rag.py` 구현 (통합 파이프라인)
- [x] 테스트 시나리오 검증
- [x] 한계점 분석 (Phase 6 필요성)

---

## 9. 현재까지 완료된 것

```
[Phase 0] 환경 설정 ✅
    └── Python, Docker, 패키지 설치

[Phase 1] PDF 분석 ✅
    └── 3개 PDF 구조 파악

[Phase 2] PDF 파싱 ✅
    └── 722개 청크 생성

[Phase 3] 임베딩 ✅
    └── ChromaDB 저장 (의미 기반 검색)

[Phase 4] 온톨로지 ✅
    └── Neo4j 저장 (325 노드, 201 관계)

[Phase 5] 기본 RAG ✅ (현재)
    └── VectorDB 검색 + LLM 답변 생성
    └── 한계 발견: 정확한 에러 코드 매칭 실패
```

---

## 10. 다음 단계 (Phase 6 예정)

### 10.1 Phase 6: 온톨로지 추론

```
목표: GraphDB를 활용한 지능적 검색

예상 작업:
1. Query Analyzer
   - 에러 코드 감지 (C4A15, C50 등)
   - 부품명 감지 (Control Box, Safety Board 등)
   - 검색 전략 결정

2. Graph Retriever
   - 에러 코드 → RESOLVED_BY → Procedure
   - 부품 → HAS_ERROR → ErrorCode

3. Hybrid Retriever
   - VectorDB + GraphDB 결과 병합
   - 중복 제거, 점수 기반 정렬
```

### 10.2 Phase 6 예상 효과

```
[Before - Phase 5]
  "C4A15 에러"  →  ❌ "정보를 찾을 수 없습니다"

[After - Phase 6]
  "C4A15 에러"  →  ✅ "케이블 확인, 재부팅 수행"
```

---

**작성일:** 2026-01-20
