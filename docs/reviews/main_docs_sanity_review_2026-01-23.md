# 메인 문서 3종 Sanity Review (논리/정합성 점검)

- Date: 2026-01-23
- Target:
  - `docs/Unified_ROADMAP.md`
  - `docs/Unified_Spec.md`
  - `docs/온톨로지_스키마_설계.md`
- Goal: “새 기능 검증”이 아니라, **문서 내부 논리** 및 **서로 간 충돌/혼선 포인트**를 빠르게 잡아내는 최종 점검

## 🔁 재리뷰(수정 반영 확인)

- Re-review Date: 2026-01-23
- Focus(이전 지적사항): (1) 로드맵 폴더 트리의 “현행 레포 vs 개념도” 혼선, (2) 센서 수치(정상범위 vs 상태구간) 정본/예시 라벨링, (3) 레거시 API 힌트 잔존
- 결과 요약:
  - ✅ (해소) 로드맵에서 `frontend/`(루트 레벨) 및 `src/api/main.py`(단일 엔트리 중심) 서술은 현행 레포 구조와 정합
  - ✅ (해소) 메인 3문서에서 `/query`/`/api/v1/query` 등의 레거시 경로 힌트는 더 이상 탐지되지 않음
  - ✅ (해소) 스키마 설계의 `states` vs 문서 예시 `normal_range` 분리 원칙에 맞춰, 스펙의 “IDLE 상태” 표현을 “정상 범위(예시 기준선)”로 정리
  - ✅ (해소) 로드맵의 폴더 트리 예시에서 센서 raw 파일명을 `axia80_week_01.parquet`로 통일

---

## 1) 결론 요약

### ✅ OK (핵심 논리/구성이 잘 맞음)

- **Phase 13~17의 운영 철학(계약/재현성 정본 고정)**이 로드맵/스펙/스키마 설계 전반에서 일관되게 유지된다.
- **API 엔드포인트 세트**(`/health`, `/api/chat`, `/api/evidence/{trace_id}`, `/api/ontology/summary`, `/api/sensors/*`)가 문서에 명시되어 있고, 실제 구현도 동일한 형태로 제공된다.
- **센서 데이터 경로 및 Degrade 정책**이 문서와 코드가 동일한 방향으로 정리되어 있다.
  - 센서 parquet 부재/엔진 부재 → readings=[] 반환, SSE는 에러 이벤트 1회 송출 후 종료(“정상 degrade”)
- **프론트 구조(Next.js App Router + 그래프/챗/근거)**가 로드맵/스펙의 서술과 잘 맞는다.

### ✅ 잔여 WARN 없음(재리뷰 기준)

- 이전에 지적했던 (1) 로드맵 폴더 트리 혼선, (2) `normal_range` vs `states` 혼선, (3) 레거시 API 힌트는 모두 해소됨

---

## 2) 사실 기반 체크(레포와의 1차 대조)

### 2.1 데이터 경로

- 문서에 반복 등장하는 센서 데이터 파일:
  - `data/sensor/raw/axia80_week_01.parquet`
- 실제 레포:
  - `data/sensor/raw/axia80_week_01.parquet` 존재

### 2.2 API 엔드포인트

문서가 명시하는 핵심 엔드포인트들이 실제 구현에 존재한다.

- `/health`
- `/api/chat`
- `/api/evidence/{trace_id}`
- `/api/ontology/summary`
- `/api/sensors/readings`
- `/api/sensors/patterns`
- `/api/sensors/events`
- `/api/sensors/stream` (SSE)

### 2.3 Degrade 정책(센서)

- `src/api/main.py`에서
  - parquet 미존재/읽기 실패 시 빈 DataFrame으로 degrade
  - `/api/sensors/readings`는 readings=[] 반환
  - SSE는 `data: {"error": "No sensor data available"}` 1회 송출 후 종료

---

## 3) 권장 정리(문서만 살짝 다듬으면 더 완성도 올라감)

### A. 로드맵의 폴더 트리 섹션 라벨 명확화

- (해소됨) 로드맵의 `frontend/` 및 `src/api/main.py` 중심 서술은 현행 레포 구조와 정합

### B. 센서 수치(정상범위/상태구간)의 정본 선언

- 스키마 설계는 “states vs normal_range” 분리를 이미 명시했으므로,
- ✅ 스펙의 “IDLE 상태” 표현을 “예시 normal_range(기준선)”로 정리 완료

### C. 레거시 API 흔적에 대한 문서 레벨 정리

- (해소됨) 메인 3문서에서 `/query`/`/api/v1/query` 등의 레거시 힌트는 현재 탐지되지 않음

### D. 로드맵 내부의 센서 raw 파일명/포맷 정리

- ✅ 로드맵의 “폴더 트리 예시” 센서 raw 파일명을 `axia80_week_01.parquet`로 통일 완료

---

## 4) 최종 판단

- **핵심 아키텍처/계약/검증 루틴은 세 문서가 서로 크게 모순되지 않고** 잘 맞는다.
- 남은 이슈는 기능적 오류라기보다 “독자가 오해할 수 있는 표현/예시/레거시 잔존” 영역이며, 가볍게 정리하면 문서가 거의 완성판이 된다.
