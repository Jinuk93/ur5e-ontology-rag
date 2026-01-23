# Step 13: UI 및 API 계약 - 설계 문서

## 1. 개요

| 항목 | 내용 |
|------|------|
| Phase | 13 - Palantir-style UI (UI/계약 정리) |
| Stage | Stage 5 (Palantir-style UI) |
| 이전 단계 | Step 12 - 응답 생성 |
| 다음 단계 | Step 14 - 프론트엔드 구현 |
| 핵심 목표 | UI 설계 명세 + 프론트/백엔드 계약(SOT) 확정 + 재현 가능한 검증 루틴 고정 |

---

## 2. 목표

### 2.1 무엇을 확정하는가(정본, SoT)

- **UI 관점 정본**: Live/Graph/History + Chat(Evidence Drawer) 화면 구조와 데이터 요구사항
- **API 관점 정본(P0)**: 프론트가 바로 붙을 수 있는 `/api/chat` 중심 계약과 snake_case ↔ camelCase 전략
- **검증 관점 정본**: “문서-코드-런타임”이 일치함을 E2E로 재현 가능하게 고정

### 2.2 핵심 결정

- 백엔드는 **snake_case를 유지**하고(예: `trace_id`, `query_type`),
- 프론트는 **API 레이어에서 camelCase로 정규화**한다.
- Evidence 조회는 `trace_id` 기반으로 **`GET /api/evidence/{trace_id}`**를 사용한다.

---

## 3. 산출물(문서/코드)

### 3.1 문서(설계 정본)

- [SoT_UI_설계_명세서.md](../references/SoT_UI_설계_명세서.md): 화면/컴포넌트/데이터 스키마(프론트 기준)
- [SoT_백엔드_API_가이드.md](../references/SoT_백엔드_API_가이드.md): 백엔드 런타임/계약/엔드포인트 정리(운영 기준)
- [SoT_재현성_가이드.md](../references/SoT_재현성_가이드.md): P0 계약 정합성 + 재현 루틴(명령어) 고정
- [SoT_백엔드_검증_리포트.md](../references/SoT_백엔드_검증_리포트.md): 런타임 검증 체크리스트 결과

### 3.2 계약/어댑터(코드 정본)

- [frontend/src/lib/api.ts](../../frontend/src/lib/api.ts): snake_case → camelCase 정규화 어댑터(정본)
- [contracts/p0_api_adapter.ts](../../contracts/p0_api_adapter.ts): 타입/참고용 계약(문서화 목적)

---

## 4. API 계약(요약)

### 4.1 필수 엔드포인트(P0)

- `GET /health`
- `POST /api/chat`
- `GET /api/evidence/{trace_id}`

### 4.2 확장 엔드포인트(P2/P3)

- `GET /api/ontology/summary`
- `GET /api/sensors/readings?limit=60&offset=0`
- `GET /api/sensors/patterns?limit=10`
- `GET /api/sensors/events?limit=20`
- `GET /api/sensors/stream?interval=1.0` (SSE)

---

## 5. 검증(설계 단계에서의 합의)

### 5.1 재현 가능한 런타임 검증이 “설계의 일부”여야 하는 이유

- UI/백엔드/문서가 분리돼 있을수록 계약 드리프트가 발생한다.
- 따라서 Step 13에서 “정본 문서 + 실행 가능한 검증 스크립트”를 함께 고정한다.

### 5.2 검증 루틴(요약)

- PowerShell: `scripts/e2e_validate.ps1`
  - 서버 기동 → `/health` 대기 → `scripts/validate_api.py` → 서버 종료
- Python: `scripts/validate_api.py`
  - 핵심 엔드포인트 키 존재/호환성 검사 + SSE 스모크

---

## 6. 완료 기준(Definition of Done)

- UI 설계 문서가 Live/Graph/History + Chat(Evidence) 기준으로 정리되어 있다.
- 백엔드 계약이 `/api/chat` 중심으로 정리되어 있다.
- snake_case ↔ camelCase 전략과 “정본 파일” 위치가 문서에 명시되어 있다.
- `scripts/e2e_validate.ps1` 1회 실행으로 PASS를 재현할 수 있다.
