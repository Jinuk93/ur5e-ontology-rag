<div align="center">

# 제조 AX를 위한 온톨로지 기반 지능형 진단 시스템

**UR5e 협동로봇 + Axia80 힘/토크 센서의 이기종 데이터를 온톨로지로 연결하여,<br/>
관계 기반 추론과 예지보전을 실현하는 PoC(Proof of Concept) 시스템**

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 1. 프로젝트 개요

### 1.1 배경

대한민국 제조업의 미래는 <b>AX(AI Transformation)</b>에 있습니다.<br>
기존 룰베이스(IF-THEN) 시스템은 단순 임계값 판단만 가능하지만, 현장에서 필요한 것은:

- "왜 이런 상황이 발생했는가?" <b>(원인 추론)</b>
- "내일 어떤 문제가 생길까?" <b>(예측)</b>
- "지금 이 맥락에서 최선의 조치는?" <b>(맥락 기반 판단)</b>

이 프로젝트는 **온톨로지 기반 관계 추론**으로 이 간극을 메우는 개념 증명입니다.

### 1.2 목표

| 구분 | 목표 |
|------|------|
| **1차** | 온톨로지 기반 제조 AI의 개념 증명 (PoC) |
| **최종** | 룰베이스 → 온톨로지 전환의 가치 입증 |

### 1.3 핵심 기능

```
┌─────────────────────────────────────────────────────────────────┐
│                         핵심 기능                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🔍 관계 기반 추론     "Fz가 -350N인데?" → 원인/예측/권장조치    │
│  📊 패턴 감지         충돌, 과부하, 드리프트, 진동 자동 감지     │
│  🌐 온톨로지 그래프    클릭으로 탐색하는 지식 관계 시각화         │
│  📄 근거 추적         모든 응답에 온톨로지 경로 + 문서 출처 제시  │
│  ⚡ 실시간 모니터링    SSE 기반 센서 데이터 스트리밍              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 PoC 구현 범위

> **현재 PoC에서 구현된 데이터 범위** (2026-01 기준)

| 데이터 소스 | 상태 | 설명 |
|------------|------|------|
| **Axia80 6축 센서** | ✅ 완전 구현 | Fx, Fy, Fz, Tx, Ty, Tz (7일 시뮬레이션) |
| **UR5e 에러 코드** | ✅ 구현됨 | C153, C189 등 (이벤트 데이터에 포함) |
| **패턴 감지** | ✅ 구현됨 | 충돌, 과부하, 드리프트, 진동 (17개 패턴) |
| **문서 벡터화** | ✅ 구현됨 | 722 chunks (매뉴얼, 에러코드 문서) |
| UR5e 조인트 각도 | 🔜 확장 예정 | Joint1~6 (rad) |
| UR5e TCP 위치 | 🔜 확장 예정 | X, Y, Z, Rx, Ry, Rz |
| UR5e 동작 모드 | 🔜 확장 예정 | idle, pick, place, move |

**현재 이기종 결합**: `Axia80 센서값` + `UR5e 에러코드` = ✅ 통합 완료

---

## 2. UR5e 협동로봇

### 2.1 개요

| 항목 | 내용 |
|------|------|
| **제조사** | Universal Robots (덴마크) |
| **모델명** | UR5e (e-Series) |
| **유형** | 6축 협동로봇 |
| **페이로드** | 5kg |
| **리치** | 850mm |

### 2.2 핵심 데이터

UR5e는 다음과 같은 데이터를 생성합니다:

| 데이터 유형 | 설명 | 예시 |
|-------------|------|------|
| **조인트 각도** | 6축 관절 위치 | Joint1~6 (rad) |
| **TCP 위치** | 툴 끝점 좌표 | X, Y, Z, Rx, Ry, Rz |
| **에러 코드** | 상태/오류 정보 | C189, C153, C204 등 |
| **동작 모드** | 현재 작업 상태 | idle, pick, place, move |

### 2.3 에러 코드 체계

```
C1xx: Safety 관련 (예: C153 충돌 감지)
C2xx: Joint 관련 (예: C204 진동 경고)
C3xx: Communication 관련
```

---

## 3. Axia80 힘/토크 센서

### 3.1 개요

| 항목 | 내용 |
|------|------|
| **제조사** | ATI Industrial Automation (미국) |
| **모델명** | Axia80 |
| **유형** | 6축 Force/Torque 센서 |
| **직경** | 82mm |
| **샘플링** | 125Hz |

### 3.2 6축 측정값

로봇 끝단에 장착되어 **힘(Force)**과 **토크(Torque)**를 실시간 측정합니다:

| 축 | 의미 | 단위 | 정상 범위 |
|----|------|------|-----------|
| **Fx** | X축 방향 힘 | N | -20 ~ +20 |
| **Fy** | Y축 방향 힘 | N | -20 ~ +20 |
| **Fz** | Z축 방향 힘 (수직) | N | -60 ~ 0 |
| **Tx** | X축 회전 토크 | Nm | -2 ~ +2 |
| **Ty** | Y축 회전 토크 | Nm | -2 ~ +2 |
| **Tz** | Z축 회전 토크 | Nm | -0.5 ~ +0.5 |

### 3.3 이상 패턴 예시

```
충돌(Collison) 
: Fz가 갑자기 -350N 이하로 급락 (100ms 이내)
과부하(Overload)
: |Fz|가 150N 초과 상태로 5초 이상 지속
드리프트(Drift)
: baseline 대비 10% 이상 편차가 30분 이상 유지
진동(Vibration)
: 표준편차가 평소의 2배 이상으로 10초 이상 지속
```

---

## 4. 온톨로지 기반 데이터 통합

### 4.1 이기종 데이터의 문제

로봇 데이터와 센서 데이터는 서로 **다른 형식, 다른 주기, 다른 의미**를 가집니다.

```
┌─────────────────────────────────────────────────────────────────┐
│  UR5e 로봇                        Axia80 센서                    │
│  ──────────                       ────────────                   │
│  • 이벤트 기반                    • 시계열 기반                  │
│  • 에러코드 (C189)                • 연속 측정값 (Fz=-350N)       │
│  • 상태 변화 시점만 기록          • 125Hz 연속 샘플링            │
│                                                                  │
│           ↓                              ↓                       │
│           └──────────┬───────────────────┘                       │
│                      ▼                                           │
│            ┌─────────────────┐                                   │
│            │    온톨로지     │                                   │
│            │  (관계 정의)    │                                   │
│            └─────────────────┘                                   │
│                      │                                           │
│           "Fz=-350N" ──▶ "충돌 패턴" ──▶ "C153 에러 가능성"      │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 4-Domain 온톨로지

```
┌───────────────────────────────────────────────────────────────────────┐
│                        UR5e Ontology Domains                          │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐          │
│   │  Equipment  │◀────▶│ Measurement │◀────▶│  Knowledge  │          │
│   │   Domain    │      │   Domain    │      │   Domain    │          │
│   │             │      │             │      │             │          │
│   │ • UR5e      │      │ • Fz, Fx... │      │ • 에러코드  │          │
│   │ • Axia80    │      │ • 상태      │      │ • 원인      │          │
│   │ • 조인트    │      │ • 패턴      │      │ • 문서      │          │
│   └─────────────┘      └─────────────┘      └─────────────┘          │
│          │                    │                    │                  │
│          └────────────────────┼────────────────────┘                  │
│                               ▼                                       │
│                      ┌─────────────┐                                  │
│                      │   Context   │                                  │
│                      │   Domain    │                                  │
│                      │             │                                  │
│                      │ • 시간대    │                                  │
│                      │ • 제품      │                                  │
│                      │ • 작업자    │                                  │
│                      └─────────────┘                                  │
│                                                                       │
│   ~50 Entities, ~100 Relationships, ~20 Rules                        │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 5. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          System Architecture                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Frontend (Next.js 16)                                            │  │
│  │  • ChatView - 자연어 질의응답                                     │  │
│  │  • GraphView - 온톨로지 관계 시각화 (React Flow)                  │  │
│  │  • LiveView - 실시간 센서 모니터링 (SSE)                          │  │
│  │  • HistoryView - 이벤트/패턴 이력                                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │ REST/SSE                                  │
│                              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Backend (FastAPI)                                                │  │
│  │  • /api/chat - 질의응답 API                                       │  │
│  │  • /api/sensors/* - 센서 데이터/패턴/이벤트                       │  │
│  │  • /api/ontology/* - 온톨로지 조회                                │  │
│  │  • /api/evidence/* - 근거 상세 조회                               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                           │
│           ┌──────────────────┼──────────────────┐                       │
│           ▼                  ▼                  ▼                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           │
│  │ Ontology Engine │ │  Vector Store   │ │  Sensor Store   │           │
│  │ (JSON/YAML)     │ │  (ChromaDB)     │ │  (Parquet)      │           │
│  │                 │ │                 │ │                 │           │
│  │ • 관계 추론     │ │ • 문서 검색     │ │ • 시계열 조회   │           │
│  │ • 규칙 실행     │ │ • 722 chunks    │ │ • 패턴 감지     │           │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘           │
│                              │                                           │
│                              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  AI/ML Layer                                                      │  │
│  │  • GPT-4 - 추론 및 응답 생성                                      │  │
│  │  • text-embedding-3-small - 문서 임베딩                           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 문서 구조

### 6.1 Steps (개발 단계별 문서)

| Step | 문서명 | 설명 |
|------|--------|------|
| 01 | 환경설정 | 프로젝트 구조, 의존성, 설정 |
| 02 | 데이터준비 | PDF 파싱, 청킹, 메타데이터 |
| 03 | 문서인덱싱 | 임베딩, ChromaDB 저장 |
| 04 | 온톨로지스키마 | 4-Domain 설계, 엔티티 정의 |
| 05 | 엔티티관계구축 | 온톨로지 로더, 관계 정의 |
| 06 | 추론규칙 | 규칙 엔진, 상태/패턴 추론 |
| 07 | 센서데이터처리 | Parquet 로딩, 시계열 조회 |
| 08 | 패턴감지 | 충돌/과부하/드리프트/진동 |
| 09 | 온톨로지연결 | 패턴-에러코드 매핑 |
| 10 | 질문분류기 | ONTOLOGY/HYBRID/RAG 분류 |
| 11 | 온톨로지추론 | 그래프 탐색, 경로 추출 |
| 12 | 응답생성 | LLM 프롬프트, 응답 구성 |
| 13 | UI및API계약 | API 스키마, UI 명세 |
| 14 | 프론트엔드구현 | Next.js 컴포넌트, 뷰 |
| 15 | 센서실시간및검증 | SSE 스트리밍, E2E 검증 |
| 16 | 통합테스트 | 유닛/통합/E2E 테스트 |
| 17 | 데모시나리오 | 재현 가능한 데모 흐름 |

### 6.2 References (참조 문서)

| 문서 | 설명 |
|------|------|
| [Unified_Spec.md](docs/Unified_Spec.md) | 전체 기술 설계서 (SoT) |
| [Unified_ROADMAP.md](docs/Unified_ROADMAP.md) | 개발 로드맵 |
| [SoT_백엔드_API_가이드.md](docs/references/SoT_백엔드_API_가이드.md) | API 명세 및 사용법 |
| [SoT_UI_설계_명세서.md](docs/references/SoT_UI_설계_명세서.md) | 프론트엔드 설계 |
| [SoT_재현성_가이드.md](docs/references/SoT_재현성_가이드.md) | 설치 및 실행 가이드 |

### 6.3 Reports (분석 보고서)

| 보고서 | 설명 |
|--------|------|
| [UR5e_로봇_분석_보고서.md](docs/reports/domain/robot/UR5e_로봇_분석_보고서.md) | UR5e 구조, 에러코드, 데이터 |
| [Axia80_센서_분석_보고서.md](docs/reports/domain/sensor/Axia80_센서_분석_보고서.md) | Axia80 6축, 측정값, 활용 |

---

## 7. 프로젝트 구조

```
ur5e-ontology-rag/
├── src/                    # 백엔드 소스 코드
│   ├── api/                # FastAPI 라우터, 스키마
│   ├── rag/                # 질문분류, 응답생성, 신뢰도게이트
│   ├── ontology/           # 온톨로지 엔진, 그래프 탐색, 규칙
│   ├── sensor/             # 센서 저장소, 패턴 감지
│   ├── embedding/          # 벡터 스토어, 임베딩
│   └── ingestion/          # PDF 파싱, 청킹
├── frontend/               # Next.js 프론트엔드
│   └── src/
│       ├── app/            # App Router 페이지
│       ├── components/     # React 컴포넌트
│       └── lib/            # API 클라이언트, 유틸
├── data/                   # 데이터 파일
│   ├── raw/pdf/            # 원본 PDF 매뉴얼
│   ├── processed/          # 청크, 온톨로지, 메타데이터
│   └── sensor/             # Axia80 센서 데이터
├── configs/                # 설정 파일
│   ├── settings.yaml       # 전역 설정
│   ├── pattern_thresholds.yaml  # 패턴 감지 임계값
│   └── inference_rules.yaml     # 추론 규칙
├── docs/                   # 문서
│   ├── steps/              # 개발 단계별 문서
│   ├── references/         # 참조 문서
│   └── reports/            # 분석 보고서
├── tests/                  # 테스트
│   ├── unit/               # 유닛 테스트 (64개)
│   └── integration/        # 통합 테스트
└── scripts/                # 실행 스크립트
```

---

## 8. 시작하기

### 8.1 요구사항

- Python 3.10+
- Node.js 18+
- OpenAI API Key

### 8.2 설치

```bash
# 1. 저장소 클론
git clone https://github.com/your-username/ur5e-ontology-rag.git
cd ur5e-ontology-rag

# 2. Python 가상환경
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력

# 4. 프론트엔드 의존성
cd frontend
npm install
cd ..
```

### 8.3 실행

```bash
# 백엔드 (포트 8000)
python scripts/run_api.py

# 프론트엔드 (포트 3000) - 새 터미널
cd frontend
npm run dev
```

브라우저에서 http://localhost:3000 접속

### 8.4 E2E 검증

```bash
# PowerShell에서 서버 실행 → 검증 → 종료를 한 번에 재현
powershell -ExecutionPolicy Bypass -File scripts/e2e_validate.ps1 -Port 8000
```

---

## 9. 기술 스택

### Backend
| 기술 | 용도 |
|------|------|
| **Python 3.10+** | 런타임 |
| **FastAPI** | REST API 서버 |
| **ChromaDB** | 벡터 데이터베이스 |
| **Pandas/PyArrow** | 데이터 처리 |
| **PyMuPDF** | PDF 파싱 |

### Frontend
| 기술 | 용도 |
|------|------|
| **Next.js 16** | React 프레임워크 |
| **Tailwind CSS** | 스타일링 |
| **shadcn/ui** | UI 컴포넌트 |
| **React Flow** | 그래프 시각화 |
| **Recharts** | 차트 |
| **TanStack Query** | 데이터 페칭 |

### AI/ML
| 기술 | 용도 |
|------|------|
| **GPT-4** | 추론 및 응답 생성 |
| **text-embedding-3-small** | 문서 임베딩 |

---

## 10. API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 헬스체크 |
| `/api/chat` | POST | 질의응답 |
| `/api/evidence/{trace_id}` | GET | 근거 상세 조회 |
| `/api/ontology/summary` | GET | 온톨로지 요약 |
| `/api/sensors/readings` | GET | 센서 측정값 |
| `/api/sensors/patterns` | GET | 감지된 패턴 |
| `/api/sensors/events` | GET | 이상 이벤트 |
| `/api/sensors/stream` | GET | SSE 실시간 스트림 |

---

## 11. 사용 예시

### 질의응답

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Fz가 -350N인데 뭐가 문제야?"}'
```

### 응답 예시

```json
{
  "trace_id": "abc123",
  "query_type": "ontology",
  "answer": "Fz 값 -350N은 충돌 패턴을 나타냅니다. 최근 유사 패턴이 3회 감지되었으며, 조치하지 않을 경우 24시간 내 C153 에러 발생 가능성이 85%입니다. 그립 위치를 확인하시기 바랍니다.",
  "analysis": {
    "entity": "Fz",
    "value": -350.0,
    "state": "Warning"
  },
  "reasoning": {
    "confidence": 0.85,
    "pattern": "collision",
    "cause": "grip_position"
  },
  "graph": {
    "nodes": [...],
    "edges": [...]
  }
}
```

---

## 12. 프론트엔드 연동

백엔드 응답은 snake_case(`trace_id`, `query_type` 등)를 유지합니다.
프론트에서는 [frontend/src/lib/api.ts](frontend/src/lib/api.ts)의 어댑터 함수를 사용해 정규화합니다.

```ts
import { buildChatRequest, normalizeChatResponse } from '@/lib/api'

const res = await fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(buildChatRequest({ message: 'Fz가 -350N인데?' }))
})

const data = normalizeChatResponse(await res.json())
console.log(data.traceId, data.queryType)
```

---

## 13. 라이선스

MIT License

---

## 14. 기여

이 프로젝트는 개인 프로젝트로서 제조 AX의 가능성을 탐구하기 위해 진행되었습니다.
피드백과 제안은 언제나 환영합니다.
