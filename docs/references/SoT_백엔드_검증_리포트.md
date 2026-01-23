# 백엔드 런타임 검증 리포트

이 문서는 "문서에 적힌 스펙"이 실제 서버 실행 결과와 일치하는지를 **런타임 호출 기준**으로 검증한 결과를 고정하기 위한 기록이다.

## 범위

- FastAPI 백엔드 실행 상태에서 HTTP 호출로 검증
- 문서: [SoT_백엔드_API_가이드.md](SoT_백엔드_API_가이드.md) 기준
- 스크립트:
  - [scripts/e2e_validate.ps1](../../scripts/e2e_validate.ps1): 서버 기동 → `/health` 대기 → 검증 실행 → 종료
  - [scripts/validate_api.py](../../scripts/validate_api.py): 엔드포인트 런타임 검증(스키마 키/호환성 포함)

## 검증 항목(8/8 + 헬스)

`validate_api.py`에서 아래를 모두 검사한다.

- `/health`: 200 및 `status`, `version` 키 확인
- `/docs`: 200
- `/api/chat`:
  - `query` 입력으로 정상 응답
  - `trace_id` 존재
  - 하위호환: `message` 입력도 허용
  - `similar_events` / `node_state` 키 존재
- `/api/evidence/{trace_id}`:
  - 정상 trace: `found=true`
  - ABSTAIN trace: `found=true`
  - 임의 trace: `found=false`
- `/api/ontology/summary`: 200 및 `summary` 키 존재
- `/api/sensors/readings`: 200 및 `readings`, `total`, `time_range` 키 존재(첫 항목 필드 최소 체크)
- `/api/sensors/patterns`: 200 및 `patterns`, `total` 키 존재
- `/api/sensors/events`: 200 및 `events`, `total` 키 존재
- `/api/sensors/stream` (SSE):
  - 200
  - `Content-Type`에 `text/event-stream` 포함
  - `X-Accel-Buffering: no`
  - 최소 1개 `data:` 라인 수신(스모크)

참고: 로컬에 센서 parquet가 없거나(`data/sensor/raw/axia80_week_01.parquet`) parquet 엔진이 없는 환경에서는 `readings=[]`로 반환되며, SSE는 `data: {"error": "No sensor data available"}` 형태의 이벤트를 1회 내보내고 종료될 수 있습니다. 이는 데모 데이터 부재 상황에서의 정상 degrade 동작으로 취급합니다.

## 재현 방법(Windows)

1) (권장) E2E 한 번에 실행

- `powershell`에서 레포 루트 기준:
  - `./scripts/e2e_validate.ps1`

2) 서버가 이미 떠 있는 경우 validate만 실행

- `python ./scripts/validate_api.py --base-url http://localhost:8002`

## 실행 증빙(2026-01-23)

- 실행 환경: Windows (PowerShell), 로컬
- 실행 커맨드(권장 문서 기준):
  - `powershell -ExecutionPolicy Bypass -File scripts/e2e_validate.ps1 -Port 8002 -ForceKillPort`
- 실행 커맨드(실제 실행):
  - `Set-ExecutionPolicy -Scope Process Bypass -Force; ./scripts/e2e_validate.ps1 -Port 8002 -ForceKillPort`
- 결과: PASS
- Exit Code: 0

검증 출력 요약(런타임):

- `/health` 200 + `status=healthy`
- `/docs` 200
- `/api/chat`:
  - `query` 입력: `trace_id` 발급 및 핵심 키 존재
  - `message` 입력: 하위호환 PASS
  - ABSTAIN 케이스: `abstain=true` + `abstain_reason` + `trace_id`
- `/api/evidence/{trace_id}`: 정상/ABSTAIN trace `found=true`, 임의 ID `found=false`
- `/api/ontology/summary` 200 + `summary` 키 존재
- `/api/sensors/readings|patterns|events` 200
- `/api/sensors/stream`(SSE) 스모크:
  - `Content-Type: text/event-stream`
  - `X-Accel-Buffering: no`
  - 데모 데이터 부재 시 `data: {"error": "No sensor data available"}` 이벤트 1회 후 종료(정상 degrade)

## 검증 과정에서 확인/개선된 환경 이슈

- **실행 위치(CWD) 의존성**: PowerShell 스크립트가 레포 루트가 아닌 위치에서 실행될 때 상대경로가 깨질 수 있어, [scripts/e2e_validate.ps1](../../scripts/e2e_validate.ps1)에서 레포 루트로 이동하도록 보강했다.
- **pytest 수집 범위 이슈**: `scripts/test_*.py` 등이 테스트로 오인 수집될 수 있어 `pytest.ini`로 수집 범위를 `tests/`로 제한했다.
  - 현재 `tests/`가 비어 있으면 `no tests ran`이 정상 동작(테스트가 실제로 없음을 의미).

## 다음 작업(선택)

- `tests/`에 최소 스모크 테스트(예: `/health` 200) 추가해서 `pytest`도 PASS 기준으로 활용
- `validate_api.py`를 CI에서 실행하도록 GitHub Actions/Makefile 타겟으로 연결
