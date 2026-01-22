# Phase 10: 평가 시스템 (Evaluation System)

> **목표:** 자동화된 품질 평가 및 성능 측정
>
> **핵심 학습:** RAG 평가 지표, 벤치마크, LLM-as-Judge
>
> **난이도:** ★★★☆☆

---

## 1. 현재 상태 및 Phase 10 필요성

### 1.1 Phase 1~9 완료 현황

```
✅ Phase 0: 개발 환경 설정
✅ Phase 1: 데이터 탐색
✅ Phase 2: PDF 파싱 & 청킹
✅ Phase 3: 벡터DB 인덱싱 (ChromaDB)
✅ Phase 4: 온톨로지 설계 (Neo4j)
✅ Phase 5: 기본 RAG 구현 (VectorDB Only)
✅ Phase 6: 온톨로지 추론 (Hybrid RAG)
✅ Phase 7: Verifier 구현 (환각 방지)
✅ Phase 8: API 서버 구축 (FastAPI)
✅ Phase 9: UI 대시보드 (Streamlit)
```

### 1.2 Phase 9에서 구현된 평가 관련 기능

Phase 9 대시보드의 **성능 평가 (Performance)** 페이지에 포함된 기능:

| 기능 | 설명 | 상태 |
|------|------|------|
| KPI 게이지 차트 | 정확도, 환각방지율, 재현율 표시 | ✅ UI만 구현 (데이터 하드코딩) |
| Phase 비교 테이블 | Phase 5/6/7/8 성능 비교 | ✅ UI만 구현 (데이터 하드코딩) |
| 벤치마크 테스트 버튼 | 5개 테스트 케이스 실행 | ✅ 구현됨 (API 호출) |
| 커스텀 테스트 | 사용자 정의 테스트 | ✅ 구현됨 |

### 1.3 Phase 10에서 추가로 구현할 것

```
[Phase 9에서 미완성된 부분]
├── 벤치마크 데이터셋이 5개뿐 → 40개 이상으로 확장
├── 평가 지표가 하드코딩됨 → 실제 계산 로직 필요
├── Phase 비교가 수동 → 자동화 필요
└── 평가 결과 저장 안됨 → 히스토리 관리 필요

[Phase 10 목표]
├── 벤치마크 데이터셋 40개 구축
├── 자동 평가 파이프라인 구현
├── LLM-as-Judge 평가 구현
├── Phase 5/6/7 자동 비교
└── 평가 리포트 자동 생성
```

---

## 2. Phase 10 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     Phase 10 평가 시스템                          │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  1. 벤치마크 데이터셋                        │  │
│  │  data/benchmark/                                           │  │
│  │  ├── error_code_qa.json   (15개) 에러코드 질문              │  │
│  │  ├── component_qa.json    (10개) 부품 관련 질문             │  │
│  │  ├── general_qa.json      (10개) 일반 질문                  │  │
│  │  └── invalid_qa.json      (5개)  잘못된 에러코드 질문       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  2. RAG 파이프라인 (테스트 대상)             │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │  Phase 5    │  │  Phase 6    │  │  Phase 7    │        │  │
│  │  │ VectorOnly  │  │   Hybrid    │  │  +Verifier  │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  3. 평가기 (Evaluator)                      │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ 검색 품질 평가 (Retrieval Metrics)                    │  │  │
│  │  │ • Precision: 검색된 것 중 정답 비율                   │  │  │
│  │  │ • Recall: 정답 중 검색된 비율                        │  │  │
│  │  │ • MRR: 첫 번째 정답의 순위                          │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ 답변 품질 평가 (Answer Metrics) - LLM-as-Judge       │  │  │
│  │  │ • Accuracy: 예상 정답과의 일치도                     │  │  │
│  │  │ • Completeness: 핵심 정보 포함 여부                  │  │  │
│  │  │ • Relevance: 질문과의 관련성                        │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ 검증 품질 평가 (Verification Metrics)                 │  │  │
│  │  │ • Hallucination Rate: 환각 발생률                    │  │  │
│  │  │ • Safe Response Rate: 안전 응답률                    │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  4. 리포트 생성기                           │  │
│  │                                                            │  │
│  │  • Markdown 리포트 (docs/Phase10_평가결과.md)             │  │
│  │  • JSON 데이터 (data/evaluation/results.json)             │  │
│  │  • 대시보드 연동 (Performance 페이지 데이터)               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 파일 구조

```
src/
├── rag/                          ← 기존 (Phase 5-7)
│   ├── pipeline.py
│   ├── analyzer.py
│   ├── retriever.py
│   ├── generator.py
│   └── verifier.py
│
└── evaluation/                    ← 신규 (Phase 10)
    ├── __init__.py
    ├── benchmark.py               ← 벤치마크 데이터셋 로더
    ├── metrics.py                 ← 평가 지표 계산
    ├── llm_judge.py               ← LLM 기반 답변 평가
    ├── evaluator.py               ← 평가 실행기
    └── report.py                  ← 리포트 생성기

data/
├── benchmark/                     ← 신규 (평가 데이터)
│   ├── error_code_qa.json         ← 에러코드 질문-정답 15개
│   ├── component_qa.json          ← 부품 질문-정답 10개
│   ├── general_qa.json            ← 일반 질문-정답 10개
│   └── invalid_qa.json            ← 잘못된 에러코드 5개
│
└── evaluation/                    ← 신규 (평가 결과)
    └── results/
        ├── eval_2024-01-21_phase5.json
        ├── eval_2024-01-21_phase6.json
        └── eval_2024-01-21_phase7.json

scripts/
├── run_rag.py                     ← Phase 5 (기존)
├── run_rag_v2.py                  ← Phase 6 (기존)
├── run_rag_v3.py                  ← Phase 7 (기존)
└── run_evaluation.py              ← 신규: 평가 실행

docs/
└── Phase10_평가결과.md             ← 신규: 자동 생성 리포트
```

---

## 4. 벤치마크 데이터셋 설계

### 4.1 데이터 스키마

```json
{
  "id": "err_001",
  "question": "C4A15 에러가 발생했습니다. 해결 방법을 알려주세요.",
  "expected_answer": "C4A15는 Joint 3과의 통신 손실 에러입니다. 해결 방법: 1) 통신 케이블 연결 확인, 2) 완전 재부팅 수행",
  "expected_contexts": ["C4A15", "Joint 3"],
  "category": "error_code",
  "difficulty": "easy",
  "expected_verification": "verified",
  "tags": ["C4A15", "communication", "joint"]
}
```

### 4.2 카테고리별 질문 구성 (40개)

| 카테고리 | 수량 | 예시 질문 | 예상 검증 결과 |
|----------|------|-----------|---------------|
| **error_code** | 15개 | "C4A15 에러 해결법" | VERIFIED |
| **component** | 10개 | "Control Box에서 발생하는 에러 목록" | VERIFIED |
| **general** | 10개 | "로봇이 갑자기 멈췄어요" | PARTIAL |
| **invalid** | 5개 | "C999 에러 해결법" | INSUFFICIENT |

### 4.3 난이도별 분포

| 난이도 | 설명 | 수량 |
|--------|------|------|
| **easy** | 단일 에러코드 직접 질문 | 20개 |
| **medium** | 부품 관련 복합 질문 | 15개 |
| **hard** | 증상 기반 추론 필요 | 5개 |

---

## 5. 평가 지표 상세

### 5.1 검색 품질 지표 (Retrieval Metrics)

```python
@dataclass
class RetrievalMetrics:
    precision: float    # |검색 ∩ 정답| / |검색|
    recall: float       # |검색 ∩ 정답| / |정답|
    f1_score: float     # 2 * P * R / (P + R)
    mrr: float          # 1 / (첫 번째 정답 순위)
    hit_rate: float     # 적어도 하나 맞춘 비율
```

| 지표 | 계산 방법 | 의미 | 목표 |
|------|----------|------|------|
| Precision | 검색된 것 중 정답 비율 | 검색 정확도 | 0.80+ |
| Recall | 정답 중 검색된 비율 | 검색 완전성 | 0.85+ |
| F1 Score | Precision과 Recall의 조화 평균 | 종합 지표 | 0.80+ |
| MRR | 첫 번째 정답의 역순위 | 검색 순위 품질 | 0.70+ |
| Hit Rate | 하나라도 맞춘 비율 | 기본 성공률 | 0.90+ |

### 5.2 답변 품질 지표 (Answer Metrics) - LLM-as-Judge

```python
@dataclass
class AnswerMetrics:
    accuracy: float      # 예상 정답과의 일치도
    completeness: float  # 핵심 정보 포함 여부
    relevance: float     # 질문과의 관련성
    faithfulness: float  # 컨텍스트 기반 여부
```

| 지표 | 평가 방법 | 의미 | 목표 |
|------|----------|------|------|
| Accuracy | LLM 평가 | 정답과 일치하는가 | 0.85+ |
| Completeness | LLM 평가 | 필요한 정보가 모두 있는가 | 0.80+ |
| Relevance | LLM 평가 | 질문에 적절한 답변인가 | 0.90+ |
| Faithfulness | 규칙 기반 | 컨텍스트에 근거하는가 | 0.95+ |

### 5.3 검증 품질 지표 (Verification Metrics)

```python
@dataclass
class VerificationMetrics:
    hallucination_rate: float    # 환각 발생률 (낮을수록 좋음)
    safe_response_rate: float    # 안전 응답률 (INSUFFICIENT 정상 반환)
    verification_accuracy: float # 검증 결과 정확도
```

| 지표 | 계산 방법 | 의미 | 목표 |
|------|----------|------|------|
| Hallucination Rate | 잘못된 에러코드 답변 / 전체 | 환각 발생률 | <5% |
| Safe Response Rate | INSUFFICIENT 정상 반환율 | 안전 응답률 | 100% |
| Verification Accuracy | 검증 결과 정확도 | 검증 시스템 성능 | 95%+ |

---

## 6. 구현 계획

### 6.1 Step 1: 벤치마크 데이터셋 구축

**파일:** `data/benchmark/*.json`, `src/evaluation/benchmark.py`

```python
# src/evaluation/benchmark.py

@dataclass
class BenchmarkItem:
    """벤치마크 항목"""
    id: str
    question: str
    expected_answer: str
    expected_contexts: List[str]
    category: str
    difficulty: str
    expected_verification: str
    tags: List[str]

class BenchmarkDataset:
    """벤치마크 데이터셋 관리"""

    def load(self, data_dir: str = "data/benchmark") -> List[BenchmarkItem]:
        """JSON 파일들에서 벤치마크 로드"""

    def get_by_category(self, category: str) -> List[BenchmarkItem]:
        """카테고리별 필터링"""

    def get_by_difficulty(self, difficulty: str) -> List[BenchmarkItem]:
        """난이도별 필터링"""
```

### 6.2 Step 2: 평가 지표 계산기

**파일:** `src/evaluation/metrics.py`

```python
# src/evaluation/metrics.py

class MetricsCalculator:
    """평가 지표 계산기"""

    def calculate_retrieval_metrics(
        self,
        retrieved: List[str],
        expected: List[str],
    ) -> RetrievalMetrics:
        """검색 품질 지표 계산"""

    def calculate_precision(self, retrieved: Set, expected: Set) -> float:
        """Precision = |검색 ∩ 정답| / |검색|"""
        if len(retrieved) == 0:
            return 0.0
        intersection = retrieved.intersection(expected)
        return len(intersection) / len(retrieved)

    def calculate_recall(self, retrieved: Set, expected: Set) -> float:
        """Recall = |검색 ∩ 정답| / |정답|"""
        if len(expected) == 0:
            return 1.0  # 정답이 없으면 Recall은 1
        intersection = retrieved.intersection(expected)
        return len(intersection) / len(expected)
```

### 6.3 Step 3: LLM-as-Judge

**파일:** `src/evaluation/llm_judge.py`

```python
# src/evaluation/llm_judge.py

class LLMJudge:
    """LLM 기반 답변 품질 평가"""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI()
        self.model = model

    def evaluate(
        self,
        question: str,
        generated_answer: str,
        expected_answer: str,
    ) -> AnswerMetrics:
        """LLM을 활용한 답변 품질 평가"""

        prompt = f"""
다음 질문에 대한 생성된 답변과 예상 정답을 비교하여 평가해주세요.

## 질문
{question}

## 생성된 답변
{generated_answer}

## 예상 정답
{expected_answer}

## 평가 기준 (각 0.0 ~ 1.0 점수)
1. accuracy: 생성된 답변이 예상 정답과 얼마나 일치하는가?
2. completeness: 예상 정답의 핵심 정보가 모두 포함되어 있는가?
3. relevance: 질문에 대한 적절한 답변인가?

## 출력 (JSON만)
{{"accuracy": 0.0, "completeness": 0.0, "relevance": 0.0}}
"""
        # LLM 호출 및 결과 파싱
```

### 6.4 Step 4: 평가 실행기

**파일:** `src/evaluation/evaluator.py`

```python
# src/evaluation/evaluator.py

@dataclass
class EvaluationResult:
    """단일 항목 평가 결과"""
    benchmark_id: str
    question: str
    generated_answer: str
    expected_answer: str
    retrieval_metrics: RetrievalMetrics
    answer_metrics: AnswerMetrics
    verification_status: str
    expected_verification: str
    latency_ms: float
    passed: bool

@dataclass
class EvaluationSummary:
    """전체 평가 요약"""
    total_items: int
    passed_items: int
    pass_rate: float
    avg_precision: float
    avg_recall: float
    avg_accuracy: float
    avg_completeness: float
    avg_latency_ms: float
    hallucination_rate: float
    by_category: Dict[str, Dict]
    by_difficulty: Dict[str, Dict]

class Evaluator:
    """RAG 평가기"""

    def __init__(
        self,
        rag_pipeline,
        benchmark: BenchmarkDataset,
    ):
        self.rag = rag_pipeline
        self.benchmark = benchmark
        self.metrics = MetricsCalculator()
        self.judge = LLMJudge()

    def evaluate_all(self) -> EvaluationSummary:
        """전체 벤치마크 평가 실행"""

    def evaluate_item(self, item: BenchmarkItem) -> EvaluationResult:
        """단일 항목 평가"""

    def compare_pipelines(
        self,
        pipelines: Dict[str, Any],
    ) -> Dict[str, EvaluationSummary]:
        """여러 파이프라인 비교 평가 (A/B 테스트)"""
```

### 6.5 Step 5: 리포트 생성기

**파일:** `src/evaluation/report.py`

```python
# src/evaluation/report.py

class ReportGenerator:
    """평가 리포트 생성기"""

    def generate_markdown(
        self,
        summary: EvaluationSummary,
        output_path: str,
    ) -> None:
        """Markdown 리포트 생성"""

    def generate_comparison_report(
        self,
        results: Dict[str, EvaluationSummary],
        output_path: str,
    ) -> None:
        """버전 비교 리포트 생성"""
```

### 6.6 Step 6: 실행 스크립트

**파일:** `scripts/run_evaluation.py`

```python
# scripts/run_evaluation.py

"""
평가 시스템 실행 스크립트

사용법:
    # 단일 버전 평가
    python scripts/run_evaluation.py --version v3

    # 전체 버전 비교
    python scripts/run_evaluation.py --compare

    # 카테고리별 평가
    python scripts/run_evaluation.py --category error_code
"""
```

---

## 7. 예상 결과

### 7.1 Phase별 예상 성능

| 지표 | Phase 5 (Vector) | Phase 6 (Hybrid) | Phase 7 (Verifier) |
|------|-----------------|------------------|-------------------|
| **Precision** | 0.45 | 0.80 | 0.85 |
| **Recall** | 0.40 | 0.85 | 0.90 |
| **Accuracy** | 0.50 | 0.82 | 0.88 |
| **Hallucination Rate** | 100% | 55% | <5% |
| **Avg Latency** | 2.0s | 3.5s | 4.0s |

### 7.2 카테고리별 예상 성능 (Phase 7 기준)

| 카테고리 | Precision | Recall | Accuracy | 설명 |
|----------|-----------|--------|----------|------|
| error_code | 0.95 | 0.92 | 0.90 | 그래프DB 직접 검색 |
| component | 0.85 | 0.88 | 0.85 | 관계 탐색 필요 |
| general | 0.70 | 0.75 | 0.78 | 벡터 검색 의존 |
| invalid | N/A | N/A | 1.00 | INSUFFICIENT 반환 |

---

## 8. 대시보드 연동

### 8.1 Performance 페이지 데이터 연동

Phase 10 평가 결과를 Phase 9 대시보드의 **성능 평가** 페이지에 연동:

```python
# src/dashboard/pages/performance.py 수정

def load_evaluation_results():
    """평가 결과 JSON에서 데이터 로드"""
    results_path = "data/evaluation/results/latest.json"
    if os.path.exists(results_path):
        with open(results_path) as f:
            return json.load(f)
    return None

def render_performance():
    # 기존 하드코딩된 데이터 대신 실제 평가 결과 사용
    results = load_evaluation_results()
    if results:
        # 실제 데이터로 차트/테이블 렌더링
    else:
        # 기존 플레이스홀더 표시
```

---

## 9. 구현 순서 및 체크리스트

### Step 1: 벤치마크 데이터셋 (1-2일)
- [ ] `data/benchmark/` 디렉토리 생성
- [ ] `error_code_qa.json` 작성 (15개)
- [ ] `component_qa.json` 작성 (10개)
- [ ] `general_qa.json` 작성 (10개)
- [ ] `invalid_qa.json` 작성 (5개)
- [ ] `src/evaluation/benchmark.py` 구현

### Step 2: 평가 지표 (0.5일)
- [ ] `src/evaluation/metrics.py` 구현
- [ ] RetrievalMetrics 계산 로직
- [ ] AnswerMetrics 계산 로직
- [ ] 단위 테스트

### Step 3: LLM-as-Judge (0.5일)
- [ ] `src/evaluation/llm_judge.py` 구현
- [ ] 평가 프롬프트 설계
- [ ] JSON 파싱 로직
- [ ] 테스트

### Step 4: Evaluator (1일)
- [ ] `src/evaluation/evaluator.py` 구현
- [ ] 단일 항목 평가
- [ ] 전체 평가
- [ ] 버전 비교 평가

### Step 5: 리포트 생성 (0.5일)
- [ ] `src/evaluation/report.py` 구현
- [ ] Markdown 리포트 템플릿
- [ ] JSON 결과 저장

### Step 6: 실행 및 통합 (1일)
- [ ] `scripts/run_evaluation.py` 구현
- [ ] Phase 5/6/7 비교 평가 실행
- [ ] 대시보드 연동
- [ ] 평가 결과 문서화

---

## 10. 예상 비용 및 시간

### 10.1 LLM 비용

```
LLM-as-Judge 비용:
├── 벤치마크: 40개 항목
├── 버전: 3개 (Phase 5/6/7)
├── 평가당 토큰: ~800 토큰 (입력 600 + 출력 200)
└── 총 토큰: 40 × 3 × 800 = 96,000 토큰

예상 비용 (gpt-4o-mini):
├── 입력: 72,000 × $0.15/1M = $0.01
├── 출력: 24,000 × $0.60/1M = $0.01
└── 총: ~$0.02
```

### 10.2 실행 시간

```
평가 실행 시간:
├── 단일 항목 평가: ~5초 (RAG 3초 + Judge 2초)
├── 전체 40개: ~3분 20초
├── 3버전 비교: ~10분
└── 리포트 생성: ~10초
```

---

## 11. 완료 기준

Phase 10 완료 조건:

1. **벤치마크 데이터셋**: 40개 질문-정답 쌍 구축
2. **자동 평가**: `python scripts/run_evaluation.py` 실행 가능
3. **성능 측정**: Phase 5/6/7 정량적 비교 완료
4. **목표 달성**:
   - Phase 7 Precision: 0.80+
   - Phase 7 Accuracy: 0.85+
   - Phase 7 Hallucination Rate: <5%
5. **문서화**: 평가 결과 리포트 생성

---

## 12. Phase 10 완료 시 전체 프로젝트 완성

```
UR5e Ontology RAG 프로젝트 완성!

[구축된 시스템]
├── 📄 PDF 파싱 파이프라인 (Phase 2)
├── 🗄️ VectorDB 인덱싱 (Phase 3)
├── 🕸️ 지식그래프 온톨로지 (Phase 4)
├── 🤖 기본 RAG (Phase 5)
├── 🔍 Hybrid RAG + 온톨로지 추론 (Phase 6)
├── ✅ Verifier 환각 방지 (Phase 7)
├── 🌐 FastAPI 서버 (Phase 8)
├── 📊 Streamlit 대시보드 (Phase 9)
└── 📈 자동 평가 시스템 (Phase 10)

[달성한 성능]
├── 정확도: 85%+
├── 환각 방지율: 95%+
├── 응답 시간: 4초 이내
└── 사용자 친화적 한글 UI
```
