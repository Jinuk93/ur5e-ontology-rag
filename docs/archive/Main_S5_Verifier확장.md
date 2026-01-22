# Main-S5: Verifier 확장

> **Phase**: Main-S5 (센서 통합 Phase 5)
> **목표**: 이중 검증 (문서 + 센서) 지원
> **선행 조건**: Main-S3 (ContextEnricher), Main-S4 (온톨로지 확장) 완료
> **상태**: 설계

---

## 1. 개요

### 1.1 목적

센서 데이터를 활용한 이중 검증 시스템을 구축합니다.

```
[기존 검증]
Query → Context Verifier → 문서 증거만 검증

[확장 검증]
Query → Context Verifier → 문서 증거 + 센서 증거 이중 검증
                        → 온톨로지 교차 검증 (패턴 → 에러코드)
                        → PARTIAL 상태 세분화
```

### 1.2 핵심 변경사항

1. **EnrichedContext 지원**: Main-S3의 EnrichedContext를 입력으로 받음
2. **센서 증거 검증**: 패턴 유형, 신뢰도, 시간 일치 확인
3. **온톨로지 교차 검증**: GraphRetriever로 패턴-에러 관계 검증
4. **PARTIAL 상태 세분화**: `PARTIAL_DOC_ONLY`, `PARTIAL_SENSOR_ONLY`, `PARTIAL_BOTH`
5. **신뢰도 부스트**: 이중 증거 시 confidence 상향

---

## 2. 검증 로직

### 2.1 이중 검증 흐름

```
┌─────────────────┐
│   EnrichedContext │
│  (Doc + Sensor)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  1. 문서 증거 검증  │  → 기존 로직 재사용
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. 센서 증거 검증  │  → [신규] 패턴 유효성 확인
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 온톨로지 교차검증 │  → [신규] 패턴 → 에러 관계 확인
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 최종 상태 판정  │  → VERIFIED / PARTIAL_* / INSUFFICIENT
└─────────────────┘
```

### 2.2 상태 판정 기준

| 상태 | 문서 증거 | 센서 증거 | 온톨로지 매칭 | 신뢰도 |
|------|---------|---------|-------------|--------|
| **VERIFIED** | O | O | O | 0.85+ |
| **PARTIAL_BOTH** | O | O | X | 0.70~0.85 |
| **PARTIAL_DOC_ONLY** | O | X | - | 0.60~0.75 |
| **PARTIAL_SENSOR_ONLY** | X | O | O | 0.55~0.70 |
| **UNVERIFIED** | X | X | - | < 0.50 |
| **INSUFFICIENT** | 컨텍스트 부족 | - | - | 0.0 |

### 2.3 신뢰도 계산

```python
def calculate_confidence(
    doc_score: float,      # 문서 증거 점수 (0~1)
    sensor_score: float,   # 센서 증거 점수 (0~1)
    ontology_match: bool,  # 온톨로지 매칭 여부
    correlation_level: str # STRONG, MODERATE, WEAK, NONE
) -> float:
    base = (doc_score * 0.5) + (sensor_score * 0.3)

    if ontology_match:
        base += 0.15

    if correlation_level == "STRONG":
        base += 0.1
    elif correlation_level == "MODERATE":
        base += 0.05

    return min(1.0, base)
```

---

## 3. 데이터 구조

### 3.1 확장된 VerificationStatus

```python
class VerificationStatus(Enum):
    VERIFIED = "verified"              # 문서 + 센서 + 온톨로지 완전 검증
    PARTIAL_BOTH = "partial_both"      # 문서 + 센서 있으나 온톨로지 불일치
    PARTIAL_DOC_ONLY = "partial_doc"   # 문서만 검증
    PARTIAL_SENSOR_ONLY = "partial_sensor"  # 센서만 검증
    UNVERIFIED = "unverified"          # 검증 불가
    INSUFFICIENT = "insufficient"       # 컨텍스트 부족
```

### 3.2 확장된 VerificationResult

```python
@dataclass
class VerificationResult:
    status: VerificationStatus
    confidence: float
    evidence_count: int
    evidence_sources: List[str]
    warnings: List[str]

    # [Main-S5] 센서 관련 필드 추가
    sensor_evidence_count: int = 0
    sensor_patterns: List[str] = field(default_factory=list)
    ontology_match: bool = False
    correlation_level: str = "NONE"

    @property
    def has_sensor_support(self) -> bool:
        """센서 증거 존재 여부"""
        return self.sensor_evidence_count > 0

    @property
    def has_dual_evidence(self) -> bool:
        """이중 증거 (문서 + 센서) 존재 여부"""
        return self.evidence_count > 0 and self.sensor_evidence_count > 0
```

---

## 4. 클래스 설계

### 4.1 SensorVerifier (신규)

```python
class SensorVerifier:
    """
    센서 증거 검증기

    EnrichedContext의 센서 증거를 검증합니다.

    검증 항목:
        1. 패턴 유형 유효성
        2. 패턴 신뢰도
        3. 시간 범위 적합성
    """

    def __init__(
        self,
        min_pattern_confidence: float = 0.7,
        max_time_gap_minutes: int = 60
    ):
        self.min_pattern_confidence = min_pattern_confidence
        self.max_time_gap_minutes = max_time_gap_minutes
        self.valid_pattern_types = ["collision", "vibration", "overload", "drift"]

    def verify_sensor_evidence(
        self,
        sensor_evidence: Optional[SensorEvidence],
        error_code: Optional[str] = None
    ) -> Tuple[bool, float, List[str]]:
        """
        센서 증거 검증

        Returns:
            Tuple[bool, float, List[str]]: (유효여부, 점수, 경고목록)
        """
```

### 4.2 OntologyVerifier (신규)

```python
class OntologyVerifier:
    """
    온톨로지 교차 검증기

    GraphRetriever를 사용해 센서 패턴과 에러코드 관계를 검증합니다.
    """

    def __init__(self, graph_retriever: GraphRetriever):
        self.graph_retriever = graph_retriever

    def verify_pattern_error_relation(
        self,
        pattern_type: str,
        error_code: str
    ) -> Tuple[bool, float]:
        """
        센서 패턴 → 에러코드 관계 검증

        Returns:
            Tuple[bool, float]: (매칭여부, 확률)
        """

    def get_expected_patterns_for_error(
        self,
        error_code: str
    ) -> List[Dict]:
        """
        에러코드에 대한 예상 센서 패턴 조회
        """
```

### 4.3 확장된 ContextVerifier

```python
class ContextVerifier:
    """
    [확장] 컨텍스트 검증기

    기존 문서 검증 + 센서 증거 검증 통합
    """

    def __init__(
        self,
        min_contexts: int = 1,
        min_relevance_score: float = 0.3,
        graph_retriever: Optional[GraphRetriever] = None
    ):
        self.min_contexts = min_contexts
        self.min_relevance_score = min_relevance_score

        # [Main-S5] 센서 검증기 추가
        self.sensor_verifier = SensorVerifier()
        self.ontology_verifier = OntologyVerifier(graph_retriever) if graph_retriever else None

    def verify_enriched_context(
        self,
        enriched_context: EnrichedContext,
        query_analysis: QueryAnalysis
    ) -> VerificationResult:
        """
        EnrichedContext 검증 (문서 + 센서)
        """
```

---

## 5. 사용 예시

### 5.1 기본 사용

```python
from src.rag import Verifier
from src.rag.context_enricher import ContextEnricher

# 인스턴스 생성
verifier = Verifier(use_sensor_verification=True)
enricher = ContextEnricher()

# EnrichedContext 생성
enriched = enricher.enrich(
    query="C153 에러 원인",
    doc_chunks=doc_results,
    error_code="C153",
    reference_time=datetime.now()
)

# 이중 검증
result = verifier.verify_enriched_context(enriched, query_analysis)

if result.status == VerificationStatus.VERIFIED:
    print(f"완전 검증됨 (신뢰도: {result.confidence:.0%})")
    print(f"센서 패턴: {result.sensor_patterns}")
elif result.status.value.startswith("partial"):
    print(f"부분 검증: {result.status.value}")
else:
    print(f"검증 실패: {result.warnings}")
```

### 5.2 온톨로지 교차 검증

```python
# 패턴-에러 관계 검증
is_match, probability = verifier.ontology_verifier.verify_pattern_error_relation(
    pattern_type="collision",
    error_code="C153"
)
# → (True, 0.95)

# 예상 패턴 조회
expected = verifier.ontology_verifier.get_expected_patterns_for_error("C153")
# → [{"type": "collision", "probability": 0.95}]
```

---

## 6. 안전 응답 확장

### 6.1 상태별 응답

| 상태 | 응답 메시지 |
|------|------------|
| VERIFIED | (정상 답변 + 출처) |
| PARTIAL_BOTH | 답변 + "센서 패턴과 온톨로지가 일치하지 않습니다" |
| PARTIAL_DOC_ONLY | 답변 + "센서 데이터 확인이 필요합니다" |
| PARTIAL_SENSOR_ONLY | 답변 + "문서 근거가 제한적입니다" |
| UNVERIFIED | 안전 응답 (근거 없음) |
| INSUFFICIENT | 안전 응답 (컨텍스트 부족) |

### 6.2 센서 정보 포함 응답

```
C153 에러 해결 방법:
1. Safety Reset 수행
2. 충돌 지점 확인

---
**검증 정보:**
- 📄 문서 근거: 2건 (error_codes, service_manual)
- 📊 센서 분석: collision 패턴 감지 (신뢰도 95%)
- 🔗 온톨로지: PAT_COLLISION → C153 매칭 확인
- 🟢 종합 신뢰도: 92%
```

---

## 7. 구현 태스크

```
Main-S5-1: SensorVerifier 구현
├── src/rag/sensor_verifier.py 작성
├── 패턴 유효성 검증
├── 신뢰도 계산
└── 검증: 단위 테스트

Main-S5-2: OntologyVerifier 구현
├── src/rag/ontology_verifier.py 작성
├── GraphRetriever 연동
├── 패턴-에러 매칭 검증
└── 검증: 단위 테스트

Main-S5-3: ContextVerifier 확장
├── src/rag/verifier.py 수정
├── verify_enriched_context() 메서드 추가
├── VerificationStatus 확장
├── VerificationResult 확장
└── 검증: 통합 테스트

Main-S5-4: SafeResponseGenerator 확장
├── 센서 정보 포함 응답
├── PARTIAL_* 상태별 메시지
└── 검증: 단위 테스트

Main-S5-5: 단위 테스트
├── tests/unit/test_sensor_verifier.py
├── tests/unit/test_ontology_verifier.py
└── tests/unit/test_verifier_extended.py
```

---

## 8. 완료 기준

- [ ] SensorVerifier 구현 완료
- [ ] OntologyVerifier 구현 완료
- [ ] VerificationStatus 확장 (PARTIAL_* 추가)
- [ ] VerificationResult 확장 (센서 필드 추가)
- [ ] verify_enriched_context() 구현
- [ ] SafeResponseGenerator 확장
- [ ] 단위 테스트 100% 통과
- [ ] 통합 테스트 통과

---

## 9. 다음 단계

Main-S5 완료 후:
- Main-S6: API/UI 확장 (센서 데이터 시각화, 검증 상태 표시)

---

**참조**: Main_S4_온톨로지확장.md, Main_S3_ContextEnricher.md
