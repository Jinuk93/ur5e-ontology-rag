# Step 16: 통합 테스트 - 완료 보고서

## 1. 완료 요약

| 항목 | 내용 |
|------|------|
| Phase | 16 - 통합 테스트 |
| 상태 | ✅ 완료 |
| 이전 단계 | Step 15 - 센서 실시간 및 검증 |
| 다음 단계 | Step 17 - 데모 시나리오 |

---

## 2. 검증 산출물(정본)

- E2E 실행 스크립트: [scripts/e2e_validate.ps1](../../scripts/e2e_validate.ps1)
- 런타임 API 검증: [scripts/validate_api.py](../../scripts/validate_api.py)
- 검증 결과 리포트: [SoT_백엔드_검증_리포트.md](../references/SoT_백엔드_검증_리포트.md)

- 통합 테스트(예):
  - [tests/integration/test_api_query.py](../../tests/integration/test_api_query.py)

---

## 3. 재현 커맨드

### 3.1 백엔드 E2E(권장)

- `powershell -ExecutionPolicy Bypass -File scripts/e2e_validate.ps1 -Port 8002 -ForceKillPort`

### 3.1b 실행 증빙(요약)

- 2026-01-23 기준: E2E 실행 PASS (Exit Code 0)
- 상세 로그/근거: [SoT_백엔드_검증_리포트.md](../references/SoT_백엔드_검증_리포트.md)

### 3.2 pytest(선택)

- `pytest -q`

### 3.3 프론트 품질 게이트(선택)

- `cd frontend`
- `npm run lint`
- `npm run build`

---

## 4. 비고

- 본 Step은 “문서-코드-런타임 정합성”을 통합 관점에서 고정한다.
- 데이터/엔진 부재로 인한 센서 API 500을 방지하기 위해, 센서 영역은 degrade 정책을 허용한다(빈 배열/에러 이벤트).
