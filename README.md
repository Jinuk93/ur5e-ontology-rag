
# UR5e Ontology RAG

온톨로지 기반 RAG + (FastAPI) UI 연동용 P0 API를 포함한 프로젝트입니다.

## 문서

- 백엔드 총 가이드: [SoT_백엔드_API_가이드.md](docs/references/SoT_백엔드_API_가이드.md)
- P0 계약/재현성 검증: [SoT_재현성_가이드.md](docs/references/SoT_재현성_가이드.md)
- UI 설계 명세서: [SoT_UI_설계_명세서.md](docs/references/SoT_UI_설계_명세서.md)
- 프론트 검증/검수 총정리: [SoT_프론트엔드_검증_리포트.md](docs/references/SoT_프론트엔드_검증_리포트.md)

## 빠른 시작

### API 서버 실행

- `python scripts/run_api.py --host 127.0.0.1 --port 8002`

### API 합격 기준(무인) 검증

PowerShell에서 아래 명령으로 서버 실행 → 검증 → 종료를 한 번에 재현합니다.

- `powershell -ExecutionPolicy Bypass -File scripts/e2e_validate.ps1 -Port 8002 -ForceKillPort`

검증 스크립트만 단독으로 돌릴 때는:

- `python scripts/validate_api.py --base-url http://127.0.0.1:8002`

## 프론트 연동 (P0)

백엔드 응답은 snake_case(`trace_id`, `query_type`, `evidence.ontology_paths` 등)를 유지합니다.
프론트에서는 [frontend/src/lib/api.ts](frontend/src/lib/api.ts)의 `buildChatRequest`/`normalizeChatResponse`를 API 레이어에서 사용해 camelCase로 정규화하는 것을 권장합니다.

참고: [contracts/p0_api_adapter.ts](contracts/p0_api_adapter.ts)는 **타입 정의 전용** 파일입니다 (로직 없음). 런타임 어댑터 정본은 `frontend/src/lib/api.ts`입니다.

예시(프론트 코드):

```ts
import { buildChatRequest, normalizeChatResponse } from '@/lib/api'

async function ask() {
	const res = await fetch('http://127.0.0.1:8002/api/chat', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(
			buildChatRequest({
				message: 'Fz가 -350N인데 이게 뭐야?',
				context: { selectedEntity: 'Fz', currentView: 'live' },
			})
		),
	})

	const raw = await res.json()
	const data = normalizeChatResponse(raw)
	console.log(data.traceId, data.queryType)
}
```

