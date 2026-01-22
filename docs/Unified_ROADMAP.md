# UR5e Ontology-based Manufacturing AX System - 개발 로드맵

> **Version**: 2.0
> **최종 수정**: 2026-01-22
> **문서 목적**: 온톨로지 기반 제조 AX 시스템 개발 로드맵
> **참고 문서**: Unified_Spec.md, 온톨로지_스키마_설계.md

---

## 목차

1. [로드맵 개요](#1-로드맵-개요)
2. [개발 원칙](#2-개발-원칙)
3. [Phase 구조](#3-phase-구조)
4. [Phase 상세](#4-phase-상세)
5. [마일스톤](#5-마일스톤)
6. [의존성 맵](#6-의존성-맵)
7. [체크리스트](#7-체크리스트)

---

# 1. 로드맵 개요

## 1.1 프로젝트 목표 (복습)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Project Goals                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [1차 목표] 온톨로지 기반 제조 AI의 개념 증명 (PoC)                      │
│            → 룰베이스와 다른 "관계 기반 추론" 시연                       │
│                                                                          │
│  [2차 목표] 팔란티어 스타일 관계 시각화 데모                             │
│            → 클릭으로 탐색 가능한 관계 그래프                            │
│                                                                          │
│  [3차 목표] 룰베이스 → 온톨로지 전환의 가치 입증                         │
│            → 동일 질문에 대한 두 방식의 응답 비교                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 1.2 개발 흐름 요약

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Development Flow                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STAGE 1: Foundation (기반 구축)                                 │    │
│  │ Phase 1-3                                                       │    │
│  │ 환경 설정 → 데이터 준비 → 문서 인덱싱                           │    │
│  └────────────────────────────────┬────────────────────────────────┘    │
│                                   │                                      │
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STAGE 2: Ontology Core (온톨로지 핵심)       ★ 핵심 단계 ★      │    │
│  │ Phase 4-6                                                       │    │
│  │ 온톨로지 설계 → 엔티티/관계 구축 → 추론 규칙                     │    │
│  └────────────────────────────────┬────────────────────────────────┘    │
│                                   │                                      │
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STAGE 3: Sensor Integration (센서 통합)                         │    │
│  │ Phase 7-9                                                       │    │
│  │ 센서 데이터 → 패턴 감지 → 온톨로지 연결                          │    │
│  └────────────────────────────────┬────────────────────────────────┘    │
│                                   │                                      │
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STAGE 4: Query Engine (질의 엔진)                               │    │
│  │ Phase 10-12                                                     │    │
│  │ 질문 분류 → 온톨로지 추론 → 응답 생성                            │    │
│  └────────────────────────────────┬────────────────────────────────┘    │
│                                   │                                      │
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STAGE 5: Palantir-style UI (팔란티어 스타일 UI)                 │    │
│  │ Phase 13-15                                                     │    │
│  │ 대시보드 → 관계 그래프 → 인터랙션                                │    │
│  └────────────────────────────────┬────────────────────────────────┘    │
│                                   │                                      │
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STAGE 6: Demo & Evaluation (데모 및 평가)                       │    │
│  │ Phase 16-17                                                     │    │
│  │ 통합 테스트 → 데모 시나리오 → 평가                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 2. 개발 원칙

## 2.1 핵심 원칙

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Development Principles                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Ontology-first (온톨로지 우선)                                      │
│     ─────────────────────────────                                       │
│     모든 기능은 온톨로지와 어떻게 연결되는지 먼저 정의                   │
│     "이 기능이 온톨로지의 어떤 부분을 활용하는가?"                       │
│                                                                          │
│  2. Incremental Value (점진적 가치)                                     │
│     ────────────────────────────                                        │
│     각 Phase 완료 시 데모 가능한 가치 산출물                             │
│     "이 Phase만으로 무엇을 보여줄 수 있는가?"                            │
│                                                                          │
│  3. Evidence-driven (근거 기반)                                         │
│     ────────────────────────                                            │
│     모든 응답에 근거 (온톨로지 경로 + 문서) 포함                         │
│     "이 답변의 근거는 무엇인가?"                                         │
│                                                                          │
│  4. Palantir-inspired (팔란티어 영감)                                   │
│     ─────────────────────────────                                       │
│     관계 시각화를 통한 직관적 이해                                       │
│     "클릭으로 탐색할 수 있는가?"                                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Phase 진행 규칙

| 규칙 | 설명 |
|------|------|
| **순차 진행** | Phase N 완료 후 Phase N+1 진행 (의존성 있는 경우) |
| **독립 병행** | 의존성 없는 Phase는 병행 가능 |
| **산출물 필수** | 각 Phase는 명확한 산출물 보유 |
| **테스트 포함** | 각 Phase 완료 전 해당 기능 테스트 |
| **문서 업데이트** | 변경사항은 관련 문서에 반영 |

---

# 3. Phase 구조

## 3.1 전체 Phase 목록

| Stage | Phase | 제목 | 핵심 산출물 |
|-------|-------|------|------------|
| **1. Foundation** | 1 | 환경 설정 | 개발 환경, 의존성 |
| | 2 | 데이터 준비 | PDF 청크, 센서 데이터 |
| | 3 | 문서 인덱싱 | ChromaDB 인덱스 |
| **2. Ontology** | 4 | 온톨로지 스키마 | 4-Domain 정의 |
| | 5 | 엔티티/관계 구축 | ontology.json |
| | 6 | 추론 규칙 | rules.yaml |
| **3. Sensor** | 7 | 센서 데이터 처리 | Parquet 저장소 |
| | 8 | 패턴 감지 | PatternDetector |
| | 9 | 온톨로지 연결 | 패턴→에러 매핑 |
| **4. Query** | 10 | 질문 분류기 | QueryClassifier |
| | 11 | 온톨로지 추론 | OntologyEngine |
| | 12 | 응답 생성 | ResponseGenerator |
| **5. UI** | 13 | 기본 대시보드 | Streamlit UI |
| | 14 | 관계 그래프 | D3.js 시각화 |
| | 15 | 인터랙션 | 클릭 탐색 |
| **6. Demo** | 16 | 통합 테스트 | E2E 테스트 |
| | 17 | 데모 시나리오 | 3가지 시나리오 |

## 3.2 온톨로지 관점에서의 Phase 분류

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Phases by Ontology Domain                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [Equipment Domain]                                                      │
│  ─────────────────                                                      │
│  Phase 4: 장비 엔티티 정의 (UR5e, Joints, ControlBox)                   │
│  Phase 5: 장비 관계 구축 (HAS_COMPONENT)                                │
│                                                                          │
│  [Measurement Domain]                                                    │
│  ────────────────────                                                   │
│  Phase 4: 센서/측정 엔티티 정의 (Axia80, Axes, States)                  │
│  Phase 7-8: 센서 데이터 처리, 패턴 감지                                 │
│  Phase 9: 패턴→원인/에러 연결                                           │
│                                                                          │
│  [Knowledge Domain]                                                      │
│  ─────────────────                                                      │
│  Phase 3: 문서 인덱싱 (에러코드, 해결책)                                │
│  Phase 5: 지식 관계 구축 (CAUSED_BY, RESOLVED_BY)                       │
│  Phase 6: 추론 규칙 정의                                                │
│                                                                          │
│  [Context Domain]                                                        │
│  ────────────────                                                       │
│  Phase 5: 컨텍스트 엔티티 정의 (Shift, Product)                         │
│  Phase 11: 맥락 기반 추론                                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 4. Phase 상세

---

## STAGE 1: Foundation (기반 구축)

### Phase 1: 환경 설정

**목표**: 개발 환경 구축

**태스크**:
- [ ] Python 3.10+ 설치 확인
- [ ] 가상환경 생성 (`venv`)
- [ ] 의존성 설치 (`pip install -r requirements.txt`)
- [ ] OpenAI API 키 설정 (`.env`)
- [ ] IDE 설정 (VSCode 권장)

**산출물**:
- 동작하는 개발 환경
- `.env` 파일
- `requirements.txt` 검증됨

**온톨로지 연결**: 없음 (인프라)

**검증**:
```bash
python --version  # >= 3.10
pip list          # 패키지 확인
python -c "import chromadb; print('OK')"
```

---

### Phase 2: 데이터 준비

**목표**: 원천 데이터 확보 및 전처리

**태스크**:
- [ ] PDF 문서 3종 확보 (이미 완료됨)
- [ ] PDF → 텍스트 청킹 (이미 완료됨: 722 chunks)
- [ ] 센서 데이터 확인 (이미 완료됨: 7일, 604,800 레코드)
- [ ] 메타데이터 검증 (`sources.yaml`)

**산출물**:
- `data/processed/chunks/*.json` (722 chunks)
- `data/sensor/raw/axia80_week_01.parquet`
- `data/processed/metadata/sources.yaml`

**온톨로지 연결**:
- Knowledge Domain의 Document 엔티티와 연결될 데이터

**검증**:
```python
# 청크 수 확인
import json
chunks = json.load(open('data/processed/chunks/user_manual_chunks.json'))
print(f"Chunks: {len(chunks)}")

# 센서 데이터 확인
import pandas as pd
df = pd.read_parquet('data/sensor/raw/axia80_week_01.parquet')
print(f"Records: {len(df)}")
```

---

### Phase 3: 문서 인덱싱

**목표**: ChromaDB에 문서 벡터 인덱싱

**태스크**:
- [ ] ChromaDB 컬렉션 생성
- [ ] 청크 임베딩 생성 (OpenAI text-embedding-3-small)
- [ ] 인덱스 저장 (`stores/chroma/`)
- [ ] 검색 테스트

**산출물**:
- `stores/chroma/` (영속 인덱스)
- `src/embedding/vector_store.py`

**온톨로지 연결**:
- Knowledge Domain: 문서 청크가 온톨로지의 Document/ErrorCode와 연결

**검증**:
```python
# 검색 테스트
from src.embedding.vector_store import VectorStore
vs = VectorStore()
results = vs.search("C153 에러 해결 방법", top_k=3)
print(results)
```

---

## STAGE 2: Ontology Core (온톨로지 핵심) ★

### Phase 4: 온톨로지 스키마 설계

**목표**: 4-Domain 온톨로지 스키마 정의

**태스크**:
- [ ] Equipment Domain 정의 (UR5e, Joints, ControlBox)
- [ ] Measurement Domain 정의 (Axia80, Axes, States, Patterns)
- [ ] Knowledge Domain 정의 (ErrorCodes, Causes, Resolutions)
- [ ] Context Domain 정의 (Shifts, Products, WorkCycles)
- [ ] 관계 타입 정의 (13개)

**산출물**:
- `data/processed/ontology/schema.yaml` (스키마 정의)
- `docs/온톨로지_스키마_설계.md` (이미 완료됨)

**온톨로지 연결**: 전체 온톨로지의 뼈대

**핵심 스키마**:
```yaml
domains:
  equipment:
    entities: [Robot, Joint, ControlBox, ToolFlange]
  measurement:
    entities: [Sensor, MeasurementAxis, State, Pattern]
  knowledge:
    entities: [ErrorCode, Cause, Resolution, Document]
  context:
    entities: [Shift, Product, WorkCycle]

relationships:
  - HAS_COMPONENT
  - MOUNTED_ON
  - MEASURES
  - HAS_STATE
  - INDICATES
  - TRIGGERS
  - CAUSED_BY
  - RESOLVED_BY
  - DOCUMENTED_IN
  - OCCURS_DURING
  - INVOLVES
```

---

### Phase 5: 엔티티/관계 구축

**목표**: 온톨로지 인스턴스 데이터 생성

**태스크**:
- [ ] Equipment 인스턴스 생성 (UR5e, Joint_0~5, ...)
- [ ] Measurement 인스턴스 생성 (Axia80, Fz, PAT_COLLISION, ...)
- [ ] Knowledge 인스턴스 생성 (C153, C189, CAUSE_*, RES_*, ...)
- [ ] Context 인스턴스 생성 (SHIFT_A/B/C, PART-A/B/C, ...)
- [ ] 관계 연결

**산출물**:
- `data/processed/ontology/ontology.json` (전체 온톨로지)
- `data/processed/ontology/lexicon.yaml` (동의어 사전)

**온톨로지 연결**: 실제 온톨로지 데이터

**ontology.json 구조**:
```json
{
  "entities": {
    "UR5e": {
      "type": "Robot",
      "domain": "equipment",
      "properties": { "payload_kg": 5.0, ... }
    },
    "Fz": {
      "type": "MeasurementAxis",
      "domain": "measurement",
      "properties": { "range": [-235, 235], "normal_range": [-60, 0] }
    },
    ...
  },
  "relationships": [
    { "source": "UR5e", "relation": "HAS_COMPONENT", "target": "Joint_0" },
    { "source": "Axia80", "relation": "MOUNTED_ON", "target": "ToolFlange" },
    { "source": "PAT_COLLISION", "relation": "TRIGGERS", "target": "C153" },
    ...
  ]
}
```

---

### Phase 6: 추론 규칙

**목표**: 온톨로지 기반 추론 규칙 정의

**태스크**:
- [ ] 상태 추론 규칙 (Fz 값 → State)
- [ ] 패턴 추론 규칙 (센서 데이터 → Pattern)
- [ ] 원인 추론 규칙 (Pattern + Context → Cause)
- [ ] 예측 규칙 (Pattern 반복 → Error 예측)

**산출물**:
- `configs/rules.yaml`
- `src/ontology/rule_engine.py`

**온톨로지 연결**: 추론 규칙이 온톨로지 관계를 활용

**rules.yaml 예시**:
```yaml
state_rules:
  - name: "FZ_STATE"
    condition: "Fz in range"
    mappings:
      - range: [-20, -10]
        state: "IDLE"
      - range: [-70, -40]
        state: "NORMAL_LOAD"
      - range: [-200, -100]
        state: "WARNING"

pattern_rules:
  - name: "COLLISION"
    condition: "abs(delta_Fz) > 500N within 100ms"
    output:
      pattern: "PAT_COLLISION"
      confidence: 0.95

cause_rules:
  - name: "RECURRING_OVERLOAD"
    condition:
      - pattern: "PAT_OVERLOAD"
      - product: "PART-C"
      - similar_events: ">= 3 in 4 days"
    output:
      cause: "CAUSE_GRIP_POSITION"
      confidence: 0.85

prediction_rules:
  - name: "PREDICT_C189"
    condition:
      - overload_count: ">= 3 in 4 days"
      - same_time_window: true
      - trend: "increasing"
    output:
      error: "C189"
      probability: 0.85
      timeframe: "24h"
```

---

## STAGE 3: Sensor Integration (센서 통합)

### Phase 7: 센서 데이터 처리

**목표**: 센서 데이터 저장소 및 조회 API

**태스크**:
- [ ] Parquet 데이터 로드
- [ ] 시간 범위 조회 API
- [ ] 통계 계산 (mean, std, min, max)
- [ ] 이상치 마킹

**산출물**:
- `src/sensor/sensor_store.py`
- `src/sensor/data_loader.py`

**온톨로지 연결**:
- Measurement Domain의 실제 데이터 소스

**인터페이스**:
```python
class SensorStore:
    def get_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """시간 범위 데이터 조회"""

    def get_statistics(self, axis: str, window: str) -> Dict:
        """축별 통계"""

    def get_current_state(self) -> Dict[str, str]:
        """현재 상태 (각 축별)"""
```

---

### Phase 8: 패턴 감지

**목표**: 센서 데이터에서 이상 패턴 자동 감지

**태스크**:
- [ ] Collision 감지 (급격한 변화)
- [ ] Overload 감지 (임계값 초과 지속)
- [ ] Vibration 감지 (표준편차 증가)
- [ ] Drift 감지 (baseline 이동)

**산출물**:
- `src/sensor/pattern_detector.py`
- `data/sensor/processed/detected_patterns.json` (이미 존재: 17개)

**온톨로지 연결**:
- Measurement Domain: Pattern 엔티티 인스턴스 생성

**인터페이스**:
```python
class PatternDetector:
    def detect(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """패턴 감지"""

    def detect_collision(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """충돌 패턴"""

    def detect_overload(self, data: pd.DataFrame) -> List[DetectedPattern]:
        """과부하 패턴"""
```

---

### Phase 9: 온톨로지 연결

**목표**: 감지된 패턴을 온톨로지와 연결

**태스크**:
- [ ] 패턴 → 에러코드 매핑
- [ ] 패턴 → 원인 매핑
- [ ] 이벤트 → 컨텍스트 연결 (시간대, 제품)
- [ ] 관계 그래프 업데이트

**산출물**:
- `configs/error_pattern_mapping.yaml`
- `src/sensor/ontology_connector.py`

**온톨로지 연결**:
- INDICATES, TRIGGERS 관계 활성화
- OCCURS_DURING, INVOLVES 관계 생성

**매핑 예시**:
```yaml
pattern_error_mapping:
  PAT_COLLISION:
    triggers:
      - code: "C153"
        confidence: 0.95
      - code: "C119"
        confidence: 0.80
    indicates:
      - cause: "CAUSE_PHYSICAL_CONTACT"
        confidence: 0.95

  PAT_OVERLOAD:
    triggers:
      - code: "C189"
        confidence: 0.90
    indicates:
      - cause: "CAUSE_PAYLOAD_EXCEEDED"
        confidence: 0.85
      - cause: "CAUSE_GRIP_POSITION"
        confidence: 0.70
```

---

## STAGE 4: Query Engine (질의 엔진)

### Phase 10: 질문 분류기

**목표**: 질문 유형 자동 분류

**태스크**:
- [ ] 온톨로지성 질문 감지 (관계/맥락 추론 필요)
- [ ] 하이브리드 질문 감지 (온톨로지 + 문서)
- [ ] 일반 RAG 질문 감지 (문서 검색만)
- [ ] 엔티티 추출
- [ ] **Evidence Schema 형식 정의** (doc_id, page, chunk_id)

**산출물**:
- `src/rag/query_classifier.py`
- `src/rag/entity_extractor.py`
- `src/rag/evidence_schema.py` (Evidence 데이터 모델)

**온톨로지 연결**:
- 질문에서 온톨로지 엔티티 식별

**인터페이스**:
```python
class QueryClassifier:
    def classify(self, query: str) -> QueryType:
        """질문 유형 분류"""
        # Returns: ONTOLOGY, HYBRID, RAG

class EntityExtractor:
    def extract(self, query: str) -> List[Entity]:
        """질문에서 엔티티 추출"""
        # "Fz가 350N" → [("Fz", "MeasurementAxis"), ("350N", "Value")]
```

**분류 기준**:
```yaml
ontology_indicators:
  - 센서 값 + "뭐야", "왜"
  - 패턴 언급 + 원인 질문
  - 예측 요청

hybrid_indicators:
  - 에러코드 + "왜", "자주"
  - 해결 + 맥락

rag_indicators:
  - 사양 질문 ("몇 kg", "범위")
  - 절차 질문 ("어떻게")
```

---

### Phase 11: 온톨로지 추론

**목표**: 온톨로지 기반 추론 엔진

**태스크**:
- [ ] 엔티티 컨텍스트 로딩
- [ ] 관계 탐색 (경로 찾기)
- [ ] 규칙 기반 추론 실행
- [ ] 예측 생성

**산출물**:
- `src/ontology/ontology_engine.py`
- `src/ontology/graph_traverser.py`

**온톨로지 연결**: 온톨로지의 핵심 활용 지점

**인터페이스**:
```python
class OntologyEngine:
    def reason(self, query: str, entities: List[Entity]) -> ReasoningResult:
        """온톨로지 기반 추론"""

    def get_context(self, entity_id: str) -> EntityContext:
        """엔티티 컨텍스트 로딩"""

    def find_path(self, source: str, target: str) -> List[Relationship]:
        """관계 경로 탐색"""

    def predict(self, patterns: List[Pattern]) -> Prediction:
        """예측 생성"""
```

**추론 파이프라인**:
```
입력: "Fz가 350N인데 이게 뭐야?"
    │
    ▼
1. 엔티티 인식 → Fz, 350N
    │
    ▼
2. 컨텍스트 로딩 → Fz.normal_range, Fz.states
    │
    ▼
3. 상태 추론 → 350N → CRITICAL
    │
    ▼
4. 패턴 매칭 → PAT_OVERLOAD
    │
    ▼
5. 관계 탐색 → PAT_OVERLOAD → CAUSE_* → RES_*
    │
    ▼
6. 이력 분석 → EVT-003, EVT-004, EVT-005
    │
    ▼
7. 예측 → C189, 85%, 24h
    │
    ▼
출력: ReasoningResult
```

---

### Phase 12: 응답 생성

**목표**: 추론 결과를 자연어 응답으로 변환

**태스크**:
- [ ] 구조화된 응답 포맷 정의
- [ ] LLM 기반 자연어 생성
- [ ] 근거 첨부 (온톨로지 경로 + 문서)
- [ ] 그래프 데이터 생성
- [ ] **ABSTAIN 케이스 처리** (신뢰도 < 임계값 시 "증거 부족" 응답)
- [ ] **Evidence Schema 출력** (doc_id/page/chunk_id 포함)

**산출물**:
- `src/rag/response_generator.py`
- `src/rag/prompt_builder.py`
- `src/rag/confidence_gate.py` (신뢰도 기반 응답 검증)

**온톨로지 연결**:
- 온톨로지 경로를 응답 근거로 포함

**응답 구조**:
```json
{
  "answer": "자연어 설명...",
  "analysis": { "entity": "Fz", "state": "CRITICAL", ... },
  "reasoning": { "pattern": "PAT_OVERLOAD", "cause": "...", "confidence": 0.85 },
  "prediction": { "error_code": "C189", "probability": 0.85 },
  "recommendation": { "immediate": "...", "reference": "..." },
  "evidence": {
    "ontology_path": "Fz → CRITICAL → PAT_OVERLOAD → C189",
    "document_refs": [
      { "doc_id": "service_manual", "page": 45, "chunk_id": "SM-045-01" }
    ]
  },
  "abstain": false,
  "abstain_reason": null,
  "graph": { "nodes": [...], "edges": [...] }
}
```

**ABSTAIN 응답 예시** (신뢰도 < 0.5):
```json
{
  "answer": "해당 질문에 대한 충분한 근거를 찾지 못했습니다.",
  "abstain": true,
  "abstain_reason": "confidence below threshold (0.35 < 0.5)",
  "evidence": { "document_refs": [] }
}
```

---

## STAGE 5: Palantir-style UI (팔란티어 스타일 UI)

### Phase 13: 기본 대시보드

**목표**: Streamlit 기반 메인 대시보드

**태스크**:
- [ ] 레이아웃 구성 (사이드바 + 메인)
- [ ] 질문 입력 인터페이스
- [ ] 답변 표시 영역
- [ ] 센서 상태 표시

**산출물**:
- `src/dashboard/app.py`
- `src/dashboard/pages/main.py`

**온톨로지 연결**:
- 현재 센서 상태를 온톨로지 State로 표시

**레이아웃**:
```
┌─────────────────────────────────────────────────────────────────┐
│  UR5e Ontology Dashboard                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────────────────────────────────┐  │
│  │ Status      │  │ Query                                    │  │
│  │ Fz: -52N ✓ │  │ ┌─────────────────────────────────────┐ │  │
│  │ Status: OK  │  │ │ 질문 입력...                        │ │  │
│  └─────────────┘  │ └─────────────────────────────────────┘ │  │
│                   │                                          │  │
│                   │ Answer:                                  │  │
│                   │ [구조화된 응답]                          │  │
│                   └─────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Phase 14: 관계 그래프 시각화

**목표**: D3.js 기반 온톨로지 관계 그래프

**태스크**:
- [ ] D3.js 그래프 컴포넌트 구현
- [ ] 노드/엣지 렌더링
- [ ] 하이라이트 기능
- [ ] Streamlit 통합 (iframe 또는 컴포넌트)

**산출물**:
- `src/dashboard/components/graph.py`
- `src/dashboard/static/graph.js`

**온톨로지 연결**: 온톨로지 관계를 시각적으로 표현

**시각화 요소**:
```
노드 타입별 색상:
- Equipment: 파란색
- Measurement: 녹색
- Knowledge: 빨간색
- Context: 노란색

엣지 스타일:
- 실선: 정적 관계 (HAS_COMPONENT, MOUNTED_ON)
- 점선: 동적 관계 (INDICATES, TRIGGERS)
```

---

### Phase 15: 인터랙션

**목표**: 클릭으로 탐색 가능한 그래프

**태스크**:
- [ ] 노드 클릭 → 상세 정보
- [ ] 엣지 클릭 → 관계 설명
- [ ] 더블클릭 → 확장/축소
- [ ] 검색/필터 기능

**산출물**:
- `src/dashboard/components/interactive_graph.py`
- 업데이트된 `graph.js`

**온톨로지 연결**:
- 노드 클릭 시 해당 엔티티의 온톨로지 정보 표시

**인터랙션 명세**:
```
[노드 클릭]
→ 사이드 패널에 엔티티 상세 정보 표시
→ 연결된 관계 하이라이트
→ 관련 문서 링크 제공

[엣지 클릭]
→ 관계 타입 설명
→ 동일 관계의 다른 예시 표시

[더블클릭]
→ 하위 노드 확장/축소
→ 깊이 제한 설정 가능

[검색]
→ 엔티티 이름으로 검색
→ 검색 결과 하이라이트
```

---

## STAGE 6: Demo & Evaluation (데모 및 평가)

### Phase 16: 통합 테스트

**목표**: End-to-End 테스트

**태스크**:
- [ ] 온톨로지 로딩 테스트
- [ ] 질문 분류 테스트
- [ ] 추론 파이프라인 테스트
- [ ] UI 통합 테스트

**산출물**:
- `tests/integration/`
- 테스트 결과 보고서

**테스트 케이스**:
```python
# 온톨로지성 질문 테스트
def test_ontology_query():
    query = "Fz가 350N인데 이게 뭐야?"
    result = engine.process(query)

    assert result.query_type == "ONTOLOGY"
    assert result.analysis.state == "CRITICAL"
    assert "PAT_OVERLOAD" in result.reasoning.pattern
    assert result.prediction.error_code == "C189"
    assert result.evidence.ontology_path is not None

# 맥락 반영 테스트
def test_context_awareness():
    query = "어제 14시쯤 이상했는데 왜 그랬지?"
    result = engine.process(query)

    assert "SHIFT_B" in result.context
    assert len(result.reasoning.similar_events) > 0
```

---

### Phase 17: 데모 시나리오

**목표**: 3가지 핵심 데모 시나리오 준비

**태스크**:
- [ ] 시나리오 1: 온톨로지 추론 데모
- [ ] 시나리오 2: 맥락 인식 데모
- [ ] 시나리오 3: 예측 데모
- [ ] 룰베이스 vs 온톨로지 비교 데모

**산출물**:
- `docs/demo_scenarios.md`
- 스크린샷/영상

**시나리오 상세**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Demo Scenario 1: 온톨로지 추론                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [시연 내용]                                                            │
│  질문: "Fz가 350N인데 이게 뭐야?"                                       │
│                                                                          │
│  [보여줄 것]                                                            │
│  1. 엔티티 인식 (Fz, 350N)                                              │
│  2. 상태 추론 (CRITICAL)                                                │
│  3. 패턴 연결 (PAT_OVERLOAD)                                            │
│  4. 원인 추론 (CAUSE_GRIP_POSITION)                                     │
│  5. 관계 그래프 시각화                                                   │
│  6. 근거 (온톨로지 경로 + 문서)                                          │
│                                                                          │
│  [룰베이스 비교]                                                        │
│  룰베이스: "정상 범위 초과" (끝)                                         │
│  온톨로지: 구조화된 분석 + 원인 + 해결책 + 근거                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    Demo Scenario 2: 맥락 인식                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [시연 내용]                                                            │
│  질문: "어제 14시쯤 이상했는데 왜 그랬지?"                              │
│                                                                          │
│  [보여줄 것]                                                            │
│  1. 시간대 인식 → SHIFT_B                                               │
│  2. 해당 시간 이벤트 조회                                               │
│  3. 제품/작업 맥락 반영 (PART-C)                                        │
│  4. 유사 이벤트 표시 (타임라인)                                         │
│  5. 패턴 분석                                                           │
│                                                                          │
│  [차별화]                                                               │
│  "단순 로그 조회가 아닌 맥락 기반 분석"                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    Demo Scenario 3: 예측                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [시연 내용]                                                            │
│  상황: 3일 연속 14시대 PART-C 과부하 이벤트                             │
│                                                                          │
│  [보여줄 것]                                                            │
│  1. 반복 패턴 인식                                                      │
│  2. 시각화 (타임라인에 패턴 표시)                                       │
│  3. 예측 생성 "내일 C189 발생 확률 85%"                                 │
│  4. 예방 조치 권장                                                      │
│                                                                          │
│  [차별화]                                                               │
│  "사후 대응이 아닌 사전 예측"                                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 5. 마일스톤

## 5.1 마일스톤 개요

| 마일스톤 | Phase | 핵심 산출물 | 완료 기준 |
|----------|-------|------------|----------|
| **M1: 기반 완료** | 1-3 | 인덱싱된 데이터 | 검색 동작 |
| **M2: 온톨로지 완료** | 4-6 | ontology.json + rules | 관계 쿼리 가능 |
| **M3: 센서 통합** | 7-9 | 패턴 감지 + 연결 | 패턴→에러 매핑 |
| **M4: 추론 엔진** | 10-12 | 전체 파이프라인 | 온톨로지 질문 응답 |
| **M5: UI 완료** | 13-15 | 팔란티어 스타일 대시보드 | 그래프 인터랙션 |
| **M6: 데모 준비** | 16-17 | 3가지 시나리오 | 데모 가능 |

## 5.2 마일스톤별 데모

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Milestone Demo Points                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  M1: 기반 완료                                                          │
│  ───────────                                                            │
│  "C153 해결 방법" 검색 → 문서 결과 표시                                  │
│                                                                          │
│  M2: 온톨로지 완료                                                      │
│  ───────────────                                                        │
│  "C153의 원인은?" → 온톨로지 관계로 답변                                │
│  Cypher: MATCH (e:ErrorCode {code:'C153'})-[:CAUSED_BY]->(c:Cause)      │
│                                                                          │
│  M3: 센서 통합                                                          │
│  ─────────────                                                          │
│  센서 데이터 → 패턴 감지 → "충돌 패턴이 C153을 유발"                    │
│                                                                          │
│  M4: 추론 엔진                                                          │
│  ─────────────                                                          │
│  "Fz가 350N인데?" → 전체 온톨로지 추론 + 예측                           │
│                                                                          │
│  M5: UI 완료                                                            │
│  ───────────                                                            │
│  관계 그래프 클릭 탐색 + 시각화                                          │
│                                                                          │
│  M6: 데모 준비                                                          │
│  ─────────────                                                          │
│  3가지 시나리오 + 룰베이스 비교                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 6. 의존성 맵

## 6.1 Phase 의존성

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Phase Dependencies                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Phase 1 (환경)                                                         │
│     │                                                                    │
│     ├──→ Phase 2 (데이터)                                               │
│     │       │                                                            │
│     │       ├──→ Phase 3 (인덱싱)                                       │
│     │       │       │                                                    │
│     │       │       └──→ Phase 12 (응답 생성) ─┐                        │
│     │       │                                   │                        │
│     │       └──→ Phase 7 (센서 처리) ──→ Phase 8 (패턴) ──→ Phase 9    │
│     │                                                         │          │
│     └──→ Phase 4 (스키마) ──→ Phase 5 (엔티티) ──→ Phase 6 (규칙)      │
│                                    │                 │                   │
│                                    │                 └──→ Phase 9 ──────┤
│                                    │                                     │
│                                    └──→ Phase 10 (분류) ──→ Phase 11 ──┤
│                                                              (추론)      │
│                                                                 │        │
│                                                                 ▼        │
│                                                            Phase 12 ─────┤
│                                                            (응답)        │
│                                                                 │        │
│                                                                 ▼        │
│                                                            Phase 13 ─────┤
│                                                            (대시보드)    │
│                                                                 │        │
│                                                                 ▼        │
│                                                    Phase 14 ──→ Phase 15│
│                                                    (그래프)    (인터랙션)│
│                                                                 │        │
│                                                                 ▼        │
│                                                    Phase 16 ──→ Phase 17│
│                                                    (테스트)    (데모)    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 6.2 병행 가능 Phase

| 그룹 | 병행 가능 Phase | 조건 |
|------|----------------|------|
| A | Phase 3, Phase 4 | Phase 2 완료 후 |
| B | Phase 7, Phase 5 | Phase 2, Phase 4 완료 후 |
| C | Phase 14, Phase 15 | Phase 13 진행 중 가능 |

---

# 7. 체크리스트

## 7.1 Phase 완료 체크리스트

### 모든 Phase 공통
- [ ] 산출물 생성 완료
- [ ] 코드 동작 확인
- [ ] 기본 테스트 통과
- [ ] 문서 업데이트 (필요시)

### 온톨로지 관련 Phase (4-6, 9, 11)
- [ ] 온톨로지 연결 정의됨
- [ ] 관계 경로 테스트
- [ ] 근거 추적 가능

### UI 관련 Phase (13-15)
- [ ] 레이아웃 일관성
- [ ] 팔란티어 스타일 준수
- [ ] 인터랙션 동작

## 7.2 마일스톤 완료 체크리스트

### M2: 온톨로지 완료
- [ ] ontology.json 완성 (~50 엔티티)
- [ ] 관계 연결 완성 (~100 관계)
- [ ] 규칙 정의 (~20 규칙)
- [ ] Cypher 쿼리 테스트 통과

### M4: 추론 엔진
- [ ] 질문 분류 정확도 > 85%
- [ ] 온톨로지 경로 정확도 > 85%
- [ ] 예측 생성 동작
- [ ] 근거 100% 제공

### M6: 데모 준비
- [ ] 시나리오 1 완료 (온톨로지 추론)
- [ ] 시나리오 2 완료 (맥락 인식)
- [ ] 시나리오 3 완료 (예측)
- [ ] 룰베이스 비교 준비

---

# 부록

## A. 기존 문서와의 관계

| 기존 문서 | 현재 문서 | 변경 사항 |
|----------|----------|----------|
| Unified_ROADMAP v1.0 | Unified_ROADMAP v2.0 | 온톨로지 중심으로 재구성 |
| Foundation_ROADMAP | Unified_ROADMAP | 통합 |
| Main__ROADMAP | Unified_ROADMAP | 통합 |

## B. 폴더 구조 (완전판)

```
ur5e-ontology-rag/
│
├── .env.example                     # Phase 1: 환경 변수 템플릿
├── pyproject.toml                   # Phase 1: 프로젝트 설정 (uv/poetry)
├── requirements.txt                 # Phase 1: pip 의존성
│
├── data/
│   ├── raw/
│   │   └── pdf/                     # Phase 2: 원본 PDF 문서
│   │       ├── user_manual.pdf
│   │       ├── service_manual.pdf
│   │       └── error_codes.pdf
│   │
│   ├── processed/
│   │   ├── chunks/                  # Phase 2: 청킹된 문서
│   │   │   ├── user_manual.json
│   │   │   ├── service_manual.json
│   │   │   └── error_codes.json
│   │   │
│   │   ├── ontology/                # Phase 4-5: 온톨로지 데이터
│   │   │   ├── schema.yaml          # 4-Domain 스키마 정의
│   │   │   ├── ontology.json        # 엔티티/관계 인스턴스
│   │   │   └── lexicon.yaml         # 동의어 사전
│   │   │
│   │   └── metadata/                # Phase 2: 문서 메타데이터
│   │       └── manifest.json
│   │
│   ├── sensor/
│   │   ├── raw/                     # Phase 2: 원본 센서 데이터
│   │   │   └── axia80_7days.csv
│   │   └── processed/               # Phase 8: 처리된 패턴 데이터
│   │       ├── patterns.parquet
│   │       └── statistics.json
│   │
│   └── benchmark/                   # Phase 16: 평가용 QA 데이터
│       ├── ontology_qa.json         # 온톨로지형 질문
│       ├── hybrid_qa.json           # 하이브리드형 질문
│       └── rag_qa.json              # RAG형 질문
│
├── configs/
│   ├── settings.yaml                # Phase 1: 전역 설정
│   ├── rules.yaml                   # Phase 6: 추론 규칙
│   └── error_pattern_mapping.yaml   # Phase 9: 에러-패턴 매핑
│
├── prompts/
│   ├── system.txt                   # Phase 12: 시스템 프롬프트
│   ├── query_ontology.txt           # Phase 12: 온톨로지형 질의
│   ├── query_hybrid.txt             # Phase 12: 하이브리드형 질의
│   └── verification.txt             # Phase 12: 검증 프롬프트
│
├── src/
│   ├── __init__.py
│   ├── config.py                    # Phase 1: 설정 로더
│   │
│   ├── ingestion/                   # Phase 2: 데이터 수집
│   │   ├── __init__.py
│   │   ├── pdf_parser.py            # PDF 텍스트 추출
│   │   ├── chunker.py               # 문서 청킹
│   │   └── models.py                # Document, Chunk 모델
│   │
│   ├── embedding/                   # Phase 3: 임베딩
│   │   ├── __init__.py
│   │   ├── embedder.py              # OpenAI 임베딩 생성
│   │   └── vector_store.py          # ChromaDB 인터페이스
│   │
│   ├── ontology/                    # Phase 4-6, 11: 온톨로지 핵심
│   │   ├── __init__.py
│   │   ├── schema.py                # EntityType, RelationType 정의
│   │   ├── graph_store.py           # Neo4j 인터페이스
│   │   ├── ontology_engine.py       # 온톨로지 추론 엔진
│   │   ├── graph_traverser.py       # 관계 경로 탐색
│   │   └── rule_engine.py           # 추론 규칙 엔진
│   │
│   ├── sensor/                      # Phase 7-9: 센서 처리
│   │   ├── __init__.py
│   │   ├── sensor_store.py          # 센서 데이터 저장
│   │   ├── data_loader.py           # CSV/Parquet 로딩
│   │   ├── pattern_detector.py      # 이상 패턴 감지
│   │   └── ontology_connector.py    # 패턴→온톨로지 연결
│   │
│   ├── rag/                         # Phase 10-12: 질의 엔진
│   │   ├── __init__.py
│   │   ├── query_classifier.py      # 질문 유형 분류
│   │   ├── entity_extractor.py      # 엔티티 추출 (온톨로지 기반)
│   │   ├── hybrid_retriever.py      # VectorDB + GraphDB 검색
│   │   ├── response_generator.py    # LLM 응답 생성
│   │   ├── prompt_builder.py        # 프롬프트 구성
│   │   └── verifier.py              # 응답 검증 & 근거 추적
│   │
│   ├── api/                         # Phase 12: REST API
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI 앱 진입점
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── query.py             # POST /query
│   │   │   ├── ontology.py          # GET /ontology/*
│   │   │   ├── sensor.py            # GET /sensor/*
│   │   │   └── health.py            # GET /health
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── request.py           # 요청 Pydantic 모델
│   │       └── response.py          # 응답 Pydantic 모델
│   │
│   └── dashboard/                   # Phase 13-15: UI
│       ├── __init__.py
│       ├── app.py                   # Streamlit 메인 앱
│       ├── pages/
│       │   ├── __init__.py
│       │   ├── 1_query.py           # 질의 인터페이스
│       │   ├── 2_graph.py           # 관계 그래프
│       │   └── 3_sensor.py          # 센서 모니터링
│       ├── components/
│       │   ├── __init__.py
│       │   ├── chat.py              # 채팅 UI
│       │   ├── graph.py             # 그래프 렌더러
│       │   ├── sensor_chart.py      # 센서 차트
│       │   └── evidence_panel.py    # 근거 패널
│       └── static/
│           ├── graph.js             # D3.js 온톨로지 그래프
│           └── styles.css           # 커스텀 스타일
│
├── scripts/
│   ├── run_api.py                   # API 서버 실행
│   ├── run_dashboard.py             # 대시보드 실행
│   ├── run_ingestion.py             # Phase 2: 데이터 수집
│   ├── run_embedding.py             # Phase 3: 임베딩 생성
│   ├── run_ontology.py              # Phase 4-5: 온톨로지 구축
│   ├── run_sensor_process.py        # Phase 7-8: 센서 처리
│   └── run_evaluation.py            # Phase 16: 평가 실행
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # pytest 설정 & fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_ingestion.py        # 수집 테스트
│   │   ├── test_embedding.py        # 임베딩 테스트
│   │   ├── test_ontology.py         # 온톨로지 테스트
│   │   ├── test_sensor.py           # 센서 테스트
│   │   └── test_rag.py              # RAG 테스트
│   └── integration/
│       ├── __init__.py
│       ├── test_api.py              # API 통합 테스트
│       └── test_e2e.py              # E2E 시나리오 테스트
│
├── stores/
│   ├── chroma/                      # Phase 3: ChromaDB 영속화
│   │   └── .gitkeep
│   └── neo4j/                       # Phase 4: Neo4j (Docker 볼륨)
│       └── .gitkeep
│
└── docs/
    ├── Unified_Spec.md              # 통합 기술 명세
    ├── Unified_ROADMAP.md           # 통합 개발 로드맵
    ├── 온톨로지_스키마_설계.md       # 온톨로지 상세 설계
    ├── Axia80_센서_분석_보고서.md    # 센서 분석
    ├── UR5e_로봇_분석_보고서.md      # 로봇 분석
    └── phases/                      # Phase별 완료 보고서
        └── Phase_XX_완료.md
```

### 폴더별 Phase 매핑

| 폴더 | 관련 Phase | 핵심 역할 |
|------|-----------|----------|
| `data/raw/pdf/` | 2 | 원본 문서 저장 |
| `data/processed/chunks/` | 2 | 청킹된 문서 |
| `data/processed/ontology/` | 4-5 | 온톨로지 데이터 |
| `data/sensor/` | 2, 8 | 센서 데이터 |
| `data/benchmark/` | 16 | 평가 데이터 |
| `configs/` | 1, 6, 9 | 설정 파일 |
| `prompts/` | 12 | LLM 프롬프트 |
| `src/ingestion/` | 2 | PDF 파싱 & 청킹 |
| `src/embedding/` | 3 | 벡터 임베딩 |
| `src/ontology/` | 4-6, 11 | **온톨로지 핵심** |
| `src/sensor/` | 7-9 | 센서 처리 |
| `src/rag/` | 10-12 | 질의 엔진 |
| `src/api/` | 12 | REST API |
| `src/dashboard/` | 13-15 | UI |
| `scripts/` | 전체 | 실행 스크립트 |
| `tests/` | 16 | 테스트 |
| `stores/` | 3-4 | DB 영속화 |
| `docs/` | 전체 | 문서화 |

### 주요 파일 설명

| 파일 | 역할 |
|-----|------|
| `src/config.py` | 환경변수, 설정 통합 로딩 |
| `src/ontology/ontology_engine.py` | **핵심**: 온톨로지 추론 엔진 |
| `src/ontology/graph_traverser.py` | 관계 경로 탐색 (Palantir-style) |
| `src/rag/query_classifier.py` | 질문 유형 분류 (온톨로지/하이브리드/RAG) |
| `src/rag/hybrid_retriever.py` | VectorDB + GraphDB 통합 검색 |
| `src/dashboard/static/graph.js` | D3.js 인터랙티브 그래프 |

---

**문서 버전**: 2.0
**작성일**: 2026-01-22
**핵심 변경**: 온톨로지 중심 개발 순서로 재구성, 팔란티어 스타일 UI 강조
