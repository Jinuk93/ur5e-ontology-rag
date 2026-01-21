# UR5e Multi-Modal RAG - 2Phase 개발 로드맵

> **2Phase**는 1Phase(베이스라인)를 기반으로 **ATI Axia80 F/T 센서 데이터를 통합**하는 심화 버전입니다.
>
> 핵심 목표: **"문서 근거 + 측정 데이터 근거"의 이중 검증 시스템 구축**

---

## 1Phase vs 2Phase 비교

| 구분 | 1Phase (베이스라인) | 2Phase (심화) |
|------|---------------------|---------------|
| **데이터 소스** | 문서 (PDF) | 문서 + 센서 (F/T) |
| **근거 유형** | doc/page/chunk | doc/page/chunk + sensor_context |
| **진단 방식** | 에러코드 → 조치 | 에러코드 + 센서패턴 → 조치 |
| **장비** | UR5e 단독 | UR5e + ATI Axia80 |
| **검증** | 문서 검증 | 이중 검증 (문서 + 센서) |

---

## 전체 파이프라인 (2Phase)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          OFFLINE (배치/준비)                               │
│                                                                           │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────┐            │
│  │  PDF    │───▶│  Parse  │───▶│  Chunk  │───▶│  ChromaDB   │            │
│  │ 문서들   │    │ (텍스트) │   │ (조각화) │    │  (벡터DB)   │            │
│  └─────────┘    └─────────┘    └─────────┘    └─────────────┘            │
│                                                                           │
│  ┌─────────┐    ┌─────────┐                                              │
│  │ontology │───▶│  Neo4j  │                                              │
│  │  .json  │    │(그래프DB)│                                              │
│  └─────────┘    └─────────┘                                              │
│                                                                           │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────┐ ◀── [신규] │
│  │ Axia80  │───▶│ Pattern │───▶│ Parquet │───▶│ SensorStore │            │
│  │시뮬레이션│    │ Detect  │    │ (저장)  │    │ (시계열DB)  │            │
│  └─────────┘    └─────────┘    └─────────┘    └─────────────┘            │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                          ONLINE (실시간 서빙)                              │
│                                                                           │
│  사용자 질문                                                               │
│       │                                                                   │
│       ▼                                                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐              │
│  │Extractor │──▶│  Linker  │──▶│ Reasoner │──▶│Retriever │              │
│  │(엔티티   │   │(온톨로지 │   │(그래프   │   │(문서     │              │
│  │ 추출)    │   │ 매핑)    │   │ 추론)    │   │ 검색)    │              │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘              │
│                                      │              │                    │
│                                      ▼              ▼                    │
│                         ┌────────────────────────────────┐               │
│                         │      Context Enricher          │ ◀── [신규]   │
│                         │    (센서 맥락 보강)            │               │
│                         └────────────────────────────────┘               │
│                                      │                                   │
│                                      ▼                                   │
│                         ┌────────────────────────────────┐               │
│                         │         Verifier               │               │
│                         │  (이중 근거 검증 게이트)       │ ◀── [확장]   │
│                         └────────────────────────────────┘               │
│                                      │                                   │
│                                      ▼                                   │
│                         ┌────────────────────────────────┐               │
│                         │        Formatter               │               │
│                         │  (답변 생성 + 센서 시각화)     │               │
│                         └────────────────────────────────┘               │
│                                      │                                   │
│                                      ▼                                   │
│                              최종 답변 + 센서 차트                         │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 목록 (2Phase)

| Phase | 제목 | 핵심 내용 | 난이도 | 의존성 |
|-------|------|----------|--------|--------|
| **2-0** | 환경 점검 | 1Phase 코드 리뷰, 2Phase 환경 설정 | ★☆☆☆☆ | - |
| **2-1** | 센서 데이터 생성 | Axia80 시뮬레이션 데이터 (1개월) | ★★☆☆☆ | 2-0 |
| **2-2** | 패턴 감지 알고리즘 | 충돌/진동/과부하 패턴 감지 | ★★★☆☆ | 2-1 |
| **2-3** | Context Enricher | 문서 검색 + 센서 맥락 통합 | ★★★☆☆ | 2-2 |
| **2-4** | 온톨로지 확장 | SensorPattern 노드, INDICATES 관계 | ★★★☆☆ | 2-2 |
| **2-5** | Verifier 확장 | 이중 검증 (문서 + 센서) | ★★★★☆ | 2-3, 2-4 |
| **2-6** | API 확장 | /sensor/* 엔드포인트 추가 | ★★☆☆☆ | 2-5 |
| **2-7** | Dashboard 확장 | 센서 차트, 통합 근거 뷰 | ★★☆☆☆ | 2-6 |
| **2-8** | 통합 테스트 & 평가 | 센서 통합 벤치마크, 품질 측정 | ★★★☆☆ | 2-7 |

---

## 각 Phase 상세 설명

### Phase 2-0: 환경 점검 및 코드 리뷰

**목적:** 1Phase 코드의 품질 점검, 2Phase 준비

#### 체크리스트
- [ ] 1Phase 전체 코드 리뷰
  - 폴더 구조가 Spec과 일치하는가?
  - 불필요한 코드/파일이 있는가?
  - 에러 처리가 충분한가?
- [ ] 의존성 패키지 추가
  ```bash
  pip install pandas pyarrow duckdb scipy plotly
  ```
- [ ] 2Phase 폴더 구조 생성
  ```
  data/sensor/raw/
  data/sensor/processed/
  data/benchmark/sensor_qa.json
  src/sensor/
  ```

**산출물:**
- 코드 리뷰 체크리스트 완료
- 2Phase 폴더 구조 생성
- 의존성 업데이트

---

### Phase 2-1: 센서 데이터 생성

**목적:** ATI Axia80 F/T 센서의 현실적인 시뮬레이션 데이터 생성

#### 핵심 개념
- **Force/Torque 센서**: 6축 측정 (Fx, Fy, Fz, Tx, Ty, Tz)
- **샘플링 레이트**: 125Hz (실제) → 1초 평균 (저장)
- **이상 패턴**: 충돌, 진동, 과부하

#### 구현 내용
```python
# scripts/generate_sensor_data.py

# 1. 정상 운영 데이터 생성 (기본 노이즈)
# 2. 이상 패턴 주입
#    - 충돌: Fz 급증 (500-900N, 50ms 이내)
#    - 진동: 고주파 성분 증가
#    - 과부하: 지속적 힘 초과
# 3. Parquet 형식으로 저장
```

#### 데이터 사양
| 항목 | 값 |
|------|-----|
| 기간 | 30일 |
| 레코드 수 | ~2,592,000 (1초 평균) |
| 파일 형식 | Parquet (압축) |
| 파일 크기 | ~50-100 MB |

**산출물:**
- `data/sensor/raw/axia80_2024_01.parquet`
- `data/sensor/metadata/sensor_config.yaml`
- 데이터 검증 리포트

---

### Phase 2-2: 패턴 감지 알고리즘

**목적:** 센서 시계열에서 이상 패턴을 자동 감지

#### 핵심 개념
- **충돌 감지**: 힘의 급격한 증가 (dF/dt)
- **진동 감지**: FFT 기반 주파수 분석
- **과부하 감지**: 이동 평균 기반 지속 초과

#### 구현 내용
```python
# src/sensor/pattern_detector.py

class PatternDetector:
    def detect_collision(self, data: pd.DataFrame) -> List[CollisionEvent]:
        """Fz 급증 패턴 감지"""

    def detect_vibration(self, data: pd.DataFrame) -> List[VibrationEvent]:
        """FFT 기반 진동 패턴 감지"""

    def detect_overload(self, data: pd.DataFrame) -> List[OverloadEvent]:
        """지속적 과부하 패턴 감지"""
```

#### 패턴별 감지 조건
| 패턴 | 조건 | 임계값 |
|------|------|--------|
| 충돌 | Fz 급증 + 빠른 rise time | >500N, <100ms |
| 진동 | 고주파 성분 비율 | >30% (50Hz 이상) |
| 과부하 | 지속적 힘 초과 | >300N, >5min |

**산출물:**
- `src/sensor/pattern_detector.py`
- `data/sensor/processed/anomaly_patterns.json`
- 단위 테스트

---

### Phase 2-3: Context Enricher 구현

**목적:** 문서 검색 결과에 센서 맥락을 추가

#### 핵심 개념
- **맥락 보강**: 질문 관련 센서 데이터 첨부
- **시간 창**: 에러 발생 전후 1시간 데이터
- **상관관계**: 문서 내용 ↔ 센서 패턴 매칭

#### 구현 내용
```python
# src/rag/context_enricher.py

class ContextEnricher:
    def enrich(
        self,
        query: str,
        doc_chunks: List[Chunk],
        error_code: Optional[str],
        timestamp: Optional[datetime]
    ) -> EnrichedContext:
        """
        문서 검색 결과에 센서 맥락 추가

        Returns:
            doc_evidence: 문서 근거
            sensor_evidence: 센서 근거
            correlation: 상관관계 분석
        """
```

#### 통합 위치
```python
# src/rag/service.py

class RAGService:
    def query(self, user_query: str, **options):
        # 1. 엔티티 추출
        # 2. 온톨로지 추론
        # 3. 벡터 검색
        # 4. [신규] 맥락 보강
        enriched = self.context_enricher.enrich(...)
        # 5. 검증
        # 6. 답변 생성
```

**산출물:**
- `src/rag/context_enricher.py`
- `src/sensor/context_provider.py`
- 통합 테스트

---

### Phase 2-4: 온톨로지 확장

**목적:** 센서 패턴을 지식그래프에 통합

#### 핵심 개념
- **SensorPattern 노드**: 센서 이상 패턴 정의
- **INDICATES 관계**: 센서패턴 → 원인 연결
- **DETECTED_BY 관계**: 증상 → 센서패턴 연결

#### 스키마 추가
```cypher
// 새로운 노드 라벨
CREATE CONSTRAINT sensor_pattern_id_unique IF NOT EXISTS
FOR (n:SensorPattern) REQUIRE n.pattern_id IS UNIQUE;

// 새로운 관계 타입
// (SensorPattern)-[:INDICATES]->(Cause)
// (Symptom)-[:DETECTED_BY]->(SensorPattern)
```

#### ontology.json 확장
```json
{
  "nodes": [
    {
      "label": "SensorPattern",
      "pattern_id": "PAT_COLLISION_Z",
      "type": "collision",
      "axis": "Fz",
      "threshold": {"peak_force": 500, "rise_time_ms": 100}
    }
  ],
  "edges": [
    {
      "type": "INDICATES",
      "from": {"label": "SensorPattern", "key": "pattern_id", "value": "PAT_COLLISION_Z"},
      "to": {"label": "Cause", "key": "cause_id", "value": "CAUSE_EXTERNAL_COLLISION"}
    }
  ]
}
```

**산출물:**
- `data/processed/ontology/ontology_v2.json`
- Neo4j 스키마 마이그레이션 스크립트
- Cypher 쿼리 테스트

---

### Phase 2-5: Verifier 확장

**목적:** 문서 + 센서 이중 검증 로직 구현

#### 핵심 개념
- **이중 검증**: 문서와 센서 모두 확인
- **PARTIAL 상태**: 문서만 확인된 경우
- **신뢰도 계산**: 근거 유형에 따른 가중치

#### Verifier Status 확장
| Status | 조건 | 조치 출력 |
|--------|------|----------|
| PASS | 문서 ✓ + 센서 ✓ | 허용 (고신뢰) |
| PARTIAL | 문서 ✓ + 센서 ✗ | 허용 (경고) |
| ABSTAIN | 문서 ✗ | 금지 |
| FAIL | 시스템 오류 | 금지 |

#### 구현 내용
```python
# src/rag/verifier.py

class Verifier:
    def verify(
        self,
        causes: List[Cause],
        actions: List[Action],
        doc_evidence: List[DocEvidence],
        sensor_evidence: Optional[SensorEvidence]
    ) -> VerificationResult:
        """
        이중 검증 수행

        Returns:
            status: PASS/PARTIAL/ABSTAIN/FAIL
            verified_causes: 검증된 원인 목록
            verified_actions: 검증된 조치 목록
            confidence: 신뢰도 점수
        """
```

**산출물:**
- `src/rag/verifier.py` 확장
- 이중 검증 로직 테스트
- 회귀 테스트 (1Phase 동작 유지)

---

### Phase 2-6: API 확장

**목적:** 센서 관련 엔드포인트 추가

#### 새로운 엔드포인트
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/sensor/context` | 센서 맥락 조회 |
| GET | `/api/v1/sensor/chart` | 센서 차트 데이터 |
| GET | `/api/v1/sensor/patterns` | 감지된 패턴 목록 |

#### 기존 엔드포인트 확장
```python
# POST /api/v1/query 확장

# Request 추가 옵션
{
    "options": {
        "include_sensor": true,
        "sensor_time_window": "1h"
    }
}

# Response 확장
{
    "sensor_context": {
        "pattern_detected": "collision",
        "peak_force": {"Fz": 850.5},
        "chart_url": "/api/v1/sensor/chart?trace_id=..."
    }
}
```

**산출물:**
- `src/api/routes/sensor.py`
- API 문서 업데이트
- 엔드포인트 테스트

---

### Phase 2-7: Dashboard 확장

**목적:** 센서 데이터 시각화 및 통합 근거 뷰

#### 새로운 컴포넌트
1. **센서 차트**: Plotly 기반 시계열 그래프
2. **패턴 마커**: 이상 구간 하이라이트
3. **통합 근거 카드**: 문서 + 센서 근거 병렬 표시

#### 구현 내용
```python
# src/dashboard/pages/sensor.py

def render_sensor_page():
    """센서 모니터링 페이지"""
    st.title("📊 센서 데이터")

    # 시계열 차트
    render_sensor_chart(data)

    # 패턴 감지 결과
    render_pattern_list(patterns)

    # 에러코드 연관성
    render_error_correlation(error_code)
```

```python
# src/dashboard/components/sensor_chart.py

def render_sensor_chart(
    data: pd.DataFrame,
    patterns: List[Pattern],
    height: int = 400
):
    """6축 센서 데이터 차트"""
    fig = go.Figure()
    # Fx, Fy, Fz, Tx, Ty, Tz 라인
    # 패턴 구간 하이라이트
    st.plotly_chart(fig)
```

**산출물:**
- `src/dashboard/pages/sensor.py`
- `src/dashboard/components/sensor_chart.py`
- 통합 근거 뷰 컴포넌트

---

### Phase 2-8: 통합 테스트 & 평가

**목적:** 센서 통합 시스템의 품질 검증

#### 평가 지표
| 지표 | 설명 | 목표 |
|------|------|------|
| Pattern Detection F1 | 패턴 감지 정확도 | > 0.85 |
| Sensor Context Relevance | 센서 맥락 관련성 | > 0.8 |
| Dual Evidence Rate | 이중 근거 비율 | > 70% |
| PASS/PARTIAL 비율 | 검증 통과율 | > 80% |

#### 벤치마크 확장
```json
// data/benchmark/sensor_qa.json

[
  {
    "id": "sen_001",
    "question": "C119 에러와 함께 Fz가 급증했습니다. 원인이 뭔가요?",
    "expected_answer": "충돌로 인한 안전 한계 초과",
    "expected_pattern": "collision",
    "expected_verification": "PASS"
  }
]
```

**산출물:**
- 센서 통합 벤치마크 데이터셋
- 전체 시스템 평가 리포트
- 개선점 도출 문서

---

## 문서 구조 (2Phase)

```
docs/
├── 00_ROADMAP.md               ← 1Phase 로드맵
├── Spec.md                     ← 1Phase 기술 설계서
│
├── 2Phase_00_ROADMAP.md        ← 현재 문서 (2Phase 로드맵)
├── 2Phase_Spec.md              ← 2Phase 기술 설계서
│
├── 2Phase-0_환경점검.md
├── 2Phase-1_센서데이터생성.md
├── 2Phase-2_패턴감지.md
├── 2Phase-3_ContextEnricher.md
├── 2Phase-4_온톨로지확장.md
├── 2Phase-5_Verifier확장.md
├── 2Phase-6_API확장.md
├── 2Phase-7_Dashboard확장.md
├── 2Phase-8_통합평가.md
│
└── 2Phase_완료보고서.md
```

---

## 진행 원칙 (2Phase)

### 1. Spec 준수
> **작업 전 반드시 2Phase_Spec.md를 읽고 시작**

- 스키마, 인터페이스, 폴더 구조는 Spec을 따름
- 변경이 필요하면 Spec 먼저 수정

### 2. 코드 리뷰
> **각 Phase 완료 시 코드 리뷰 수행**

체크리스트:
- [ ] Spec과 일치하는가?
- [ ] 테스트가 있는가?
- [ ] 에러 처리가 충분한가?
- [ ] 문서화가 되어있는가?

### 3. 테스트 우선
> **기능 구현 전에 테스트 케이스 정의**

- 예상 입력/출력 먼저 정의
- 테스트 통과 후 다음 단계

### 4. 점진적 통합
> **작은 단위로 통합, 자주 검증**

- 컴포넌트 단위 테스트
- 통합 후 E2E 테스트
- 회귀 테스트 (1Phase 동작 유지)

### 5. 문서화
> **코드와 문서는 동시에**

- 구현 완료 시 Phase 문서 업데이트
- 트러블슈팅 기록
- 다음 담당자를 위한 가이드

---

## 예상 일정

| Phase | 예상 기간 | 비고 |
|-------|----------|------|
| 2-0 | 1일 | 환경 점검, 코드 리뷰 |
| 2-1 | 2일 | 센서 데이터 생성 |
| 2-2 | 3일 | 패턴 감지 알고리즘 |
| 2-3 | 3일 | Context Enricher |
| 2-4 | 2일 | 온톨로지 확장 |
| 2-5 | 3일 | Verifier 확장 |
| 2-6 | 2일 | API 확장 |
| 2-7 | 2일 | Dashboard 확장 |
| 2-8 | 3일 | 통합 테스트 & 평가 |
| **합계** | **~21일** | |

---

## 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 센서 데이터 현실성 부족 | 패턴 감지 정확도 저하 | 실제 센서 스펙 기반 생성 |
| 온톨로지 확장 복잡도 | 기존 쿼리 호환성 | 하위 호환 유지, 점진적 마이그레이션 |
| Verifier 로직 복잡화 | 버그 발생 | 단위 테스트 강화, 회귀 테스트 |
| 성능 저하 | 응답 지연 | 센서 조회 캐싱, 비동기 처리 |

---

**문서 버전**: 2Phase v1.0
**작성일**: 2024-01-21
**작성자**: Claude (AI Assistant)
