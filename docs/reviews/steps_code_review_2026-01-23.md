# Step 문서 기준 코드 구현 리뷰 (Step 01~17)

- 작성일: 2026-01-23
- 범위: `docs/steps/step_01~step_17_*.md`가 요구하는 구현이 실제 코드/스크립트/테스트/프론트 구성과 정합한지 점검
- 방식:
  - Step 문서에서 경로(코드/데이터/스크립트)를 추출해 **존재 여부 1차 대조**
  - 핵심 구현 파일을 중심으로 **구조/책임/테스트 가능성/리팩토링 후보**를 리뷰
  - 본 문서는 “리뷰(근거+개선안)” 목적이며, 본 리뷰 작성 시점에는 코드 수정/리팩토링을 수행하지 않음

---

## 0. 요약 결론

- 전반: Step 01~15, 17은 **요구 구현물이 대부분 존재**하며(모듈/스크립트/설정/프론트 포함), E2E 검증 루틴(서버 기동→검증→종료)도 구성되어 있음.
- 가장 큰 갭: Step 16(통합 테스트)에서 문서가 기대하는 `tests/unit/*` 기반 단위 테스트 세트가 현재 사실상 부재(빈 패키지). 통합 테스트도 `tests/integration/test_api_query.py` 1개로 제한되어 테스트 안전망이 약함(E2E 재현은 가능).
- 구조적 기술부채: API가 `src/api/main.py` 단일 파일에 집중되어 있고 `src/api/routes/`, `src/api/schemas/`는 사실상 placeholder 상태. Step 문서가 말하는 “라우터/스키마 분리” 목표와는 간극이 있음.

---

## 1. Step별 정합성 체크(요약)

> 상태 기준
> - **PASS**: Step 문서가 요구하는 핵심 구현/산출물이 존재하고 흐름이 자연스럽게 연결됨
> - **WARN**: 동작은 가능하나 구조/테스트/운영 관점의 갭(리팩토링 필요)이 큼
> - **FAIL**: Step 문서가 요구하는 핵심 구현물이 누락 또는 대체 불가한 수준의 드리프트

| Step | 상태 | 근거(핵심) |
|---:|:---:|---|
| 01 환경설정 | WARN | 설정/패키지 구조는 정리되어 있으나 API `routes/`/`schemas/`는 placeholder |
| 02 데이터준비 | PASS | ingestion 모듈 + manifest/chunks 산출물 + 실행 스크립트 구성 |
| 03 문서인덱싱 | PASS | embedding 모듈 + Chroma 저장소 + 실행 스크립트 구성 |
| 04 온톨로지스키마 | PASS | schema/models 정의 + 스키마 파일(데이터) 존재 |
| 05 엔티티관계구축 | PASS | loader + build 스크립트 + ontology.json/lexicon.yaml 존재 |
| 06 추론규칙 | PASS | rule_engine + inference_rules.yaml + 관련 설정 파일 존재 |
| 07 센서데이터처리 | PASS | data_loader/sensor_store + 데이터 경로/검증 스크립트 존재 |
| 08 패턴감지 | PASS | patterns/pattern_detector + thresholds 설정 존재 |
| 09 온톨로지연결 | PASS | ontology_connector + error_pattern_mapping.yaml 존재 |
| 10 질문분류기 | PASS | query_classifier + evidence_schema + entity_extractor 존재 |
| 11 온톨로지추론 | PASS | graph_traverser + ontology_engine 구현 존재 |
| 12 응답생성 | PASS | response_generator + confidence_gate + prompt_builder 존재 |
| 13 UI 및 API 계약 | WARN | API 계약/검증 루틴은 있으나 백엔드 코드 구조(라우터/스키마 분리) 부채 큼 |
| 14 프론트엔드구현 | PASS | Next.js 프론트 구조 + api.ts 정규화 계층 존재 |
| 15 센서실시간 및 검증 | PASS | `/api/sensors/*` + SSE + validate/e2e 스크립트 존재 |
| 16 통합테스트 | WARN | E2E/통합 테스트는 존재하나 `tests/unit/*`가 비어 테스트 안전망이 문서 기대치에 못 미침 |
| 17 데모시나리오 | PASS | run_api + e2e_validate 기반 재현 시나리오 구성 |

---

## 2. 핵심 구현 매핑(대표)

- 설정/환경: `src/config.py`, `configs/settings.yaml`, `.env(.example)`, `requirements.txt`
- 데이터 준비(문서): `src/ingestion/*`, `scripts/run_ingestion.py`, `data/processed/chunks/*`, `data/processed/metadata/*`
- 임베딩/벡터스토어: `src/embedding/*`, `scripts/run_embedding.py`, `stores/chroma/*`
- 온톨로지: `src/ontology/*`, `data/processed/ontology/*`, `scripts/build_ontology.py`, `configs/*rules*.yaml`
- 센서: `src/sensor/*`, `data/sensor/*`, `scripts/detect_patterns.py`, `scripts/validate_sensor_data.py`
- RAG/추론 파이프라인: `src/rag/*`
- API: `src/api/main.py` (현재 대부분의 엔드포인트/스키마 집중)
- 프론트: `frontend/src/*` (특히 `frontend/src/lib/api.ts`가 계약/정규화의 정본 역할)

---

## 3. Step 16(통합 테스트) 드리프트 상세

Step 16 문서에서 기대하는 범위(요약):
- 단위 테스트: `tests/unit/*` (추론/검색/검증 로직)
- 통합 테스트: `tests/integration/*` (API 계약)
- E2E: `scripts/e2e_validate.ps1` + `scripts/validate_api.py`

현재 상태(워크스페이스 기준):
- `tests/unit/`는 패키지로만 존재하고 실제 테스트 파일이 없음
- `tests/integration/`는 `test_api_query.py` 1개만 존재
- E2E 스크립트는 존재(재현성 자체는 OK)

결론:
- “테스트 계층(유닛/통합/EE) 균형”이라는 Step 16 의도 대비 **pytest 기반 단위 테스트 근거가 부족**함.
- 다만 E2E 스크립트와 통합 테스트는 존재하므로 “런타임 재현성” 관점에서는 충족, “회귀 방지 안전망” 관점에서는 보강 필요.

---

## 4. 리팩토링 백로그(우선순위)

### P0 (리팩토링 착수 전 안전망)
1. `tests/unit/`에 최소 단위 테스트 세트 추가
   - 대상: `src/ontology/ontology_engine.py`, `src/ontology/graph_traverser.py`, `src/rag/query_classifier.py`, `src/rag/confidence_gate.py`
2. `tests/integration/` 확장
   - 대상: `/health`, `/api/chat`, `/api/evidence/{trace_id}`, `/api/ontology/summary`, `/api/sensors/*`, SSE 스모크(가능 범위)

### P1 (구조 개선)
3. `src/api/main.py` 분리
   - `src/api/routes/*`에 router로 분해하고, pydantic 모델을 `src/api/schemas/*`로 이동
4. 센서 데이터 로딩/캐시 로직을 `src/sensor/`로 이동하고 API는 thin controller로 유지

### P2 (품질/운영)
5. 설정/경로 의존성 통일
   - API에서 `Path(__file__)...`로 센서 경로를 잡는 부분을 `get_settings().paths.sensor_dir`로 통일
6. 런타임 검증 스크립트(validate_api)가 “계약 정본” 역할을 하도록 스키마/필드 검증을 더 엄격히(단, degrade 정책은 명시적으로 허용)

---

## 5. 다음 액션 제안

- (권장) 위 P0부터 진행해서 테스트 안전망 확보 후, API 분리/모듈 책임 정리(P1)로 들어가는 순서가 리스크가 가장 낮습니다.
- 원하시면, 이 리뷰를 기반으로 **리팩토링 브랜치 작업 계획(TODO) + 첫 번째 PR 단위(예: API router 분리 1차)**까지 바로 잡아드릴 수 있습니다.
