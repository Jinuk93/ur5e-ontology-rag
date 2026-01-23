# Steps vs 코드 구현 리뷰

- Review Date: 2026-01-23
- 검수 기준: `docs/steps/*.md` (Step 01~17) 문서 대비 실제 코드 구현 정합성
- 목적: 리팩토링 기준 수립

---

## 1. 결론 요약

### 전체 판정: ✅ PASS (17/17 Steps 구현 완료)

| 구분 | 상태 | 비고 |
|------|------|------|
| Phase 1-3 (Data Pipeline) | ✅ 완료 | 722 chunks 인덱싱 |
| Phase 4-6 (Ontology) | ✅ 완료 | 54 entities, 62 relationships |
| Phase 7-9 (Sensor) | ✅ 완료 | 4 pattern types, 17 detected |
| Phase 10-12 (Query Engine) | ✅ 완료 | 3 QueryTypes, ABSTAIN 처리 |
| Phase 13-17 (UI/Demo) | ✅ 완료 | E2E PASS (2026-01-23) |

### 리팩토링 필요 항목

| 우선순위 | 항목 | 파일 | 예상 작업량 |
|---------|------|------|-----------|
| 🔴 High | CORS 설정 | `src/api/main.py:57` | 5분 |
| 🔴 High | Evidence Store 영속성 | `src/api/main.py:71` | 30분 |
| 🟠 Medium | TODO 미완성 (vibration/drift) | `src/ontology/rule_engine.py:~200` | 2-4시간 |
| 🟠 Medium | 하드코딩된 임계값 | `src/sensor/pattern_detector.py` | 1시간 |
| 🟠 Medium | doc_type 불일치 | `data/processed/chunks/` | 10분 |
| 🟠 Medium | GraphTraverser depth 기본값 | `src/ontology/graph_traverser.py` | 15분 |
| 🟢 Low | 메모리 확장성 | `src/sensor/data_loader.py` | 향후 |
| 🟢 Low | TimeExpression 파싱 확장 | `src/rag/entity_extractor.py` | 향후 |
| 🟢 Low | Frontend Error Boundary | `frontend/src/` | 향후 |

---

## 2. Phase별 상세 리뷰

### Phase 1-3: Data Pipeline (환경 → 인덱싱)

#### Step 01: 환경설정 ✅

**파일**:
- `src/config.py` (213 lines) - 8개 설정 클래스
- `src/__init__.py` (34 lines)
- `requirements.txt` (84 packages)
- `configs/settings.yaml`

**장점**:
- Dataclass 기반 설정 + `@lru_cache` 싱글톤
- 환경변수 + YAML 분리

**이슈**:
- ⚠️ Neo4j 기본 비밀번호가 배포 기본값으로 포함됨 (`.env`, `docker-compose.yaml`의 `password123`) → 변경 권장
- ⚠️ CORS `allow_origins=["*"]` → 프로덕션 제한 필요

---

#### Step 02: 데이터 준비 ✅

**파일**:
- `src/ingestion/models.py` (130 lines)
- `src/ingestion/pdf_parser.py` (145 lines)
- `src/ingestion/chunker.py` (140 lines)

**결과**: 3개 PDF → 722 chunks (426 + 197 + 99)

**이슈**:
- ⚠️ `doc_type` 필드 불일치: `error_codes` vs `error_code`
  - `pdf_parser.py`: "error_codes" (복수)
  - `error_codes_chunks.json`: "error_code" (단수)
  - 단, 로드 시 `src/ingestion/models.py`의 `DOC_TYPE_ALIASES`로 `error_code → error_codes` 정규화됨 (런타임 영향은 제한적)

---

#### Step 03: 문서 인덱싱 ✅

**파일**:
- `src/embedding/embedder.py` (115 lines)
- `src/embedding/vector_store.py` (250 lines)
- `scripts/run_embedding.py` (200 lines)

**장점**:
- OpenAI 배치 처리 (100개/배치)
- ChromaDB cosine 거리 메트릭

**이슈**:
- ✅ Chroma 컬렉션 메타데이터에 `hnsw:space=cosine` 설정됨
  - 현재 점수 변환(`score = 1 - distance`)도 cosine 가정에 맞음
  - 추후 `hnsw:space`가 바뀌면(예: l2) score 변환 로직도 함께 조정 필요

---

### Phase 4-6: Ontology Layer (스키마 → 규칙)

#### Step 04: 온톨로지 스키마 ✅

**파일**:
- `src/ontology/schema.py` (191 lines)
- `src/ontology/models.py` (175 lines)
- `data/processed/ontology/schema.yaml` (280 lines)

**구조**:
- 4 Domains (Equipment, Measurement, Knowledge, Context)
- 16 EntityTypes
- 14 RelationTypes

**이슈**:
- ⚠️ `Entity.properties` dict 스키마 검증 없음

---

#### Step 05: 엔티티/관계 구축 ✅

**파일**:
- `src/ontology/loader.py` (204 lines)
- `data/processed/ontology/ontology.json` (501 lines)
- `data/processed/ontology/lexicon.yaml` (402 lines)

**결과**: 54 entities, 62 relationships (62/62 PASS)

**장점**:
- Lexicon alias 해석 (synonyms/aliases 둘 다 지원)
- 캐시 + 명시적 캐시 무효화

---

#### Step 06: 추론 규칙 ✅

**파일**:
- `src/ontology/rule_engine.py` (503 lines)
- `configs/inference_rules.yaml` (211 lines)

**기능**:
- State 추론 (Fz 범위 → Normal/Warning/Critical)
- Pattern 감지 (현재: collision, overload)
- Cause 추론 + Error 예측

**이슈**:
- ❌ **TODO 미완성** (Line ~200): `# TODO: 진동, 드리프트 감지 추가`
- ✅ 임계값은 `configs/pattern_thresholds.yaml`을 로드하고, 미존재/키 누락 시 코드 기본값으로 폴백

---

### Phase 7-9: Sensor Integration (데이터 → 온톨로지 연결)

#### Step 07: 센서 데이터 처리 ✅

**파일**:
- `src/sensor/data_loader.py` (138 lines)
- `src/sensor/sensor_store.py` (265 lines)

**장점**:
- Parquet 로딩 + 캐싱
- 선형 보간 (결측치 처리)
- RuleEngine 통합

**이슈**:
- ⚠️ 메모리 사용량: 604,800 레코드 전체 로드 (확장성 한계)

---

#### Step 08: 패턴 감지 ✅

**파일**:
- `src/sensor/patterns.py` (92 lines)
- `src/sensor/pattern_detector.py` (629 lines)

**결과**: 4 pattern types, 17 detected

**기능**:
- Collision (피크 감지)
- Overload (지속 임계값)
- Drift (비율 + 절대값 폴백)
- Vibration (rolling std)

**이슈**:
- ⚠️ `src/sensor/pattern_detector.py`는 임계값을 클래스 상수로 하드코딩
  - 참고: `configs/pattern_thresholds.yaml`은 `src/ontology/rule_engine.py`에서 사용 중이므로, "미사용"이라기보다 "모듈 간 설정 분산" 이슈에 가까움

---

#### Step 09: 온톨로지 연결 ✅

**파일**:
- `src/sensor/ontology_connector.py` (480 lines)
- `configs/error_pattern_mapping.yaml` (198 lines)

**기능**:
- Pattern → Error 매핑 (TRIGGERS)
- Pattern → Cause 매핑 (INDICATES)
- Shift 시간대 매핑 (6-14: A, 14-22: B, 22-6: C)

**이슈**:
- ⚠️ Shift 매핑 하드코딩 (설정화 필요)

---

### Phase 10-12: Query Engine (분류 → 생성)

#### Step 10: 질문 분류기 ✅

**파일**:
- `src/rag/evidence_schema.py` (152 lines)
- `src/rag/entity_extractor.py` (323 lines)
- `src/rag/query_classifier.py` (352 lines)

**기능**:
- QueryType: ONTOLOGY, HYBRID, RAG
- 한국어 조사 지원 (가/이/를/은/는/도/에서/의/로)
- 엔티티 추출: Axis, Value, ErrorCode, TimeExpression, Pattern, Shift, Product

**테스트 결과**: 100% 정확도

**이슈**:
- ⚠️ TimeExpression 파싱 제한적 (어제, 오늘, 시간만)

---

#### Step 11: 온톨로지 추론 ✅

**파일**:
- `src/ontology/graph_traverser.py` (599 lines)
- `src/ontology/ontology_engine.py` (646 lines)

**기능**:
- BFS 그래프 탐색 (depth/direction/relation 필터)
- 최단 경로 찾기
- 관계 체인 추적 (INDICATES → RESOLVED_BY)

**이슈**:
- ⚠️ `max_depth` 기본값 3 → 5로 증가 권장
- ⚠️ Null 체크 누락 (일부 경로)

---

#### Step 12: 응답 생성 ✅

**파일**:
- `src/rag/confidence_gate.py` (245 lines)
- `src/rag/prompt_builder.py` (220 lines)
- `src/rag/response_generator.py` (445 lines)

**기능**:
- ConfidenceGate: 4가지 ABSTAIN 조건
- 템플릿 기반 응답 생성 (LLM 미사용)
- Graph 데이터 생성 (nodes/edges)

**이슈**:
- ⚠️ `PromptBuilder` 존재하나 미사용 (향후 LLM 통합용?)
- ⚠️ Evidence store 인메모리 (세션 종료 시 소실)

---

### Phase 13-17: UI & Deployment

#### Step 13: UI 및 API 계약 ✅

**산출물**:
- `SoT_UI_설계_명세서.md`
- `SoT_백엔드_API_가이드.md`
- `contracts/p0_api_adapter.ts`

**이슈**:
- ⚠️ CORS `allow_origins=["*"]` (프로덕션 제한 필요)

---

#### Step 14: 프론트엔드 구현 ✅

**파일**:
- `frontend/src/lib/api.ts` - snake_case → camelCase 정규화
- `frontend/src/components/{live,graph,history,chat}/*`

**장점**:
- TypeScript 타입 안전성
- API 어댑터 패턴 (`normalizeChatResponse()`)
- Fallback 처리 (snake_case OR camelCase 둘 다 수용)

**이슈**:
- ⚠️ API URL에 로컬 기본값 fallback 존재 (`NEXT_PUBLIC_API_URL` 미설정 시 `http://127.0.0.1:8002`)
  - 프로덕션에서는 `NEXT_PUBLIC_API_URL`을 반드시 주입하도록 배포 가이드/검증(빌드 시 체크) 추가 권장
- ⚠️ Error Boundary 없음

---

#### Step 15: 센서 실시간 및 검증 ✅

**파일**:
- `src/api/main.py` - REST + SSE 엔드포인트
- `scripts/validate_api.py` - 8/8 엔드포인트 검증
- `scripts/e2e_validate.ps1` - E2E 스크립트

**장점**:
- Degrade 정책 문서화 (데이터 없으면 `[]` 반환)

---

#### Step 16: 통합 테스트 ✅

**인프라**:
- `scripts/e2e_validate.ps1` - E2E (PASS 2026-01-23)
- `tests/integration/test_api_query.py`
- `scripts/validate_api.py`

**이슈**:
- ⚠️ 테스트 커버리지/안전망 불명확
  - `tests/unit/`는 현재 실질 테스트가 없음(`__init__.py`만 존재)
  - 현재 근거는 E2E 스크립트 + 통합 테스트 중심이므로, 회귀 방지를 위해 유닛 테스트 최소셋(핵심 모듈) 보강 권장

---

#### Step 17: 데모 시나리오 ✅

**시나리오**:
1. ChatPanel → trace_id → Evidence Drawer
2. Graph View → Path Breadcrumb
3. Live View (REST/SSE) + degrade 처리

---

## 3. 리팩토링 권장 사항

### 3.1 High Priority (프로덕션 전 필수)

#### A. CORS 설정 수정
```python
# src/api/main.py:57
# 변경 전
allow_origins=["*"]

# 변경 후
allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
```
**예상 작업량**: 5분

---

#### B. Evidence Store 영속성 문서화 또는 구현
```python
# src/api/main.py:71
# 현재: 인메모리 dict (세션 종료 시 소실)
_evidence_store: Dict[str, Dict[str, Any]] = {}

# 옵션 1: 문서화 (최소)
# 옵션 2: 파일 기반 저장소 구현
```
**예상 작업량**: 30분

---

### 3.2 Medium Priority (곧 수정 권장)

#### C. TODO 완성 (vibration/drift 추론)
```python
# src/ontology/rule_engine.py:~200
# TODO: 진동, 드리프트 감지 추가
```
**예상 작업량**: 2-4시간

---

#### D. 임계값 설정 통합
```python
# 현재: 여러 파일에 하드코딩
# - src/sensor/pattern_detector.py: class constants
# - src/ontology/rule_engine.py: configs/pattern_thresholds.yaml 사용 (일부 폴백 기본값 포함)

# 권장: configs/pattern_thresholds.yaml를 단일 SoT로 두고,
#       PatternDetector도 동일 설정을 읽도록 통합(또는 RuleEngine에 위임)
```
**예상 작업량**: 1시간

---

#### E. doc_type 불일치 해결
```bash
# 옵션 1: chunks 재생성
python scripts/run_embedding.py --force

# 옵션 2: 검색 시 정규화
```
**예상 작업량**: 10분

---

#### F. GraphTraverser depth 기본값 증가
```python
# src/ontology/graph_traverser.py
# 변경 전: max_depth=3
# 변경 후: max_depth=5
```
**예상 작업량**: 15분

---

### 3.3 Low Priority (향후 개선)

- 메모리 확장성: DataLoader 스트리밍/청킹
- TimeExpression 파싱 확장 ("30분", "2시간" 지원)
- Frontend Error Boundary 추가
- Neo4j 프로덕션 자격 증명 관리

---

## 4. 코드 품질 분석

### 4.1 장점

| 항목 | 평가 |
|------|------|
| 아키텍처 | ✅ 4-Domain 온톨로지 + Phase 기반 파이프라인 명확 |
| 에러 처리 | ✅ Graceful degradation (센서 API) |
| 타입 안전성 | ✅ Dataclass + Type hints 일관 |
| 문서화 | ✅ 각 Step별 완료 보고서 |

### 4.2 개선 필요

| 항목 | 현황 | 권장 |
|------|------|------|
| 설정 관리 | 하드코딩 많음 | Config 파일 통합 |
| 영속성 | 인메모리 evidence | 세션 범위 문서화 또는 저장소 추상화 |
| 확장성 | 600K 레코드 전체 로드 | 청킹/스트리밍 고려 |

---

## 5. 최종 판단

- **코드 구현**: ✅ **SOLID** - 17개 Step 모두 구현 완료
- **프로덕션 준비**: ⚠️ **조건부** - High Priority 3개 항목 해결 필요
- **리팩토링 범위**: Medium Priority 항목 중심으로 진행 권장

### 권장 리팩토링 순서

1. CORS 수정 (5분)
2. doc_type 불일치 해결 (10분)
3. GraphTraverser depth 증가 (15분)
4. 임계값 설정 통합 (1시간)
5. Evidence Store 문서화 (30분)
6. TODO 완성 (2-4시간)

**총 예상 작업량**: 4-6시간
