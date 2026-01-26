# Step 10: 질문 분류기 - 완료 보고서

## 1. 완료 요약

| 항목 | 내용 |
|------|------|
| Phase | 10 - 질문 분류기 (Query Classifier) |
| 상태 | ✅ 완료 |
| 이전 단계 | Phase 09 - 온톨로지 연결 (Stage 3 완료) |
| 다음 단계 | Phase 11 - 온톨로지 추론 |
| Stage | Stage 4 (Query Engine) 시작 |

---

## 2. 구현 파일 목록

| 파일 | 라인 수 | 설명 |
|------|---------|------|
| `src/rag/evidence_schema.py` | 152 | 근거 스키마 (QueryType, Evidence 등) |
| `src/rag/entity_extractor.py` | 599 | 엔티티 추출기 (확장) |
| `src/rag/query_classifier.py` | 406 | 질문 분류기 (확장) |
| `src/rag/__init__.py` | 84 | 모듈 노출 |
| **합계** | **1,241** | |

---

## 3. 구현 내용

### 3.1 QueryType Enum

```python
class QueryType(str, Enum):
    """질문 유형"""
    ONTOLOGY = "ontology"   # 온톨로지성 질문 (관계/맥락 추론 필요)
    HYBRID = "hybrid"       # 하이브리드 질문 (온톨로지 + 문서)
    RAG = "rag"            # 일반 RAG 질문 (문서 검색만)
```

### 3.2 Evidence Schema

```python
@dataclass
class ExtractedEntity:
    """추출된 엔티티"""
    text: str               # 원본 텍스트
    entity_id: str          # 온톨로지 엔티티 ID
    entity_type: str        # 엔티티 타입
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ClassificationResult:
    """질문 분류 결과"""
    query: str
    query_type: QueryType
    confidence: float
    entities: List[ExtractedEntity]
    indicators: List[str]
    metadata: Dict[str, Any]
```

### 3.3 EntityExtractor 클래스

```python
class EntityExtractor:
    """온톨로지 엔티티 추출기"""

    # 추출 패턴
    AXIS_PATTERN = re.compile(
        r'(?<![a-zA-Z])(Fz|Fx|Fy|Tx|Ty|Tz|Mx|My|Mz)' + KOREAN_PARTICLES,
        re.IGNORECASE
    )
    VALUE_PATTERN = re.compile(r'(-?\d+(?:\.\d+)?)\s*(N|Nm|kg|mm|도|℃)?')
    ERROR_CODE_PATTERN = re.compile(r'\b(C\d{1,3})\b', re.IGNORECASE)
    TIME_PATTERN = re.compile(r'(어제|오늘|그제|아까|방금|(\d{1,2})시|(\d{1,2})분)')
    PATTERN_KEYWORDS = ["충돌", "과부하", "드리프트", "진동", ...]
    SHIFT_PATTERN = re.compile(r'(주간|야간|오전|오후|SHIFT_[ABC])')
    PRODUCT_PATTERN = re.compile(r'(PART-[A-Z]|제품[A-Z]|모델[A-Z])')

    # 모멘트 → 토크 변환 (v2.0 신규)
    MOMENT_TO_TORQUE = {"Mx": "Tx", "My": "Ty", "Mz": "Tz"}

    def extract(self, query: str) -> List[ExtractedEntity]
```

**추출 엔티티 타입:**
- `MeasurementAxis`: 센서 축 (Fz, Fx, Fy, Tx, Ty, Tz, Mx, My, Mz)
- `Value`: 수치 값 (-350N, 5kg 등)
- `ErrorCode`: 에러 코드 (C153, C119 등)
- `TimeExpression`: 시간 표현 (어제, 14시 등)
- `Pattern`: 패턴 키워드 (충돌, 과부하 등)
- `Shift`: 근무 교대 (주간, 야간, SHIFT_A 등)
- `Product`: 제품 ID (PART-A 등)
- `Joint`: 조인트 (Joint0, Joint1, ... Joint5) - v2.0 신규
- `SafetyFeature`: 안전 기능 (긴급 정지, emergency stop) - v2.0 신규

**한국어 조사 지원:**
- AXIS_PATTERN이 한국어 조사(가/이/를/은/는/도/에서/의/로)를 지원
  - 예: "Fz가 -350N" → "Fz" 추출 성공 ✅
  - 예: "Fz는 정상" → "Fz" 추출 성공 ✅
  - 예: "Tx도 확인" → "Tx" 추출 성공 ✅

**모멘트/토크 자동 변환 (v2.0 신규):**
- Mx → Tx, My → Ty, Mz → Tz 자동 변환
- 예: "Mx가 -20Nm" → entity_id: "Tx" (토크로 정규화)

**엔티티 별명 지원 (v2.0 신규):**
- Joint 별명: "Joint1" → "Joint_1", "조인트0" → "Joint_0"
- 안전 기능 별명: "긴급 정지" → "C159", "emergency stop" → "C159"

### 3.4 QueryClassifier 클래스

```python
class QueryClassifier:
    """온톨로지 기반 질문 분류기"""

    # 온톨로지성 질문 지표
    ONTOLOGY_INDICATORS = {
        "sensor_value_question": {
            "patterns": [r"(Fz|Fx|Fy|Tx|Ty|Tz).{0,20}(뭐야|뭘까|무엇|왜|이유|원인|문제)", ...],
            "weight": 0.9
        },
        "pattern_cause_question": {...},
        "prediction_request": {...},
        "state_question": {...},
        "temporal_context": {...},
        "relationship_query": {...},
    }

    # 하이브리드 질문 지표
    HYBRID_INDICATORS = {
        "error_context_question": {...},
        "resolution_context": {...},
        "comparison_question": {...},
    }

    # 일반 RAG 질문 지표
    RAG_INDICATORS = {
        "specification_question": {...},
        "procedure_question": {...},
        "definition_question": {...},
        "list_request": {...},
    }

    def classify(self, query: str) -> ClassificationResult
    def get_query_intent(self, query: str) -> Dict[str, Any]
```

---

## 4. 테스트 결과

### 4.1 분류 테스트

```
=== QueryClassifier Test ===

Q: Fz가 -350N인데 이게 뭐야?
  Type: ontology
  Confidence: 90.00%
  Indicators: ['sensor_value_question']
  Entities: Fz(MeasurementAxis), -350.0N(Value)

Q: C153 에러가 자주 발생해
  Type: hybrid
  Confidence: 80.00%
  Indicators: ['error_context_question']
  Entities: C153(ErrorCode)

Q: 어제 14시쯤 이상했는데 왜 그랬지?
  Type: ontology
  Confidence: 100.00%
  Indicators: ['temporal_context', 'sensor_value_question']
  Entities: 어제(TimeExpression), 14(TimeExpression)

Q: UR5e 페이로드가 몇 kg?
  Type: rag
  Confidence: 80.00%
  Indicators: ['specification_question']
  Entities: (없음)
```

✅ 모든 테스트 케이스 정상 분류

### 4.2 분류 기준

| 질문 유형 | 특징 | 예시 |
|----------|------|------|
| ONTOLOGY | 관계/맥락 추론 필요 | "Fz가 -350N인데 이게 뭐야?" |
| HYBRID | 온톨로지 + 문서 조합 | "C153 에러가 자주 발생해" |
| RAG | 문서 검색만 필요 | "UR5e 페이로드가 몇 kg?" |

---

## 5. 분류 알고리즘

### 5.1 점수 계산

```
1. 엔티티 추출 (EntityExtractor)
2. 지표별 패턴 매칭 및 점수 계산
   - ONTOLOGY_INDICATORS
   - HYBRID_INDICATORS
   - RAG_INDICATORS
3. 엔티티 기반 보정 (ontology_score에 보너스)
   - MeasurementAxis + Value: +0.3
   - Pattern: +0.2
   - TimeExpression: +0.15
   - Shift: +0.1
   - Product: +0.1
4. 최고 점수 유형 선택
5. 최고 점수 < 0.3이면 기본값 RAG
```

### 5.2 지표 가중치

| 지표 | 가중치 |
|------|--------|
| sensor_value_question | 0.9 |
| prediction_request | 0.9 |
| relationship_query | 0.9 |
| pattern_cause_question | 0.85 |
| temporal_context | 0.85 |
| error_context_question | 0.8 |
| state_question | 0.8 |
| specification_question | 0.8 |
| resolution_context | 0.75 |
| procedure_question | 0.75 |
| comparison_question | 0.7 |
| list_request | 0.7 |
| definition_question | 0.6 |

---

## 6. 사용 예시

```python
from src.rag import QueryClassifier, EntityExtractor, QueryType

# 질문 분류
classifier = QueryClassifier()
result = classifier.classify("Fz가 -350N인데 이게 뭐야?")
print(result.query_type)  # QueryType.ONTOLOGY
print(result.confidence)  # 0.9
print(result.entities)    # [ExtractedEntity(Fz), ExtractedEntity(-350N)]
print(result.indicators)  # ['sensor_value_question']

# 엔티티 추출만
extractor = EntityExtractor()
entities = extractor.extract("C153 에러가 발생했어")
print(entities)  # [ExtractedEntity(C153)]

# 의도 분석
intent = classifier.get_query_intent("충돌이 왜 발생했어?")
print(intent["sub_intent"])  # 'cause_analysis'
```

---

## 7. 체크리스트 완료

### 7.1 구현 항목

- [x] `src/rag/evidence_schema.py` 구현
  - [x] QueryType Enum
  - [x] ExtractedEntity 데이터클래스
  - [x] DocumentReference 데이터클래스
  - [x] OntologyPath 데이터클래스
  - [x] Evidence 데이터클래스
  - [x] ClassificationResult 데이터클래스
- [x] `src/rag/entity_extractor.py` 구현 (599줄로 확장)
  - [x] 센서 축 추출 (Fz, Fx, ...)
  - [x] 모멘트 축 추출 및 변환 (Mx→Tx, My→Ty, Mz→Tz) - v2.0 신규
  - [x] 수치 값 추출 (-350N, 5kg, ...)
  - [x] 에러 코드 추출 (C153, ...)
  - [x] 시간 표현 추출 (어제, 14시, ...)
  - [x] 패턴 키워드 추출 (충돌, 과부하, ...)
  - [x] Shift 추출 (주간, 야간, ...)
  - [x] 제품 ID 추출 (PART-A, ...)
  - [x] Joint 별명 지원 (Joint1→Joint_1) - v2.0 신규
  - [x] 안전 기능 별명 지원 (긴급 정지→C159) - v2.0 신규
- [x] `src/rag/query_classifier.py` 구현
  - [x] ONTOLOGY 지표 패턴
  - [x] HYBRID 지표 패턴
  - [x] RAG 지표 패턴
  - [x] classify() 메서드
  - [x] get_query_intent() 메서드
- [x] `src/rag/__init__.py` 업데이트

### 7.2 검증 항목

- [x] ONTOLOGY 질문 분류 정확성
- [x] HYBRID 질문 분류 정확성
- [x] RAG 질문 분류 정확성
- [x] 엔티티 추출 정확성

---

## 8. 폴더 구조 (Phase 10 완료)

```
ur5e-ontology-rag/
└── src/
    └── rag/
        ├── __init__.py          [52줄, 업데이트]
        ├── evidence_schema.py   [152줄, 신규]
        ├── entity_extractor.py  [599줄, 확장]
        └── query_classifier.py  [352줄, 신규]
```

---

## 9. 다음 단계 (Phase 11)

### Phase 11 (온톨로지 추론)에서의 활용

```python
from src.rag import QueryClassifier, QueryType
from src.ontology import OntologyEngine, create_ontology_engine

classifier = QueryClassifier()
engine = create_ontology_engine()

# 질문 분류
result = classifier.classify(user_query)

# 엔티티 변환
entities = [
    {"entity_id": e.entity_id, "entity_type": e.entity_type, "text": e.text}
    for e in result.entities
]

# 분류 결과에 따른 처리
if result.query_type == QueryType.ONTOLOGY:
    # 온톨로지 기반 추론
    reasoning = engine.reason(user_query, entities)
elif result.query_type == QueryType.HYBRID:
    # 온톨로지 + 문서 조합
    reasoning = engine.hybrid_query(user_query, entities, document_results)
else:  # RAG
    # 문서 검색만
    answer = rag_search(user_query)
```

### Phase 11 구현 예정 파일

- `src/ontology/ontology_engine.py` - 온톨로지 추론 엔진
- `src/ontology/graph_traverser.py` - 그래프 탐색기

---

## 10. 문서 정보

| 항목 | 값 |
|------|------|
| 문서 버전 | v2.0 |
| ROADMAP 섹션 | Stage 4, Phase 10 |
| Spec 섹션 | 7.1 질문 분류 |
| 최종 업데이트 | 2026-01-26 |

### 10.1 v2.0 변경 사항

- `entity_extractor.py` 라인 수: 323 → 599
- AXIS_PATTERN에 Mx/My/Mz 추가
- MOMENT_TO_TORQUE 매핑 추가 (모멘트→토크 변환)
- Joint 별명 지원 (Joint0~5, 조인트0~5)
- 안전 기능 별명 지원 (긴급 정지 → C159)
