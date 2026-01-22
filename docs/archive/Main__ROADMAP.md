# UR5e Multi-Modal RAG 시스템 - 개발 로드맵 (Main)

> **Main Version**: Foundation(Phase 0-10) 개선 + ATI Axia80 센서 통합
>
> 이 문서는 Foundation_ROADMAP.md를 분석/검토하여 개선하고,
> 센서 데이터 통합을 포함한 **완전판 로드맵**입니다.

---

## 전체 파이프라인 개요

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              OFFLINE (배치/준비)                           │
│                                                                           │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────┐              │
│  │  PDF    │──▶│  Parse  │──▶│  Chunk  │──▶│  ChromaDB   │              │
│  │ 문서들   │   │ (텍스트) │  │ (조각화) │   │  (벡터DB)   │              │
│  └─────────┘   └─────────┘   └─────────┘   └─────────────┘              │
│                                                                           │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                                 │
│  │ontology │──▶│ lexicon │──▶│  Neo4j  │                                 │
│  │  .json  │   │  .yaml  │   │(그래프DB)│                                 │
│  └─────────┘   └─────────┘   └─────────┘                                 │
│                                                                           │
│  ┌─────────┐   ┌─────────┐   ┌─────────────┐  [Main 신규]                │
│  │ Axia80  │──▶│ Pattern │──▶│ SensorStore │                             │
│  │시뮬레이션│   │ Detect  │   │ (Parquet)   │                             │
│  └─────────┘   └─────────┘   └─────────────┘                             │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                              ONLINE (실시간 서빙)                          │
│                                                                           │
│  사용자 질문                                                               │
│       │                                                                   │
│       ▼                                                                   │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                    Query Analyzer (질문 분석)                      │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│       │                                                                   │
│       ▼                                                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐              │
│  │  Entity  │──▶│  Graph   │──▶│  Vector  │──▶│ Context  │              │
│  │  Linker  │   │ Retriever│   │ Retriever│   │ Enricher │  [Main 신규] │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘              │
│                              │                                            │
│                              ▼                                            │
│                    ┌──────────────────┐                                  │
│                    │     Verifier     │                                  │
│                    │  (근거 검증 Gate) │                                  │
│                    └──────────────────┘                                  │
│                              │                                            │
│                              ▼                                            │
│                    ┌──────────────────┐                                  │
│                    │    Generator     │                                  │
│                    │  (답변 생성/포맷) │                                  │
│                    └──────────────────┘                                  │
│                              │                                            │
│                              ▼                                            │
│                    최종 답변 + 근거 + 센서 차트                            │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 구조 개요

### Part 1: Foundation 개선 (Main-F)

| Phase | 제목 | 핵심 내용 | 선행 조건 |
|-------|------|----------|----------|
| **Main-F1** | Entity Linker 개선 | Lexicon + Rules 기반 링킹 | Foundation 완료 |
| **Main-F2** | Trace 시스템 완성 | audit_trail.jsonl 구현 | Foundation 완료 |
| **Main-F3** | 메타데이터 정비 | sources.yaml, chunk_manifest | Foundation 완료 |

### Part 2: 센서 통합 (Main-S)

| Phase | 제목 | 핵심 내용 | 선행 조건 |
|-------|------|----------|----------|
| **Main-S1** | 센서 데이터 생성 | Axia80 시뮬레이션 1개월 | Main-F 완료 |
| **Main-S2** | 패턴 감지 | 충돌/진동/과부하 감지 | Main-S1 |
| **Main-S3** | Context Enricher | 문서-센서 맥락 통합 | Main-S2 |
| **Main-S4** | 온톨로지 확장 | SensorPattern 노드 추가 | Main-S2 |
| **Main-S5** | Verifier 확장 | 이중 검증, PARTIAL 상태 | Main-S3, Main-S4 |
| **Main-S6** | API/UI 확장 | 센서 엔드포인트, 대시보드 | Main-S5 |

---

# Part 1: Foundation 개선 Phase

---

## Main-F1: Entity Linker 개선

**목표**: 단순 정규식 → Lexicon + Rules + Embedding 기반 링킹

### 배경 (Foundation의 문제점)

```python
# Foundation 구현: 단순 정규식만 사용
self.error_code_pattern = re.compile(r'\b(C\d+(?:A\d+)?)\b', re.IGNORECASE)
```

**문제점**:
- 동의어/한영 변환 미지원 ("컨트롤 박스" → "Control Box")
- 약어 처리 미흡 ("J3" → "Joint 3")
- 유사 매칭 불가

### 구현 태스크

```
Main-F1-1: lexicon.yaml 작성
├── data/processed/ontology/lexicon.yaml 생성
├── 에러코드 동의어 정의 (C4A15, C-4A15, c4a15 등)
├── 부품명 동의어 정의 (한영, 약어 포함)
└── 검증: 최소 10개 에러코드, 5개 부품에 대해 동의어 정의

Main-F1-2: rules.yaml 작성
├── configs/rules.yaml 생성
├── 에러코드 정규식 패턴 정의
├── 부품명 매칭 우선순위 정의
└── 검증: 샘플 쿼리로 정규화 테스트

Main-F1-3: EntityLinker 클래스 개선
├── src/rag/entity_linker.py 수정
├── Lexicon 매칭 구현
├── Rules 기반 정규화 구현
├── Embedding fallback 구현
└── 검증: 단위 테스트 10개 이상
```

### 예상 산출물

**lexicon.yaml**:
```yaml
error_codes:
  C4A15:
    canonical: "C4A15"
    synonyms: ["C-4A15", "c4a15", "C4-A15", "C 4 A 15"]
    node_id: "ERR_C4A15"

components:
  control_box:
    canonical: "Control Box"
    synonyms: ["컨트롤 박스", "컨트롤러", "controller", "제어기"]
    node_id: "COMP_CONTROL_BOX"
```

**rules.yaml**:
```yaml
error_code:
  patterns:
    - regex: 'C-?(\d+)(?:A(\d+))?'
      normalize: 'C{base}A{sub}'
  validation:
    base_range: [0, 55]

component:
  matching:
    order: ["lexicon", "regex", "embedding"]
    min_confidence: 0.7
```

### 코드 리뷰 체크포인트

| 항목 | 확인 내용 |
|------|----------|
| 정합성 | lexicon.yaml의 node_id가 Neo4j 노드와 일치하는가? |
| 커버리지 | 주요 에러코드/부품에 대한 동의어가 충분한가? |
| 테스트 | 한영/약어 변환이 테스트되었는가? |
| 성능 | Embedding fallback 시 지연 시간은 적절한가? |

### 완료 기준

- [ ] lexicon.yaml에 최소 20개 에러코드, 10개 부품 동의어 정의
- [ ] rules.yaml 작성 완료
- [ ] EntityLinker 클래스 개선 완료
- [ ] 단위 테스트 통과율 100%
- [ ] 기존 벤치마크 성능 저하 없음

---

## Main-F2: Trace 시스템 완성

**목표**: 모든 요청/응답을 추적 가능하게 audit_trail.jsonl 구현

### 배경 (Foundation의 문제점)

- `audit_trail.jsonl` 미구현
- `trace_id`가 로그에만 남고 저장/조회 불가
- 디버깅 시 파이프라인 재현 어려움

### 구현 태스크

```
Main-F2-1: audit_trail 구조 정의
├── stores/audit/audit_trail.jsonl 스키마 확정
├── 필수 필드: trace_id, timestamp, user_query, verifier_status
├── 선택 필드: analysis, linked_entities, graph_paths, latency_ms
└── 검증: 스키마 문서화

Main-F2-2: AuditLogger 구현
├── src/api/services/audit_logger.py 작성
├── 요청 시작/종료 로깅
├── 각 파이프라인 단계 로깅
└── 검증: 로그 파일 생성 확인

Main-F2-3: /evidence/{trace_id} 엔드포인트 완성
├── src/api/routes/search.py 수정
├── trace_id로 audit_trail 조회
├── 전체 파이프라인 정보 반환
└── 검증: API 테스트
```

### 예상 산출물

**audit_trail.jsonl** (한 줄 예시):
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-21T10:30:00Z",
  "user_query": "C4A15 에러 해결법",
  "normalized_query": "C4A15 에러 해결법",
  "analysis": {
    "error_codes": ["C4A15"],
    "components": [],
    "query_type": "error_resolution"
  },
  "linked_entities": [
    {"entity": "C4A15", "node_id": "ERR_C4A15", "confidence": 0.95}
  ],
  "graph_paths": ["(ERR_C4A15)-[RESOLVED_BY]->(RES_001)"],
  "retrieval_results": [{"chunk_id": "ec_15_001", "score": 0.89}],
  "verifier_status": "PASS",
  "answer": "...",
  "latency_ms": 564
}
```

### 코드 리뷰 체크포인트

| 항목 | 확인 내용 |
|------|----------|
| 완전성 | 모든 파이프라인 단계가 로깅되는가? |
| 성능 | 로깅이 응답 지연에 영향을 주지 않는가? |
| 조회 | trace_id로 빠르게 조회 가능한가? |
| 보안 | 민감 정보가 필터링되는가? |

### 완료 기준

- [ ] audit_trail.jsonl 스키마 확정
- [ ] AuditLogger 클래스 구현 완료
- [ ] 모든 API 요청에서 로깅 동작
- [ ] /evidence/{trace_id} 엔드포인트 동작
- [ ] 로그 조회 성능 < 100ms

---

## Main-F3: 메타데이터 정비

**목표**: 근거 추적을 위한 메타데이터 파일 추가

### 배경 (Foundation의 문제점)

- `sources.yaml` 미구현 (문서 출처 정보 없음)
- `chunk_manifest.jsonl` 미구현 (청크 → 문서 역추적 불가)
- 근거 제시 시 정확한 페이지/섹션 참조 어려움

### 구현 태스크

```
Main-F3-1: sources.yaml 작성
├── data/processed/metadata/sources.yaml 생성
├── 각 문서의 출처 정보 정의
├── 버전, 날짜, URL 등 메타 정보
└── 검증: 기존 doc_id와 일치 확인

Main-F3-2: chunk_manifest.jsonl 생성
├── 기존 청킹 스크립트 수정
├── 각 청크의 원본 문서/페이지/섹션 매핑
├── 재인덱싱 수행
└── 검증: 청크 → 문서 역추적 테스트

Main-F3-3: 근거 추적 기능 구현
├── src/rag/retriever.py에 메타데이터 조회 추가
├── 응답에 정확한 citation 포함
└── 검증: 샘플 질문으로 근거 추적 테스트
```

### 예상 산출물

**sources.yaml**:
```yaml
documents:
  service_manual:
    title: "UR e-Series Service Manual"
    version: "5.12"
    date: "2023-06"
    pages: 328
    language: "en"
    url: "https://www.universal-robots.com/..."

  error_codes:
    title: "Error Codes Directory"
    version: "5.12"
    date: "2023-06"
    pages: 45
    language: "en"
```

**chunk_manifest.jsonl** (한 줄 예시):
```json
{
  "chunk_id": "error_codes_15_001",
  "doc_id": "error_codes",
  "page": 15,
  "section": "Communication Errors",
  "char_start": 2456,
  "char_end": 3128,
  "tokens": 187
}
```

### 코드 리뷰 체크포인트

| 항목 | 확인 내용 |
|------|----------|
| 정합성 | chunk_id가 기존 ChromaDB와 일치하는가? |
| 완전성 | 모든 청크가 manifest에 있는가? |
| 조회성능 | manifest 조회가 빠른가? |

### 완료 기준

- [ ] sources.yaml 작성 완료
- [ ] chunk_manifest.jsonl 생성 완료
- [ ] 모든 청크에 대해 원본 추적 가능
- [ ] 응답에 정확한 citation 포함

---

# Part 2: 센서 통합 Phase

---

## Main-S1: 센서 데이터 생성

**목표**: ATI Axia80 시뮬레이션 데이터 1개월치 생성

### 센서 개요

| 항목 | 값 |
|------|-----|
| 센서 | ATI Axia80 Force/Torque |
| 측정축 | 6축 (Fx, Fy, Fz, Tx, Ty, Tz) |
| 힘 범위 | ±500 N (Fx, Fy), ±1000 N (Fz) |
| 토크 범위 | ±20 Nm |
| 샘플링 | 125 Hz → 1초 평균 (저장) |
| 기간 | 1개월 (30일) |

### 구현 태스크

```
Main-S1-1: 데이터 생성기 구현
├── scripts/generate_sensor_data.py 작성
├── 정상 패턴 생성 (baseline)
├── 이상 패턴 삽입 (충돌, 진동, 과부하)
└── 검증: 데이터 분포 시각화

Main-S1-2: Parquet 저장
├── data/sensor/raw/axia80_2024_01.parquet 생성
├── 최적의 압축/파티션 설정
└── 검증: 파일 크기, 조회 성능

Main-S1-3: 센서 설정 파일
├── data/sensor/metadata/sensor_config.yaml 작성
├── 정상 범위, 이상 임계값 정의
└── 검증: 설정값 검증
```

### 데이터 스키마

```python
# Parquet 스키마
{
    "timestamp": datetime64[ns],  # UTC
    "Fx": float32,  # X축 힘 (N)
    "Fy": float32,  # Y축 힘 (N)
    "Fz": float32,  # Z축 힘 (N)
    "Tx": float32,  # X축 토크 (Nm)
    "Ty": float32,  # Y축 토크 (Nm)
    "Tz": float32,  # Z축 토크 (Nm)
    "status": string  # normal/warning/error
}
```

### 이상 패턴 시나리오

| Pattern | 설명 | 발생 빈도 | 특성 |
|---------|------|----------|------|
| `collision` | 충돌 | 일 2-5회 | Fz 급증 (>500N, <100ms) |
| `vibration` | 진동 | 일 1-2회 | 고주파 성분 증가 |
| `overload` | 과부하 | 일 0-1회 | 지속적 힘 초과 |
| `drift` | 드리프트 | 주 1회 | 점진적 baseline 이동 |

### 예상 산출물

**sensor_config.yaml**:
```yaml
sensor:
  model: "ATI Axia80"
  sampling_rate: 125  # Hz
  storage_rate: 1     # Hz (1초 평균)

thresholds:
  collision:
    Fz_spike: 500      # N
    rise_time_ms: 100
  vibration:
    fft_threshold: 50  # Hz
  overload:
    duration_s: 5

normal_ranges:
  Fx: [-100, 100]
  Fy: [-100, 100]
  Fz: [-200, 200]
  Tx: [-5, 5]
  Ty: [-5, 5]
  Tz: [-5, 5]
```

### 완료 기준

- [ ] 1개월치 데이터 생성 (~2.6M 레코드)
- [ ] 이상 패턴 삽입 (충돌 60-150회, 진동 30-60회 등)
- [ ] Parquet 파일 크기 < 500MB
- [ ] 데이터 분포 시각화 확인

---

## Main-S2: 패턴 감지

**목표**: 센서 데이터에서 이상 패턴 자동 감지

### 구현 태스크

```
Main-S2-1: PatternDetector 클래스
├── src/sensor/pattern_detector.py 작성
├── 충돌 감지 (spike detection)
├── 진동 감지 (FFT analysis)
├── 과부하 감지 (threshold duration)
└── 검증: 알려진 패턴 감지 테스트

Main-S2-2: 이상 패턴 저장
├── data/sensor/processed/anomaly_patterns.json 생성
├── 감지된 패턴 메타데이터 저장
└── 검증: 패턴 조회 기능

Main-S2-3: 에러코드 연관
├── 패턴 → 에러코드 매핑 정의
├── 온톨로지와 연결 준비
└── 검증: 매핑 정확도
```

### PatternDetector 인터페이스

```python
class PatternDetector:
    def __init__(self, config_path: str):
        self.config = load_yaml(config_path)

    def detect(
        self,
        data: pd.DataFrame,
        pattern_types: List[str] = None
    ) -> List[DetectedPattern]:
        """
        센서 데이터에서 이상 패턴 감지

        Args:
            data: 센서 데이터 (timestamp, Fx, Fy, Fz, Tx, Ty, Tz)
            pattern_types: 감지할 패턴 유형 (None이면 전체)

        Returns:
            감지된 패턴 목록
        """

@dataclass
class DetectedPattern:
    pattern_id: str
    type: str  # collision, vibration, overload, drift
    timestamp: datetime
    duration_ms: int
    metrics: Dict[str, float]  # peak_axis, peak_value, etc.
    confidence: float
    related_error_codes: List[str]
```

### 패턴 감지 알고리즘

| Pattern | 알고리즘 | 파라미터 |
|---------|---------|----------|
| `collision` | Spike Detection | threshold=500N, window=100ms |
| `vibration` | FFT + Peak Finding | freq_threshold=50Hz |
| `overload` | Threshold Duration | threshold=300N, duration=5s |
| `drift` | Baseline Deviation | window=1h, deviation=10% |

### 완료 기준

- [ ] PatternDetector 클래스 구현 완료
- [ ] 4가지 패턴 유형 감지 가능
- [ ] 감지 정확도(F1) > 85%
- [ ] anomaly_patterns.json 생성 완료
- [ ] 패턴 → 에러코드 매핑 정의

---

## Main-S3: Context Enricher

**목표**: 문서 검색 결과에 센서 맥락 추가

### 개념

```
Query → Vector Retrieval → Context Enricher → Verifier
              (문서)            (센서 추가)     (통합 검증)
```

### 구현 태스크

```
Main-S3-1: ContextEnricher 클래스
├── src/rag/context_enricher.py 작성
├── 에러코드 기반 센서 조회
├── 시간 윈도우 기반 조회
└── 검증: 샘플 쿼리로 enrichment 테스트

Main-S3-2: 문서-센서 상관관계 분석
├── 에러 발생 전후 센서 패턴 분석
├── 상관관계 레벨 결정 (STRONG/MODERATE/WEAK/NONE)
└── 검증: 상관관계 정확도

Main-S3-3: RAGService 통합
├── src/api/services/rag_service.py 수정
├── ContextEnricher 파이프라인 추가
└── 검증: 통합 테스트
```

### ContextEnricher 인터페이스

```python
class ContextEnricher:
    def enrich(
        self,
        query: str,
        doc_chunks: List[Chunk],
        error_code: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        time_window: str = "1h"
    ) -> EnrichedContext:
        """
        문서 청크에 센서 맥락 추가

        Returns:
            doc_evidence: 문서 근거
            sensor_evidence: 센서 근거
            correlation: 상관관계 분석
        """

@dataclass
class EnrichedContext:
    doc_evidence: List[DocEvidence]
    sensor_evidence: Optional[SensorEvidence]
    correlation: CorrelationResult

@dataclass
class SensorEvidence:
    patterns: List[DetectedPattern]
    statistics: Dict[str, AxisStats]
    time_range: Tuple[datetime, datetime]
    chart_data: List[Dict]  # 시각화용

@dataclass
class CorrelationResult:
    level: str  # STRONG, MODERATE, WEAK, NONE
    reason: str
    supporting_evidence: List[str]
```

### 상관관계 레벨 정의

| Level | 조건 | 예시 |
|-------|------|------|
| `STRONG` | 문서 원인 + 센서 패턴 일치 | "C119 발생 + 충돌 패턴 감지" |
| `MODERATE` | 문서 원인만 또는 센서만 | "C119 문서 확인, 센서 미확인" |
| `WEAK` | 관련 가능성 있음 | "진동 패턴 있으나 원인 불명확" |
| `NONE` | 센서 데이터 없음 | "센서 데이터 조회 불가" |

### 완료 기준

- [ ] ContextEnricher 클래스 구현 완료
- [ ] 상관관계 분석 로직 구현
- [ ] RAGService 통합 완료
- [ ] 통합 테스트 통과

---

## Main-S4: 온톨로지 확장

**목표**: 센서 패턴을 온톨로지에 통합

### 추가할 노드/관계

```
[기존]
(Component) --[HAS_ERROR]--> (ErrorCode)
(ErrorCode) --[RESOLVED_BY]--> (Resolution)
(ErrorCode) --[CAUSED_BY]--> (Cause)

[추가]
(SensorPattern) --[INDICATES]--> (Cause)
```

### 구현 태스크

```
Main-S4-1: SensorPattern 노드 정의
├── ontology.json에 SensorPattern 노드 추가
├── 속성: pattern_id, type, threshold
└── 검증: 스키마 검증

Main-S4-2: INDICATES 관계 추가
├── 센서패턴 → 원인 관계 정의
├── Neo4j에 적재
└── 검증: Cypher 쿼리 테스트

Main-S4-3: GraphRetriever 확장
├── src/rag/graph_retriever.py 수정
├── 센서 패턴 기반 추론 추가
└── 검증: 통합 테스트
```

### 온톨로지 확장 예시

**ontology.json 추가분**:
```json
{
  "nodes": {
    "SensorPattern": [
      {
        "pattern_id": "PAT_COLLISION",
        "type": "collision",
        "description": "Z축 충돌 패턴",
        "threshold": {"Fz": 500, "rise_time_ms": 100}
      },
      {
        "pattern_id": "PAT_VIBRATION",
        "type": "vibration",
        "description": "고주파 진동 패턴",
        "threshold": {"freq_min": 50}
      }
    ]
  },
  "relationships": [
    {
      "type": "INDICATES",
      "source": "PAT_COLLISION",
      "target": "CAUSE_PHYSICAL_CONTACT",
      "confidence": 0.9
    }
  ]
}
```

### Cypher 쿼리 예시

```cypher
-- 에러코드와 연관된 센서 패턴 조회
MATCH (e:ErrorCode {code: $code})-[:CAUSED_BY]->(c:Cause)<-[:INDICATES]-(sp:SensorPattern)
RETURN e.code, c.description, sp.type, sp.threshold
```

### 완료 기준

- [ ] SensorPattern 노드 4개 이상 정의
- [ ] INDICATES 관계 정의 완료
- [ ] Neo4j 적재 완료
- [ ] GraphRetriever 확장 완료

---

## Main-S5: Verifier 확장

**목표**: 이중 검증(문서+센서) 및 PARTIAL 상태 추가

### 기존 vs 확장

| 항목 | Foundation | Main |
|------|------------|------|
| Status | PASS, ABSTAIN, FAIL | + PARTIAL |
| 검증 대상 | 문서만 | 문서 + 센서 |
| Action 조건 | 문서 citation | 문서 필수 + 센서 보강 |

### 구현 태스크

```
Main-S5-1: Verifier 상태 확장
├── src/rag/verifier.py 수정
├── PARTIAL 상태 추가
├── 이중 검증 로직 구현
└── 검증: 상태별 테스트

Main-S5-2: Cause 검증 등급
├── DOC_AND_SENSOR, DOC_SUPPORTED, SENSOR_INDICATED, HYPOTHESIS
├── 등급별 신뢰도 반영
└── 검증: 등급 판정 테스트

Main-S5-3: 회귀 테스트
├── 기존 테스트 케이스 확인
├── 센서 없는 쿼리에서 기존 동작 유지
└── 검증: 회귀 없음 확인
```

### 검증 로직

```python
def determine_status(
    doc_verified: bool,
    sensor_verified: Optional[bool]
) -> str:
    """
    Verifier 상태 결정

    - doc_verified: 문서 근거 확인 여부
    - sensor_verified: 센서 근거 확인 여부 (None이면 센서 무관 질문)
    """
    if not doc_verified:
        return "ABSTAIN"  # 문서 근거 필수

    if sensor_verified is None:
        return "PASS"  # 센서 무관 질문

    if sensor_verified:
        return "PASS"  # 이중 검증 완료
    else:
        return "PARTIAL"  # 문서만 확인, 센서 불일치
```

### Cause 검증 등급

| 등급 | 조건 | 신뢰도 |
|------|------|--------|
| `DOC_AND_SENSOR` | 문서 + 센서 모두 지지 | 0.9+ |
| `DOC_SUPPORTED` | 문서 근거만 있음 | 0.7~0.9 |
| `SENSOR_INDICATED` | 센서 패턴만 있음 | 0.5~0.7 |
| `HYPOTHESIS` | 둘 다 부족 | <0.5 |

### 완료 기준

- [ ] PARTIAL 상태 구현 완료
- [ ] 이중 검증 로직 구현 완료
- [ ] Cause 검증 등급 구현 완료
- [ ] 기존 테스트 회귀 없음
- [ ] 새 테스트 케이스 추가

---

## Main-S6: API/UI 확장

**목표**: 센서 엔드포인트 및 대시보드 센서 페이지 추가

### API 확장

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/sensor/context` | 센서 맥락 조회 |
| GET | `/api/v1/sensor/chart` | 센서 차트 데이터 |
| GET | `/api/v1/sensor/patterns` | 감지된 패턴 목록 |

### 구현 태스크

```
Main-S6-1: 센서 API 구현
├── src/api/routes/sensor.py 작성
├── /sensor/context 엔드포인트
├── /sensor/chart 엔드포인트
├── /sensor/patterns 엔드포인트
└── 검증: API 테스트

Main-S6-2: 스키마 정의
├── src/api/schemas/sensor.py 작성
├── SensorContextRequest/Response
├── SensorChartRequest/Response
└── 검증: OpenAPI 문서 확인

Main-S6-3: 대시보드 센서 페이지
├── src/dashboard/pages/sensor.py 작성
├── 센서 시계열 차트
├── 패턴 감지 히스토리
├── 에러코드 연관 표시
└── 검증: UI 테스트

Main-S6-4: 센서 차트 컴포넌트
├── src/dashboard/components/sensor_chart.py 작성
├── Plotly 기반 시계열 차트
├── 이상 패턴 하이라이트
└── 검증: 시각화 확인
```

### API 스키마

**GET /api/v1/sensor/context**

Request:
```
?error_code=C119&time_window=1h
```

Response:
```json
{
  "error_code": "C119",
  "time_window": "1h",
  "patterns": [
    {
      "pattern_id": "PAT_001",
      "type": "collision",
      "timestamp": "2024-01-15T10:30:00Z",
      "confidence": 0.92
    }
  ],
  "statistics": {
    "Fz": {"mean": 45.2, "max": 850.5, "std": 120.3}
  }
}
```

**GET /api/v1/sensor/chart**

Request:
```
?start=2024-01-15T10:00:00Z&end=2024-01-15T11:00:00Z&axis=Fz
```

Response:
```json
{
  "axis": "Fz",
  "data": [
    {"timestamp": "2024-01-15T10:00:00Z", "value": 45.2},
    {"timestamp": "2024-01-15T10:00:01Z", "value": 47.8}
  ],
  "anomalies": [
    {"timestamp": "2024-01-15T10:30:00Z", "type": "collision"}
  ]
}
```

### 대시보드 센서 페이지 구성

```
┌─────────────────────────────────────────────────────────────┐
│ 센서 모니터링                                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [시간 범위 선택] [축 선택: Fx Fy Fz Tx Ty Tz]               │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │              시계열 차트 (Plotly)                       │ │
│ │                    ▲                                    │ │
│ │                   ┌┴┐← 이상 패턴 하이라이트            │ │
│ │    ─────────────┘  └───────────────────                │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 감지된 패턴                                                 │
│ ┌──────────┬──────────┬──────────┬────────────┐            │
│ │ 시간     │ 유형     │ 신뢰도   │ 연관 에러  │            │
│ ├──────────┼──────────┼──────────┼────────────┤            │
│ │ 10:30:00 │ collision│ 92%      │ C119, C153 │            │
│ │ 14:15:00 │ vibration│ 87%      │ C204      │            │
│ └──────────┴──────────┴──────────┴────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### 완료 기준

- [ ] 센서 API 3개 엔드포인트 구현 완료
- [ ] API 스키마 정의 완료
- [ ] 대시보드 센서 페이지 구현 완료
- [ ] 센서 차트 컴포넌트 구현 완료
- [ ] 통합 테스트 통과

---

# 통합 테스트 시나리오

## 시나리오 1: 충돌 에러 진단

```
[입력] "C119 에러가 발생했어요. 방금 전에 이상한 소리가 났습니다."

[예상 동작]
1. Query Analyzer: error_code=C119, 충돌 가능성 감지
2. Entity Linker: C119 → ERR_C119
3. Graph Retriever: C119 → Safety Limit Violation → 원인/조치 조회
4. Vector Retriever: "C119" 관련 문서 청크 검색
5. Context Enricher: 최근 1시간 센서 데이터 조회, 충돌 패턴 감지
6. Verifier: 문서 근거 O, 센서 근거 O → PASS (DOC_AND_SENSOR)
7. Generator:
   - 원인: "안전 한계 초과 (문서 확인) + Z축 충돌 패턴 감지 (센서 확인)"
   - 조치: "Safety Reset 수행 (Service Manual p.45)"
   - 센서: "10:30에 Fz 850N 급증 감지"

[출력]
{
  "verifier_status": "PASS",
  "answer": "C119 에러는 안전 한계 초과로 발생합니다. 센서 데이터 분석 결과, 10:30에 Z축 충돌이 감지되었습니다...",
  "causes": [{"title": "Z축 충돌", "evidence_type": "DOC_AND_SENSOR"}],
  "actions": [{"title": "Safety Reset 수행", "doc_refs": [...]}],
  "sensor_context": {"patterns": [...], "chart_url": "..."}
}
```

## 시나리오 2: 문서만으로 답변 (센서 무관)

```
[입력] "UR5e의 작업반경은 얼마인가요?"

[예상 동작]
1. Query Analyzer: 일반 질문, 센서 불필요
2. Vector Retriever: 작업반경 관련 문서 검색
3. Context Enricher: 센서 조회 스킵
4. Verifier: 문서 근거 O, 센서 N/A → PASS
5. Generator: 문서 기반 답변

[출력]
{
  "verifier_status": "PASS",
  "answer": "UR5e의 작업반경은 850mm입니다. (User Manual p.12)",
  "sensor_context": null
}
```

## 시나리오 3: 센서 불일치 경고

```
[입력] "C119 에러가 발생했어요."

[예상 동작]
1. Context Enricher: 센서 조회, 이상 패턴 없음
2. Verifier: 문서 근거 O, 센서 근거 X → PARTIAL

[출력]
{
  "verifier_status": "PARTIAL",
  "answer": "C119 에러는 안전 한계 초과입니다. 단, 최근 센서 데이터에서 충돌 패턴이 감지되지 않았습니다. 다른 원인일 수 있습니다.",
  "warning": "센서 데이터와 불일치"
}
```

---

# 마일스톤

## 마일스톤 1: Foundation 개선 완료 (Main-F)

| 태스크 | 주요 산출물 |
|--------|------------|
| Main-F1 | lexicon.yaml, rules.yaml, 개선된 EntityLinker |
| Main-F2 | audit_trail.jsonl, AuditLogger |
| Main-F3 | sources.yaml, chunk_manifest.jsonl |

**완료 기준**: 기존 벤치마크 성능 유지 + 추적 기능 동작

---

## 마일스톤 2: 센서 데이터 파이프라인 (Main-S1~S2)

| 태스크 | 주요 산출물 |
|--------|------------|
| Main-S1 | axia80_2024_01.parquet, sensor_config.yaml |
| Main-S2 | PatternDetector, anomaly_patterns.json |

**완료 기준**: 1개월치 데이터 생성 + 패턴 감지 F1 > 85%

---

## 마일스톤 3: RAG 통합 (Main-S3~S5)

| 태스크 | 주요 산출물 |
|--------|------------|
| Main-S3 | ContextEnricher |
| Main-S4 | 확장된 ontology.json |
| Main-S5 | 확장된 Verifier |

**완료 기준**: 이중 검증 동작 + 통합 테스트 통과

---

## 마일스톤 4: API/UI 완성 (Main-S6)

| 태스크 | 주요 산출물 |
|--------|------------|
| Main-S6 | 센서 API 3개, 대시보드 센서 페이지 |

**완료 기준**: 전체 시나리오 동작 + 데모 가능

---

# 코드 리뷰 체크리스트 (공통)

각 Phase 완료 시 다음 항목을 검토합니다:

## 1. Spec 일치
- [ ] Main__Spec.md의 스키마/인터페이스와 일치하는가?
- [ ] API 응답 형식이 Spec과 동일한가?

## 2. 테스트
- [ ] 핵심 로직에 단위 테스트가 있는가?
- [ ] 경계 조건이 테스트되었는가?
- [ ] 통합 테스트가 있는가?

## 3. 에러 처리
- [ ] 예외 상황이 처리되는가?
- [ ] Fallback 로직이 있는가?
- [ ] 사용자에게 적절한 에러 메시지가 반환되는가?

## 4. 성능
- [ ] 응답 시간이 합리적인가? (< 3초)
- [ ] 메모리 사용이 적절한가?
- [ ] 캐싱이 필요한 곳에 적용되었는가?

## 5. 보안
- [ ] 민감 정보가 노출되지 않는가?
- [ ] 입력 검증이 있는가?

## 6. 로깅
- [ ] 디버깅에 충분한 로그가 있는가?
- [ ] 로그 레벨이 적절한가?
- [ ] trace_id가 로그에 포함되는가?

---

# 진행 원칙

1. **한 Phase씩** - 다음 Phase로 넘어가기 전에 현재 Phase 완료
2. **문서 먼저** - 코드 작성 전에 설계/스키마 확정
3. **Spec 참조** - Main__Spec.md를 기준으로 구현
4. **테스트 필수** - 기능 구현 후 반드시 테스트 작성
5. **리뷰 후 진행** - 코드 리뷰 체크리스트 확인 후 다음 단계

---

# 문서 구조

```
docs/
├── Foundation_Spec.md        # 레퍼런스 (원본)
├── Foundation_ROADMAP.md     # 레퍼런스 (원본)
├── Foundation_Phase*.md      # Foundation Phase별 완료보고서
│
├── Main__Spec.md             # 현재 기술 설계서 (완전판)
├── Main__ROADMAP.md          # 현재 문서 (로드맵 완전판)
└── Main__Phase*.md           # Main Phase별 완료보고서 (작성 예정)
```

---

**문서 버전**: Main v1.0
**작성일**: 2024-01-21
**기반 문서**: Foundation_ROADMAP.md
**참조 문서**: Main__Spec.md
**작성자**: Claude (AI Assistant)
