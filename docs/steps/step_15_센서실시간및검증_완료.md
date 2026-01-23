# Step 15: 센서 실시간 및 검증 - 완료 보고서

## 1. 완료 요약

| 항목 | 내용 |
|------|------|
| Phase | 15 - 센서 실시간 및 검증 |
| 상태 | ✅ 완료 |
| 이전 단계 | Step 14 - 프론트엔드 구현 |
| 다음 단계 | (후속) Step 16 - 통합 테스트/데모 |

---

## 2. 구현/검증 산출물

### 2.1 백엔드(센서/SSE)

- 구현 위치: [src/api/main.py](../../src/api/main.py)
- 엔드포인트:
  - `GET /api/sensors/readings`
  - `GET /api/sensors/patterns`
  - `GET /api/sensors/events`
  - `GET /api/sensors/stream` (SSE)

### 2.2 검증 자동화

- [scripts/validate_api.py](../../scripts/validate_api.py)
  - 8/8(+health) 엔드포인트 런타임 검증 + SSE 스모크
- [scripts/e2e_validate.ps1](../../scripts/e2e_validate.ps1)
  - 서버 기동 → `/health` 대기 → validate 실행 → 서버 종료

### 2.3 런타임 검증 리포트

- [SoT_백엔드_검증_리포트.md](../references/SoT_백엔드_검증_리포트.md)

---

## 3. 재현 방법

PowerShell에서(레포 루트):

- `powershell -ExecutionPolicy Bypass -File scripts/e2e_validate.ps1 -Port 8002 -ForceKillPort`

---

## 4. Degrade 정책(데모 데이터 부재)

- 센서 parquet가 없거나 parquet 엔진이 없는 환경에서도 서버는 예외를 흡수하고,
  - readings는 `[]`로 반환될 수 있다.
  - SSE는 에러 이벤트를 1회 송출하고 종료될 수 있다.

이 정책은 “데모 데이터/환경 부재로 인한 500”을 방지하기 위한 의도된 동작이다.
