# P0 API 계약 정합성 및 재현성 검증 작업보고서 (GPT)

- 작성일: 2026-01-23
- 목적: **프론트가 바로 붙을 수 있는 P0 API 계약(/api/chat)** 을 코드/문서/검증 스크립트 관점에서 정합하게 맞추고, Windows 환경에서 **재현 가능한 PASS 검증 루틴**을 확보한다.

---

## 1) 결론 요약 (지금 바로 알면 되는 것)

- P0 API 엔드포인트는 **`POST /api/chat` 단일 계약** 중심으로 정리됨.
- 요청은 `query`(권장) + `message`(하위호환) 모두 수용.
- 응답은 snake_case(`trace_id`, `query_type` 등)를 유지하며, 프론트는 **API 레이어 어댑터에서 camelCase로 변환하는 방식을 권장**.
- Evidence/Graph 스키마 드리프트를 막기 위해 검증 스크립트에서 **키 존재 체크**를 강화.
- 서버 실행 → 검증 → 종료를 한 번에 수행하는 **무인(E2E) PowerShell 스크립트**를 추가했고, 실제 실행에서 PASS 확인.

---

## 2) 배경/문제 정의

최근 작업의 핵심은 두 가지였다.

1. **계약 드리프트(문서 ↔ 코드 ↔ 프론트 기대치) 해결**
   - 요청 필드: `query` vs `message`
   - 응답 필드: `trace_id`/`traceId`, evidence/graph 하위 필드 누락

2. **Windows 환경에서 재현 가능한 검증 루틴 확보**
   - 포트 점유(이전 서버 프로세스 잔존)로 인해 검증이 흔들림
   - 콘솔 인코딩(cp949)에서 특정 문자 출력(체크마크 등) 문제가 날 수 있음
   - 서버 start/stop을 사람이 매번 수동으로 하지 않아도 되게 “한 방에” 돌릴 필요

---

## 3) 변경 사항(무엇을 했나)

### A. 검증 스크립트 개선: 포트/호스트 유연화

- 파일: scripts/validate_api.py
- 내용:
  - `--base-url` 인자 추가 (예: `http://127.0.0.1:8002`)
  - `--wait-seconds` 인자 추가 (서버 준비 대기 시간 조절)
  - 고정된 `http://localhost:8002` 의존을 제거해, 다양한 포트/환경에서 동일 검증 사용 가능

### B. 무인(E2E) 재현 스크립트 추가: start → validate → stop

- 파일: scripts/e2e_validate.ps1
- 역할:
  1) 포트 점유 여부 확인
  2) 필요 시 기존 리스닝 PID 강제 종료(`-ForceKillPort`)
  3) 서버 기동(`python scripts/run_api.py --host ... --port ...`)
  4) `/health` 응답이 올 때까지 대기
  5) `python scripts/validate_api.py` 실행
  6) 서버 종료 + 포트 해제 확인

- 작업 중 발견한 PowerShell 함정 및 수정:
  - `$Host`는 PowerShell 내장(읽기 전용) 변수 → 파라미터 이름을 `$BindHost`로 변경
  - `$PID`는 PowerShell 자동 변수 → foreach 루프 변수명을 `$procId`로 변경

### C. README 정리

- 파일: README.md
- 내용:
  - 기존 README가 비어 있어 최소한의 “실행/검증” 가이드를 추가
  - `scripts/e2e_validate.ps1` 단일 커맨드로 무인 재현이 가능함을 명시

---

## 4) 재현 방법 (내 PC에서 다시 PASS 확인)

### 4.1 한 줄로 전체 재현 (권장)

PowerShell에서:

- `powershell -ExecutionPolicy Bypass -File scripts/e2e_validate.ps1 -Port 8002 -ForceKillPort`

### 4.2 서버/검증 분리 실행 (수동)

1) 서버 시작:
- `python scripts/run_api.py --host 127.0.0.1 --port 8002`

2) 다른 터미널에서 검증:
- `python scripts/validate_api.py --base-url http://127.0.0.1:8002`

---

## 5) 현재 API 상태 체크리스트

- `/health`: 동작
- `/api/chat` (query): 동작 + `trace_id` 포함
- `/api/chat` (message 하위호환): 동작
- `/api/evidence/{trace_id}`: 동작 (found True/False)
- `evidence.similar_events`: 포함(키 존재)
- `graph.nodes[*].state`: 포함(키 존재; UI 색상/스타일링 보조)

---

## 6) 계약 결정(권장안)

- 백엔드: **snake_case 유지**(Python/Pydantic/로그/저장 구조 일관성)
- 프론트: **API 레이어에서 camelCase 변환 어댑터 고정**

권장 변환 예시(핵심):
- `trace_id` → `traceId`
- `query_type` → `queryType`
- `abstain_reason` → `abstainReason`
- `evidence.document_refs` → `evidence.documentRefs`
- `evidence.ontology_paths` → `evidence.ontologyPathObjects` (현재 실동작은 구조화 dict 배열 기반)
- `evidence.similar_events` → `evidence.similarEvents`

---

## 7) 다음 할 일(옵션)

- (완료) 프론트가 바로 붙도록 **TS 타입 + 변환 어댑터(normalizeChatResponse)** 를 레포에 추가
- (완료) 문서(UI_설계_명세서)에서 `ontology_paths`를 “문자열”이 아닌 “구조화 객체 배열” 기준으로 확정 표기
- CI(옵션): `scripts/e2e_validate.ps1`와 동일한 검증을 GitHub Actions로도 돌릴지 결정

---

## 8) 업데이트 로그 (계속 여기에 누적)

- 2026-01-23: P0 API 재현성 검증 루틴 확립(E2E 스크립트 추가) + validate 스크립트 인자화 + README 최소 가이드 추가
- 2026-01-23: 프론트용 snake_case→camelCase 변환 어댑터(TypeScript) 추가: `contracts/p0_api_adapter.ts`
- 2026-01-23: README에 프론트 연동 예제 추가 + UI 명세서에서 evidence.ontology_paths 기준(구조화 객체 배열) 확정
