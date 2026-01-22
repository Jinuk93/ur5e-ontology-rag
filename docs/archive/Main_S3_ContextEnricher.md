# Main-S3: Context Enricher

> **Phase**: Main-S3 (센서 통합 Phase 3)
> **목표**: 문서 검색 결과에 센서 맥락 추가
> **선행 조건**: Main-S2 (패턴 감지) 완료
> **상태**: 설계

---

## 1. 개요

### 1.1 목적

문서 기반 검색 결과에 센서 데이터 맥락을 추가하여,
**이중 근거(문서 + 센서)**를 제공하는 Context Enricher를 구현합니다.

```
Query → Vector Retrieval → Context Enricher → Verifier
              (문서)            (센서 추가)     (통합 검증)
```

### 1.2 핵심 기능

1. **센서 데이터 조회**: 에러코드/시간 기반으로 관련 센서 데이터 조회
2. **패턴 매칭**: 감지된 패턴과 문서 원인 간 상관관계 분석
3. **증거 통합**: 문서 증거 + 센서 증거를 통합 컨텍스트로 구성

---

## 2. 인터페이스 설계

### 2.1 ContextEnricher 클래스

```python
class ContextEnricher:
    """
    문서 검색 결과에 센서 맥락을 추가합니다.

    사용 예시:
        enricher = ContextEnricher()
        enriched = enricher.enrich(
            query="C153 에러 원인",
            doc_chunks=[chunk1, chunk2],
            error_code="C153",
            reference_time=datetime(2024, 1, 17, 14, 0)
        )
    """

    def __init__(
        self,
        sensor_store: Optional[SensorStore] = None,
        pattern_detector: Optional[PatternDetector] = None
    ):
        """
        Args:
            sensor_store: 센서 데이터 저장소
            pattern_detector: 패턴 감지기
        """

    def enrich(
        self,
        query: str,
        doc_chunks: List[Dict],
        error_code: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        time_window: str = "1h"
    ) -> EnrichedContext:
        """
        문서 청크에 센서 맥락 추가

        Args:
            query: 사용자 질문
            doc_chunks: 검색된 문서 청크 목록
            error_code: 관련 에러코드
            reference_time: 기준 시점 (None이면 현재)
            time_window: 조회 시간 윈도우 (예: "1h", "30m")

        Returns:
            EnrichedContext: 통합 컨텍스트
        """

    def analyze_correlation(
        self,
        error_code: str,
        patterns: List[DetectedPattern],
        doc_causes: List[str]
    ) -> CorrelationResult:
        """
        에러코드-패턴-문서원인 간 상관관계 분석

        Args:
            error_code: 에러코드
            patterns: 감지된 센서 패턴
            doc_causes: 문서에서 추출한 원인 목록

        Returns:
            CorrelationResult: 상관관계 분석 결과
        """
```

### 2.2 데이터 클래스

```python
@dataclass
class EnrichedContext:
    """통합 컨텍스트"""
    doc_evidence: List[DocEvidence]
    sensor_evidence: Optional[SensorEvidence]
    correlation: CorrelationResult

    def to_dict(self) -> Dict:
        """JSON 직렬화"""

@dataclass
class DocEvidence:
    """문서 증거"""
    chunk_id: str
    content: str
    score: float
    source: str  # 문서명
    page: Optional[int]

@dataclass
class SensorEvidence:
    """센서 증거"""
    patterns: List[DetectedPattern]
    statistics: Dict[str, AxisStats]
    time_range: Tuple[datetime, datetime]
    has_anomaly: bool

@dataclass
class AxisStats:
    """축별 통계"""
    mean: float
    std: float
    min: float
    max: float

@dataclass
class CorrelationResult:
    """상관관계 분석 결과"""
    level: str  # STRONG, MODERATE, WEAK, NONE
    confidence: float
    reason: str
    supporting_evidence: List[str]
```

---

## 3. 상관관계 분석

### 3.1 상관관계 레벨 정의

| Level | 조건 | 신뢰도 | 설명 |
|-------|------|--------|------|
| **STRONG** | 문서 원인 + 센서 패턴 일치 | 0.9+ | 문서와 센서 모두 동일 원인 지지 |
| **MODERATE** | 문서 원인만 또는 센서만 | 0.7~0.9 | 한쪽 증거만 확인 |
| **WEAK** | 관련 가능성 있음 | 0.5~0.7 | 패턴 있으나 원인 불명확 |
| **NONE** | 센서 데이터 없음 | 0.0 | 센서 조회 불가/무관 질문 |

### 3.2 매핑 규칙

에러코드 → 센서 패턴 매핑:

| 에러코드 | 예상 패턴 | 매칭 조건 |
|----------|-----------|-----------|
| C153 | collision | Fz spike > 500N |
| C119 | collision | Fz spike > 500N |
| C189 | overload | Fz > 300N, duration > 5s |
| C204 | vibration | Tx/Ty noise 증가 |

### 3.3 판정 로직

```python
def _determine_correlation_level(
    self,
    error_code: str,
    patterns: List[DetectedPattern],
    doc_causes: List[str]
) -> Tuple[str, float, str]:
    """
    상관관계 레벨 결정

    Returns:
        (level, confidence, reason)
    """
    # 센서 데이터 없음
    if not patterns:
        return ("NONE", 0.0, "센서 데이터 없음 또는 조회 실패")

    # 에러코드 → 예상 패턴 매핑
    expected_pattern = self._get_expected_pattern(error_code)

    # 매칭되는 패턴 찾기
    matching_patterns = [
        p for p in patterns
        if p.pattern_type == expected_pattern
    ]

    if matching_patterns and doc_causes:
        # 문서 원인과 센서 패턴 모두 일치
        return ("STRONG", 0.95, f"문서 원인 확인 + {expected_pattern} 패턴 감지")

    elif matching_patterns:
        # 센서 패턴만 있음
        return ("MODERATE", 0.75, f"{expected_pattern} 패턴 감지, 문서 원인 미확인")

    elif doc_causes:
        # 문서 원인만 있음
        return ("MODERATE", 0.70, "문서 원인 확인, 센서 패턴 미감지")

    elif patterns:
        # 다른 패턴 있음
        return ("WEAK", 0.55, f"예상 외 패턴 감지: {patterns[0].pattern_type}")

    return ("WEAK", 0.50, "관련 패턴 없음")
```

---

## 4. RAGService 통합

### 4.1 파이프라인 수정

```
[기존]
Query → Analyzer → Linker → GraphRetriever → VectorRetriever → Verifier → Generator

[변경]
Query → Analyzer → Linker → GraphRetriever → VectorRetriever
                                                    ↓
                                          → ContextEnricher → Verifier → Generator
```

### 4.2 RAGService 수정 사항

```python
# src/api/services/rag_service.py

class RAGService:
    def __init__(self):
        # 기존
        self.analyzer = QueryAnalyzer()
        self.linker = EntityLinker()
        self.graph_retriever = GraphRetriever()
        self.vector_retriever = VectorRetriever()
        self.verifier = Verifier()
        self.generator = Generator()

        # 추가
        self.context_enricher = ContextEnricher()

    async def search(self, query: str, ...) -> SearchResponse:
        # 기존 파이프라인
        analysis = self.analyzer.analyze(query)
        entities = self.linker.link(query)
        graph_results = self.graph_retriever.retrieve(entities)
        vector_results = self.vector_retriever.retrieve(query)

        # [추가] Context Enrichment
        error_code = analysis.get("error_codes", [None])[0]
        enriched_context = self.context_enricher.enrich(
            query=query,
            doc_chunks=vector_results,
            error_code=error_code,
            reference_time=datetime.now(),
            time_window="1h"
        )

        # Verifier에 enriched context 전달
        verification = self.verifier.verify(
            query=query,
            context=enriched_context  # 변경
        )

        # Generator에 전달
        answer = self.generator.generate(
            query=query,
            context=enriched_context,
            verification=verification
        )
```

---

## 5. 파일 구조

```
src/rag/
├── context_enricher.py      # [신규] ContextEnricher 클래스
└── schemas/
    └── enriched_context.py  # [신규] 데이터 클래스

tests/unit/
└── test_context_enricher.py # [신규] 단위 테스트
```

---

## 6. 구현 태스크

```
Main-S3-1: 데이터 클래스 정의
├── src/rag/schemas/enriched_context.py 작성
├── EnrichedContext, DocEvidence, SensorEvidence 정의
└── 검증: import 및 직렬화 테스트

Main-S3-2: ContextEnricher 클래스 구현
├── src/rag/context_enricher.py 작성
├── enrich() 메서드 구현
├── analyze_correlation() 메서드 구현
└── 검증: 단위 테스트

Main-S3-3: 에러코드-패턴 매핑 정의
├── configs/error_pattern_mapping.yaml 작성
├── 매핑 규칙 정의
└── 검증: 매핑 정확도

Main-S3-4: RAGService 통합
├── src/api/services/rag_service.py 수정
├── ContextEnricher 파이프라인 추가
└── 검증: 통합 테스트

Main-S3-5: 단위 테스트 작성
├── tests/unit/test_context_enricher.py 작성
├── 각 상관관계 레벨 테스트
└── 검증: 테스트 통과율 100%
```

---

## 7. 테스트 케이스

### 7.1 상관관계 레벨 테스트

| 케이스 | 입력 | 예상 레벨 |
|--------|------|-----------|
| 충돌 에러 + 충돌 패턴 | error_code=C153, pattern=collision | STRONG |
| 충돌 에러 + 패턴 없음 | error_code=C153, patterns=[] | MODERATE |
| 에러 없음 + 패턴 있음 | error_code=None, pattern=collision | WEAK |
| 에러 없음 + 패턴 없음 | error_code=None, patterns=[] | NONE |

### 7.2 통합 테스트

```python
def test_enrich_with_collision():
    """충돌 에러 + 센서 패턴 통합 테스트"""
    enricher = ContextEnricher()

    # Mock 데이터
    doc_chunks = [{"chunk_id": "ec_15_001", "content": "C153: Safety Stop...", "score": 0.9}]

    result = enricher.enrich(
        query="C153 에러 원인",
        doc_chunks=doc_chunks,
        error_code="C153",
        reference_time=datetime(2024, 1, 17, 14, 0),
        time_window="1h"
    )

    assert result.correlation.level == "STRONG"
    assert result.sensor_evidence is not None
    assert len(result.sensor_evidence.patterns) > 0
```

---

## 8. 완료 기준

- [ ] EnrichedContext, DocEvidence, SensorEvidence 데이터 클래스 구현
- [ ] ContextEnricher.enrich() 메서드 구현
- [ ] ContextEnricher.analyze_correlation() 메서드 구현
- [ ] 에러코드-패턴 매핑 설정 파일 작성
- [ ] RAGService 통합 완료
- [ ] 단위 테스트 100% 통과
- [ ] 통합 테스트 통과

---

## 9. 다음 단계

Main-S3 완료 후:
- Main-S4: 온톨로지 확장 (SensorPattern 노드 추가)
- Main-S5: Verifier 확장 (이중 검증, PARTIAL 상태)

---

**참조**: Main__ROADMAP.md, Main_S2_패턴감지.md
