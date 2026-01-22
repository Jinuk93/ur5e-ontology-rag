# Step 01: 환경 설정 - 설계서

## 1. 개요

### 1.1 Phase 정보
- **Phase 번호**: 01
- **Phase 명**: 환경 설정 (Environment Setup)
- **Stage**: Stage 1 - 데이터 기반 (Data Foundation)
- **목표**: 프로젝트 개발 환경 구축 및 의존성 설정

### 1.2 Phase 목표 (Unified_ROADMAP.md 기준)
- Python 3.10+ 환경 확인
- 가상환경(venv) 생성 및 활성화
- 의존성 설치 (`pip install -r requirements.txt`)
- 환경변수 설정 (`.env` 파일)
- IDE 설정 (선택사항)

### 1.3 핵심 산출물
- 개발 환경 완료
- 의존성 설치 완료
- 설정 파일 구성 완료

---

## 2. 다룰 파일

### 2.1 핵심 구현 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `src/config.py` | 프로젝트 설정 통합 관리 모듈 | 구현 완료 |
| `src/__init__.py` | src 패키지 초기화 | 구현 완료 |

### 2.2 설정 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `requirements.txt` | Python 패키지 의존성 정의 | 구현 완료 |
| `configs/settings.yaml` | 프로젝트 설정값 (비민감 정보) | 구현 완료 |
| `.env.example` | 환경변수 템플릿 (Git 추적) | 구현 완료 |
| `.env` | 실제 환경변수 (Git 미추적) | 사용자 설정 필요 |

### 2.3 패키지 초기화 파일 (`__init__.py`)

| 파일 경로 | 소속 모듈 | 역할 |
|-----------|-----------|------|
| `src/ingestion/__init__.py` | 데이터 수집 | PDF 처리 모듈 |
| `src/embedding/__init__.py` | 임베딩 | 벡터 변환 모듈 |
| `src/ontology/__init__.py` | 온톨로지 | 지식 그래프 모듈 |
| `src/sensor/__init__.py` | 센서 | 센서 데이터 처리 |
| `src/rag/__init__.py` | RAG | 검색 증강 생성 |
| `src/api/__init__.py` | API | FastAPI 서버 |
| `src/api/routes/__init__.py` | API 라우터 | 엔드포인트 정의 |
| `src/api/schemas/__init__.py` | API 스키마 | Pydantic 모델 |
| `src/dashboard/__init__.py` | 대시보드 | Streamlit UI |
| `src/dashboard/pages/__init__.py` | 대시보드 페이지 | UI 페이지 |
| `src/dashboard/components/__init__.py` | 대시보드 컴포넌트 | UI 컴포넌트 |

### 2.4 인프라 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `docker-compose.yaml` | Neo4j, ChromaDB 컨테이너 | 구현 완료 |
| `venv/` | Python 가상환경 | 생성 완료 |

---

## 3. 설계 상세

### 3.1 설정 관리 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    설정 로딩 프로세스                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   .env 파일                configs/settings.yaml            │
│   (민감 정보)              (일반 설정)                       │
│       │                          │                          │
│       ▼                          ▼                          │
│   ┌─────────────────────────────────────────┐              │
│   │           src/config.py                  │              │
│   │   ┌─────────────────────────────────┐   │              │
│   │   │       get_settings()            │   │              │
│   │   │   - load_dotenv()               │   │              │
│   │   │   - yaml.safe_load()            │   │              │
│   │   │   - Settings dataclass 생성     │   │              │
│   │   └─────────────────────────────────┘   │              │
│   └─────────────────────────────────────────┘              │
│                          │                                  │
│                          ▼                                  │
│   ┌─────────────────────────────────────────┐              │
│   │         Settings (Dataclass)            │              │
│   ├─────────────────────────────────────────┤              │
│   │  - openai_api_key    (from .env)       │              │
│   │  - neo4j_uri/user/pw (from .env)       │              │
│   │  - document: DocumentSettings          │              │
│   │  - embedding: EmbeddingSettings        │              │
│   │  - retrieval: RetrievalSettings        │              │
│   │  - llm: LLMSettings                    │              │
│   │  - verifier: VerifierSettings          │              │
│   │  - api: APISettings                    │              │
│   │  - logging: LoggingSettings            │              │
│   │  - paths: PathSettings                 │              │
│   └─────────────────────────────────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Settings Dataclass 구조

```python
@dataclass
class Settings:
    """프로젝트 전체 설정"""

    # 환경변수에서 로드 (민감 정보)
    openai_api_key: str        # OpenAI API 키
    neo4j_uri: str             # Neo4j 연결 URI
    neo4j_user: str            # Neo4j 사용자
    neo4j_password: str        # Neo4j 비밀번호

    # 설정 파일에서 로드 (일반 설정)
    document: DocumentSettings   # 청크 크기, 오버랩
    embedding: EmbeddingSettings # 임베딩 모델, 배치 크기
    retrieval: RetrievalSettings # top_k, threshold
    llm: LLMSettings            # 모델, temperature
    verifier: VerifierSettings  # 검증 규칙
    api: APISettings            # 서버 host/port
    logging: LoggingSettings    # 로그 레벨
    paths: PathSettings         # 경로 설정
```

### 3.3 의존성 구조 (requirements.txt)

```
┌─────────────────────────────────────────────────────────────┐
│                    의존성 카테고리                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [1] 환경 설정          [2] PDF 처리         [3] AI/LLM     │
│  - python-dotenv       - pymupdf            - openai       │
│  - pyyaml                                   - tiktoken     │
│                                                             │
│  [4] 벡터 DB           [5] 그래프 DB        [6] 웹 프레임워크│
│  - chromadb           - neo4j              - fastapi       │
│                                            - uvicorn       │
│                                            - pydantic      │
│                                                             │
│  [7] UI 대시보드       [8] 유틸리티         [9] 센서 처리   │
│  - streamlit          - requests           - pyarrow       │
│  - plotly             - tqdm               - duckdb        │
│  - pyvis                                   - scipy         │
│  - networkx                                                │
│  - pandas                                                  │
│                                                             │
│  [10] 개발/테스트                                           │
│  - pytest                                                  │
│  - black                                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 온톨로지 시스템과의 연결점

Phase 1에서 설정하는 항목들이 온톨로지 기반 RAG 시스템에 어떻게 활용되는지:

| 설정 항목 | 온톨로지 시스템에서의 역할 |
|-----------|---------------------------|
| `openai_api_key` | LLM 추론 및 임베딩 생성에 사용 |
| `neo4j_*` | 온톨로지 그래프 (Entity, Relationship) 저장소 연결 |
| `document.*` | PDF → 청크 변환 시 크기 결정 (Knowledge Domain) |
| `embedding.*` | DocumentChunk 임베딩 생성 설정 |
| `retrieval.*` | RAG 검색 시 top_k, threshold 적용 |
| `llm.*` | OntologyEngine 추론 결과 기반 응답 생성 |
| `verifier.*` | 근거 검증 및 그래프 탐색 깊이 설정 |
| `paths.ontology_dir` | ontology.json, rules.yaml 저장 경로 |
| `paths.chroma_dir` | 벡터 인덱스 저장 경로 |
| `paths.neo4j_dir` | Neo4j 데이터 저장 경로 |

### 3.5 4-Domain 온톨로지와 설정 매핑

```
┌──────────────────────────────────────────────────────────────┐
│                 온톨로지 4-Domain 설정 매핑                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Equipment Domain          Measurement Domain                │
│  ┌─────────────────┐      ┌─────────────────────────────┐   │
│  │ Robot, Joint,   │      │ MeasurementAxis, SensorData │   │
│  │ Sensor          │      │                             │   │
│  │                 │      │ 설정: paths.sensor_dir      │   │
│  │ 설정: neo4j_*   │      │       retrieval.*           │   │
│  └─────────────────┘      └─────────────────────────────┘   │
│                                                              │
│  Knowledge Domain          Context Domain                    │
│  ┌─────────────────┐      ┌─────────────────────────────┐   │
│  │ DocumentChunk,  │      │ SensorPattern, DiagnosisCtx │   │
│  │ ErrorCode,      │      │                             │   │
│  │ Cause, Resolve  │      │ 설정: verifier.*            │   │
│  │                 │      │       llm.*                 │   │
│  │ 설정: document.*│      │                             │   │
│  │       embedding*│      │                             │   │
│  │       paths.*   │      │                             │   │
│  └─────────────────┘      └─────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Unified_Spec.md 정합성 검증

### 4.1 시스템 아키텍처 요구사항 충족

| Spec 요구사항 | Phase 1 구현 내용 | 충족 여부 |
|--------------|------------------|----------|
| 설정 관리 모듈 | `src/config.py` | O |
| 환경변수 분리 | `.env` + `settings.yaml` | O |
| 싱글톤 패턴 | `@lru_cache` 적용 | O |
| 타입 안전성 | `dataclass` 사용 | O |
| 경로 관리 | `PathSettings` 클래스 | O |

### 4.2 API 설정 요구사항 충족

| Spec 요구사항 | Phase 1 구현 내용 | 충족 여부 |
|--------------|------------------|----------|
| 서버 host/port 설정 | `APISettings` | O |
| 디버그 모드 설정 | `api.debug` | O |
| 로깅 설정 | `LoggingSettings` | O |

---

## 5. 구현 체크리스트

### 5.1 기존 구현 상태 확인

- [x] Python 3.10+ 환경 (venv 존재 확인)
- [x] requirements.txt 작성 (84줄, 10개 카테고리)
- [x] configs/settings.yaml 작성 (121줄, 7개 섹션)
- [x] .env.example 작성 (64줄, 6개 섹션)
- [x] src/config.py 구현 (213줄)
- [x] 모든 `__init__.py` 파일 생성
- [x] src/__init__.py 내용 작성 (34줄)

### 5.2 검증 명령어 (ROADMAP 기준)

```bash
# Python 버전 확인
python --version  # >= 3.10

# 패키지 확인
pip list

# 핵심 패키지 import 테스트
python -c "import chromadb; print('ChromaDB OK')"
python -c "import openai; print('OpenAI OK')"
python -c "import neo4j; print('Neo4j OK')"
python -c "from src.config import get_settings; print('Config OK')"
```

### 5.3 설정 로딩 테스트

```bash
# 설정 검증
python -c "from src.config import get_settings; s = get_settings(); print(f'LLM: {s.llm.model}, Chunk: {s.document.chunk_size}')"
```

### 5.4 추가 완료 작업

- [x] src/__init__.py 내용 작성
- [x] docker-compose.yaml 검증 완료
- [ ] 실제 .env 파일 설정 (사용자 작업 필요)

---

## 6. 참조 문서

### 6.1 ROADMAP 참조
- Section A.1: Phase 1 상세 (환경 설정)
- Section B: 폴더 구조 (Phase 매핑)
- Section D: Phase 의존성 그래프

### 6.2 Spec 참조
- Section 3: 시스템 아키텍처
- Section 5: 데이터 흐름
- Section 6: API 설계

### 6.3 온톨로지 스키마 참조
- Section 3: 엔티티 정의 (Settings가 연결되는 대상)
- Section 4: 관계 유형 (그래프 탐색 설정)
- Section 5: 추론 규칙 (verifier 설정)

---

## 7. 설계 결정 사항

### 7.1 설정 분리 전략

**결정**: 민감 정보(.env)와 일반 설정(settings.yaml) 분리

**근거**:
1. 보안: API 키 등 민감 정보는 Git 추적 제외
2. 유연성: 환경별(dev/prod) 설정 파일 교체 용이
3. 가독성: YAML 형식으로 설정값 문서화

### 7.2 싱글톤 패턴 적용

**결정**: `@lru_cache(maxsize=1)`로 Settings 인스턴스 캐싱

**근거**:
1. 성능: 반복적인 파일 로드 방지
2. 일관성: 모든 모듈이 동일한 설정 객체 참조
3. 테스트 용이: `reload_settings()`로 캐시 무효화 가능

### 7.3 Dataclass 사용

**결정**: 모든 설정을 `@dataclass`로 정의

**근거**:
1. 타입 안전: IDE 자동완성 및 타입 체크
2. 기본값: 필드별 기본값 설정 용이
3. 불변성: 설정값 실수로 변경 방지

---

## 8. 다음 Phase 연결

### Phase 02 (데이터 준비)와의 연결

Phase 1에서 설정한 내용이 Phase 2에서 사용되는 방식:

```
Phase 1 설정                    Phase 2 사용
─────────────────────────────────────────────────
paths.data_raw_dir      →    PDF 파일 읽기 경로
paths.data_processed_dir →    청크 저장 경로
document.chunk_size     →    텍스트 분할 크기
document.chunk_overlap  →    청크 겹침 크기
```

---

## 9. 온톨로지 스키마 연결 상세 (리팩토링 추가)

### 9.1 엔티티별 설정 연결

온톨로지 스키마의 엔티티들이 설정값에 의존하는 방식:

| 온톨로지 엔티티 | 의존 설정 | 사용 Phase |
|----------------|----------|-----------|
| **Robot, Joint, Sensor** | `neo4j_*` | Phase 4-5 |
| **MeasurementAxis** | `paths.sensor_dir` | Phase 7-8 |
| **SensorPattern** | `verifier.max_graph_hops` | Phase 8-9 |
| **ErrorCode, Cause, Resolution** | `paths.ontology_dir` | Phase 5-6 |
| **DocumentChunk** | `document.chunk_size/overlap`, `embedding.*` | Phase 2-3 |
| **Shift, Product, WorkCycle** | `paths.benchmark_dir` | Phase 16-17 |

### 9.2 관계 타입과 설정 연결

| 관계 타입 | 관련 설정 | 설명 |
|----------|----------|------|
| `HAS_COMPONENT`, `MOUNTED_ON` | `neo4j_*` | 장비 계층 구조 저장 |
| `MEASURES`, `HAS_STATE` | `paths.sensor_dir` | 센서 측정값 경로 |
| `INDICATES`, `TRIGGERS` | `verifier.min_evidence_score` | 패턴→에러 매핑 신뢰도 |
| `CAUSED_BY`, `RESOLVED_BY` | `verifier.require_citation_for_action` | 근거 기반 조치 권장 |
| `DOCUMENTED_IN` | `paths.chunks_dir` | 문서 참조 경로 |

### 9.3 추론 규칙과 설정 연결

온톨로지 추론 규칙(`configs/rules.yaml`)이 사용하는 설정:

```yaml
# 상태 추론 (StateRules)
→ paths.sensor_dir: 센서 데이터 로드 경로

# 패턴 추론 (PatternRules)
→ verifier.min_evidence_score: 패턴 감지 신뢰도 임계값

# 원인 추론 (CauseRules)
→ verifier.max_graph_hops: 원인 탐색 깊이

# 예측 규칙 (PredictionRules)
→ llm.model: 예측 생성에 사용할 LLM
→ llm.temperature: 예측 일관성 (0.0 권장)
```

---

## 10. Phase 2 준비 사항 상세

### 10.1 필수 선행 조건

Phase 2 (데이터 준비) 시작 전 확인 사항:

| 항목 | 확인 방법 | 상태 |
|------|----------|------|
| Python 환경 | `python --version` | O |
| 의존성 설치 | `pip list \| grep pymupdf` | O |
| 설정 로드 | `get_settings()` 호출 | O |
| 데이터 경로 존재 | `paths.data_raw_dir` 확인 | O |

### 10.2 Phase 2에서 사용할 설정값

```python
# Phase 2에서 사용되는 설정
settings = get_settings()

# PDF 읽기 경로
pdf_dir = settings.paths.data_raw_dir  # data/raw/pdf/

# 청크 저장 경로
chunks_dir = settings.paths.chunks_dir  # data/processed/chunks/

# 청킹 파라미터
chunk_size = settings.document.chunk_size    # 512
chunk_overlap = settings.document.chunk_overlap  # 50
```

---

*작성일: 2026-01-22*
*Phase: 01 - 환경 설정*
*문서 버전: v2.0 (리팩토링)*
