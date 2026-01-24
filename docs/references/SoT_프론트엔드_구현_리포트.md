# 프론트엔드 작업보고서 (P0)

- 목적: 레포 기준으로 **무슨 작업을 했는지**와 **다음 할 일**을 기록

---

## 2) 현재 프론트 코드 상태(레포 기준)

### 2.1 프로젝트 생성

- Next.js(App Router) 프로젝트 생성: `frontend/`
- 설치된 핵심 패키지:
  - UI: shadcn/ui(Radix 기반)
  - Graph: `@xyflow/react` (React Flow)
  - Chart: `recharts`
  - 상태: `zustand`
  - 데이터: `@tanstack/react-query`(P1에서 적용)

> 주의: 현재 `frontend/` 폴더는 Git에 아직 add 되지 않은 “untracked” 상태입니다.

### 2.2 타입/어댑터(백엔드 snake_case ↔ 프론트 camelCase)

- 타입: `frontend/src/types/api.ts`
- API 클라이언트 + 변환 어댑터: `frontend/src/lib/api.ts`
  - `normalizeChatResponse(raw)`:
    - `trace_id → traceId`, `query_type → queryType`, `abstain_reason → abstainReason`
    - `evidence.ontology_paths → evidence.ontologyPathObjects`
    - `evidence.document_refs → evidence.documentRefs`
    - `evidence.similar_events → evidence.similarEvents`
    - `graph.nodes/edges` 매핑
  - `buildChatRequest(req)`:
    - `message` 우선 전송, 없으면 `query`
  - 기본 base URL: `NEXT_PUBLIC_API_URL` 없으면 `http://127.0.0.1:8002`

### 2.3 상태 관리

- UI 상태: `frontend/src/stores/uiStore.ts`
  - 뷰 전환(`live|graph|history`), 선택 엔티티, 그래프 중심 노드, 모바일 채팅 열림 상태
- 채팅 상태: `frontend/src/stores/chatStore.ts`
  - 메세지 배열 + 로딩/에러 포함

### 2.4 UI 컴포넌트(현재 구현된 범위)

- 레이아웃
  - `frontend/src/components/layout/Header.tsx`
  - `frontend/src/components/layout/SplitView.tsx`

- Live View(모니터링 느낌의 데모)
  - `frontend/src/components/live/LiveView.tsx`
  - `frontend/src/components/live/ObjectCard.tsx`
  - `frontend/src/components/live/RiskAlertBar.tsx`
  - `frontend/src/components/live/RealtimeChart.tsx`
  - `frontend/src/components/live/EventList.tsx`

- Graph View(React Flow 기반 데모)
  - `frontend/src/components/graph/GraphView.tsx`
  - `frontend/src/components/graph/SubGraph.tsx`
  - `frontend/src/components/graph/OntologyNode.tsx`
  - `frontend/src/components/graph/PathBreadcrumb.tsx`

- History View(차트 컴포넌트 일부)
  - `frontend/src/components/history/TrendChart.tsx`

- shadcn/ui 컴포넌트
  - `frontend/src/components/ui/*`

### 2.5 Chat View (신규)

- `frontend/src/components/chat/ChatPanel.tsx`
  - 입력창 + 전송 버튼
  - `useChatMutation()`으로 채팅 API 호출 연동
  - 응답 렌더링: `answer`, `traceId`, `queryType`, `confidence`
  - 근거 토글: `evidence.ontologyPathObjects`, `evidence.documentRefs`, `graph` 요약
  - traceId 기준 evidence 프리패치 + Drawer 연동
  - 추천 질문 표시

### 2.6 History View (확장)

- `frontend/src/components/history/HistoryView.tsx`
  - 기간 선택 (1시간/24시간/7일)
  - TrendChart + 패턴 마커
  - 패턴 테이블 (충돌/과부하/드리프트)
  - 예측 카드 (placeholder)

### 2.7 연결 완료

- `frontend/src/app/page.tsx` → 실제 대시보드로 교체 완료
  - Header + SplitView 구성
  - main: currentView 기반 Live/Graph/History 뷰 전환
  - side: ChatPanel

### 2.8 React Query 연동 (신규)

- `frontend/src/lib/queryClient.ts`: QueryClient 설정 (staleTime 5분, gcTime 10분)
- `frontend/src/providers/QueryProvider.tsx`: QueryClientProvider 래퍼 (DevTools 포함)
- `frontend/src/hooks/useApi.ts`: API 훅 모음
  - `useHealth()`: 헬스체크 (30초 폴링)
  - `useOntologySummary()`: 온톨로지 요약 (10분 캐싱, 훅 제공)
  - `useEvidence(traceId)`: 근거 조회
  - `useChatMutation()`: 채팅 요청 (응답에 evidence가 있으면 캐시 세팅)
  - `usePrefetchEvidence()`: traceId 기준 evidence 프리패치
- `frontend/src/app/layout.tsx`: QueryProvider 적용

### 2.9 Evidence Drawer (신규)

- `frontend/src/components/evidence/EvidenceDrawer.tsx`
  - Sheet 기반 오른쪽 슬라이드 패널
  - 온톨로지 경로 시각화 (노드 → 관계 → 노드)
  - 문서 참조 (relevance 프로그레스 바)
  - 유사 이벤트 목록
  - 그래프 요약 (노드/엣지 타입별 집계)

### 2.10 Header 연결 상태 표시 (신규)

- `frontend/src/components/layout/Header.tsx`
  - useHealth() 훅으로 백엔드 연결 상태 체크
  - 연결됨/연결 끊김 배지 표시 (Wifi/WifiOff 아이콘)

### 2.11 센서 API 연동 (P2 신규)

**백엔드 센서 API 추가** (`src/api/main.py`):
- `/api/sensors/readings`: 센서 측정값 조회 (limit, offset 지원)
- `/api/sensors/patterns`: 감지된 패턴 목록
- `/api/sensors/events`: 이상 이벤트 목록

**프론트엔드 센서 훅 추가** (`frontend/src/hooks/useApi.ts`):
- `useSensorReadings(limit, offset)`: 5초 폴링으로 실시간 센서 데이터
- `useSensorPatterns(limit)`: 패턴 목록 (1분 캐싱)
- `useSensorEvents(limit)`: 이벤트 목록 (1분 캐싱)

**LiveView 실제 API 연동** (`frontend/src/components/live/LiveView.tsx`):
- Mock 데이터 제거 → 실제 백엔드 API 호출
- 센서값 기반 엔티티 상태(normal/warning/critical) 자동 계산
- 이벤트 목록 실제 데이터 표시
- 로딩/에러 상태 UI 표시

### 2.12 SSE 실시간 스트리밍 (P3-1 신규)

**백엔드 SSE 엔드포인트 추가** (`src/api/main.py`):
- `/api/sensors/stream`: SSE 스트리밍 엔드포인트
  - `interval` 파라미터로 전송 간격 조절 (기본 1초)
  - 저장된 센서 데이터를 순차적으로 재생 (시뮬레이션)
  - 클라이언트 연결 해제 감지

**프론트엔드 SSE 훅 추가** (`frontend/src/hooks/useSSE.ts`):
- `useSensorSSE(options)`: EventSource 기반 SSE 구독 훅
  - `interval`: 전송 간격 (초)
  - `bufferSize`: 버퍼 크기 (기본 60개)
  - `enabled`: 활성화 여부
  - 자동 재연결 (3초 후)
  - `reconnect()`, `disconnect()` 메서드 제공

**LiveView SSE/폴링 모드 전환** (`frontend/src/components/live/LiveView.tsx`):
- SSE 모드 (기본): 1초 간격 실시간 스트리밍
- 폴링 모드 (fallback): 5초 간격 REST API 폴링
- UI에서 모드 전환 버튼 + 연결 상태 표시

### 2.13 다크/라이트 테마 전환 (P3-2 신규)

**next-themes 적용** (`frontend/src/providers/ThemeProvider.tsx`):
- `next-themes` 라이브러리 설치 및 ThemeProvider 구성
- 기본 테마: dark
- 시스템 테마 감지 지원 (`enableSystem`)

**테마 토글 버튼** (`frontend/src/components/ui/theme-toggle.tsx`):
- Sun/Moon 아이콘으로 현재 테마 표시
- 클릭 시 다크/라이트 모드 전환
- 하이드레이션 불일치 방지 (`useSyncExternalStore` 사용)

**Header 테마 적용** (`frontend/src/components/layout/Header.tsx`):
- 하드코딩된 색상 → CSS 변수 기반 테마 색상으로 변경
- ThemeToggle 버튼 추가

**레이아웃 업데이트** (`frontend/src/app/layout.tsx`):
- ThemeProvider 래핑
- `suppressHydrationWarning` 추가
- body 배경색 테마 적용

### 2.14 다국어 지원 i18n (P3-3 신규)

**next-intl 적용**:
- `next-intl` 라이브러리 설치
- `frontend/messages/ko.json`, `frontend/messages/en.json` 번역 파일

**i18n 설정** (`frontend/src/i18n/`):
- `config.ts`: 지원 언어 목록 (ko, en), 기본 언어 (ko)
- `request.ts`: 서버 사이드 언어 설정

**상태 관리** (`frontend/src/stores/localeStore.ts`):
- Zustand + persist로 사용자 언어 선호도 저장

**프로바이더** (`frontend/src/providers/IntlProvider.tsx`):
- NextIntlClientProvider 래퍼
- SSR/클라이언트 하이드레이션 처리

**언어 전환 버튼** (`frontend/src/components/ui/language-toggle.tsx`):
- Globe 아이콘 + 현재 언어 표시
- 클릭 시 한국어/영어 전환

**컴포넌트 번역 적용**:
- Header: 네비게이션 메뉴, 연결 상태
- LiveView: 모니터링 객체, 스트림 모드, 에러 메시지

### 2.15 ABSTAIN 개선 UI (P3-4 신규)

**타입 확장** (`frontend/src/types/api.ts`):
- `PartialEvidence` 인터페이스 추가 (found/missing 정보)
- `ChatResponse`에 `partialEvidence`, `suggestedQuestions` 필드 추가

**AbstainMessage 컴포넌트** (`frontend/src/components/chat/ChatPanel.tsx`):
- 판단 보류(abstain: true) 시 특별 UI 표시
- 🤔 "확실한 답변을 드리기 어렵습니다" 메시지
- 확인된 정보 / 부족한 정보 목록 표시
- 추천 질문 버튼 (클릭 시 입력창에 자동 입력)
- 부분 답변이 있으면 "참고할 수 있는 내용" 섹션 표시

**번역 추가**:
- `messages/ko.json`: abstainTitle, foundInfo, missingInfo, trySuggestions, referenceInfo
- `messages/en.json`: 동일 키 영어 번역

### 2.16 애니메이션 (P3-5 신규)

**Framer Motion 설치**:
- `framer-motion` 패키지 설치

**애니메이션 설정** (`frontend/src/lib/animations.ts`):
- `fadeIn`: 페이드 인 애니메이션
- `slideUp`, `slideFromLeft`, `slideFromRight`: 슬라이드 애니메이션
- `scaleUp`: 스케일 업 (카드용)
- `staggerContainer`, `staggerItem`: 순차 애니메이션
- `cardHover`, `cardTap`: 카드 호버/탭 효과
- `chatMessage`: 채팅 메시지 애니메이션
- `pageTransition`: 뷰 전환 애니메이션

**컴포넌트 애니메이션 적용**:
- `page.tsx`: 뷰 전환 시 AnimatePresence + motion.div로 페이드/슬라이드 효과
- `ChatPanel.tsx`: 메시지 목록에 AnimatePresence, 메시지 추가 시 애니메이션
- `ObjectCard.tsx`: 호버 시 scale(1.02), 클릭 시 scale(0.98) 효과
- `RiskAlertBar.tsx`: 알림 버튼들 순차적 페이드인, 호버/탭 애니메이션

### 2.17 이기종 결합 예측 컴포넌트 (P4 신규) → **제거됨** ❌

~~**HeterogeneousPrediction 컴포넌트** (`frontend/src/components/live/HeterogeneousPrediction.tsx`):~~
- ~~Axia80 센서 데이터 + 온톨로지 기반 에러코드 예측 통합 표시~~
- ~~현재 UR5e 상태 / Axia80 센서 현황 요약~~

**변경 사항 (2026-01-24):**
- `HeterogeneousPrediction` 컴포넌트 **삭제**
- 기능이 `CorrelationTable` (실시간 예지보전)에 통합됨

### 2.18 통계 요약 개선 (P4 신규)

**StatisticsSummary 컴포넌트 리팩토링** (`frontend/src/components/live/StatisticsSummary.tsx`):
- **Axia80 6축 센서 평균값 표시**: Fx, Fy, Fz, Tx, Ty, Tz
- **예비보전 점수 계산**: 충돌/과부하/드리프트 발생 및 Fz 편차 기반 (0-100점)
- **기간 전환**: 24시간 / 7일 토글 버튼
- **데이터 직접 조회**: useSensorPatterns, useSensorReadingsRange 훅 사용
- **상태별 색상 표시**: 양호(녹색), 주의(노란색), 점검 권장(주황색), 긴급 점검(빨간색)

### 2.19 네비게이션 변경 (P4 신규)

**Header.tsx 변경**:
- History 탭 제거 (Live, Graph 2개 탭만 유지)
- 네비게이션 간소화

### 2.20 AI 예측 UI 개선 (P4 신규)

**EventList.tsx 변경**:
- "예측" 컬럼명 → "AI 예측"으로 변경
- AI 예측 컬럼에 노란색 Zap(⚡) 아이콘 추가
- AI 예측 배경색을 진한 네이비(bg-blue-950/40)로 변경
- 예측 로직을 온톨로지 에러코드 → 권장 조치 중심으로 변경
  - 예: "재발 가능성 높음", "그리퍼 점검 필요", "작업 경로 검토" 등

### 2.21 실시간 예지보전 UI 개선 (P5 신규)

**CorrelationTable 컴포넌트 변경** (`frontend/src/components/live/CorrelationTable.tsx`):
- 이름 변경: "UR5e + Axia80 상관분석" → "**실시간 예지보전**"
- 배지 변경: "Simulated" → "**AI 예측**" (청록색 펄스 애니메이션)
- 위험도 카드에 **AI 배지** 추가 (우측 상단, 청록-보라 그라데이션)
- "위험도 평가" → "**위험도 예측**" 라벨 변경
- **위험 감지 기록** 섹션 추가 (하단에 row 형태로 표시)
  - 최대 20개 저장, 화면에 5개 표시 후 스크롤
  - low 제외, medium/high/critical만 기록
  - 시간, 시나리오, 위험도, 최대 힘, 위험%, 지속시간 표시

### 2.22 이상 감지 알림 시스템 (P5 신규)

**alertStore.ts** (`frontend/src/stores/alertStore.ts`):
- Zustand 기반 이벤트 저장소
- `LiveDetectedEvent` 타입: 시나리오, 위험도, 최대 힘/위험도, 지속시간, 보호정지 등
- `AlertSettings`: 알림 ON/OFF, 사운드 ON/OFF, 시나리오/위험도별 필터

**useAnomalyAlert.ts** (`frontend/src/hooks/useAnomalyAlert.ts`):
- IntegratedStreamData 모니터링
- 시나리오 변경 시 Toast 알림 + 이벤트 기록
- 위험도 상승 시 추가 알림
- 정상 복귀 시 초록색 성공 알림

**useAlertSound.ts** (`frontend/src/hooks/useAlertSound.ts`):
- Web Audio API 기반 경고음 생성
- 위험도별 다른 비프 패턴 (low: 1회, medium: 2회, high: 3회, critical: 상승음 4회)

**sonner.tsx** (`frontend/src/components/ui/sonner.tsx`):
- Toast 알림 설정
- 위치: 정중앙 상단 (offset 60px, 상단바 안 가림)
- 최대 2개 동시 표시
- 크기: 작게 (text-xs, py-1.5, max-w-280px)
- 경고/위험: 빨간 배경 + 빨간 아이콘
- 정상 복귀: 초록 배경 + 초록 체크 아이콘

**LiveView 알림 토글** (`frontend/src/components/live/LiveView.tsx`):
- 상단에 종(Bell) 아이콘 버튼: Toast 알림 ON/OFF
- 스피커(Volume) 아이콘 버튼: 경고음 ON/OFF

### 2.23 센서 통합 모니터링 차트 개선 (P6 신규)

**RealtimeChart 컴포넌트 변경** (`frontend/src/components/live/RealtimeChart.tsx`):
- 제목 변경: "힘 센서 실시간 모니터링" → "**UR5e + Axia80 센서 통합 모니터링**"
- **UR5e 텔레메트리 데이터 추가**:
  - `tcp_speed` (TCP 속도, m/s) - 로즈 색상
  - `joint_torque_sum` (관절 토크 합, Nm) - 보라색
  - `joint_current_avg` (평균 전류, A) - 청록색
- 축 타입 확장: `Axia80AxisType` + `UR5eAxisType` → `AxisType`
- 체크박스 그룹화: Axia80 / UR5e 구분자로 시각적 분리
- `integratedData` prop 추가로 통합 SSE 데이터 지원

**LiveView 변경** (`frontend/src/components/live/LiveView.tsx`):
- RealtimeChart에 `integratedData={integratedData}` 전달
- axes 확장: `['Fz', 'Fx', 'Fy', 'tcp_speed', 'joint_torque_sum', 'joint_current_avg']`

### 2.24 이벤트 감지 카드 (P6 신규)

**EventDetectionCard 컴포넌트** (`frontend/src/components/live/EventDetectionCard.tsx`):
- Entity Cards 영역에 추가 (Fy 좌우력 옆)
- **실제 발생한 이벤트** (EventList의 events) 기반
- **이벤트 타입별 개수 표시**: 충돌 N건, 과부하 N건, 드리프트 N건
- **총 이벤트 수 및 심각도 구분**: 위험(critical), 경고(warning), 정상(info)
- 이벤트 없으면 "정상" 표시 (녹색 체크 아이콘)
- 이벤트 있으면 빨간색/노란색 테두리 + 펄스 애니메이션

**LiveView 변경** (`frontend/src/components/live/LiveView.tsx`):
- EventDetectionCard에 `events` prop 전달 (useSensorEvents 데이터)

### 2.25 이벤트 해결 관리 시스템 (P7 신규)

**eventResolveStore.ts** (`frontend/src/stores/eventResolveStore.ts`):
- Zustand + persist 기반 이벤트 해결 상태 저장소
- LocalStorage에 영속화 (새로고침해도 유지)
- `resolvedEventIds`: 해결된 이벤트 ID Set
- `resolveEvent(id)`, `unresolveEvent(id)`, `toggleResolve(id)` 액션
- `isResolved(id)`: 해결 여부 확인

**EventList.tsx 변경** (`frontend/src/components/live/EventList.tsx`):
- **"해결완료" 체크박스 컬럼 추가** (테이블 끝)
- **컬럼 간격 균등화**: 7개 컬럼 (12% / 12% / 14% / 14% / 14% / 20% / 14%)
- 체크 시 해당 행 연하게 표시 (opacity-50, bg-green-950/10)
- 녹색 체크 아이콘 (CheckCircle2) 표시
- 체크박스 클릭 시 행 클릭 이벤트 전파 방지 (stopPropagation)

**EventDetectionCard.tsx 변경** (`frontend/src/components/live/EventDetectionCard.tsx`):
- `useEventResolveStore` 연동
- **해결된 이벤트 제외**하여 미해결 이벤트만 카운트
- 표시 형식: "미해결 N건 (위험 X, 경고 Y) / 해결 M건"
- 해결된 이벤트가 있으면 녹색으로 해결 건수 표시

**i18n 변경** (`frontend/messages/ko.json`, `frontend/messages/en.json`):
- Axia80 센서 설명 변경: "ATI 6축 힘/토크 센서" → "Fz, Fx, Fy + 이벤트 감지"

### 2.26 잔여 작업

- 없음 (모든 기능 구현 완료 ✅)

---

## 3) 바로 실행(로컬 확인)

PowerShell:

1) 프론트 개발 서버
- `cd frontend`
- `npm run dev`

2) 백엔드(별도 터미널)
- `python scripts/run_api.py --host 127.0.0.1 --port 8002`

환경변수로 API 주소를 바꾸려면:
- `setx NEXT_PUBLIC_API_URL "http://127.0.0.1:8002"`

---

## 4) 대화 clear 해도 작업을 안 잃는 방법(운영 규칙)

1) 코드가 쌓이면 바로 Git에 기록
- `git add frontend`
- `git commit -m "frontend: scaffold P0 UI"`
- `git push`

2) 문서도 같이 스냅샷
- 이 파일(`SoT_프론트엔드_구현_리포트.md`)에 진행상황/다음할일을 누적
- API 계약 변경이 생기면 `SoT_UI_설계_명세서.md`와 `SoT_재현성_가이드.md` 업데이트

---

## 5) 다음 할 일(우선순위)

### 완료된 항목

- ~~(P0) `frontend/src/app/page.tsx`를 "실제 대시보드"로 연결~~ ✅ 완료
- ~~(P0) ChatPanel 구현~~ ✅ 완료
- ~~(P1) History View 확장 (패턴 테이블, 추세/마커)~~ ✅ 완료
- ~~(P1) React Query 적용~~ ✅ 완료
  - QueryClient + Provider 설정
  - useHealth, useOntologySummary, useEvidence, useChatMutation 훅 구현
  - Header에 연결 상태 표시 연동
- ~~(P2) Evidence 상세 모달/Drawer~~ ✅ 완료
  - EvidenceDrawer 컴포넌트
  - ChatPanel 연동 ("상세" 버튼)
- ~~(P2) 실제 센서 데이터 연동~~ ✅ 완료
  - 백엔드: `/api/sensors/readings`, `/api/sensors/patterns`, `/api/sensors/events` 엔드포인트 추가
  - 프론트엔드: useSensorReadings, useSensorPatterns, useSensorEvents 훅 구현
  - LiveView: Mock 데이터 → 실제 API 연동, 상태 자동 계산
- ~~(P3-1) SSE 기반 실시간 센서 업데이트~~ ✅ 완료
  - 백엔드: `/api/sensors/stream` SSE 스트리밍 엔드포인트 추가
  - 프론트엔드: `useSensorSSE` 훅 구현 (자동 재연결, 버퍼링)
  - LiveView: SSE/폴링 모드 전환 UI 추가
- ~~(P3-2) 다크/라이트 테마 전환~~ ✅ 완료
  - `next-themes` 설치 및 ThemeProvider 구성
  - ThemeToggle 컴포넌트 추가
  - Header 및 레이아웃 테마 적용
- ~~(P3-3) 다국어 지원 (i18n)~~ ✅ 완료
  - `next-intl` 설치 및 IntlProvider 구성
  - 한국어/영어 번역 파일 생성
  - LanguageToggle 컴포넌트 추가
  - Header, LiveView 번역 적용
- ~~(P3-4) ABSTAIN 개선 UI~~ ✅ 완료
  - 판단 보류 시 부족 정보 / 추천 질문 표시
  - AbstainMessage 컴포넌트 구현
  - API 타입 확장 (PartialEvidence, suggestedQuestions)
- ~~(P3-5) 애니메이션 (Framer Motion)~~ ✅ 완료
  - `framer-motion` 설치
  - 뷰 전환, 메시지 추가, 카드 호버/탭 애니메이션 적용

### 남은 항목

- 없음 (P0~P3 모두 완료, UI 설계 명세서 Phase 3 항목 전체 구현)

---

## 6) 변경 이력

- `frontend/` Next.js + Tailwind + shadcn/ui 초기 세팅
- 타입(`src/types/api.ts`) + API 어댑터(`src/lib/api.ts`) 추가
- Live/Graph/TrendChart 컴포넌트 뼈대 추가
- **P0 완료** - page.tsx 대시보드 교체, ChatPanel 구현, HistoryView 확장
  - `page.tsx`: Header + SplitView, currentView 기반 뷰 전환
  - `ChatPanel.tsx`: 입력 → 채팅 API → 응답 렌더링(traceId, evidence, graph)
  - `HistoryView.tsx`: 기간 선택, 패턴 테이블, 예측 카드
- **P1 완료** - React Query 적용 + Evidence Drawer 구현
  - `queryClient.ts`: React Query 클라이언트 설정
  - `QueryProvider.tsx`: 프로바이더 래퍼 + DevTools
  - `useApi.ts`: useHealth, useOntologySummary, useEvidence, useChatMutation 훅
  - `EvidenceDrawer.tsx`: 근거 상세 슬라이드 패널
  - `Header.tsx`: 연결 상태 배지 추가
  - `ChatPanel.tsx`: useChatMutation 사용 + traceId 기준 evidence 프리패치 + Evidence Drawer 연동
- **P2 완료** - 실제 센서 데이터 연동
  - `src/api/main.py`: 센서 API 엔드포인트 추가 (/api/sensors/readings, patterns, events)
  - `frontend/src/lib/api.ts`: 센서 API 함수 추가
  - `frontend/src/hooks/useApi.ts`: useSensorReadings, useSensorPatterns, useSensorEvents 훅 추가
  - `frontend/src/components/live/LiveView.tsx`: Mock 데이터 제거, 실제 API 연동, 상태 자동 계산
- **P3-1 완료** - SSE 기반 실시간 센서 업데이트
  - `src/api/main.py`: `/api/sensors/stream` SSE 스트리밍 엔드포인트 추가
  - `frontend/src/hooks/useSSE.ts`: useSensorSSE 훅 구현 (EventSource, 자동 재연결, 버퍼링)
  - `frontend/src/components/live/LiveView.tsx`: SSE/폴링 모드 전환 UI, 연결 상태 표시
- **P3-2 완료** - 다크/라이트 테마 전환
  - `next-themes` 패키지 설치
  - `frontend/src/providers/ThemeProvider.tsx`: ThemeProvider 래퍼
  - `frontend/src/components/ui/theme-toggle.tsx`: ThemeToggle 컴포넌트
  - `frontend/src/components/layout/Header.tsx`: 테마 적용 + ThemeToggle 추가
  - `frontend/src/app/layout.tsx`: ThemeProvider 적용, body 테마 색상
- **P3-3 완료** - 다국어 지원 (i18n)
  - `next-intl` 패키지 설치
  - `frontend/messages/ko.json`, `frontend/messages/en.json`: 번역 파일
  - `frontend/src/i18n/config.ts`: 언어 설정
  - `frontend/src/stores/localeStore.ts`: 언어 상태 관리
  - `frontend/src/providers/IntlProvider.tsx`: 다국어 프로바이더
  - `frontend/src/components/ui/language-toggle.tsx`: 언어 전환 버튼
  - `frontend/src/components/layout/Header.tsx`: 언어 전환 버튼 추가, 번역 적용
  - `frontend/src/components/live/LiveView.tsx`: 번역 적용
- **P3-4 완료** - ABSTAIN 개선 UI
  - `frontend/src/types/api.ts`: PartialEvidence 인터페이스 및 ChatResponse 확장
  - `frontend/src/components/chat/ChatPanel.tsx`: AbstainMessage 컴포넌트 추가
  - `frontend/messages/ko.json`, `frontend/messages/en.json`: ABSTAIN 관련 번역 추가
- **P3-5 완료** - Framer Motion 애니메이션
  - `framer-motion` 패키지 설치
  - `frontend/src/lib/animations.ts`: 애니메이션 변수 정의
  - `frontend/src/app/page.tsx`: 뷰 전환 애니메이션 (AnimatePresence)
  - `frontend/src/components/chat/ChatPanel.tsx`: 메시지 애니메이션 적용
  - `frontend/src/components/live/ObjectCard.tsx`: 카드 호버/탭 애니메이션
  - `frontend/src/components/live/RiskAlertBar.tsx`: 순차 페이드인 애니메이션
- **P4 완료** - 이기종 결합 예측 및 통계 개선
  - `frontend/src/components/live/HeterogeneousPrediction.tsx`: 이기종 결합 예측 컴포넌트 신규 생성
  - `frontend/src/components/live/StatisticsSummary.tsx`: Axia80 6축 평균, 예비보전 점수 추가
  - `frontend/src/components/live/EventList.tsx`: AI 예측 컬럼 개선 (Zap 아이콘, 네이비 배경)
  - `frontend/src/components/layout/Header.tsx`: History 탭 제거
  - `frontend/src/components/live/LiveView.tsx`: HeterogeneousPrediction 통합
- **P5 완료** - 이상 감지 알림 시스템 및 UI 개선 (2026-01-24)
  - `frontend/src/stores/alertStore.ts`: 이벤트 저장소 (Zustand)
  - `frontend/src/hooks/useAnomalyAlert.ts`: 이상 감지 알림 통합 훅
  - `frontend/src/hooks/useAlertSound.ts`: Web Audio API 경고음 훅
  - `frontend/src/components/ui/sonner.tsx`: Toast 알림 컴포넌트
  - `frontend/src/components/live/CorrelationTable.tsx`: "상관분석" → "실시간 예지보전", AI 배지 추가, 위험 감지 기록 섹션
  - `frontend/src/components/live/LiveView.tsx`: HeterogeneousPrediction 제거, 알림 토글 버튼 추가
  - `frontend/src/app/layout.tsx`: Toaster 컴포넌트 추가
- **P6 완료** - UR5e + Axia80 센서 통합 모니터링 차트 (2026-01-24)
  - `frontend/src/components/live/RealtimeChart.tsx`: UR5e 텔레메트리 데이터 추가 (tcp_speed, joint_torque_sum, joint_current_avg)
  - `frontend/src/components/live/LiveView.tsx`: integratedData 전달, 통합 axes 설정
  - `frontend/src/components/live/EventDetectionCard.tsx`: 이벤트 감지 카드 신규 (충돌/과부하/마모 모니터링)
- **P7 완료** - 이벤트 해결 관리 시스템 (2026-01-24)
  - `frontend/src/stores/eventResolveStore.ts`: 이벤트 해결 상태 저장소 (Zustand + persist)
  - `frontend/src/components/live/EventList.tsx`: "해결완료" 체크박스 컬럼 추가, 컬럼 간격 균등화
  - `frontend/src/components/live/EventDetectionCard.tsx`: 해결된 이벤트 제외 카운트, 해결 건수 표시
  - `frontend/messages/ko.json`, `frontend/messages/en.json`: Axia80 센서 설명 변경 (Fz, Fx, Fy + 이벤트 감지)
