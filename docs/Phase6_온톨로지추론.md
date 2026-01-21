# Phase 6: 온톨로지 추론

> **목표:** GraphDB를 활용한 지능적 검색으로 RAG 정확도 향상
>
> **핵심 학습:** 엔티티 링킹, 그래프 탐색, Query Expansion
>
> **난이도:** ★★★★☆

---

## 1. Phase 5 한계 및 Phase 6 필요성

### 1.1 Phase 5에서 발견된 문제

```
[질문] "C4A15 에러가 발생했어요"

[Phase 5 - VectorDB 검색]
  검색 결과:
    1. error_codes_C305_164  ← C4A15가 아님!
    2. error_codes_C51_035
    3. error_codes_C295_154

  답변: "제공된 정보에서 C4A15를 찾을 수 없습니다" ❌
```

**원인:** VectorDB는 의미적 유사도 기반 검색이므로, "C4A15"와 "C305"를 비슷하게 인식

### 1.2 Phase 6 해결 방향

```
[질문] "C4A15 에러가 발생했어요"

[Phase 6 - 온톨로지 추론]
  1. 에러 코드 감지: "C4A15" 추출
  2. GraphDB 쿼리:
     MATCH (e:ErrorCode {name: 'C4A15'})-[:RESOLVED_BY]->(p:Procedure)
     RETURN e, p
  3. 결과:
     - "통신 케이블 확인"
     - "완전 재부팅 수행"

  답변: "C4A15 에러 해결 방법: 1) 케이블 확인 2) 재부팅" ✅
```

---

## 2. Phase 6 목표

### 2.1 전체 파이프라인

```
┌─────────────────────────────────────────────────────────────┐
│                    Phase 6 RAG Pipeline                      │
│                                                              │
│  [사용자 질문]                                               │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────┐        │
│  │            Query Analyzer (신규)                 │        │
│  │  • 에러 코드 감지 (C4A15, C50 등)               │        │
│  │  • 부품명 감지 (Control Box, Joint 등)          │        │
│  │  • 쿼리 타입 분류                               │        │
│  └─────────────────────────────────────────────────┘        │
│       │                                                      │
│       ├───────────────────┬─────────────────────┐           │
│       ▼                   ▼                     ▼           │
│  ┌──────────┐       ┌──────────┐         ┌──────────┐      │
│  │ GraphDB  │       │ VectorDB │         │ Keyword  │      │
│  │ (관계)   │       │ (의미)   │         │ (정확)   │      │
│  └──────────┘       └──────────┘         └──────────┘      │
│       │                   │                     │           │
│       └───────────────────┴─────────────────────┘           │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────┐        │
│  │            Hybrid Retriever (신규)               │        │
│  │  • 결과 병합                                     │        │
│  │  • 중복 제거                                     │        │
│  │  • 점수 기반 정렬                               │        │
│  └─────────────────────────────────────────────────┘        │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────┐        │
│  │            Context Builder (기존 확장)           │        │
│  │  • Graph 결과 포맷팅                            │        │
│  │  • Vector 결과 포맷팅                           │        │
│  └─────────────────────────────────────────────────┘        │
│                           │                                  │
│                           ▼                                  │
│                    [LLM 답변 생성]                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 핵심 컴포넌트

| 컴포넌트 | 역할 | 신규/확장 |
|---------|------|----------|
| **Query Analyzer** | 질문 분석, 엔티티 추출 | 신규 |
| **Graph Retriever** | GraphDB 검색 | 신규 |
| **Hybrid Retriever** | Vector + Graph 병합 | 신규 |
| **Context Builder** | 컨텍스트 구성 확장 | 확장 |

---

## 3. 파일 구조 (계획)

```
src/rag/
├── __init__.py
├── retriever.py           ← 기존 (VectorDB)
├── prompt_builder.py      ← 기존
├── generator.py           ← 기존
├── query_analyzer.py      ← 신규: 질문 분석
├── graph_retriever.py     ← 신규: GraphDB 검색
└── hybrid_retriever.py    ← 신규: 하이브리드 검색

scripts/
├── run_rag.py             ← 기존
└── run_rag_v2.py          ← 신규: Phase 6 버전
```

---

## 4. 상세 구현 계획

### 4.1 Query Analyzer (`query_analyzer.py`)

**목적:** 사용자 질문을 분석하여 검색 전략 결정

```python
@dataclass
class QueryAnalysis:
    """질문 분석 결과"""
    original_query: str           # 원본 질문
    error_codes: List[str]        # 감지된 에러 코드 (C4A15, C50 등)
    components: List[str]         # 감지된 부품명 (Control Box 등)
    keywords: List[str]           # 핵심 키워드
    query_type: str               # error_resolution, component_info, general
    search_strategy: str          # graph_first, vector_first, hybrid

class QueryAnalyzer:
    """질문 분석기"""

    def analyze(self, query: str) -> QueryAnalysis:
        """
        질문을 분석하여 검색 전략 결정

        1. 에러 코드 패턴 감지 (정규식)
        2. 부품명 감지 (온톨로지 매칭)
        3. 검색 전략 결정
        """
```

**에러 코드 감지 패턴:**
```python
# 에러 코드 정규식
ERROR_CODE_PATTERN = r'\b(C\d+(?:A\d+)?)\b'

# 예시
"C4A15 에러가 발생했어요" → error_codes: ["C4A15"]
"C50 또는 C51 에러" → error_codes: ["C50", "C51"]
```

**쿼리 타입 분류:**

| 쿼리 타입 | 조건 | 검색 전략 |
|----------|------|----------|
| `error_resolution` | 에러 코드 감지됨 | `graph_first` |
| `component_info` | 부품명 감지됨 | `graph_first` |
| `general` | 둘 다 없음 | `vector_first` |

### 4.2 Graph Retriever (`graph_retriever.py`)

**목적:** GraphDB(Neo4j)에서 관계 기반 검색

```python
@dataclass
class GraphResult:
    """Graph 검색 결과"""
    entity_type: str              # ErrorCode, Component, Procedure
    entity_name: str              # C4A15, Control Box 등
    related_entities: List[dict]  # 관련 엔티티
    relation_type: str            # RESOLVED_BY, HAS_ERROR 등
    source: str = "graph"

class GraphRetriever:
    """GraphDB 기반 검색기"""

    def __init__(self):
        self.graph_store = GraphStore()

    def search_error_resolution(self, error_code: str) -> List[GraphResult]:
        """
        에러 코드의 해결 방법 검색

        Cypher:
            MATCH (e:ErrorCode {name: $error_code})-[:RESOLVED_BY]->(p:Procedure)
            RETURN e, p
        """

    def search_component_errors(self, component: str) -> List[GraphResult]:
        """
        부품 관련 에러 검색

        Cypher:
            MATCH (c:Component)-[:HAS_ERROR]->(e:ErrorCode)
            WHERE c.name CONTAINS $component
            RETURN c, e
        """

    def search_error_causes(self, error_code: str) -> List[GraphResult]:
        """
        에러 원인(부품) 검색

        Cypher:
            MATCH (e:ErrorCode)-[:CAUSED_BY]->(c:Component)
            WHERE e.name = $error_code
            RETURN e, c
        """
```

### 4.3 Hybrid Retriever (`hybrid_retriever.py`)

**목적:** VectorDB + GraphDB 결과 통합

```python
@dataclass
class HybridResult:
    """하이브리드 검색 결과"""
    content: str                  # 텍스트 내용
    source_type: str              # "graph" or "vector"
    score: float                  # 관련성 점수
    metadata: dict                # 추가 정보

class HybridRetriever:
    """하이브리드 검색기"""

    def __init__(self):
        self.vector_retriever = Retriever()
        self.graph_retriever = GraphRetriever()
        self.query_analyzer = QueryAnalyzer()

    def retrieve(self, query: str, top_k: int = 5) -> List[HybridResult]:
        """
        하이브리드 검색 수행

        1. 질문 분석
        2. 검색 전략에 따라 검색
        3. 결과 병합 및 정렬
        """
        # 1. 질문 분석
        analysis = self.query_analyzer.analyze(query)

        # 2. 검색 전략 실행
        if analysis.search_strategy == "graph_first":
            results = self._search_graph_first(query, analysis, top_k)
        elif analysis.search_strategy == "vector_first":
            results = self._search_vector_first(query, analysis, top_k)
        else:
            results = self._search_hybrid(query, analysis, top_k)

        return results
```

**검색 전략별 로직:**

```python
def _search_graph_first(self, query, analysis, top_k):
    """Graph 우선 검색"""
    results = []

    # 1. Graph 검색 (에러 코드가 있으면)
    for error_code in analysis.error_codes:
        graph_results = self.graph_retriever.search_error_resolution(error_code)
        results.extend(self._convert_graph_results(graph_results))

    # 2. Vector 검색으로 보충
    if len(results) < top_k:
        vector_results = self.vector_retriever.retrieve(query, top_k - len(results))
        results.extend(self._convert_vector_results(vector_results))

    return results[:top_k]
```

---

## 5. 예상 테스트 시나리오

### 5.1 에러 코드 질문 (Graph 우선)

| # | 질문 | 분석 결과 | 예상 동작 |
|---|------|----------|----------|
| 1 | "C4A15 에러 해결법" | `error_codes=["C4A15"]` | Graph → RESOLVED_BY |
| 2 | "C50 에러가 발생했어요" | `error_codes=["C50"]` | Graph → RESOLVED_BY |
| 3 | "C4 또는 C5 에러" | `error_codes=["C4", "C5"]` | Graph → 다중 검색 |

### 5.2 부품 질문 (Graph 우선)

| # | 질문 | 분석 결과 | 예상 동작 |
|---|------|----------|----------|
| 4 | "Control Box 에러 목록" | `components=["Control Box"]` | Graph → HAS_ERROR |
| 5 | "Safety Board 문제" | `components=["Safety Board"]` | Graph → HAS_ERROR |
| 6 | "Joint 3 관련 에러" | `components=["Joint 3"]` | Graph → CAUSED_BY |

### 5.3 일반 질문 (Vector 우선)

| # | 질문 | 분석 결과 | 예상 동작 |
|---|------|----------|----------|
| 7 | "로봇이 갑자기 멈췄어요" | `query_type="general"` | Vector 검색 |
| 8 | "캘리브레이션 방법" | `query_type="general"` | Vector 검색 |
| 9 | "안전 설정" | `query_type="general"` | Vector 검색 |

---

## 6. Before vs After 예상

### 6.1 "C4A15 에러 해결법"

**Before (Phase 5):**
```
검색: VectorDB → 다른 에러 코드 반환
답변: "제공된 정보에서 찾을 수 없습니다" ❌
```

**After (Phase 6):**
```
분석: error_codes = ["C4A15"], strategy = "graph_first"
검색: GraphDB → RESOLVED_BY → Procedure
결과:
  - "Verify the communication cables are connected properly"
  - "Conduct a complete rebooting sequence"
답변: "C4A15 에러 해결 방법:
       1. 통신 케이블 연결 상태 확인
       2. 완전 재부팅 수행" ✅
```

### 6.2 "Control Box 관련 에러"

**Before (Phase 5):**
```
검색: VectorDB → 일부 관련 청크만
답변: 부분적인 정보
```

**After (Phase 6):**
```
분석: components = ["Control Box"], strategy = "graph_first"
검색: GraphDB → HAS_ERROR → ErrorCode (전체 목록)
답변: "Control Box 관련 에러 코드:
       - C4: Communication error
       - C50: Joint error
       - C55: Safety system error
       ..." ✅
```

---

## 7. 구현 순서

### Step 1: Query Analyzer
1. 에러 코드 패턴 감지 (정규식)
2. 부품명 감지 (온톨로지 매칭)
3. 쿼리 타입/전략 결정

### Step 2: Graph Retriever
1. 에러 해결 검색 (RESOLVED_BY)
2. 부품 에러 검색 (HAS_ERROR)
3. 에러 원인 검색 (CAUSED_BY)

### Step 3: Hybrid Retriever
1. 분석 결과에 따른 검색 전략 실행
2. Graph + Vector 결과 병합
3. 중복 제거 및 정렬

### Step 4: Context Builder 확장
1. Graph 결과 포맷팅
2. Vector 결과 포맷팅
3. 통합 컨텍스트 구성

### Step 5: 통합 테스트
1. 에러 코드 질문 테스트
2. 부품 질문 테스트
3. 일반 질문 테스트

---

## 8. 체크리스트

- [ ] `src/rag/query_analyzer.py` 구현
- [ ] `src/rag/graph_retriever.py` 구현
- [ ] `src/rag/hybrid_retriever.py` 구현
- [ ] `src/rag/prompt_builder.py` 확장 (Graph 결과 포맷팅)
- [ ] `scripts/run_rag_v2.py` 구현 (Phase 6 버전)
- [ ] 테스트 시나리오 검증 (9개)

---

## 9. 예상 비용

```
LLM 비용 변화 없음 (검색 로직만 개선)
GraphDB 쿼리: 무료 (로컬 Neo4j)

예상 개선:
├── 에러 코드 질문 정확도: 0% → 90%+
├── 부품 질문 정확도: 50% → 90%+
└── 일반 질문: 동일
```

---

## 10. 참고: 온톨로지 추론이란?

### 10.1 단순 검색 vs 온톨로지 추론

```
[단순 검색]
  질문 → 키워드 매칭 → 결과

[온톨로지 추론]
  질문 → 엔티티 인식 → 관계 탐색 → 추론 → 결과

  예: "C4A15 해결법"
      │
      ├─ 엔티티 인식: C4A15 = ErrorCode
      │
      ├─ 관계 탐색: ErrorCode -[RESOLVED_BY]→ Procedure
      │
      └─ 추론 결과: ["케이블 확인", "재부팅"]
```

### 10.2 이 프로젝트의 차별점

```
일반 RAG:
  질문 → VectorDB → 유사 문서 → LLM

Ontology RAG (이 프로젝트):
  질문 → 엔티티 인식 → GraphDB 추론 → VectorDB 보충 → LLM
                    ↑
             "온톨로지 우선" 철학
```