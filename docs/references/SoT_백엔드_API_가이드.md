# UR5e Ontology RAG - 백엔드 총 가이드

- 대상: 백엔드/프론트/데모 운영자(로컬 실행, 계약 확인, 트러블슈팅)
- 목표: 이 프로젝트의 **목적·기능·스펙·아키텍처**를 한 문서로 묶고, **프론트엔드(검수 결과 포함)** 와 구조적으로 "맞물리게" 운영 가능한 백엔드 기준점을 제공합니다.

---

## 0) TL;DR (가장 빠른 재현)

### 0.1 필수 준비

- Python 패키지 설치: `pip install -r requirements.txt`
- OpenAI 키(필요 시): `.env`에 `OPENAI_API_KEY=...`

### 0.2 API 서버 실행

- `python scripts/run_api.py --host 127.0.0.1 --port 8002 --reload`
- 문서: `http://127.0.0.1:8002/docs`

### 0.3 무인(E2E) 검증 (권장)

PowerShell에서:

- `powershell -ExecutionPolicy Bypass -File scripts/e2e_validate.ps1 -Port 8002 -ForceKillPort`

이 명령은 **서버 기동 → /health 준비 대기 → /api/chat 및 /api/evidence 검증 → 서버 종료**까지 한 번에 수행합니다.

현재 E2E는 `validate_api.py`를 통해 **가이드에 명시된 주요 엔드포인트(센서/SSE 포함)** 를 런타임 호출로 함께 검증합니다.

---

## 1) 프로젝트 목적과 범위(백엔드 관점)

### 1.1 무엇을 제공하나?

백엔드는 “제조 현장용 AI 진단 대시보드”를 위해 아래 기능을 API로 제공합니다.

- **챗봇 질의응답**: 온톨로지 기반 추론 + RAG를 결합해 진단/원인/조치 제안
- **근거 추적(Traceability)**: 답변마다 `trace_id`를 발급하고, trace 기반으로 Evidence/Graph를 조회
- **센서 데이터 API**: (데모용) 저장된 센서 데이터(parquet/json)를 “실시간처럼” 제공
- **SSE 스트리밍**: LiveView에서 EventSource로 구독 가능한 스트림 제공

### 1.2 “프론트와 맞물리게” 만든 핵심 결정

- 백엔드 응답은 **snake_case 유지** (`trace_id`, `query_type`, `abstain_reason` 등)
- 프론트는 API 레이어에서 **camelCase로 정규화**
  - 정본: [frontend/src/lib/api.ts](../../frontend/src/lib/api.ts)
  - 참고(문서/계약 타입): [contracts/p0_api_adapter.ts](../../contracts/p0_api_adapter.ts) — 타입 정의 전용
- `trace_id`는 프론트 Evidence Drawer/프리패치의 키로 사용

프론트 검수 결과(게이트/리스크/보완사항 포함)는 아래 문서와 함께 운영하는 것을 권장합니다.

- [SoT_프론트엔드_검증_리포트.md](SoT_프론트엔드_검증_리포트.md)
- [SoT_UI_설계_명세서.md](SoT_UI_설계_명세서.md)

---

## 2) 런타임 아키텍처(요약)

### 2.1 구성 요소

- **API Layer (FastAPI)**: [src/api/main.py](../../src/api/main.py)
- **RAG/추론 코어**
  - Query 분류: `QueryClassifier` ([src/rag/query_classifier.py](../../src/rag/query_classifier.py))
  - 온톨로지 추론: `OntologyEngine` ([src/ontology/ontology_engine.py](../../src/ontology/ontology_engine.py))
  - 응답 생성: `ResponseGenerator` ([src/rag/response_generator.py](../../src/rag/response_generator.py))
- **저장소**
  - 벡터스토어(Chroma, 로컬 영속): [src/embedding/vector_store.py](../../src/embedding/vector_store.py) → `stores/chroma/`
  - 그래프DB(Neo4j, 선택): [docker-compose.yaml](../../docker-compose.yaml) → `stores/neo4j/`
- **센서 데이터(데모용)**
  - Raw parquet: `data/sensor/raw/axia80_week_01.parquet`
  - Processed json: `data/sensor/processed/detected_patterns.json`, `data/sensor/processed/anomaly_events.json`

### 2.2 데이터/요청 흐름

1) 프론트 ChatPanel → `POST /api/chat`
2) 백엔드: 분류 → 추론 → 생성 → `trace_id` 발급
3) 백엔드: 응답을 메모리 Evidence Store에 보관 (`trace_id → full_response`)
4) 프론트 Evidence Drawer → `GET /api/evidence/{trace_id}`

센서 LiveView는 다음 중 하나로 데이터를 받습니다.

- 폴링: `GET /api/sensors/readings|patterns|events`
- SSE: `GET /api/sensors/stream` (EventSource)

---

## 3) 설정(환경변수 + YAML)

### 3.1 환경변수(.env)

[src/config.py](../../src/config.py)에서 `.env`를 로드합니다.

- `OPENAI_API_KEY` (선택 - 프론트엔드에서 헤더로 전달 가능)
- `NEO4J_URI` (기본: `bolt://localhost:7687`)
- `NEO4J_USER` (기본: `neo4j`)
- `NEO4J_PASSWORD`

샘플: [.env.example](../../.env.example)

> **참고**: OpenAI API 키는 프론트엔드에서 `X-OpenAI-API-Key` 헤더로 전달할 수 있습니다. 헤더로 전달된 키가 서버 환경변수보다 우선합니다. 자세한 내용은 [4.1 ChatRequest](#41-chatrequest-요청)를 참조하세요.

### 3.2 YAML 설정(configs/settings.yaml)

- 파일: [configs/settings.yaml](../../configs/settings.yaml)
- 주요 항목:
  - `document.chunk_size`, `document.chunk_overlap`
  - `embedding.model` / `llm.model`
  - `retrieval.top_k`, `retrieval.similarity_threshold`
  - `verifier.min_evidence_score` (ABSTAIN에 직접 영향)

주의: 현재 API 서버 실행 스크립트([scripts/run_api.py](../../scripts/run_api.py))는 인자(host/port)를 받으며, YAML의 `api.host/port`는 런타임에서 참고용으로만 쓰일 수 있습니다(실제 바인딩은 run_api.py 인자 기준).

---

## 4) API 계약(프론트 연동 관점)

### 4.1 ChatRequest (요청)

- 엔드포인트: `POST /api/chat`
- 스키마: [src/api/routes/chat.py](../../src/api/routes/chat.py)
  - `query`(권장) 또는 `message`(하위호환) 중 하나는 필수
  - validator에서 `query` 우선, 없으면 `message`를 `query`로 승격

#### API 키 전달 방식

OpenAI API 키는 **HTTP 헤더**를 통해 전달합니다 (보안상 권장):

- **헤더 이름**: `X-OpenAI-API-Key`
- **우선순위**: 헤더 > 서버 `.env` 설정
  - 헤더에 유효한 키(`sk-`로 시작)가 있으면 해당 키 사용
  - 없으면 서버의 `OPENAI_API_KEY` 환경변수 사용
  - 둘 다 없으면 LLM 기능 없이 온톨로지 추론만 수행

요청 예시:

```bash
curl -X POST "http://127.0.0.1:8002/api/chat" \
  -H "Content-Type: application/json" \
  -H "X-OpenAI-API-Key: sk-..." \
  -d '{"query": "Fz가 -350N인데 이게 뭐야?"}'
```

요청 본문 예시:

```json
{
  "query": "Fz가 -350N인데 이게 뭐야?",
  "context": {
    "currentView": "live",
    "selectedEntity": "Fz"
  }
}
```

### 4.2 ChatResponse (응답)

- snake_case 기준(백엔드):
  - `trace_id`, `query_type`, `abstain`, `abstain_reason`
  - `evidence.ontology_paths`, `evidence.document_refs`, `evidence.similar_events`
  - `graph.nodes[*].state`(UI 색상/강조에 활용)

프론트 정규화(권장):

- 어댑터: [frontend/src/lib/api.ts](../../frontend/src/lib/api.ts)의 `normalizeChatResponse()`
- ABSTAIN UI 연동을 위해 다음도 매핑됨(프론트 검수에서 보완 완료):
  - `partial_evidence` → `partialEvidence`
  - `suggested_questions` → `suggestedQuestions`

### 4.3 Evidence 조회

- 엔드포인트: `GET /api/evidence/{trace_id}`
- 동작:
  - 존재하면 `found: true` + `evidence` + `full_response`
  - 없으면 `found: false`

---

## 5) 엔드포인트 목록(요약)

구현 위치: [src/api/main.py](../../src/api/main.py)

- System
  - `GET /health`
- Chat/Evidence
  - `POST /api/chat`
  - `GET /api/evidence/{trace_id}`
- Ontology
  - `GET /api/ontology/summary`
- Sensors
  - `GET /api/sensors/readings?limit=60&offset=0`
  - `GET /api/sensors/patterns?limit=10`
  - `GET /api/sensors/events?limit=20`
  - `GET /api/sensors/stream?interval=1.0` (SSE)

SSE 테스트 예시(터미널):

- `curl -N "http://127.0.0.1:8002/api/sensors/stream?interval=1"`

---

## 6) 데이터 디렉토리(운영 기준)

- 문서/청크/온톨로지(오프라인 파이프라인 산출물)
  - `data/processed/chunks/`
  - `data/processed/ontology/`
- 센서(데모 재생용)
  - `data/sensor/raw/axia80_week_01.parquet`
  - `data/sensor/processed/detected_patterns.json`
  - `data/sensor/processed/anomaly_events.json`

센서 파일이 없으면 API는 비어있는 응답을 반환하거나 경고 로그를 남깁니다(예: readings=빈 배열).

---

## 7) Neo4j(선택) - 그래프 DB

- 실행: [docker-compose.yaml](../../docker-compose.yaml)
- 기본 포트:
  - 브라우저: `http://localhost:7474`
  - Bolt: `bolt://localhost:7687`
- 기본 계정(데모용): `neo4j/password123`

주의: 운영 환경에서는 비밀번호/볼륨/권한을 별도로 관리해야 합니다.

---

## 8) 검증/테스트

### 8.1 P0 합격 기준 검증(권장)

- E2E: [scripts/e2e_validate.ps1](../../scripts/e2e_validate.ps1)
- 검증 스크립트: [scripts/validate_api.py](../../scripts/validate_api.py)

검증이 확인하는 것(요약):

- `/health` 접근
- `/docs` 접근
- `POST /api/chat` 응답에 `trace_id` 존재
- ABSTAIN 케이스에서 `abstain`/`abstain_reason`/`trace_id` 존재
- `GET /api/evidence/{trace_id}` 조회 가능
- `GET /api/ontology/summary` 응답 키 확인
- `GET /api/sensors/readings|patterns|events` 응답 키 확인
- `GET /api/sensors/stream` (SSE) 스모크: `data:` 라인 1개 수신 + 헤더 확인

### 8.2 pytest

- 단위/통합 테스트 위치: `tests/`
- 실행(예시): `pytest -q`

---

## 9) 트러블슈팅(현장용)

- 포트 점유: `scripts/e2e_validate.ps1 -ForceKillPort` 사용 권장
- SSE가 프록시에서 끊김:
  - 운영 프록시에서 버퍼링/타임아웃 설정 확인
  - 응답 헤더는 이미 `X-Accel-Buffering: no`를 포함
- 센서 데이터가 비어있음:
  - `data/sensor/raw/axia80_week_01.parquet` 경로/파일 존재 확인
- 프론트가 API를 못 붙음:
  - 프론트 환경변수 `NEXT_PUBLIC_API_URL=http://127.0.0.1:8002`
  - CORS 설정: 환경변수 `CORS_ORIGINS`로 허용 도메인 지정 (쉼표 구분)
    - 예: `CORS_ORIGINS=http://localhost:3000,https://myapp.com`
    - 미설정 시 기본값: `http://localhost:3000`, `http://127.0.0.1:3000`

---

## 10) 관련 문서(권장 읽는 순서)

- 프론트 관점 전체 검수: [SoT_프론트엔드_검증_리포트.md](SoT_프론트엔드_검증_리포트.md)
- UI와 데이터 구조: [SoT_UI_설계_명세서.md](SoT_UI_설계_명세서.md)
- P0 계약/재현: [SoT_재현성_가이드.md](SoT_재현성_가이드.md)
- 백엔드 런타임 검증 리포트: [SoT_백엔드_검증_리포트.md](SoT_백엔드_검증_리포트.md)
- 시스템 설계서(대형 스펙): [Unified_Spec.md](../Unified_Spec.md)
