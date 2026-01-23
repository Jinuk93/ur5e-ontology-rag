# Step 14: 프론트엔드 구현 - 설계 문서

## 1. 개요

| 항목 | 내용 |
|------|------|
| Phase | 14 - 프론트엔드 구현 (Next.js Dashboard) |
| Stage | Stage 5 (Palantir-style UI) |
| 이전 단계 | Step 13 - UI 및 API 계약 |
| 다음 단계 | Step 15 - 센서 실시간 및 검증 |

---

## 2. 목표

- Next.js(App Router) 기반으로 **3-View(Live/Graph/History) + Chat(Evidence)** 대시보드를 구현한다.
- UI는 “객체 중심(Object-centric)”과 “근거 기반(Traceability)”을 핵심으로 한다.
- 모든 API 연동은 Step 13의 계약을 준수하며, 변환은 프론트 API 레이어에서 수행한다.

---

## 3. 산출물(코드)

- `frontend/src/app/*`: 라우팅 및 레이아웃
- `frontend/src/components/*`: View 컴포넌트(Live/Graph/History/Chat/Evidence)
- `frontend/src/lib/api.ts`: API 클라이언트 + 정규화(정본)
- `frontend/src/hooks/*`: React Query 훅 + SSE 훅
- `frontend/src/stores/*`: Zustand 기반 UI/Chat 상태

---

## 4. 설계 포인트

### 4.1 API 연동 패턴

- “raw 응답”을 컴포넌트가 직접 쓰지 않는다.
- `frontend/src/lib/api.ts`에서 정규화된 타입으로 변환 후 컴포넌트로 전달한다.

### 4.2 Evidence Drawer

- `traceId`를 키로 Evidence를 prefetch/조회한다.
- 온톨로지 경로(노드/관계 배열)를 UI에서 가시화한다.

### 4.3 LiveView 실시간 전략

- 기본은 SSE(EventSource) 구독
- 실패/비활성 시 REST 폴링으로 fallback

---

## 5. 완료 기준(Definition of Done)

- `/` 페이지에서 Live/Graph/History 전환이 가능하다.
- ChatPanel이 `/api/chat` 호출을 통해 답변을 렌더링한다.
- Evidence Drawer가 `traceId` 기준으로 열리고, 근거/그래프 요약을 표시한다.
- `NEXT_PUBLIC_API_URL`로 백엔드 주소를 교체 가능하다.
