# Step 1~17 문서 정합성 리뷰 (Document Review)

- Target: Step 1~17 문서 전체 + 메인 3문서(로드맵/스펙/스키마설계) + SoT(references)
- Goal: **내용/경로/데이터/아키텍처** 정합성 점검 및 드리프트(불일치) 식별

---

## 0. 전제(요청 기준) 확인

사용자가 정의한 “정본(Source of Truth) 방향”을 본 리뷰의 기준으로 고정한다.

- Step 1~12: **메인 3문서(로드맵/스펙/스키마설계) → Step/코드/검증** 방향으로 작성됨
- Step 13~17: **Step의 설계/기능을 먼저 결정 → 메인 3문서(로드맵/스펙/스키마설계)는 사후 업데이트** 방향
- 또한 Phase 13 이후는 `docs/references/*`의 SoT 문서가 “계약/재현성 정본” 역할을 수행

즉, Step 13~17 구간에서 메인 3문서는 ‘근거’라기보다 ‘집계/정리 문서’에 가까우며, 실제 계약/재현성은 SoT를 기준으로 검증해야 한다.

---

## 1. 검토 범위 및 방법

### 1.1 읽기/확인한 주요 파일

- 메인 3문서
  - `docs/Unified_ROADMAP.md`
  - `docs/Unified_Spec.md`
  - `docs/온톨로지_스키마_설계.md`
- Step 13~17 (설계 문서 직접 확인)
  - `docs/steps/step_13_UI및API계약_설계.md`
  - `docs/steps/step_14_프론트엔드구현_설계.md`
  - `docs/steps/step_15_센서실시간및검증_설계.md`
  - `docs/steps/step_16_통합테스트_설계.md`
  - `docs/steps/step_17_데모시나리오_설계.md`
- Step 10 (완료 문서 샘플 확인)
  - `docs/steps/step_10_질문분류기_완료.md`
- SoT 문서 존재 확인
  - `docs/references/*` (7개)
- 문서가 참조하는 핵심 런타임/검증 경로 존재 확인
  - `scripts/e2e_validate.ps1`, `scripts/validate_api.py`, `scripts/run_api.py`, `src/api/main.py`
  - `frontend/`, `contracts/p0_api_adapter.ts`
- 도메인 분석 보고서(정본) 존재 확인
  - `docs/reports/domain/sensor/Axia80_센서_분석_보고서.md`
  - `docs/reports/domain/robot/UR5e_로봇_분석_보고서.md`

### 1.2 점검 항목

- **경로 정합성**: 문서에 적힌 파일/폴더가 실제로 존재하는가
- **정본 구조 정합성**: Step13~17에서 SoT(references)로 정본이 고정되어 있는가
- **아키텍처 정합성**: 백엔드/프론트 구성, 엔트리포인트, 검증 루틴이 문서와 일치하는가
- **데이터 정합성**: 도메인 보고서/데이터 경로가 메인 문서와 일치하는가
- **드리프트 탐지**: 과거 문서(구경로/구문서)가 남아 혼선을 만드는가

---

## 2. 요약 결과

### 2.1 PASS(정합)

- Phase 13~17에서 요구하는 핵심 파일들이 실제로 존재함
  - `frontend/` 존재
  - `contracts/p0_api_adapter.ts` 존재
  - `scripts/e2e_validate.ps1`, `scripts/validate_api.py` 존재
  - `scripts/run_api.py`, `src/api/main.py` 존재
- SoT 폴더/문서가 실제로 존재하고, Step 13 문서에서 SoT로의 링크가 명확함
  - `docs/references/SoT_UI_설계_명세서.md`
  - `docs/references/SoT_백엔드_API_가이드.md`
  - `docs/references/SoT_재현성_가이드.md` 등
- 도메인 분석 보고서(정본)가 `docs/reports/domain/...`에 존재하며, 메인 3문서의 상대경로(`reports/domain/...`)와 정합

### 2.2 WARN(정리 필요)

- `docs/` 루트에 **구문서(legacy)로 보이는 파일들이 남아있고**, 내용상 “정본이 references로 이동”한 현재 구조와 충돌 가능성이 있음
  - 예: `docs/프론트엔드_작업보고서.md` 내부에 `docs/UI_설계_명세서.md`, `docs/재현성검증.md` 업데이트 지시가 남아 있음
  - 이는 사용자가 의도한 “references로 정본 이동”과 상충하며, 향후 독자가 구문서를 정본으로 오인할 위험이 큼
- Step 1~12는 이번 패스에서 ‘전체 내용 일치’까지는 정밀 감사하지 않았고, **샘플( Step10 ) + 구조/경로 중심으로만 확인**함
  - 필요 시 Step1~12도 동일 수준(핵심 경로/데이터/계약 항목)으로 정밀 리뷰 확장 권장

---

## 3. 상세 리뷰

## 3.1 Step 13~17 vs 메인 3문서: 정본 방향성

- Step 13 문서 자체가 “SoT(정본) 확정”을 목표로 명시하고 있어, 사용자가 말한 13~17 방향성과 일치한다.
- 메인 로드맵(`docs/Unified_ROADMAP.md`)도 Phase 13을 “UI 및 API 계약(SoT + 재현 검증)”으로 정의하고 있어, **13~17이 ‘독단 설계 후 메인 문서 업데이트’**라는 운영 방식과 큰 충돌은 없다.

권장 보강:
- 메인 3문서 어딘가(예: 로드맵 Phase 13 섹션)에 **“Phase 13~17은 SoT(references) 및 steps가 정본이며, 메인 문서는 집계 문서”**라는 문장 1~2줄을 명시하면 드리프트 방지가 더 강해진다.

## 3.2 경로/링크 정합성(핵심)

문서에서 자주 등장하는 핵심 경로는 실제 레포에 존재한다.

- 프론트 정본: `frontend/src/lib/api.ts` (Step 13에서 정본으로 선언)
- 계약 참고: `contracts/p0_api_adapter.ts`
- E2E 검증: `scripts/e2e_validate.ps1` + `scripts/validate_api.py`
- 백엔드 엔트리포인트: `scripts/run_api.py` + `src/api/main.py`
- 도메인 정본 보고서: `docs/reports/domain/{sensor,robot}/*`

## 3.3 아키텍처/실행 절차 정합성

- Step 16의 “Windows E2E 한 방” 커맨드(`scripts/e2e_validate.ps1`) 기반 검증은 레포 구조와 정합한다.
- Step 17의 백엔드 실행 커맨드(`python scripts/run_api.py --host 127.0.0.1 --port 8002`)도 파일 존재 기준으로 정합한다.

주의:
- 실제로 E2E가 PASS하는지는 본 리뷰에서 실행 검증까지는 수행하지 않았다(문서/경로/구성 정합성 리뷰 중심). 필요 시 `scripts/e2e_validate.ps1`를 실제로 돌려서 결과를 리뷰 문서에 추가하는 “런타임 증빙” 섹션을 확장할 수 있다.

## 3.4 데이터 정합성(도메인 보고서)

- `docs/Unified_Spec.md` 및 `docs/온톨로지_스키마_설계.md`는 도메인 보고서를 `reports/domain/...`로 참조한다.
- 실제 정본은 `docs/reports/domain/...`에 있고, 메인 문서가 `docs/` 폴더에 있으므로 상대경로 해석상 정합하다.

## 3.5 Step 1~12: 샘플( Step10 ) 기반 정합성 체크

- `docs/steps/step_10_질문분류기_완료.md`는 Phase 10(Query Engine) 범위를 명확히 정의하고, 구현 파일을 `src/rag/*`로 특정한다.
- 이는 레포의 `src/` 구조(추론/RAG 관련 코드가 `src/`에 위치)와 충돌하지 않는다.

다만 Step 1~12 전체에 대해 “메인 3문서와 1:1 내용 일치” 수준의 감사는 아직 미수행이다.
- 다음 확장 리뷰 시, 각 Step(1~12)에 대해
  - (a) 메인 3문서의 해당 Phase 요구사항(산출물/데이터/검증)을 요약
  - (b) Step 문서의 산출물/경로/테스트가 그 요구사항을 충족하는지
  - (c) 실제 코드/스크립트 경로 존재 여부
  를 표 형태로 정리하면 가장 깔끔하게 정합성을 증명할 수 있다.

---

## 4. 드리프트/리스크(정리 권장)

### 4.1 docs 루트의 legacy 문서 존재

현재 `docs/` 루트에 다음과 같은 문서가 남아 있고, 내부에 구경로/구지시가 남아있다.

- `docs/프론트엔드_작업보고서.md`
  - `docs/UI_설계_명세서.md`, `docs/재현성검증.md` 업데이트 지시 등
- `docs/UI_설계_명세서.md`

이 상태는 “정본이 `docs/references`로 이동했다”는 운영 원칙과 충돌할 수 있다.

권장 조치(택1):
1) docs 루트 legacy 문서를 **stub-only**로 바꾸고 `docs/references/*`로 유도
2) 또는 docs 루트 legacy 문서를 삭제(단, 외부 링크/북마크 호환이 필요하면 stub 유지)

---

## 5. 우선순위 액션 아이템

1) (중요) `docs/` 루트 legacy 문서 처리 방침 결정
   - stub-only 유지 vs 삭제
2) (권장) 메인 3문서에 “Step 13~17 정본 방향(steps+SoT 우선)”을 1~2줄 명시
3) (선택) Step 1~12도 동일한 방식으로 ‘요구사항→산출물→검증’ 매핑 표를 만들어 정합성 증빙 강화
4) (선택) `scripts/e2e_validate.ps1` 실제 실행 결과를 이 리뷰에 추가(런타임 PASS 스냅샷)

---

## 6. 결론

- Step 13~17 구간의 문서 구조(SoT 기반 계약/재현성 고정)와 레포 구조(프론트/백엔드/검증 스크립트)는 **전반적으로 정합**하다.
- 가장 큰 혼선 요인은 `docs/` 루트에 남아있는 legacy 문서들로, **정본 이동 원칙과 충돌**할 가능성이 높다.
- Step 1~12는 구조/샘플 기준으로 큰 충돌은 보이지 않지만, 요청하신 “전체 내용 일치” 수준의 완전 감사는 추가 패스가 필요하다.
