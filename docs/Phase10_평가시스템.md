# Phase 10: 평가 시스템 (Evaluation)

> **목표:** 자동화된 품질 평가 및 지속적 개선
>
> **핵심 학습:** RAG 평가 지표, 벤치마크, A/B 테스트
>
> **난이도:** ★★★☆☆

---

## 1. Phase 9 완료 및 Phase 10 필요성

### 1.1 Phase 9까지 완료된 상황

```
[현재 상황]
- RAG 시스템이 "잘 동작하는 것 같다"
- 하지만 정확히 얼마나 잘 동작하는지 모름
- 개선했을 때 실제로 나아졌는지 측정 불가

[문제점]
1. 정량적 평가 지표 없음
2. 버전별 성능 비교 불가
3. 회귀(regression) 감지 불가
4. 개선 우선순위 결정 어려움
```

### 1.2 Phase 10 해결 방향

```
[Phase 8 - 평가 시스템]

1. 벤치마크 데이터셋 구축
   └─ 질문-정답 쌍 (Gold Standard)

2. 자동 평가 지표
   ├─ 검색 품질: Precision, Recall, MRR
   └─ 답변 품질: 정확도, 완전성, 관련성

3. A/B 테스트 프레임워크
   └─ Phase 5 vs 6 vs 7 비교

4. 평가 리포트
   └─ 자동 생성, 시각화
```

---

## 2. Phase 10 목표

### 2.1 평가 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                   Phase 10 Evaluation System                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Benchmark Dataset (신규)                │    │
│  │  • 질문-정답 쌍 (QA pairs)                          │    │
│  │  • 에러 코드 질문, 부품 질문, 일반 질문             │    │
│  │  • 예상 검색 결과 (Expected Contexts)               │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              RAG Pipeline (V1/V2/V3)                 │    │
│  │  • Phase 5: run_rag.py                              │    │
│  │  • Phase 6: run_rag_v2.py                           │    │
│  │  • Phase 7: run_rag_v3.py                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Evaluator (신규)                        │    │
│  │  • Retrieval Metrics: Precision, Recall, MRR        │    │
│  │  • Answer Metrics: Accuracy, Completeness           │    │
│  │  • LLM-as-Judge: GPT 기반 품질 평가                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Report Generator (신규)                 │    │
│  │  • 평가 결과 JSON/Markdown                          │    │
│  │  • 버전별 비교 테이블                               │    │
│  │  • 시각화 (차트)                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 핵심 컴포넌트

| 컴포넌트 | 역할 | 신규/확장 |
|---------|------|----------|
| **Benchmark Dataset** | 평가용 질문-정답 데이터 | 신규 |
| **Evaluator** | 자동 평가 수행 | 신규 |
| **Metrics** | 평가 지표 계산 | 신규 |
| **ReportGenerator** | 평가 리포트 생성 | 신규 |

---

## 3. 파일 구조 (계획)

```
src/
├── rag/                      ← 기존
└── evaluation/               ← 신규
    ├── __init__.py
    ├── benchmark.py          ← 벤치마크 데이터셋
    ├── evaluator.py          ← 평가 실행기
    ├── metrics.py            ← 평가 지표
    └── report.py             ← 리포트 생성

data/
└── benchmark/                ← 신규
    ├── error_code_qa.json    ← 에러 코드 질문-정답
    ├── component_qa.json     ← 부품 질문-정답
    └── general_qa.json       ← 일반 질문-정답

scripts/
├── run_rag.py                ← Phase 5
├── run_rag_v2.py             ← Phase 6
├── run_rag_v3.py             ← Phase 7
└── run_evaluation.py         ← 신규: 평가 실행
```

---

## 4. 상세 구현 계획

### 4.1 벤치마크 데이터셋 (`benchmark.py`)

**목적:** 평가용 질문-정답 쌍 관리

```python
@dataclass
class BenchmarkItem:
    """벤치마크 항목"""
    id: str                          # 고유 ID
    question: str                    # 질문
    expected_answer: str             # 예상 정답
    expected_contexts: List[str]     # 예상 검색 결과 (chunk_id 또는 entity_name)
    category: str                    # 카테고리 (error_code, component, general)
    difficulty: str                  # 난이도 (easy, medium, hard)
    tags: List[str]                  # 태그

class BenchmarkDataset:
    """벤치마크 데이터셋"""

    def __init__(self, data_dir: str = "data/benchmark"):
        self.data_dir = data_dir
        self.items: List[BenchmarkItem] = []

    def load(self) -> None:
        """JSON 파일에서 벤치마크 로드"""

    def get_by_category(self, category: str) -> List[BenchmarkItem]:
        """카테고리별 항목 반환"""

    def get_by_difficulty(self, difficulty: str) -> List[BenchmarkItem]:
        """난이도별 항목 반환"""
```

**벤치마크 데이터 예시 (error_code_qa.json):**

```json
[
  {
    "id": "err_001",
    "question": "C4A15 에러가 발생했어요. 어떻게 해결하나요?",
    "expected_answer": "C4A15는 Joint 3과의 통신 손실 에러입니다. 해결 방법: 1) 통신 케이블 연결 확인, 2) 완전 재부팅 수행",
    "expected_contexts": ["C4A15", "error_codes_C4_001"],
    "category": "error_code",
    "difficulty": "easy",
    "tags": ["C4A15", "communication", "joint"]
  },
  {
    "id": "err_002",
    "question": "C50 에러 원인이 뭐예요?",
    "expected_answer": "C50은 Robot powerup issue로, Control Box의 전원 관련 문제입니다.",
    "expected_contexts": ["C50", "Control Box"],
    "category": "error_code",
    "difficulty": "easy",
    "tags": ["C50", "power", "control box"]
  },
  {
    "id": "err_003",
    "question": "C999 에러 해결법",
    "expected_answer": "C999는 유효하지 않은 에러 코드입니다. 유효 범위는 C0~C55입니다.",
    "expected_contexts": [],
    "category": "error_code",
    "difficulty": "easy",
    "tags": ["invalid", "C999"]
  }
]
```

### 4.2 평가 지표 (`metrics.py`)

**목적:** RAG 성능 평가를 위한 다양한 지표 계산

```python
@dataclass
class RetrievalMetrics:
    """검색 품질 지표"""
    precision: float      # 정밀도: 검색된 것 중 관련 있는 비율
    recall: float         # 재현율: 관련 있는 것 중 검색된 비율
    f1_score: float       # F1 점수
    mrr: float            # Mean Reciprocal Rank
    hit_rate: float       # 적어도 하나 맞춘 비율

@dataclass
class AnswerMetrics:
    """답변 품질 지표"""
    accuracy: float       # 정확도 (LLM 평가)
    completeness: float   # 완전성 (LLM 평가)
    relevance: float      # 관련성 (LLM 평가)
    faithfulness: float   # 충실도 (컨텍스트 기반 여부)

class MetricsCalculator:
    """평가 지표 계산기"""

    def calculate_retrieval_metrics(
        self,
        retrieved: List[str],
        expected: List[str],
    ) -> RetrievalMetrics:
        """
        검색 품질 지표 계산

        Args:
            retrieved: 실제 검색된 컨텍스트 ID 리스트
            expected: 예상 컨텍스트 ID 리스트

        Returns:
            RetrievalMetrics: 검색 지표
        """
        # Precision = |retrieved ∩ expected| / |retrieved|
        # Recall = |retrieved ∩ expected| / |expected|

    def calculate_answer_metrics(
        self,
        answer: str,
        expected_answer: str,
        contexts: List[str],
    ) -> AnswerMetrics:
        """
        답변 품질 지표 계산 (LLM-as-Judge)

        Args:
            answer: 생성된 답변
            expected_answer: 예상 정답
            contexts: 사용된 컨텍스트

        Returns:
            AnswerMetrics: 답변 지표
        """
```

### 4.3 LLM-as-Judge 평가

**목적:** GPT를 활용한 답변 품질 자동 평가

```python
class LLMJudge:
    """LLM 기반 답변 품질 평가"""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    def evaluate(
        self,
        question: str,
        generated_answer: str,
        expected_answer: str,
    ) -> Dict[str, float]:
        """
        LLM을 활용한 답변 품질 평가

        Returns:
            Dict with keys: accuracy, completeness, relevance
        """
        prompt = f"""
다음 질문에 대한 생성된 답변과 예상 정답을 비교하여 평가해주세요.

## 질문
{question}

## 생성된 답변
{generated_answer}

## 예상 정답
{expected_answer}

## 평가 기준 (각 0.0 ~ 1.0)
1. accuracy (정확도): 생성된 답변이 예상 정답과 얼마나 일치하는가?
2. completeness (완전성): 예상 정답의 핵심 정보가 모두 포함되어 있는가?
3. relevance (관련성): 질문에 대한 적절한 답변인가?

## 출력 형식 (JSON)
{{"accuracy": 0.0, "completeness": 0.0, "relevance": 0.0}}
"""
```

### 4.4 Evaluator (`evaluator.py`)

**목적:** 전체 평가 프로세스 실행

```python
@dataclass
class EvaluationResult:
    """단일 평가 결과"""
    benchmark_id: str
    question: str
    generated_answer: str
    expected_answer: str
    retrieved_contexts: List[str]
    expected_contexts: List[str]
    retrieval_metrics: RetrievalMetrics
    answer_metrics: AnswerMetrics
    latency_ms: float
    verification_status: str

@dataclass
class EvaluationSummary:
    """평가 요약"""
    total_items: int
    avg_retrieval_precision: float
    avg_retrieval_recall: float
    avg_answer_accuracy: float
    avg_answer_completeness: float
    avg_latency_ms: float
    by_category: Dict[str, Dict]
    by_difficulty: Dict[str, Dict]

class Evaluator:
    """RAG 평가기"""

    def __init__(self, rag_pipeline, benchmark: BenchmarkDataset):
        self.rag = rag_pipeline
        self.benchmark = benchmark
        self.metrics = MetricsCalculator()
        self.judge = LLMJudge()

    def evaluate_all(self) -> EvaluationSummary:
        """전체 벤치마크 평가"""

    def evaluate_item(self, item: BenchmarkItem) -> EvaluationResult:
        """단일 항목 평가"""

    def compare_versions(
        self,
        pipelines: Dict[str, Any],
    ) -> Dict[str, EvaluationSummary]:
        """버전별 비교 평가 (A/B 테스트)"""
```

### 4.5 Report Generator (`report.py`)

**목적:** 평가 결과 리포트 생성

```python
class ReportGenerator:
    """평가 리포트 생성기"""

    def generate_markdown(
        self,
        summary: EvaluationSummary,
        output_path: str,
    ) -> None:
        """Markdown 리포트 생성"""

    def generate_json(
        self,
        summary: EvaluationSummary,
        output_path: str,
    ) -> None:
        """JSON 리포트 생성"""

    def generate_comparison_report(
        self,
        results: Dict[str, EvaluationSummary],
        output_path: str,
    ) -> None:
        """버전 비교 리포트 생성"""
```

---

## 5. 벤치마크 데이터셋 구성

### 5.1 카테고리별 질문

| 카테고리 | 질문 수 | 예시 |
|----------|--------|------|
| **error_code** | 15개 | "C4A15 에러 해결법", "C50 원인" |
| **component** | 10개 | "Control Box 에러 목록", "Joint 3 문제" |
| **general** | 10개 | "로봇이 멈췄어요", "캘리브레이션 방법" |
| **invalid** | 5개 | "C999 에러", "C100 해결법" |
| **총합** | **40개** | |

### 5.2 난이도별 분포

| 난이도 | 설명 | 질문 수 |
|--------|------|--------|
| **easy** | 단순 에러 코드 질문 | 20개 |
| **medium** | 부품 관련, 복합 질문 | 15개 |
| **hard** | 추론 필요, 모호한 질문 | 5개 |

---

## 6. 평가 지표 상세

### 6.1 검색 품질 지표

| 지표 | 계산 방법 | 의미 |
|------|----------|------|
| **Precision** | `|retrieved ∩ expected| / |retrieved|` | 검색된 것 중 정답 비율 |
| **Recall** | `|retrieved ∩ expected| / |expected|` | 정답 중 검색된 비율 |
| **F1 Score** | `2 * P * R / (P + R)` | Precision과 Recall의 조화 평균 |
| **MRR** | `1 / rank_of_first_relevant` | 첫 번째 관련 결과의 순위 역수 |
| **Hit Rate** | `검색 성공 수 / 전체` | 적어도 하나 맞춘 비율 |

### 6.2 답변 품질 지표

| 지표 | 평가 방법 | 의미 |
|------|----------|------|
| **Accuracy** | LLM-as-Judge | 예상 정답과의 일치도 |
| **Completeness** | LLM-as-Judge | 핵심 정보 포함 여부 |
| **Relevance** | LLM-as-Judge | 질문과의 관련성 |
| **Faithfulness** | 규칙 기반 | 컨텍스트 기반 답변 여부 |

---

## 7. 예상 테스트 시나리오

### 7.1 버전별 비교 (A/B 테스트)

```
[테스트 대상]
├── Phase 5 (run_rag.py)    - VectorDB만
├── Phase 6 (run_rag_v2.py) - Hybrid (Graph + Vector)
└── Phase 7 (run_rag_v3.py) - Hybrid + Verifier

[예상 결과]
에러 코드 질문:
  Phase 5: Recall 30%, Accuracy 40%
  Phase 6: Recall 90%, Accuracy 85%
  Phase 7: Recall 90%, Accuracy 90%

일반 질문:
  Phase 5: Recall 70%, Accuracy 75%
  Phase 6: Recall 75%, Accuracy 78%
  Phase 7: Recall 75%, Accuracy 80%
```

### 7.2 카테고리별 평가

| 카테고리 | Phase 5 | Phase 6 | Phase 7 |
|----------|---------|---------|---------|
| error_code | 40% | 85% | 90% |
| component | 50% | 80% | 85% |
| general | 75% | 78% | 80% |
| invalid | 0% | 0% | 100% |

---

## 8. 리포트 예시

### 8.1 Markdown 리포트

```markdown
# RAG Evaluation Report

**Date:** 2026-01-21
**Pipeline:** Phase 7 (run_rag_v3.py)
**Benchmark:** 40 items

## Summary

| Metric | Score |
|--------|-------|
| Retrieval Precision | 0.85 |
| Retrieval Recall | 0.90 |
| Answer Accuracy | 0.88 |
| Answer Completeness | 0.82 |
| Avg Latency | 3.5s |

## By Category

| Category | Precision | Recall | Accuracy |
|----------|-----------|--------|----------|
| error_code | 0.95 | 0.92 | 0.90 |
| component | 0.80 | 0.85 | 0.85 |
| general | 0.75 | 0.80 | 0.80 |
| invalid | N/A | N/A | 1.00 |

## Version Comparison

| Version | Precision | Recall | Accuracy |
|---------|-----------|--------|----------|
| Phase 5 | 0.45 | 0.40 | 0.50 |
| Phase 6 | 0.80 | 0.85 | 0.82 |
| Phase 7 | 0.85 | 0.90 | 0.88 |
```

---

## 9. 구현 순서

### Step 1: 벤치마크 데이터셋
1. JSON 스키마 정의
2. 에러 코드 질문-정답 40개 작성
3. BenchmarkDataset 클래스 구현

### Step 2: 평가 지표
1. RetrievalMetrics 구현
2. AnswerMetrics 구현
3. LLM-as-Judge 구현

### Step 3: Evaluator
1. 단일 항목 평가
2. 전체 평가
3. 버전 비교

### Step 4: Report Generator
1. Markdown 리포트
2. JSON 리포트
3. 비교 리포트

### Step 5: 통합 테스트
1. Phase 5/6/7 비교 평가
2. 결과 분석

---

## 10. 체크리스트

- [ ] `data/benchmark/` 디렉토리 생성
  - [ ] error_code_qa.json (15개)
  - [ ] component_qa.json (10개)
  - [ ] general_qa.json (10개)
  - [ ] invalid_qa.json (5개)
- [ ] `src/evaluation/` 디렉토리 생성
  - [ ] `benchmark.py` 구현
  - [ ] `metrics.py` 구현
  - [ ] `evaluator.py` 구현
  - [ ] `report.py` 구현
- [ ] `scripts/run_evaluation.py` 구현
- [ ] Phase 5/6/7 비교 평가 실행
- [ ] 평가 리포트 생성

---

## 11. 예상 비용

```
LLM 비용 (LLM-as-Judge):
├── 벤치마크: 40개 항목
├── 버전: 3개 (Phase 5/6/7)
├── 평가당 토큰: ~500 토큰
└── 총: 40 * 3 * 500 = 60,000 토큰

예상 비용: ~$0.10 (gpt-4o-mini 기준)

실행 시간:
├── 단일 평가: ~5초
├── 전체 (40개): ~3분
└── 3버전 비교: ~10분
```

---

## 12. 참고: RAG 평가 방법론

### 12.1 RAGAS 프레임워크

```
RAGAS (Retrieval Augmented Generation Assessment):
├── Context Precision: 검색 정밀도
├── Context Recall: 검색 재현율
├── Faithfulness: 답변이 컨텍스트에 기반하는지
└── Answer Relevancy: 답변이 질문에 관련 있는지
```

### 12.2 이 프로젝트의 접근법

```
우리의 평가 시스템:
├── Retrieval Metrics (규칙 기반)
│   └── Precision, Recall, MRR
├── Answer Metrics (LLM 기반)
│   └── Accuracy, Completeness, Relevance
└── Verification Metrics (Phase 7)
    └── Hallucination Rate, Safe Response Rate
```

---

## 13. 프로젝트 완료

Phase 10은 로드맵의 마지막 단계입니다.

```
전체 로드맵 완료:
├── Phase 0-4: 기반 구축 (환경, 데이터, VectorDB, GraphDB)
├── Phase 5: 기본 RAG
├── Phase 6: 온톨로지 추론
├── Phase 7: Verifier
├── Phase 8: API 서버
├── Phase 9: UI 대시보드
└── Phase 10: 평가 시스템 ← 현재
```

Phase 10 완료 시, UR5e Ontology RAG 시스템이 완성됩니다!
