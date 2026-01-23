# Step 15: 센서 실시간 및 검증 - 설계 문서

## 1. 개요

| 항목 | 내용 |
|------|------|
| Phase | 15 - 센서 실시간(SSE/폴링) + 검증 자동화 |
| Stage | Stage 5 (Palantir-style UI) |
| 이전 단계 | Step 14 - 프론트엔드 구현 |
| 다음 단계 | (후속) Step 16 - 통합 테스트/데모 시나리오 |

---

## 2. 목표

- 센서 데이터는 “데모 재생” 관점에서 제공한다.
  - REST(폴링) + SSE(스트리밍) 두 경로 제공
- 데이터 부재/환경 이슈에서도 서버가 500으로 죽지 않고 **degrade**한다.
- Windows 환경에서 서버 start/stop까지 포함한 **무인(E2E) 검증**이 1회 실행으로 가능하다.

---

## 3. 산출물

### 3.1 백엔드 엔드포인트

- `GET /api/sensors/readings`
- `GET /api/sensors/patterns`
- `GET /api/sensors/events`
- `GET /api/sensors/stream` (SSE)

### 3.2 검증 스크립트

- `scripts/validate_api.py`: 런타임 호출 기반 스키마/호환성 검사 + SSE 스모크
- `scripts/e2e_validate.ps1`: 서버 기동/대기/검증/종료 자동화

---

## 4. 설계 원칙

- “데모 데이터가 없으면 실패”가 아니라, **빈 응답/에러 이벤트**로 degrade한다.
- SSE는 EventSource 호환 포맷(`data: {JSON}\n\n`)을 따른다.

---

## 5. 완료 기준(Definition of Done)

- validate 스크립트가 센서 3종 + SSE 포함 주요 엔드포인트를 런타임으로 확인한다.
- `scripts/e2e_validate.ps1` 1회 실행으로 PASS를 재현할 수 있다.
- parquet 엔진/데이터 부재 상황에서도 `/api/sensors/readings`가 500이 아닌 정상 응답을 반환한다.
