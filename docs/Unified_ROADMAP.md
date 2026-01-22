# UR5e Multi-Modal RAG 시스템 - 통합 개발 로드맵

> **Version**: 1.0 (Unified)
> **최종 수정**: 2026-01-22
> **문서 목적**: Foundation + Main 단계 통합, 실제 구현 순서 및 도메인별 정리

---

## 목차

1. [전체 파이프라인 개요](#1-전체-파이프라인-개요)
2. [Phase 구조 개요](#2-phase-구조-개요)
3. [도메인별 구성요소](#3-도메인별-구성요소)
4. [시간순 Phase 상세](#4-시간순-phase-상세)
5. [마일스톤](#5-마일스톤)
6. [코드 리뷰 체크리스트](#6-코드-리뷰-체크리스트)
7. [진행 원칙](#7-진행-원칙)

---

# 1. 전체 파이프라인 개요

## 1.1 시스템 구성도

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
│  ┌─────────┐   ┌─────────┐   ┌─────────────┐                             │
│  │ Axia80  │──▶│ Pattern │──▶│ SensorStore │                             │
│  │시뮬레이션│   │ Detect  │   │ (Parquet)   │                             │
│  └─────────┘   └─────────┘   └─────────────┘                             │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                              ONLINE (실시간 서빙)                          │
│                                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Query   │─▶│  Entity  │─▶│  Graph   │─▶│  Vector  │─▶│ Context  │   │
│  │ Analyzer │  │  Linker  │  │ Retriever│  │ Retriever│  │ Enricher │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                │                          │
│                                                ▼                          │
│                              ┌──────────────────────────────────┐        │
│                              │           Verifier               │        │
│                              │  (Document + Sensor + Ontology)  │        │
│                              └──────────────────────────────────┘        │
│                                                │                          │
│                                                ▼                          │
│                              ┌──────────────────────────────────┐        │
│                              │         Generator                │        │
│                              │     최종 답변 + 근거 + 차트       │        │
│                              └──────────────────────────────────┘        │
└───────────────────────────────────────────────────────────────────────────┘
```

## 1.2 개발 흐름 요약

```
환경설정 → 데이터 준비 → 벡터 인덱싱 → 온톨로지 구축 → 기본 RAG
    │           │            │             │            │
    ▼           ▼            ▼             ▼            ▼
  Phase 0    Phase 1-2    Phase 3      Phase 4      Phase 5-6
    │
    │   → 검증/API/UI → 평가 → Entity Linker 개선 → Trace/메타데이터
    │         │          │            │                  │
    ▼         ▼          ▼            ▼                  ▼
         Phase 7-9    Phase 10     Phase 11           Phase 12-13
    │
    │   → 센서 데이터 → 패턴 감지 → Context Enricher → 온톨로지 확장
    │         │            │              │                │
    ▼         ▼            ▼              ▼                ▼
         Phase 14      Phase 15       Phase 16         Phase 17
    │
    └─→ Verifier 확장 → API/UI 확장
              │              │
              ▼              ▼
          Phase 18       Phase 19
```

---

# 2. Phase 구조 개요

## 2.1 전체 Phase 목록 (시간순)

| Phase | 제목 | 핵심 내용 | 도메인 |
|-------|------|----------|--------|
| **0** | 환경 설정 | Python, Docker, 의존성 | 인프라 |
| **1** | 데이터 탐색 | PDF 구조 분석, 샘플 QA | 데이터 |
| **2** | PDF 파싱 & 청킹 | PyMuPDF, 청킹 전략 | 데이터 |
| **3** | 벡터 인덱싱 | Embedding, ChromaDB | 검색 |
| **4** | 온톨로지 설계 | 지식그래프, Neo4j | 지식 |
| **5** | 기본 RAG | 검색 + LLM 답변 | 검색 |
| **6** | 온톨로지 추론 | 엔티티 링킹, 그래프 탐색 | 지식 |
| **7** | Verifier | 근거 검증, 안전 정책 | 검증 |
| **8** | API 서버 | FastAPI, 엔드포인트 | 서빙 |
| **9** | UI 대시보드 | Streamlit, 시각화 | 서빙 |
| **10** | 평가 시스템 | 벤치마크, 품질 측정 | 운영 |
| **11** | Entity Linker 개선 | Lexicon + Rules | 지식 |
| **12** | Trace 시스템 | audit_trail.jsonl | 운영 |
| **13** | 메타데이터 정비 | sources.yaml, manifest | 데이터 |
| **14** | 센서 데이터 생성 | Axia80 시뮬레이션 | 센서 |
| **15** | 패턴 감지 | 충돌/진동/과부하 | 센서 |
| **16** | Context Enricher | 문서+센서 통합 | 검색 |
| **17** | 온톨로지 확장 | SensorPattern 노드 | 지식 |
| **18** | Verifier 확장 | 이중 검증, PARTIAL | 검증 |
| **19** | API/UI 확장 | 센서 시각화 | 서빙 |

## 2.2 기존 Phase 매핑

| 통합 Phase | Foundation Phase | Main Phase |
|------------|------------------|------------|
| 0~10 | Phase 0~10 | - |
| 11 | - | Main-F1 |
| 12 | - | Main-F2 |
| 13 | - | Main-F3 |
| 14 | - | Main-S1 |
| 15 | - | Main-S2 |
| 16 | - | Main-S3 |
| 17 | - | Main-S4 |
| 18 | - | Main-S5 |
| 19 | - | Main-S6 |

---

# 3. 도메인별 구성요소

## 3.1 도메인 레이어

```
┌─────────────────────────────────────────────────────────────────┐
│                        도메인 레이어 구조                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    서빙 레이어 (Serving)                 │   │
│  │    Dashboard (Streamlit) + API (FastAPI)                │   │
│  │    Phase: 8, 9, 19                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    검증 레이어 (Verification)            │   │
│  │    Verifier + SensorVerifier + OntologyVerifier          │   │
│  │    Phase: 7, 18                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    검색 레이어 (Retrieval)               │   │
│  │    Vector + Graph + Hybrid + Context Enricher            │   │
│  │    Phase: 3, 5, 16                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    지식 레이어 (Knowledge)               │   │
│  │    Ontology + Entity Linker + Graph Reasoning            │   │
│  │    Phase: 4, 6, 11, 17                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    데이터 레이어 (Data)                  │   │
│  │    PDF + Chunks + Metadata + Sensor                      │   │
│  │    Phase: 1, 2, 13, 14, 15                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    운영 레이어 (Operations)              │   │
│  │    Trace + Audit + Evaluation                            │   │
│  │    Phase: 10, 12                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    인프라 레이어 (Infrastructure)        │   │
│  │    Python + Docker + Dependencies                        │   │
│  │    Phase: 0                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3.2 도메인별 구성요소 상세

### 인프라 레이어
| 구성요소 | 설명 | 파일/폴더 |
|----------|------|----------|
| Python 환경 | 3.10+ | `requirements.txt` |
| Docker | Neo4j, 서비스 컨테이너화 | `docker-compose.yaml` |
| 설정 | 환경변수, 설정 파일 | `.env`, `configs/` |

### 데이터 레이어
| 구성요소 | 설명 | 파일/폴더 |
|----------|------|----------|
| PDF 원본 | UR5e 공식 문서 | `data/raw/pdf/` |
| 청크 데이터 | 파싱/청킹된 텍스트 | `data/processed/chunks/` |
| 메타데이터 | 문서 출처, 매핑 | `data/processed/metadata/` |
| 센서 데이터 | Axia80 시뮬레이션 | `data/sensor/` |

### 지식 레이어
| 구성요소 | 설명 | 파일/폴더 |
|----------|------|----------|
| 온톨로지 | 지식그래프 정의 | `data/processed/ontology/ontology.json` |
| Lexicon | 동의어 사전 | `data/processed/ontology/lexicon.yaml` |
| Rules | 정규화 룰 | `configs/rules.yaml` |
| Entity Linker | 엔티티 링킹 모듈 | `src/rag/entity_linker.py` |
| Graph Retriever | 그래프 검색 | `src/rag/graph_retriever.py` |

### 검색 레이어
| 구성요소 | 설명 | 파일/폴더 |
|----------|------|----------|
| Vector Store | ChromaDB 인덱스 | `stores/chroma/` |
| Retriever | 벡터 검색 | `src/rag/retriever.py` |
| Hybrid Retriever | 그래프+벡터 통합 | `src/rag/hybrid_retriever.py` |
| Context Enricher | 센서 맥락 추가 | `src/rag/context_enricher.py` |

### 검증 레이어
| 구성요소 | 설명 | 파일/폴더 |
|----------|------|----------|
| Verifier | 문서 검증 | `src/rag/verifier.py` |
| Sensor Verifier | 센서 검증 | `src/rag/sensor_verifier.py` |
| Ontology Verifier | 온톨로지 검증 | `src/rag/ontology_verifier.py` |

### 서빙 레이어
| 구성요소 | 설명 | 파일/폴더 |
|----------|------|----------|
| API | FastAPI 서버 | `src/api/` |
| Dashboard | Streamlit UI | `src/dashboard/` |

### 운영 레이어
| 구성요소 | 설명 | 파일/폴더 |
|----------|------|----------|
| Audit Logger | 추적 로깅 | `src/api/services/audit_logger.py` |
| Evaluation | 평가 시스템 | `src/evaluation/` |
| Audit Trail | 로그 저장소 | `stores/audit/audit_trail.jsonl` |

---

# 4. 시간순 Phase 상세

## Phase 0: 환경 설정
**목표**: 개발 환경 구축

### 태스크
- Python 3.10+ 설치 확인
- 가상환경 생성 (`venv`)
- 의존성 설치 (`pip install -r requirements.txt`)
- Docker 설치 (Neo4j용)
- IDE 설정

### 산출물
- 동작하는 개발 환경
- `.env` 파일 (API 키, DB 설정)

### 검증
- [ ] Python 버전 확인
- [ ] 모든 패키지 설치 완료
- [ ] Neo4j 연결 테스트

---

## Phase 1: 데이터 탐색
**목표**: PDF 문서 구조 파악

### 태스크
- PDF 3개 직접 열어보기
- 문서 구조 파악 (목차, 섹션, 테이블)
- 에러코드 테이블 분석
- 샘플 질문-답변 쌍 작성

### 산출물
- 데이터 분석 노트
- 샘플 QA 데이터

---

## Phase 2: PDF 파싱 & 청킹
**목표**: PDF를 검색 가능한 텍스트로 변환

### 태스크
- PyMuPDF로 텍스트 추출
- 페이지별/섹션별 분리
- 청킹 전략 정의 (크기, 오버랩)
- 메타데이터 기록 (doc_id, page)

### 산출물
- `data/processed/chunks/*.json`
- 파싱 스크립트

### 핵심 코드
```python
# src/ingestion/chunker.py
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Chunk]:
    """텍스트를 청크로 분할"""
```

---

## Phase 3: 벡터 인덱싱
**목표**: ChromaDB에 문서 인덱싱

### 태스크
- Embedding 이해 (OpenAI text-embedding-3-small)
- ChromaDB 설정 및 저장
- 검색 테스트

### 산출물
- `stores/chroma/` (인덱스 파일)
- 인덱싱 스크립트

### 핵심 코드
```python
# src/embedding/vector_store.py
class VectorStore:
    def add_documents(self, chunks: List[Chunk]) -> None:
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
```

---

## Phase 4: 온톨로지 설계
**목표**: 지식그래프 구축

### 태스크
- Node/Relationship 설계
- `ontology.json` 작성
- Neo4j에 적재
- Cypher 쿼리 작성

### 산출물
- `data/processed/ontology/ontology.json`
- Neo4j 그래프

### 노드 구조
| Node | 속성 |
|------|------|
| ErrorCode | code, message |
| Component | name, synonyms |
| Resolution | resolution_id, text |
| Cause | cause_id, description |

---

## Phase 5: 기본 RAG
**목표**: 최소 동작 버전 (MVP)

### 태스크
- 질문 → 검색 → LLM 답변 흐름
- 프롬프트 엔지니어링
- 테스트

### 산출물
- 기본 RAG 파이프라인
- 테스트 결과

---

## Phase 6: 온톨로지 추론
**목표**: "온톨로지 우선" 구현

### 태스크
- 엔티티 추출 (LLM 기반)
- 온톨로지 노드에 매핑
- 그래프 경로 탐색
- Query Expansion

### 산출물
- 온톨로지 추론 모듈
- 확장 검색

---

## Phase 7: Verifier
**목표**: 근거 검증 시스템

### 태스크
- PASS/ABSTAIN/FAIL 정책 정의
- 문서 근거 확인 로직
- Action에 citation 강제

### 산출물
- `src/rag/verifier.py`

### 핵심 로직
```python
class Verifier:
    def verify(self, causes, actions, evidence) -> VerificationResult:
        """근거 기반 검증"""
        # 문서 citation 없으면 Action 출력 금지
```

---

## Phase 8: API 서버
**목표**: FastAPI 기반 REST API

### 태스크
- 엔드포인트 설계
- 요청/응답 스키마
- 에러 처리

### 엔드포인트
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/query` | 질의응답 |
| GET | `/api/v1/health` | 상태 점검 |

---

## Phase 9: UI 대시보드
**목표**: Streamlit 기반 UI

### 태스크
- 질문 입력 / 답변 표시
- 근거 미리보기
- 그래프 시각화

### 산출물
- `src/dashboard/`

---

## Phase 10: 평가 시스템
**목표**: 품질 측정

### 태스크
- 벤치마크 데이터셋 구축
- 평가 지표 구현
- 평가 실행 및 보고서

### 지표
- Recall@5, Accuracy, Hallucination Rate

---

## Phase 11: Entity Linker 개선
**목표**: Lexicon + Rules 기반 링킹

### 태스크
- `lexicon.yaml` 작성 (20개 에러코드, 21개 부품)
- `rules.yaml` 작성
- EntityLinker 클래스 개선

### 산출물
- `data/processed/ontology/lexicon.yaml`
- `configs/rules.yaml`
- 개선된 `src/rag/entity_linker.py`

### 테스트
- 23개 단위 테스트, 100% 통과

---

## Phase 12: Trace 시스템
**목표**: 완전한 audit_trail 구현

### 태스크
- AuditLogger 클래스 구현
- audit_trail.jsonl 저장
- /evidence/{trace_id} 엔드포인트

### 산출물
- `src/api/services/audit_logger.py`
- `stores/audit/audit_trail.jsonl`
- `src/api/routes/evidence.py`

---

## Phase 13: 메타데이터 정비
**목표**: 근거 추적 메타데이터

### 태스크
- `sources.yaml` 작성
- `chunk_manifest.jsonl` 생성
- MetadataService 구현

### 산출물
- `data/processed/metadata/sources.yaml`
- `data/processed/metadata/chunk_manifest.jsonl` (722개 청크)
- `src/api/services/metadata_service.py`

---

## Phase 14: 센서 데이터 생성
**목표**: Axia80 시뮬레이션 데이터

### 태스크
- 데이터 생성기 구현
- Parquet 저장
- 이상 패턴 삽입

### 산출물
- `data/sensor/raw/axia80_week_01.parquet` (604,800 레코드)
- `data/sensor/metadata/sensor_config.yaml`

---

## Phase 15: 패턴 감지
**목표**: 센서 이상 패턴 자동 감지

### 태스크
- PatternDetector 클래스 구현
- 4가지 패턴 (collision, vibration, overload, drift)
- SensorStore 구현

### 산출물
- `src/sensor/pattern_detector.py`
- `src/sensor/sensor_store.py`
- `data/sensor/processed/detected_patterns.json`

### 테스트
- 26개 단위 테스트, 100% 통과

---

## Phase 16: Context Enricher
**목표**: 문서+센서 맥락 통합

### 태스크
- ContextEnricher 클래스 구현
- 상관관계 분석
- error_pattern_mapping.yaml 작성

### 산출물
- `src/rag/context_enricher.py`
- `configs/error_pattern_mapping.yaml`

---

## Phase 17: 온톨로지 확장
**목표**: 센서 패턴 노드 추가

### 태스크
- SensorPattern 노드 정의
- INDICATES, TRIGGERS 관계 추가
- GraphRetriever 확장

### 산출물
- 확장된 `ontology.json`
- 확장된 `src/rag/graph_retriever.py`

---

## Phase 18: Verifier 확장
**목표**: 이중 검증 (문서+센서)

### 태스크
- SensorVerifier 구현
- OntologyVerifier 구현
- VerificationStatus 확장

### 산출물
- `src/rag/sensor_verifier.py`
- `src/rag/ontology_verifier.py`
- 확장된 `src/rag/verifier.py`

### VerificationStatus
- VERIFIED, PARTIAL_BOTH, PARTIAL_DOC_ONLY, PARTIAL_SENSOR_ONLY, INSUFFICIENT

---

## Phase 19: API/UI 확장
**목표**: 센서 시각화 대시보드

### 태스크
- 센서 분석 페이지 추가
- Plotly 차트 구현
- 패턴 타임라인

### 산출물
- `src/dashboard/pages/sensor_analysis.py`

---

# 5. 마일스톤

## 마일스톤 1: 기본 RAG 완성 (Phase 0-6)
| Phase | 산출물 |
|-------|--------|
| 0 | 개발 환경 |
| 1-2 | 청크 데이터 |
| 3 | ChromaDB 인덱스 |
| 4 | Neo4j 그래프 |
| 5-6 | 기본 RAG + 온톨로지 추론 |

**완료 기준**: 질문 → 답변 동작

---

## 마일스톤 2: 서비스 완성 (Phase 7-10)
| Phase | 산출물 |
|-------|--------|
| 7 | Verifier |
| 8 | API 서버 |
| 9 | 대시보드 |
| 10 | 평가 시스템 |

**완료 기준**: 데모 가능한 시스템

---

## 마일스톤 3: Foundation 개선 (Phase 11-13)
| Phase | 산출물 |
|-------|--------|
| 11 | 개선된 Entity Linker |
| 12 | Audit Trail |
| 13 | 메타데이터 |

**완료 기준**: 추적 가능한 시스템

---

## 마일스톤 4: 센서 통합 (Phase 14-19)
| Phase | 산출물 |
|-------|--------|
| 14-15 | 센서 데이터 + 패턴 감지 |
| 16-17 | Context Enricher + 온톨로지 확장 |
| 18-19 | Verifier 확장 + 센서 UI |

**완료 기준**: Multi-Modal RAG 완성

---

# 6. 코드 리뷰 체크리스트

## 6.1 Spec 일치
- [ ] Unified_Spec.md의 스키마/인터페이스와 일치하는가?
- [ ] API 응답 형식이 Spec과 동일한가?

## 6.2 테스트
- [ ] 핵심 로직에 단위 테스트가 있는가?
- [ ] 경계 조건이 테스트되었는가?
- [ ] 통합 테스트가 있는가?

## 6.3 에러 처리
- [ ] 예외 상황이 처리되는가?
- [ ] Fallback 로직이 있는가?
- [ ] 사용자에게 적절한 에러 메시지가 반환되는가?

## 6.4 성능
- [ ] 응답 시간이 합리적인가? (< 3초)
- [ ] 메모리 사용이 적절한가?

## 6.5 로깅
- [ ] 디버깅에 충분한 로그가 있는가?
- [ ] trace_id가 로그에 포함되는가?

---

# 7. 진행 원칙

1. **한 Phase씩** - 다음 Phase로 넘어가기 전에 현재 Phase 완료
2. **문서 먼저** - 코드 작성 전에 설계 확정
3. **Spec 참조** - Unified_Spec.md를 기준으로 구현
4. **테스트 필수** - 기능 구현 후 반드시 테스트 작성
5. **작은 단위로** - 한 번에 100줄보다 10줄씩 10번
6. **자주 커밋** - 의미 있는 단위로 커밋

---

# 부록: 참조 문서

## A. 기존 문서 → 통합 문서 매핑

| 기존 문서 | 통합 문서 | 설명 |
|----------|----------|------|
| Foundation_Spec.md | Unified_Spec.md | 기술 설계서 |
| Main__Spec.md | Unified_Spec.md | 기술 설계서 |
| Foundation_ROADMAP.md | Unified_ROADMAP.md | 로드맵 |
| Main__ROADMAP.md | Unified_ROADMAP.md | 로드맵 |
| Phase*_완료보고서.md | Implementation_Summary.md | 구현 요약 |

## B. Phase별 완료보고서 위치

| Phase | 기존 완료보고서 |
|-------|----------------|
| 0~10 | `docs/archive/Foundation_Phase*_완료보고서.md` |
| 11 (F1) | `docs/archive/Main_F1_완료보고서.md` |
| 12 (F2) | `docs/archive/Main_F2_완료보고서.md` |
| 13 (F3) | `docs/archive/Main_F3_완료보고서.md` |
| 14 (S1) | `docs/archive/Main_S1_센서데이터생성.md` |
| 15 (S2) | `docs/archive/Main_S2_완료보고서.md` |
| 16 (S3) | `docs/archive/Main_S3_완료보고서.md` |
| 17 (S4) | `docs/archive/Main_S4_완료보고서.md` |
| 18 (S5) | `docs/archive/Main_S5_완료보고서.md` |
| 19 (S6) | `docs/archive/Main_S6_완료보고서.md` |

---

**문서 버전**: Unified v1.0
**작성일**: 2026-01-22
**기반 문서**: Foundation_ROADMAP.md, Main__ROADMAP.md
