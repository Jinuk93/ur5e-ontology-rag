# Step 12: 응답 생성 - 설계 문서

## 1. 개요

| 항목 | 내용 |
|------|------|
| Phase | 12 - 응답 생성 (Response Generation) |
| Stage | Stage 4 (Query Engine) |
| 이전 단계 | Phase 11 - 온톨로지 추론 |
| 다음 단계 | Phase 13 - 기본 대시보드 |
| Spec 섹션 | 7.3 응답 구조 |

---

## 2. 목표

추론 결과(ReasoningResult)를 사용자에게 제공할 구조화된 응답으로 변환합니다.

### 핵심 기능
1. **LLM 기반 자연어 응답 생성** - 추론 결과를 자연어로 설명
2. **구조화된 응답 포맷** - analysis, reasoning, prediction, recommendation
3. **근거 첨부** - 온톨로지 경로 + 문서 참조
4. **ABSTAIN 케이스 처리** - 신뢰도 부족 시 "증거 부족" 응답
5. **그래프 데이터 생성** - UI 시각화용 노드/엣지 데이터

---

## 3. 산출물

| 파일 | 설명 |
|------|------|
| `src/rag/confidence_gate.py` | 신뢰도 기반 응답 검증 |
| `src/rag/prompt_builder.py` | LLM 프롬프트 구성 |
| `src/rag/response_generator.py` | 응답 생성기 |
| `src/rag/__init__.py` | 모듈 노출 (업데이트) |

---

## 4. 아키텍처

### 4.1 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Response Generation Pipeline                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [Phase 10-11 출력]                                                      │
│  ─────────────────                                                      │
│  ClassificationResult                    ReasoningResult                │
│  • query_type (ONTOLOGY/HYBRID/RAG)     • reasoning_chain               │
│  • entities                              • conclusions                   │
│  • confidence                            • predictions                   │
│                                          • recommendations               │
│                                          • ontology_paths                │
│                                          • confidence                    │
│          │                                       │                       │
│          └───────────────┬───────────────────────┘                       │
│                          │                                               │
│                          ▼                                               │
│  ┌───────────────────────────────────────────────────────────────┐      │
│  │                    ConfidenceGate                              │      │
│  │                                                                │      │
│  │  신뢰도 평가:                                                  │      │
│  │  • 추론 신뢰도 < 0.5 → ABSTAIN                                │      │
│  │  • 엔티티 없음 → ABSTAIN                                      │      │
│  │  • 근거 없음 → ABSTAIN                                        │      │
│  └───────────────────────────────────────────────────────────────┘      │
│                          │                                               │
│                ┌─────────┴─────────┐                                    │
│                │                   │                                    │
│         [ABSTAIN]           [PROCEED]                                   │
│                │                   │                                    │
│                ▼                   ▼                                    │
│  ┌─────────────────────┐  ┌───────────────────────────────────────┐    │
│  │  ABSTAIN Response   │  │              PromptBuilder             │    │
│  │  "증거 부족"        │  │                                        │    │
│  └─────────────────────┘  │  1. 시스템 프롬프트 구성               │    │
│                           │  2. 추론 결과 컨텍스트 포함            │    │
│                           │  3. 응답 포맷 지시                     │    │
│                           └───────────────────────────────────────┘    │
│                                        │                                │
│                                        ▼                                │
│                           ┌───────────────────────────────────────┐    │
│                           │           LLM (GPT-4)                  │    │
│                           │                                        │    │
│                           │  자연어 응답 생성                      │    │
│                           └───────────────────────────────────────┘    │
│                                        │                                │
│                                        ▼                                │
│                           ┌───────────────────────────────────────┐    │
│                           │         ResponseGenerator              │    │
│                           │                                        │    │
│                           │  1. 응답 구조화                        │    │
│                           │  2. 근거 첨부                          │    │
│                           │  3. 그래프 데이터 생성                 │    │
│                           └───────────────────────────────────────┘    │
│                                        │                                │
│                                        ▼                                │
│                           ┌───────────────────────────────────────┐    │
│                           │          GeneratedResponse             │    │
│                           │                                        │    │
│                           │  • trace_id                            │    │
│                           │  • answer (자연어)                     │    │
│                           │  • analysis, reasoning, prediction     │    │
│                           │  • evidence (paths + docs)             │    │
│                           │  • graph (nodes, edges)                │    │
│                           └───────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 모듈 구조

```
src/rag/
├── evidence_schema.py      # [Phase 10] Evidence 스키마
├── entity_extractor.py     # [Phase 10] 엔티티 추출
├── query_classifier.py     # [Phase 10] 질문 분류
├── confidence_gate.py      # [신규] 신뢰도 게이트
├── prompt_builder.py       # [신규] 프롬프트 구성
├── response_generator.py   # [신규] 응답 생성
└── __init__.py             # [업데이트]
```

---

## 5. 상세 설계

### 5.1 ConfidenceGate

**목적**: 응답 생성 전 신뢰도 검증, ABSTAIN 여부 결정

```python
@dataclass
class GateResult:
    """게이트 통과 결과"""
    passed: bool                    # 통과 여부
    abstain_reason: Optional[str]   # ABSTAIN 사유
    confidence: float               # 최종 신뢰도
    warnings: List[str]             # 경고 메시지

class ConfidenceGate:
    """신뢰도 기반 응답 검증"""

    # 임계값 설정
    MIN_CONFIDENCE = 0.5           # 최소 추론 신뢰도
    MIN_ENTITY_CONFIDENCE = 0.6    # 최소 엔티티 신뢰도

    def evaluate(
        self,
        classification: ClassificationResult,
        reasoning: ReasoningResult
    ) -> GateResult:
        """신뢰도 평가"""

    def _check_entity_quality(self, entities: List[ExtractedEntity]) -> Tuple[bool, str]
    def _check_reasoning_quality(self, reasoning: ReasoningResult) -> Tuple[bool, str]
    def _check_evidence_quality(self, reasoning: ReasoningResult) -> Tuple[bool, str]
```

**ABSTAIN 조건**:
| 조건 | 사유 |
|------|------|
| reasoning.confidence < 0.5 | "confidence below threshold" |
| 엔티티 없음 | "no entities extracted" |
| 온톨로지 경로 없음 | "no ontology paths found" |
| 추론 체인 비어있음 | "no reasoning chain" |

### 5.2 PromptBuilder

**목적**: LLM 프롬프트 구성

```python
class PromptBuilder:
    """LLM 프롬프트 구성기"""

    def build_prompt(
        self,
        classification: ClassificationResult,
        reasoning: ReasoningResult,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """프롬프트 구성"""

    def _build_system_prompt(self, query_type: QueryType) -> str
    def _build_context_section(self, reasoning: ReasoningResult) -> str
    def _build_instruction_section(self, query_type: QueryType) -> str
```

**프롬프트 구조**:
```
[시스템 역할]
당신은 UR5e 협동로봇과 Axia80 힘/토크 센서 전문가입니다.
온톨로지 기반 추론 결과를 사용자에게 설명합니다.

[컨텍스트]
- 질문: {query}
- 추출된 엔티티: {entities}
- 추론 결과: {reasoning_chain}
- 결론: {conclusions}
- 예측: {predictions}
- 온톨로지 경로: {ontology_paths}

[지시사항]
1. 추론 결과를 자연어로 설명
2. 핵심 정보 요약
3. 권장 조치 제시
4. 근거 명시

[응답 형식]
JSON 형태로 응답...
```

### 5.3 ResponseGenerator

**목적**: 최종 응답 생성 및 구조화

```python
@dataclass
class GeneratedResponse:
    """생성된 응답"""
    trace_id: str                           # 추적 ID
    query_type: str                         # 질문 유형
    answer: str                             # 자연어 응답
    analysis: Dict[str, Any]                # 분석 결과
    reasoning: Dict[str, Any]               # 추론 결과
    prediction: Optional[Dict[str, Any]]    # 예측 (있는 경우)
    recommendation: Dict[str, Any]          # 권장사항
    evidence: Dict[str, Any]                # 근거
    abstain: bool                           # ABSTAIN 여부
    abstain_reason: Optional[str]           # ABSTAIN 사유
    graph: Dict[str, Any]                   # 그래프 데이터

    def to_dict(self) -> Dict[str, Any]

class ResponseGenerator:
    """응답 생성기"""

    def __init__(
        self,
        confidence_gate: Optional[ConfidenceGate] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        llm_client: Optional[Any] = None
    ):
        """초기화"""

    def generate(
        self,
        classification: ClassificationResult,
        reasoning: ReasoningResult,
        context: Optional[Dict[str, Any]] = None,
        document_refs: Optional[List[DocumentReference]] = None
    ) -> GeneratedResponse:
        """응답 생성"""

    def _generate_abstain_response(
        self,
        classification: ClassificationResult,
        gate_result: GateResult
    ) -> GeneratedResponse

    def _generate_natural_response(
        self,
        classification: ClassificationResult,
        reasoning: ReasoningResult,
        context: Optional[Dict[str, Any]]
    ) -> str

    def _build_evidence(
        self,
        reasoning: ReasoningResult,
        document_refs: Optional[List[DocumentReference]]
    ) -> Dict[str, Any]

    def _build_graph_data(
        self,
        reasoning: ReasoningResult
    ) -> Dict[str, Any]
```

---

## 6. 응답 구조 (Spec 7.3 준수)

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "query_type": "ontology",

  "answer": "Fz -350N은 정상 범위(-60N~0N)를 크게 초과한 CRITICAL 상태입니다...",

  "analysis": {
    "entity": "Fz",
    "value": -350,
    "normal_range": [-60, 0],
    "state": "CRITICAL",
    "deviation": "정상 대비 약 6배"
  },

  "context": {
    "shift": "B (14:00-22:00)",
    "product": "PART-C",
    "work_phase": "pick"
  },

  "reasoning": {
    "pattern": "PAT_OVERLOAD",
    "cause": "CAUSE_GRIP_POSITION",
    "confidence": 0.85,
    "similar_events": ["EVT-003", "EVT-004", "EVT-005"]
  },

  "prediction": {
    "error_code": "C189",
    "probability": 0.85,
    "timeframe": "24시간 내"
  },

  "recommendation": {
    "immediate": "그립 위치 확인",
    "short_term": "PART-C 작업 SOP 검토",
    "reference": "Service Manual p.45"
  },

  "evidence": {
    "ontology_path": "Fz → CRITICAL → PAT_OVERLOAD → C189",
    "ontology_paths": [
      {
        "path": ["Fz", "CRITICAL", "PAT_OVERLOAD", "C189"],
        "relations": ["HAS_STATE", "INDICATES", "TRIGGERS"],
        "confidence": 0.85
      }
    ],
    "document_refs": [
      {"doc_id": "service_manual", "page": 45, "chunk_id": "SM-045-01"}
    ],
    "similar_events": ["EVT-003", "EVT-004", "EVT-005"]
  },

  "abstain": false,
  "abstain_reason": null,

  "graph": {
    "nodes": [
      {"id": "Fz", "type": "MeasurementAxis", "label": "Fz (-350N)"},
      {"id": "PAT_OVERLOAD", "type": "Pattern", "label": "과부하"},
      {"id": "C189", "type": "ErrorCode", "label": "C189"}
    ],
    "edges": [
      {"source": "Fz", "target": "PAT_OVERLOAD", "relation": "INDICATES"},
      {"source": "PAT_OVERLOAD", "target": "C189", "relation": "TRIGGERS"}
    ]
  }
}
```

### ABSTAIN 응답 예시

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440001",
  "query_type": "ontology",

  "answer": "해당 질문에 대한 충분한 근거를 찾지 못했습니다.",

  "analysis": {},
  "reasoning": {},
  "prediction": null,
  "recommendation": {
    "immediate": "질문을 더 구체적으로 해주세요.",
    "reference": null
  },

  "evidence": {
    "ontology_paths": [],
    "document_refs": []
  },

  "abstain": true,
  "abstain_reason": "confidence below threshold (0.35 < 0.5)",

  "graph": {
    "nodes": [],
    "edges": []
  }
}
```

---

## 7. LLM 연동 전략

### 7.1 LLM 없이 동작 (기본 모드)

Phase 12에서는 LLM API 없이도 동작하는 **구조화된 응답 생성**을 기본으로 합니다:

```python
def _generate_structured_response(
    self,
    classification: ClassificationResult,
    reasoning: ReasoningResult
) -> str:
    """LLM 없이 구조화된 응답 생성"""

    # 템플릿 기반 자연어 생성
    answer_parts = []

    # 상태 분석
    for conclusion in reasoning.conclusions:
        if conclusion.get("type") == "state":
            answer_parts.append(
                f"{conclusion['entity']} 값은 {conclusion['state']} 상태입니다."
            )

    # 패턴 분석
    for conclusion in reasoning.conclusions:
        if conclusion.get("type") == "pattern":
            answer_parts.append(
                f"감지된 패턴: {conclusion['pattern']}"
            )

    # 예측
    for prediction in reasoning.predictions:
        answer_parts.append(
            f"예측: {prediction['error_code']} 발생 확률 {prediction['probability']:.0%}"
        )

    # 권장사항
    for rec in reasoning.recommendations:
        answer_parts.append(f"권장: {rec.get('action', '')}")

    return " ".join(answer_parts)
```

### 7.2 LLM 연동 (선택적)

LLM API가 설정된 경우 더 자연스러운 응답 생성:

```python
def _generate_with_llm(
    self,
    prompt: str
) -> str:
    """LLM으로 자연어 응답 생성"""
    if not self.llm_client:
        return self._generate_structured_response(...)

    # OpenAI API 호출
    response = self.llm_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1000
    )
    return response.choices[0].message.content
```

---

## 8. 그래프 데이터 생성

### 8.1 노드 추출

```python
def _extract_nodes(self, reasoning: ReasoningResult) -> List[Dict]:
    """추론 결과에서 노드 추출"""
    nodes = []
    seen_ids = set()

    # 처리된 엔티티
    for entity in reasoning.entities:
        if entity["entity_id"] not in seen_ids:
            nodes.append({
                "id": entity["entity_id"],
                "type": entity["entity_type"],
                "label": entity.get("text", entity["entity_id"]),
            })
            seen_ids.add(entity["entity_id"])

    # 결론에서 추가 노드
    for conclusion in reasoning.conclusions:
        for key in ["pattern", "cause", "error", "state"]:
            if key in conclusion and conclusion[key] not in seen_ids:
                nodes.append({
                    "id": conclusion[key],
                    "type": key.capitalize(),
                    "label": conclusion[key],
                })
                seen_ids.add(conclusion[key])

    return nodes
```

### 8.2 엣지 추출

```python
def _extract_edges(self, reasoning: ReasoningResult) -> List[Dict]:
    """추론 결과에서 엣지 추출"""
    edges = []

    # 온톨로지 경로에서 엣지 추출
    for path_str in reasoning.ontology_paths:
        # "Fz →[HAS_STATE]→ CRITICAL" 형태 파싱
        parts = path_str.split(" →")
        for i, part in enumerate(parts[:-1]):
            # 관계 추출
            match = re.search(r'\[(\w+)\]', parts[i+1])
            if match:
                relation = match.group(1)
                source = part.strip()
                target = parts[i+1].split("→")[-1].strip()
                edges.append({
                    "source": source,
                    "target": target,
                    "relation": relation,
                })

    return edges
```

---

## 9. 테스트 시나리오

### 9.1 정상 응답 테스트

```python
def test_normal_response():
    """정상 응답 생성 테스트"""
    classifier = QueryClassifier()
    engine = OntologyEngine()
    generator = ResponseGenerator()

    # 질문 분류
    query = "Fz가 -350N인데 이게 뭐야?"
    classification = classifier.classify(query)

    # 추론
    entities = [e.to_dict() for e in classification.entities]
    reasoning = engine.reason(query, entities)

    # 응답 생성
    response = generator.generate(classification, reasoning)

    assert response.abstain == False
    assert response.answer != ""
    assert response.trace_id is not None
    assert "Fz" in response.analysis.get("entity", "")
    assert len(response.graph["nodes"]) > 0
```

### 9.2 ABSTAIN 테스트

```python
def test_abstain_response():
    """ABSTAIN 응답 테스트"""
    generator = ResponseGenerator()

    # 신뢰도 낮은 분류 결과
    classification = ClassificationResult(
        query="뭔가 이상해",
        query_type=QueryType.RAG,
        confidence=0.3,
        entities=[],
        indicators=[],
    )

    # 빈 추론 결과
    reasoning = ReasoningResult(
        query="뭔가 이상해",
        entities=[],
        reasoning_chain=[],
        conclusions=[],
        predictions=[],
        recommendations=[],
        ontology_paths=[],
        confidence=0.2,
    )

    response = generator.generate(classification, reasoning)

    assert response.abstain == True
    assert response.abstain_reason is not None
    assert "증거" in response.answer or "부족" in response.answer
```

---

## 10. 체크리스트

### 10.1 구현 항목

- [ ] `src/rag/confidence_gate.py` 구현
  - [ ] GateResult 데이터클래스
  - [ ] ConfidenceGate 클래스
  - [ ] 신뢰도 평가 로직
  - [ ] ABSTAIN 조건 검사
- [ ] `src/rag/prompt_builder.py` 구현
  - [ ] 시스템 프롬프트 구성
  - [ ] 컨텍스트 섹션 구성
  - [ ] 응답 지시 섹션 구성
- [ ] `src/rag/response_generator.py` 구현
  - [ ] GeneratedResponse 데이터클래스
  - [ ] ResponseGenerator 클래스
  - [ ] 구조화된 응답 생성 (LLM 없이)
  - [ ] ABSTAIN 응답 생성
  - [ ] 근거 첨부
  - [ ] 그래프 데이터 생성
- [ ] `src/rag/__init__.py` 업데이트

### 10.2 검증 항목

- [ ] 정상 응답 생성 테스트
- [ ] ABSTAIN 응답 생성 테스트
- [ ] 그래프 데이터 생성 테스트
- [ ] 근거 첨부 테스트
- [ ] Phase 10-11 연동 테스트

---

## 11. 문서 정보

| 항목 | 값 |
|------|------|
| 문서 버전 | v1.0 |
| ROADMAP 섹션 | Stage 4, Phase 12 |
| Spec 섹션 | 7.3 응답 구조 |
