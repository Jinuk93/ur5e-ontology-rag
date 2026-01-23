# Step 16: 통합 테스트 - 설계 문서

## 1. 개요

| 항목 | 내용 |
|------|------|
| Phase | 16 - 통합 테스트 (Integration Test) |
| Stage | Stage 6 (Demo & Evaluation) |
| 이전 단계 | Step 15 - 센서 실시간 및 검증 |
| 다음 단계 | Step 17 - 데모 시나리오 |

---

## 2. 목표

- 문서에 정의된 핵심 계약과 실행 절차가 **런타임에서 재현 가능**함을 고정한다.
- “백엔드 단독 PASS”뿐 아니라, 프론트 빌드 게이트/기본 동작까지 포함해 **데모 가능한 상태**를 보장한다.

---

## 3. 검증 범위

### 3.1 백엔드 런타임 API 검증(필수)

- 스크립트 기반: `scripts/e2e_validate.ps1` + `scripts/validate_api.py`
- 검증 대상(요약):
  - `/health`, `/docs`
  - `/api/chat`, `/api/evidence/{trace_id}`
  - `/api/ontology/summary`
  - `/api/sensors/readings|patterns|events|stream(SSE)`

### 3.2 pytest(권장)

- `tests/unit/*`: 코어 로직(추론/검색/검증) 단위 테스트
- `tests/integration/*`: API/통합 관점 테스트

### 3.3 프론트 품질 게이트(권장)

- `frontend/`에서:
  - `npm run lint`
  - `npm run build`

---

## 4. 재현 절차(설계)

### 4.1 E2E 한 방(권장, Windows)

PowerShell(레포 루트):

- `powershell -ExecutionPolicy Bypass -File scripts/e2e_validate.ps1 -Port 8002 -ForceKillPort`

### 4.2 pytest

- `pytest -q`

### 4.3 프론트 빌드

- `cd frontend`
- `npm run lint`
- `npm run build`

---

## 5. 완료 기준(Definition of Done)

- E2E 검증 스크립트가 1회 실행으로 PASS(Exit Code 0)한다.
- pytest가 수집/실행 가능하며(환경에 따라 일부 선택), 핵심 단위/통합 테스트가 PASS한다.
- 프론트 `lint/build`가 PASS한다.
- 위 재현 커맨드들이 문서에 고정되어 있다.
