# 프론트엔드 전반 검증/검수 총정리

- 목적: 프론트 Phase 0~3 구현에 대해, 레포 근거(코드/문서/품질 게이트)로 **검증 결과**와 **보완 사항**을 고정 기록

---

## 1) 결론

- Phase 0~3(= UI 명세서 Phase 1~3 범위)은 **대체로 완료**로 판단됨.
- 단, “구현은 되어 있으나 실동작 연결이 빠질 수 있는 지점”이 일부 있었고, 그중 2건은 실제로 보완함:
  - ABSTAIN 관련 필드(부분 근거/추천 질문) **snake_case → camelCase 어댑터 매핑 누락** 보완
  - next-intl 빌드 경고(`ENVIRONMENT_FALLBACK`) 제거(`timeZone` 기본값 지정)

---

## 2) 검증 기준(게이트)

- 프론트 품질 게이트: `frontend`에서
  - `npm run lint` 통과
  - `npm run build` 통과
- 문서 정합성: UI 명세서/작업보고서에 완료 항목 반영 여부 확인
- 구현 정합성: “파일 존재”가 아니라 **실제 사용/연동되는지**(예: React Query mutation 사용, 어댑터 매핑, Provider 적용) 중심으로 확인

---

## 3) 문서 기반 완료 체크

### 3.1 UI 명세서(Phase 3)

- `SoT_UI_설계_명세서.md`에서 Phase 3이 ✅ 완료로 표시됨
  - ABSTAIN 개선 UI
  - 애니메이션(Framer Motion)

### 3.2 프론트 작업보고서

- `SoT_프론트엔드_구현_리포트.md`에 P0~P3 및 P3-4/P3-5 완료가 누적 기록되어 있음

---

## 4) 코드 기반 검증(핵심 포인트)

### 4.1 /api/chat 계약 및 어댑터

- 백엔드는 snake_case를 유지하고, 프론트는 API 레이어에서 camelCase로 변환하는 전략을 유지
- `frontend/src/lib/api.ts`의 `normalizeChatResponse()`에서 다음을 포함해 변환함:
  - `trace_id` → `traceId`
  - `query_type` → `queryType`
  - evidence 하위 필드(ontology_paths/document_refs/similar_events)

### 4.2 P1: React Query 연결(“구현만”이 아니라 “실사용”)

- ChatPanel이 `sendChatMessage()`를 직접 호출하면 evidence 캐시/프리로드가 “있어도” 실효가 약해질 수 있어,
  - `useChatMutation()` 기반으로 연결(요청-응답, trace 기반 prefetch까지)되는지 확인

### 4.3 P2: 센서 실데이터 연동

- LiveView가 Mock이 아니라 실제 API(readings/patterns/events)로부터 폴링 기반 데이터를 받는지 확인

### 4.4 P3-1: SSE

- 백엔드 SSE(`/api/sensors/stream`) 구현 및 라우트 등록 스모크 확인
- 프론트 `useSensorSSE` 훅 + LiveView 모드 전환 UI(SSE/폴링) 확인

### 4.5 P3-2: Theme

- `next-themes` Provider 적용 및 Header 토글 연결 확인

### 4.6 P3-3: i18n

- `next-intl` Provider 적용 및 ko/en 메시지 적용 확인

### 4.7 P3-4: ABSTAIN 개선 UI

- Chat 응답에서 `abstain: true`인 경우, ChatPanel에서 특별 UI를 렌더링하는지 확인
- 타입 확장(PartialEvidence / suggestedQuestions) 존재 확인

### 4.8 P3-5: Framer Motion

- `framer-motion` 의존성 존재
- `frontend/src/lib/animations.ts`에 variants 존재
- 뷰 전환/채팅/카드/알림 등에 실제로 motion 적용되어 있는지 확인

---

## 5) 검수 중 실제로 보완한 사항(중요)

### 5.1 ABSTAIN 필드 어댑터 누락 보완

- 문제: 백엔드가 `partial_evidence`, `suggested_questions`로 내려주면, 프론트 `ChatResponse.partialEvidence/suggestedQuestions`가 비어 ABSTAIN UI가 “구현은 있어도 비활성”이 될 수 있음
- 조치: `normalizeChatResponse()`에 해당 snake_case 매핑 추가

### 5.2 추천 질문 클릭 처리 개선

- 문제: 추천 질문 클릭 시 DOM을 직접 찾아 input을 조작하면(특히 React 19/Strict Mode), 상태와 불일치/취약해질 수 있음
- 조치: `setInput()` 기반으로 상태를 갱신하도록 개선

### 5.3 next-intl 빌드 경고(ENVIRONMENT_FALLBACK) 제거

- 문제: `next-intl`이 SSR/빌드 환경에서 기본 `timeZone`이 없으면 환경 차이로 인한 마크업 불일치 가능성을 경고
- 조치: `IntlProvider`에 `timeZone="Asia/Seoul"` 지정
- 결과: `npm run build`에서 경고 로그가 사라짐

---

## 6) 남은 리스크/제안(짧게)

- SSE는 단방향(EventSource)이라 운영 환경 요구(인증/권한/재시도/백프레셔/관측성)에 맞춰 보강 여지 있음
- 센서 데이터는 캐시/시뮬레이션 구조가 포함되어 있어, 실시간 원천 연동 시 커서/중복/결손 처리 기준 정리가 필요

---

## 7) 재현(로컬)

PowerShell 예시:

- 프론트
  - `cd frontend`
  - `npm run lint`
  - `npm run build`
  - `npm run dev`

- 백엔드(별도 터미널)
  - `python scripts/run_api.py --host 127.0.0.1 --port 8002`

필요 시 프론트 API 주소:
- `NEXT_PUBLIC_API_URL=http://127.0.0.1:8002`
