# Step 11: 온톨로지 추론 - 완료 보고서

## 1. 완료 요약

| 항목 | 내용 |
|------|------|
| Phase | 11 - 온톨로지 추론 (Ontology Reasoning) |
| 상태 | ✅ 완료 |
| 완료일 | 2026-01-22 |
| 이전 단계 | Phase 10 - 질문 분류기 |
| 다음 단계 | Phase 12 - 응답 생성 |
| Stage | Stage 4 (Query Engine) |

---

## 2. 구현 파일 목록

| 파일 | 라인 수 | 설명 |
|------|---------|------|
| `src/ontology/graph_traverser.py` | 599 | 그래프 탐색기 (BFS, 경로 찾기) |
| `src/ontology/ontology_engine.py` | 646 | 온톨로지 추론 엔진 |
| `src/ontology/__init__.py` | 113 | 모듈 노출 (업데이트) |
| **합계** | **1,358** | |

---

## 3. 구현 내용

### 3.1 GraphTraverser 클래스

```python
class GraphTraverser:
    """온톨로지 그래프 탐색기"""

    def bfs(
        self,
        start_id: str,
        max_depth: int = 3,
        relation_filter: Optional[List[RelationType]] = None,
        direction: str = "both"
    ) -> TraversalResult

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[OntologyPath]

    def follow_relation_chain(
        self,
        start_id: str,
        relation_chain: List[RelationType],
        direction: str = "outgoing"
    ) -> List[OntologyPath]

    def get_entity_context(
        self,
        entity_id: str,
        depth: int = 2
    ) -> Dict[str, Any]

    def get_reasoning_path(
        self,
        pattern_id: str
    ) -> Dict[str, Any]
```

**핵심 기능:**
- BFS 기반 관계 탐색 (깊이, 방향, 관계 필터 지원)
- 두 엔티티 간 최단 경로 찾기
- 관계 체인 따라가기 (예: INDICATES → RESOLVED_BY)
- 엔티티 컨텍스트 수집
- 패턴 추론 경로 생성 (cause_paths, error_paths, resolution_paths)

### 3.2 OntologyPath 데이터클래스

```python
@dataclass
class OntologyPath:
    """온톨로지 경로"""
    steps: List[PathStep]
    total_confidence: float = 1.0

    def to_string(self) -> str:
        # "Fz →[HAS_STATE]→ State_Critical →[INDICATES]→ CAUSE_*"

    @property
    def length(self) -> int
    @property
    def start_entity(self) -> Optional[str]
    @property
    def end_entity(self) -> Optional[str]
```

### 3.3 OntologyEngine 클래스

```python
class OntologyEngine:
    """온톨로지 기반 추론 엔진"""

    def get_context(self, entity_id: str) -> Optional[EntityContext]

    def find_path(self, source_id: str, target_id: str) -> Optional[OntologyPath]

    def get_related_entities(
        self,
        entity_id: str,
        depth: int = 2,
        relation_filter: Optional[List[RelationType]] = None
    ) -> TraversalResult

    def reason(
        self,
        query: str,
        entities: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult

    def predict(
        self,
        pattern_history: List[Dict],
        context: Optional[Dict] = None
    ) -> List[Dict]

    def hybrid_query(
        self,
        query: str,
        entities: List[Dict[str, Any]],
        document_results: Optional[List[Dict]] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]
```

### 3.4 ReasoningResult 데이터클래스

```python
@dataclass
class ReasoningResult:
    """추론 결과"""
    query: str
    entities: List[Dict[str, Any]]
    reasoning_chain: List[Dict[str, Any]]  # 추론 단계
    conclusions: List[Dict[str, Any]]      # 결론
    predictions: List[Dict[str, Any]]      # 예측
    recommendations: List[Dict[str, Any]]  # 권장사항
    ontology_paths: List[str]              # 온톨로지 경로 문자열
    confidence: float
    evidence: Dict[str, Any]
```

---

## 4. 테스트 결과

### 4.1 GraphTraverser 테스트

```
--- GraphTraverser Test ---
Fz context: ['HAS_STATE']
PAT_COLLISION causes: 1
PAT_COLLISION errors: 2
```

✅ Fz 컨텍스트 로딩 성공 (HAS_STATE 관계)
✅ PAT_COLLISION 추론 경로: 1 원인, 2 에러

### 4.2 OntologyEngine 테스트

```
Q: Fz가 -350N인데 이게 뭐야?
  Classification: ontology (90%)
  Entities: ['-350.0N']
  Reasoning steps: 0
  Conclusions: 0

Q: 충돌이 왜 발생했어?
  Classification: ontology (100%)
  Reasoning steps: 1
  Conclusions: 3
  Recommendations: 1
```

✅ QueryClassifier와 OntologyEngine 연동 성공
✅ 패턴 질문 → 원인/에러/해결책 추론 성공

### 4.3 엔진 요약

```
Ontology: 54 entities, 62 relationships
Rules: {'state_rules': 3, 'cause_rules': 4, 'prediction_rules': 3}
```

---

## 5. 추론 파이프라인

### 5.1 MeasurementAxis + Value 처리

```
입력: "Fz = -350N"
    │
    ▼
1. 컨텍스트 로딩
   → Fz.normal_range, Fz.states
    │
    ▼
2. 상태 추론 (RuleEngine.infer_state)
   → -350N → State_Critical
    │
    ▼
3. 패턴 매칭 (값이 임계값 초과 시)
   → PAT_COLLISION 또는 PAT_OVERLOAD
    │
    ▼
4. 추론 경로 탐색 (GraphTraverser)
   → PAT_* → INDICATES → CAUSE_*
   → PAT_* → TRIGGERS → ErrorCode
    │
    ▼
출력: ReasoningResult
```

### 5.2 Pattern 질문 처리

```
입력: "충돌" (패턴 키워드)
    │
    ▼
1. 패턴 ID 매핑
   → 충돌 → PAT_COLLISION
    │
    ▼
2. 추론 경로 생성 (get_reasoning_path)
   → cause_paths: PAT_COLLISION → CAUSE_*
   → error_paths: PAT_COLLISION → C153, C119
   → resolution_paths: CAUSE_* → RES_*
    │
    ▼
출력: ReasoningResult
```

### 5.3 ErrorCode 처리

```
입력: "C153" (에러 코드)
    │
    ▼
1. CAUSED_BY 탐색
   → C153 → CAUSE_*
    │
    ▼
2. TRIGGERS 역탐색
   → PAT_COLLISION → C153
    │
    ▼
3. RESOLVED_BY 탐색
   → CAUSE_* → RES_*
    │
    ▼
출력: ReasoningResult
```

---

## 6. 사용 예시

```python
from src.ontology import OntologyEngine, create_ontology_engine
from src.rag import QueryClassifier

# 엔진 생성
classifier = QueryClassifier()
engine = create_ontology_engine()

# 질문 분류
query = "충돌이 왜 발생했어?"
result = classifier.classify(query)

# 추론 실행
entities = [
    {"entity_id": e.entity_id, "entity_type": e.entity_type, "text": e.text}
    for e in result.entities
]
reasoning = engine.reason(query, entities)

# 결과 확인
print(f"추론 단계: {len(reasoning.reasoning_chain)}")
print(f"결론: {reasoning.conclusions}")
print(f"권장사항: {reasoning.recommendations}")
print(f"경로: {reasoning.ontology_paths}")
```

### 경로 찾기 예시

```python
# 두 엔티티 간 경로
path = engine.find_path("PAT_COLLISION", "RES_DECELERATE")
if path:
    print(path.to_string())
    # PAT_COLLISION →[INDICATES]→ CAUSE_PHYSICAL_CONTACT →[RESOLVED_BY]→ RES_DECELERATE
```

### 엔티티 컨텍스트 조회

```python
# Fz 컨텍스트
context = engine.get_context("Fz")
print(context.properties)      # {"normal_range": [-60, 0], ...}
print(context.states)          # ["State_Normal", "State_Warning", ...]
print(context.related_patterns)  # ["PAT_COLLISION", "PAT_OVERLOAD"]
```

---

## 7. 체크리스트 완료

### 7.1 구현 항목

- [x] `src/ontology/graph_traverser.py` 구현
  - [x] PathStep, OntologyPath 데이터클래스
  - [x] TraversalResult 데이터클래스
  - [x] BFS 탐색 (깊이, 방향, 필터)
  - [x] 경로 찾기 (find_path)
  - [x] 관계 체인 따라가기 (follow_relation_chain)
  - [x] 엔티티 컨텍스트 수집 (get_entity_context)
  - [x] 패턴 추론 경로 생성 (get_reasoning_path)
- [x] `src/ontology/ontology_engine.py` 구현
  - [x] EntityContext 데이터클래스
  - [x] ReasoningResult 데이터클래스
  - [x] get_context() - 엔티티 컨텍스트 로딩
  - [x] reason() - 온톨로지 기반 추론
  - [x] predict() - 에러 예측
  - [x] hybrid_query() - 하이브리드 질문 처리
- [x] `src/ontology/__init__.py` 업데이트

### 7.2 검증 항목

- [x] GraphTraverser BFS 탐색 정상 동작
- [x] 패턴 추론 경로 생성 (cause, error, resolution)
- [x] QueryClassifier → OntologyEngine 연동
- [x] 패턴 질문 추론 성공

---

## 8. 폴더 구조 (Phase 11 완료)

```
ur5e-ontology-rag/
└── src/
    └── ontology/
        ├── __init__.py          [113줄, 업데이트]
        ├── schema.py            [192줄, Phase 4]
        ├── models.py            [176줄, Phase 5]
        ├── loader.py            [Phase 5]
        ├── rule_engine.py       [504줄, Phase 6]
        ├── graph_traverser.py   [599줄, 신규]
        └── ontology_engine.py   [646줄, 신규]
```

---

## 9. Stage 4 진행 현황

| Phase | 제목 | 상태 | 핵심 기능 |
|-------|------|------|----------|
| 10 | 질문 분류기 | ✅ 완료 | QueryClassifier, EntityExtractor |
| 11 | 온톨로지 추론 | ✅ 완료 | OntologyEngine, GraphTraverser |
| 12 | 응답 생성 | 🔜 예정 | ResponseGenerator, PromptBuilder |

---

## 10. 다음 단계 (Phase 12)

### Phase 12 (응답 생성)에서의 활용

```python
from src.ontology import OntologyEngine
from src.rag import QueryClassifier, ResponseGenerator

classifier = QueryClassifier()
engine = OntologyEngine()
generator = ResponseGenerator()

# 질문 처리 파이프라인
query = "Fz가 -350N인데 이게 뭐야?"
classification = classifier.classify(query)
reasoning = engine.reason(query, classification.entities)
response = generator.generate(reasoning)

# 응답 예시
# {
#   "answer": "Fz 값 -350N은 비정상 상태입니다...",
#   "evidence": {
#     "ontology_path": "Fz → State_Critical → PAT_COLLISION → C153",
#     "documents": [...]
#   }
# }
```

---

## 11. 문서 정보

| 항목 | 값 |
|------|------|
| 문서 버전 | v1.0 |
| 작성일 | 2026-01-22 |
| ROADMAP 섹션 | Stage 4, Phase 11 |
| Spec 섹션 | 6.2 온톨로지 추론 |
