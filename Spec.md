# UR5e Ontology RAG 시스템 - 기술 설계서
---

## 📋 목차
1. 프로젝트 개요  
2. 타겟 디바이스 선정  
3. 공식 문서 데이터 (Ground Truth)  
4. 시스템 아키텍처(System Architecture)  
5. 폴더 구조 *(TBD)*  
6. 구성요소별 기술 스택 및 역할 *(TBD)*  
7. API Contract: 인터페이스 명세 *(TBD)*  
8. 온톨로지 구조 설계 *(TBD)*  
9. 근거 검증 규칙 *(TBD)*  
10. 정량적 성능 평가 계획 *(TBD)*  
11. 예외 처리 및 보안정책 *(TBD)*  

---

## 1. 프로젝트 개요

### 1.1 배경 및 문제점
- 설비 매뉴얼/에러코드 문서가 방대하고, 버전 및 형식(PDF/Web)이 분산되어 있어 현장에서 정보 탐색 시간이 큼
- 현장 엔지니어의 서술(구어체/약어/별칭)이 통일되지 않아 키워드 검색 및 RAG 품질이 흔들릴 수 있음
- 근거 없는 조치(Action) 제안은 안전/품질 리스크로 이어질 수 있음

### 1.2 프로젝트 목적
- **공식 Document Set을 단일 근거(Ground Truth)로 사용**
- 모호한 질의에 대해 **“증상-부품-원인-조치” 구조로 정규화(온톨로지 기반)**
- 답변마다 **근거(문서: doc/page/chunk)** + **추론 경로(그래프 path)**를 함께 제공하여 신뢰성 확보
- 초보 엔지니어가 **1차 진단/점검을 수행**할 수 있는 수준의 가이드 제공

### 1.3 핵심 가치
- 근거 우선: 근거가 없으면 답변을 제한하고 추가 질문으로 정보 보강
- 추적 가능성: “왜 이 결론?”을 온톨로지 경로와 근거로 설명
- 운영 가능: 도메인 지식은 `ontology.json`으로 지속 추가/수정 가능
- 현장 효율: 시나리오/매뉴얼 탐색 시간을 절감

### 1.4 최종 산출물
- **대시보드(Demo)**: 질문/답변 + 근거 문서 미리보기 + 그래프 추론 경로 시각화
- **엔진(Core)**: Ontology Reasoning(Neo4j) + Hybrid RAG(ChromaDB) + Verifier(Evidence Gate) + LLM(요약/생성)
- **데이터팩(Data)**:
  - UR5e Official Document Set(PDF)
  - `ontology.json` (Neo4j 적재용)
  - `sources.yaml`, `chunk_manifest.jsonl` (근거 추적 메타데이터)
  - ChromaDB persisted index
  - `audit_trail.jsonl` (trace 기반 감사/평가 로그)

---

## 2. 타겟 디바이스 선정 (UR5e)

### 2.1 선정 이유 (WHY)
1) 공식 문서의 완전성  
- Service Manual 및 Error Codes Directory가 공개되어 Ground Truth 확보가 용이

2) 글로벌 협동로봇 시장에서의 높은 활용도  
- 현장 적용 시나리오(고장/점검/수리)가 풍부하고 실무 활용도가 높음

3) 용어/인터페이스 표준이 잘 잡혀 있음  
- PolyScope 및 문서 체계가 비교적 정돈되어 있어 온톨로지 정규화/매핑에 유리

### 2.2 범위 설정 (Scope)
- 핵심 부품: 5~10개 핵심 부품 우선 집중 (예: Joint, Controller, Safety 등)
- 유지보수 시나리오: 10~20개 주요 고장/점검 시나리오 정의 (예: 특정 에러코드/증상 기반)

---

## 3. 공식 문서 데이터 (Ground Truth)

### 3.1 사용 문서
- Service Manual (e-Series): 문제 해결, 서비스 절차, 부품 교체 가이드
- Error Codes Directory (PolyScope): 에러 코드 → 설명 → 조치 매핑
- User Manual (UR5e): 운영 맥락, 안전 지침, 용어 정의 및 정렬
- Online Manuals Index (Support Site): 문서 간 상호참조 및 최신 업데이트 확인 (Reference)

> 원칙: **다음 3~4개 공식 PDF를 유일한 Ground Truth 소스로 사용**하여 신뢰성을 확보한다.

### 3.2 문서 식별자(doc_id) 정책 (권장)
- 모든 문서는 `doc_id`로 식별하며, 근거 조회/미리보기/감사로그에서 공통 키로 사용한다.
- 예: `UR_ServiceManual_eSeries_vX`, `UR_ErrorCodes_PolyScope_vY`, `UR5e_UserManual_vZ`

---

## 4. 시스템 아키텍처(System Architecture) — Ontology-first Hybrid RAG

### 4.1 설계 목표 (Ontology가 1번, RAG는 2번)
- **온톨로지 우선(Ontology-first)**: 사용자의 자연어 질의를 먼저 **온톨로지 엔티티/관계로 정규화**하고, 그래프 경로 기반으로 “가능한 원인/조치 후보”를 구성한다.
- **근거 우선(Evidence-first)**: 문서 근거(`doc/page/chunk`) 또는 그래프 경로가 없는 정보는 **강한 단정 출력 금지**(제한/추가질문으로 전환)한다.
- **추적 가능(Traceability)**: 모든 요청/응답은 `trace_id`로 재현 가능해야 한다. (입력 → 엔티티링킹 → 그래프경로 → 검색 → 검증 → 출력)
- **하이브리드 추론(Hybrid Reasoning)**:  
  - Graph(Neo4j) = 도메인 구조 + 인과/조치 논리의 뼈대  
  - Vector(ChromaDB) = 공식 문서 근거 확보(grounding)  
  - **원칙:** “그래프로 방향 잡고, 문서로 증명한다.”
- **안전한 조치(Action Safety)**: 조치(Action)는 **문서 인용(citation) 필수**. 근거 부족 시 **ABSTAIN(조치 제안 금지)** 한다.
- **운영 가능(Operability)**: 배치 인덱싱/그래프 적재/로그 수집이 분리되어 반복 운영 가능해야 한다.

---

### 4.2 전체 구성 (Offline + Online)

#### 4.2.1 Offline (One-time/Batch): Data Preparation
Offline 단계는 Online 단계가 “즉시 질의응답”할 수 있도록 아래 5가지를 준비한다.
1) **문서 텍스트 인덱스(Vector Store)**
2) **근거 추적 메타데이터(Evidence Metadata)**
3) **원본 PDF 저장소(PDF Repository)**
4) **온톨로지 그래프(Graph DB)**
5) **온톨로지 사전/동의어/정규화 룰(Ontology Lexicon)** *(온톨로지 중심을 위해 추가)*

#### 4.2.2 Online (Runtime): Inference & Serving
Online 단계는 UI → API → Core Logic 순으로 요청을 처리하며,
- 모든 처리 결과는 `trace_id`에 귀속된다.
- UI는 답변뿐 아니라 “근거 페이지 미리보기”와 “그래프 경로(왜 그런지)”를 함께 보여준다.
- 핵심 흐름은 **(자연어 → 온톨로지 정규화/추론) → (문서 근거로 검증/승인)** 이다.

---

### 4.3 Layer별 책임과 데이터 계약

#### 4.3.1 Layer 1 — UI (Streamlit Dashboard)
**책임**
- 엔지니어 질의 입력 및 결과 시각화
- 답변 “본문” + “근거 미리보기” + “그래프 경로(노드/관계)”를 한 화면 제공
- ABSTAIN 시: 조치 대신 **추가 질문 / 점검 체크리스트** 중심으로 UX 제공

**UI 핵심 데이터**
- `user_query`, `trace_id`
- `answer`
- `structured_data`: (증상-부품-원인-조치) 구조화 결과
- `evidence`: 문서 근거 목록(각 근거의 `doc/page/chunk` + `snippet`)
- `graph_path`: 그래프 추론 경로(노드/관계 시퀀스)
- `verifier_status`: PASS / ABSTAIN / FAIL
- (권장) `why_this`: “그래프 경로 요약 + 근거 요약” 한 줄 카드

---

#### 4.3.2 Layer 2 — API (FastAPI Server)
**책임**
- 외부 요청 단일 진입점(권한/입력 검증/레이트리밋/로깅)
- Core Logic 실행 트리거 및 결과 반환
- 근거/미리보기/헬스체크 등 부가 엔드포인트 제공

**권장 엔드포인트**
- `POST /query`
  - 입력: `user_query`, (optional) `session_id`, (optional) `filters`
  - 출력: `trace_id`, `verifier_status`, `answer`, `structured_data`, `verifier_result`
- `GET /evidence/{trace_id}`
  - 출력: `evidence`, `graph_path`, `ontology_debug(링킹결과)`, `retrieval_debug`, `audit_summary`
- `GET /preview?doc_id=...&page=...`
  - 출력: 해당 PDF 페이지 렌더(이미지/바이너리)
- `GET /health`
  - Neo4j/ChromaDB/파일스토어/LLM 연결 상태 점검

---

#### 4.3.3 Layer 3 — Core Logic (Ontology-first 질의 처리 파이프라인)
Core Logic은 “한 번의 질의”를 처리하는 고정된 파이프라인이다.  
핵심 컨셉은 다음과 같다.

- 자연어를 **온톨로지 엔티티/관계로 변환(정규화/링킹)** 해서 “추론 가능한 형태”로 만든다.
- 그래프가 생성한 후보(원인/조치/키워드)를 바탕으로 문서 검색을 수행하고,
- 문서 근거를 통해 최종 출력(특히 Action)을 **검증/승인**한다.

##### Step 0) Trace 생성 & 입력 정규화
- `trace_id` 발급(UUID 권장)
- 텍스트 정규화: 공백/기호/대소문자/한영 혼용/에러코드 표기(C-153, C153 등) 통일
- (선택) `session_id` 기반 최소 맥락 결합(최근 엔티티 유지 정도만)

##### Step 1) Entity Extraction (LLM-assisted) — 엔티티 “후보” 생성
- 질의에서 엔티티 후보를 추출한다. *(감지 단계)*
  - 예: `ErrorCode`, `Symptom`, `Component`, (선택) `Condition/Context`
- 이 결과는 아직 텍스트 후보이므로, 바로 Neo4j에 넣지 않고 Step 2에서 고정한다.

##### Step 2) Entity Linking (Ontology 핵심) — 후보를 그래프 노드 ID로 “고정”
- Step 1 후보를 **온톨로지 노드 ID**에 매핑한다. *(정규화/고정 단계)*
- 링크 방식(권장 혼합)
  - 사전/동의어 매칭: `ontology.json`의 `synonyms`
  - 정규표현식 룰: 에러코드/부품코드/표준 표기
  - (선택) 임베딩 유사도 기반 후보 보강
- 산출물
  - `linked_entities`: `{entity_type, node_id, confidence, matched_by}`
- 링크 실패 시 정책
  - 즉시 FAIL이 아니라, **추가 질문 후보 생성**(NEED_MORE_INFO)으로 전환  
    - 예: “에러코드가 C153 맞나요?”, “증상이 보호정지인가요, 브레이크 저항인가요?”

##### Step 3) Ontology Reasoning (Neo4j) — 그래프 경로로 “원인/조치 후보” 생성
- 링크된 엔티티를 seed로 Cypher 실행
- 산출물
  - `graph_paths`: 가능한 추론 경로들  
    - 예: `Symptom → MAY_CAUSE → Cause → FIXED_BY → Action`
  - `candidate_causes/actions`: 그래프 기반 Top-N 후보
  - `expansion_terms`: 관련 부품/동의어/연관 에러코드 등 검색 확장 키워드
- 중요한 규칙
  - 그래프는 “가능한 후보”를 낸다.
  - **확정/조치 제안은 문서 근거로만 한다.**

##### Step 4) Graph-guided Query Building — “그래프가 만든 검색 쿼리”
- `expanded_query = user_query + expansion_terms + (optional) doc_hint`
- (선택) `DocumentRef(REFERS_TO)`가 있다면 `doc_id` 힌트로 필터링 강화 가능  
  - 예: “이 조치는 Service Manual 섹션을 참조” 같은 힌트

##### Step 5) Vector Retrieval (ChromaDB) — 문서 근거 확보
- `expanded_query`를 embedding → top-k chunk 검색
- chunk 메타데이터(필수)
  - `doc_id`, `page`, `section`, `chunk_id`, `score`
- (권장) 그래프 힌트 기반 re-ranking
  - 그래프가 언급한 부품/원인/조치 키워드가 chunk에 포함되면 가점

##### Step 6) Evidence Alignment — 근거 정합성 정리
- retrieval 결과를 “근거 후보(evidence candidates)”로 정리한다.
- 같은 `doc_id/page`는 묶어서 미리보기/인용에 유리하게 만든다.
- (권장) Action 키워드가 chunk에 실제로 등장하는지 확인(헛인용 방지)

##### Step 7) Verifier (Evidence Gate) — 출력 제어(안전장치)
Verifier는 “출력 가능 여부”를 결정한다.
- **PASS**: 근거 충분 → 답변/조치 출력 허용
- **ABSTAIN**: 근거 부족 → 조치 금지 + 추가 질문/점검 후보 중심
- **FAIL**: 시스템 오류(DB 다운/타임아웃/내부 예외)

Verifier 핵심 규칙(요약)
- Cause(원인)
  - `graph_path` 존재 AND/OR 문서 근거 score 임계치 충족 시 “원인 후보”로 제시 가능  
  - 단, “확정” 표현은 금지하고 “가능성/후보” 톤 유지
- Action(조치)
  - **문서 citation(`doc_id/page/chunk`)이 반드시 있어야 출력 가능**
  - 그래프에 `FIXED_BY`가 있어도 문서 근거 없으면 **Action은 ABSTAIN**

##### Step 8) Answer Drafting (LLM) + Response Formatting
- LLM은 “문장화/요약/가독성” 역할에 집중(사실 생성 금지)
- 최종 출력은 구조화 포맷으로 고정한다.
  - Top causes (근거 + 그래프 경로)
  - Inspection steps (안전한 점검 순서)
  - Actions (Verifier 통과한 것만)
  - Evidence (`doc/page/chunk` + snippet)
  - Graph path (노드/관계 시퀀스)
  - `trace_id`, `verifier_status`

---

### 4.4 Layer 4 — Data Stores & Logging

#### 4.4.1 Neo4j (Graph DB) — 추론의 뼈대
- 역할: 온톨로지 기반 경로 탐색, 인과 구조 제공, query expansion 생성
- 저장 대상(예시)
  - Node: Component / Symptom / ErrorCode / Cause / Action / DocumentRef
  - Relationship: HAS_PART, HAS_SYMPTOM, MAY_CAUSE, FIXED_BY, REFERS_TO
- (권장) 무결성/인덱스
  - 고유 제약: `*_id UNIQUE`
  - 텍스트 검색: `name/synonyms` fulltext index

#### 4.4.2 ChromaDB Persisted Index (Vector Store) — 문서 근거
- 역할: 문서 chunk 임베딩 기반 top-k 검색
- 저장 대상
  - chunk text + embedding vector
  - metadata: `doc_id`, `page`, `section`, `chunk_id`, (optional) `source_url`

#### 4.4.3 Evidence Metadata Files — 근거 역추적(Preview/감사로그 핵심)
- `sources.yaml`: 문서 출처/식별자/버전 정보
- `chunk_manifest.jsonl`: `chunk_id -> (doc_id, page, section)` 매핑
- 목적: `/evidence`, `/preview`를 안정적으로 수행

#### 4.4.4 Source PDF Repository (Local Storage)
- 역할: 원본 PDF 보관 및 페이지 렌더 제공
- 조회 키: `(doc_id, page)` → PDF page 이미지 렌더

#### 4.4.5 Audit Store (`audit_trail.jsonl`) — 재현/평가의 연료
- 역할: 요청 단위 감사/재현/평가를 위한 로그 저장
- 최소 기록(권장)
  - `trace_id`, `timestamp`, `user_query`, (optional) `normalized_query`
  - `extracted_entities`, `linked_entities(node_id/confidence)`
  - `graph_paths(topN)`, `expansion_terms`
  - `retrieval_topk(doc_id/page/chunk_id/score)`
  - `verifier_status` + `decision_reason`
  - `final_answer` + `structured_data` 요약
- 활용
  - 재현(왜 이 답이 나왔는지)
  - 정량 평가(정확도/ABSTAIN 비율/근거정합률 등)

---

### 4.5 Layer 5 — External Services

#### 4.5.1 Embedding Service
- Offline: 문서 chunk embedding 생성
- Online: expanded query embedding 생성

#### 4.5.2 LLM Service
- Entity Extraction 보조
- 답변 문장화(요약/표현)
- 주의: 조치(Action)는 Verifier 통과한 문서 근거 기반만 허용

---

### 4.6 핵심 동작 시나리오(요약)
1) 사용자가 UI에 질의 입력  
2) API가 `trace_id` 발급 후 Core Logic 실행  
3) 엔티티 추출 → **온톨로지 링크(핵심)** → 그래프 경로 탐색/후보 생성  
4) 그래프 기반 확장 쿼리 → 벡터 검색(top-k) → 근거 정합성 정리  
5) Verifier가 PASS/ABSTAIN/FAIL 결정  
6) PASS면 조치 포함 답변 / ABSTAIN이면 조치 금지 + 추가 질문/점검 중심  
7) `/evidence/{trace_id}`로 근거/경로/로그 조회  
8) `/preview`로 근거 PDF 페이지를 UI에서 즉시 렌더링

---

## 5. 폴더 구조 (Repository Layout)

본 구조는 **Offline(배치 준비)** 와 **Online(실시간 서빙)** 를 엄격히 분리하고,  
Ontology-first 운영을 위해 **Entity Linking/정규화 룰(lexicon/rules)** 을 “구성요소로서” 명시한다.

### 5.1 설계 원칙
- **Offline/Online 분리**: 인덱싱/그래프 적재는 배치로, 질의응답은 런타임으로 운영한다.
- **온톨로지 운영 가능성**: 동의어/정규화/링킹 룰을 파일로 관리하여 지속 개선 가능해야 한다.
- **추적 가능성**: 모든 요청 결과는 `trace_id`로 재현 가능한 형태로 저장/조회된다.
- **DB 볼륨 분리**: Chroma/Neo4j/Audit 로그는 마운트 볼륨으로 운영한다.