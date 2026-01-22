# Main-S5: Verifier 확장 - 완료 보고서

> **Phase**: Main-S5 (센서 통합 Phase 5)
> **목표**: 이중 검증 (문서 + 센서) 지원
> **상태**: 완료
> **일자**: 2026-01-21

---

## 1. 구현 요약

### 1.1 완료 항목

| 항목 | 파일 | 상태 |
|------|------|------|
| SensorVerifier | `src/rag/sensor_verifier.py` | 완료 |
| OntologyVerifier | `src/rag/ontology_verifier.py` | 완료 |
| Verifier 확장 | `src/rag/verifier.py` | 완료 |
| 단위 테스트 | `tests/unit/test_verifier_extended.py` | 완료 (24개 통과) |

### 1.2 파일 구조

```
src/rag/
├── __init__.py                    # [수정] 새 클래스 export 추가
├── verifier.py                    # [수정] 이중 검증 로직 추가
├── sensor_verifier.py             # [신규] 센서 증거 검증기
└── ontology_verifier.py           # [신규] 온톨로지 교차 검증기

tests/unit/
└── test_verifier_extended.py      # [신규] 확장 테스트 (24개)
```

---

## 2. 구현 세부사항

### 2.1 VerificationStatus 확장

| 상태 | 값 | 설명 |
|------|-----|------|
| `VERIFIED` | verified | 문서 + 센서 + 온톨로지 완전 검증 |
| `PARTIAL` | partial | 부분 검증 (레거시 호환) |
| `PARTIAL_BOTH` | partial_both | 문서 + 센서 있으나 온톨로지 불일치 |
| `PARTIAL_DOC_ONLY` | partial_doc | 문서만 검증 |
| `PARTIAL_SENSOR_ONLY` | partial_sensor | 센서만 검증 |
| `UNVERIFIED` | unverified | 검증 불가 |
| `INSUFFICIENT` | insufficient | 컨텍스트 부족 |

### 2.2 VerificationResult 확장

```python
@dataclass
class VerificationResult:
    # 기존 필드
    status: VerificationStatus
    confidence: float
    evidence_count: int
    evidence_sources: List[str]
    warnings: List[str]

    # [Main-S5] 센서 관련 필드
    sensor_evidence_count: int = 0
    sensor_patterns: List[str] = []
    ontology_match: bool = False
    correlation_level: str = "NONE"

    @property
    def has_sensor_support(self) -> bool: ...

    @property
    def has_dual_evidence(self) -> bool: ...
```

### 2.3 SensorVerifier 클래스

```python
class SensorVerifier:
    """센서 증거 검증기"""

    def verify(
        self,
        sensor_evidence: Optional[SensorEvidence],
        error_code: Optional[str] = None,
        reference_time: Optional[datetime] = None
    ) -> SensorVerificationResult:
        """
        검증 항목:
        1. 패턴 유형 유효성 (collision, vibration, overload, drift)
        2. 패턴 신뢰도 (기본 70% 이상)
        3. 시간 범위 적합성 (기본 60분)
        4. 에러코드 관련성 매칭
        """
```

**에러-패턴 매핑:**

| 에러코드 | 예상 패턴 |
|---------|----------|
| C153 | collision |
| C119 | collision |
| C189 | overload |
| C204 | vibration |

### 2.4 OntologyVerifier 클래스

```python
class OntologyVerifier:
    """온톨로지 교차 검증기"""

    def verify_pattern_error_relation(
        self,
        pattern_type: str,
        error_code: str
    ) -> Tuple[bool, float]:
        """패턴 → 에러코드 관계 검증"""

    def get_expected_patterns_for_error(
        self,
        error_code: str
    ) -> List[Dict]:
        """에러코드에 대한 예상 패턴 조회"""

    def get_causes_for_pattern(
        self,
        pattern_type: str
    ) -> List[Dict]:
        """패턴에 대한 원인 조회"""
```

### 2.5 Verifier 확장

```python
class Verifier:
    def __init__(
        self,
        use_sensor_verification: bool = False,
        graph_retriever: Optional[GraphRetriever] = None,
    ):
        # 센서 검증 활성화 시 SensorVerifier, OntologyVerifier 초기화

    def verify_enriched_context(
        self,
        enriched_context: EnrichedContext,
        query_analysis: Optional[QueryAnalysis] = None,
    ) -> VerificationResult:
        """EnrichedContext 이중 검증"""

    def add_enriched_citation(
        self,
        answer: str,
        verification: VerificationResult,
    ) -> str:
        """이중 검증 정보 포함 출처 추가"""
```

---

## 3. 이중 검증 로직

### 3.1 검증 흐름

```
EnrichedContext 입력
        │
        ▼
┌───────────────────┐
│  1. 문서 증거 검증   │
│  - 증거 수 확인      │
│  - 평균 점수 계산    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  2. 센서 증거 검증   │
│  - 패턴 유효성       │
│  - 신뢰도 확인       │
│  - 에러 매칭        │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 3. 온톨로지 교차검증  │
│  - 패턴 → 에러 관계  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 4. 최종 상태 판정   │
│  - 신뢰도 계산       │
│  - 상태 결정        │
└───────────────────┘
```

### 3.2 신뢰도 계산

```python
def _calculate_dual_confidence(
    doc_score,        # 문서 점수 (50%)
    sensor_score,     # 센서 점수 (30%)
    ontology_match,   # 온톨로지 매칭 (+15%)
    correlation_level # 상관관계 (+10%/+5%)
) -> float:
    base = (doc_score * 0.5) + (sensor_score * 0.3)
    if ontology_match:
        base += 0.15
    if correlation_level == "STRONG":
        base += 0.1
    elif correlation_level == "MODERATE":
        base += 0.05
    return min(1.0, max(0.0, base))
```

### 3.3 상태 판정 기준

| 상태 | 조건 |
|------|------|
| VERIFIED | 문서 O + 센서 O + 온톨로지 O + 신뢰도 ≥ 75% |
| PARTIAL_BOTH | 문서 O + 센서 O + 온톨로지 X |
| PARTIAL_DOC_ONLY | 문서 O + 센서 X |
| PARTIAL_SENSOR_ONLY | 문서 X + 센서 O |
| INSUFFICIENT | 문서 X + 센서 X |

---

## 4. 테스트 결과

### 4.1 단위 테스트

```
24 passed in 2.79s
```

### 4.2 테스트 카테고리

| 카테고리 | 테스트 수 | 내용 |
|----------|----------|------|
| VerificationStatus | 2 | 새 상태 확인 |
| VerificationResult | 4 | 센서 필드, is_safe_to_answer |
| SensorVerifier | 5 | 패턴 검증, 에러 매칭 |
| OntologyVerifier | 5 | 패턴-에러 관계, 원인 조회 |
| VerifierExtended | 7 | verify_enriched_context, 신뢰도 계산 |
| Integration | 1 | 전체 검증 흐름 |

---

## 5. 사용 예시

### 5.1 기본 사용

```python
from src.rag import Verifier, ContextEnricher

# 센서 검증 활성화
verifier = Verifier(use_sensor_verification=True)
enricher = ContextEnricher()

# EnrichedContext 생성
enriched = enricher.enrich(
    query="C153 에러 원인",
    doc_chunks=doc_results,
    error_code="C153"
)

# 이중 검증
result = verifier.verify_enriched_context(enriched)

print(f"상태: {result.status.value}")
print(f"신뢰도: {result.confidence:.0%}")
print(f"센서 패턴: {result.sensor_patterns}")
print(f"온톨로지 매칭: {result.ontology_match}")
```

### 5.2 출처 정보 추가

```python
answer = "C153 에러는 충돌로 인해 발생합니다."
final_answer = verifier.add_enriched_citation(answer, result)

# 출력:
# C153 에러는 충돌로 인해 발생합니다.
#
# ---
# **검증 정보:**
# - 📄 문서 근거: 2건 (error_codes:ec_001, service_manual:sm_001)
# - 📊 센서 분석: collision 패턴 감지
# - 🔗 온톨로지: 패턴-에러 매칭 확인
# - 📈 상관관계: STRONG
# - 🟢 종합 신뢰도: 92%
```

---

## 6. 통합 포인트

### 6.1 RAGService 연동

```python
class RAGService:
    def query(self, question: str) -> str:
        # 1. 기존 RAG 파이프라인
        analysis = self.analyzer.analyze(question)
        contexts = self.retriever.retrieve(analysis)

        # 2. EnrichedContext 생성 (Main-S3)
        enriched = self.enricher.enrich(
            query=question,
            doc_chunks=contexts,
            error_code=analysis.error_codes[0] if analysis.error_codes else None
        )

        # 3. 이중 검증 (Main-S5)
        verification = self.verifier.verify_enriched_context(enriched)

        if not verification.is_safe_to_answer:
            return self.verifier.get_safe_response(verification, analysis)

        # 4. 생성 및 출처 추가
        answer = self.generator.generate(question, contexts)
        return self.verifier.add_enriched_citation(answer, verification)
```

---

## 7. 다음 단계

- [x] Main-S1: 센서 데이터 생성 (완료)
- [x] Main-S2: 패턴 감지 (완료)
- [x] Main-S3: Context Enricher (완료)
- [x] Main-S4: 온톨로지 확장 (완료)
- [x] Main-S5: Verifier 확장 (완료)
- [ ] Main-S6: API/UI 확장 (센서 데이터 시각화)

---

**작성**: Main-S5 Verifier 확장
**참조**: Main_S5_Verifier확장.md, Main_S4_완료보고서.md
