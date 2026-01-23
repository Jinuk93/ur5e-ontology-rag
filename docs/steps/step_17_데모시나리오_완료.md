# Step 17: 데모 시나리오 - 완료 보고서

## 1. 완료 요약

| 항목 | 내용 |
|------|------|
| Phase | 17 - 데모 시나리오 |
| 상태 | ✅ 완료 |
| 이전 단계 | Step 16 - 통합 테스트 |

---

## 2. 데모 시나리오(체크리스트)

### 2.1 시나리오 1: 온톨로지 추론 + 근거

- [ ] ChatPanel에서 질문 입력 또는 `/api/chat` 호출
- [ ] `trace_id` 확인
- [ ] Evidence Drawer 또는 `/api/evidence/{trace_id}`로 근거 확인

### 2.2 시나리오 2: 그래프/경로 탐색

- [ ] Graph View에서 노드 선택
- [ ] Path Breadcrumb(온톨로지 경로) 확인

### 2.3 시나리오 3: Live 센서(REST/SSE)

- [ ] Live View에서 센서값/이벤트/패턴 표시
- [ ] SSE 모드 연결 또는 폴링 fallback 동작 확인
- [ ] 데이터 부재 시 degrade(빈 목록/에러 이벤트) 확인

---

## 3. 재현 커맨드

### 3.1 백엔드

- `python scripts/run_api.py --host 127.0.0.1 --port 8002`

### 3.2 프론트(UI)

- `cd frontend`
- `npm run dev`

### 3.3 E2E 검증(데모 전 권장)

- `powershell -ExecutionPolicy Bypass -File scripts/e2e_validate.ps1 -Port 8002 -ForceKillPort`

### 3.4 실행 증빙(요약)

- 2026-01-23 기준: E2E 실행 PASS (Exit Code 0)
- 상세 로그/근거: [SoT_백엔드_검증_리포트.md](../references/SoT_백엔드_검증_리포트.md)

---

## 4. 관련 정본 문서

- UI 설계: [SoT_UI_설계_명세서.md](../references/SoT_UI_설계_명세서.md)
- 백엔드 가이드: [SoT_백엔드_API_가이드.md](../references/SoT_백엔드_API_가이드.md)
- 재현성 검증: [SoT_재현성_가이드.md](../references/SoT_재현성_가이드.md)
- 런타임 검증 리포트: [SoT_백엔드_검증_리포트.md](../references/SoT_백엔드_검증_리포트.md)
