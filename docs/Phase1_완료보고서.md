# Phase 1: PDF 구조 파악 - 완료 보고서

> **목표:** PDF 문서들의 구조를 분석하여 온톨로지 설계와 청킹 전략의 기초 데이터를 확보한다.
>
> **왜 필요한가?** 문서 구조를 이해해야 효과적인 청킹 전략과 온톨로지 설계가 가능하다.

---

## 1. 개요

### 1.1 분석 대상 문서

| 문서 | 파일명 | 크기 | 페이지 | 용도 |
|------|--------|------|--------|------|
| **에러 코드** | `ErrorCodes.pdf` | 1.27 MB | 167 | 에러 코드 정의 및 해결 방법 |
| **서비스 매뉴얼** | `e-Series_Service_Manual_en.pdf` | 22.16 MB | 123 | 수리/유지보수 절차 |
| **사용자 매뉴얼** | `710-965-00_UR5e_User_Manual_en_Global.pdf` | 19.70 MB | 249 | 로봇 조작 및 설정 가이드 |

### 1.2 분석 도구

```
scripts/
├── analyze_pdf.py              ← 전체 PDF 기본 정보 분석
├── analyze_error_codes.py      ← ErrorCodes.pdf 상세 분석
├── analyze_service_manual.py   ← Service Manual 상세 분석
└── analyze_user_manual.py      ← User Manual 상세 분석
```

---

## 2. ErrorCodes.pdf 분석 결과

### 2.1 문서 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    ErrorCodes.pdf                           │
├─────────────────────────────────────────────────────────────┤
│  페이지 1-11: 표지, 저작권, 면책조항, 소개                    │
│  페이지 12~: 에러 코드 정의                                  │
├─────────────────────────────────────────────────────────────┤
│  TOC 항목: 232개                                            │
│  - Level 1: 1개 (Introduction)                              │
│  - Level 2: 231개 (에러 코드들)                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 에러 코드 패턴

| 패턴 | 형식 | 개수 | 예시 |
|------|------|------|------|
| **C 코드** | `C[숫자]` | 231개 | C0, C1, C2, C3, C4 ... |

### 2.3 에러 코드 구조 예시

```
1.1. C0 No error
If you unable to resolve the issue, login to http://myUR.universal-robots...

1.2. C1 Outbuffer overflow
C1A1 Buffer of stored warnings overflowed
```

**관찰된 패턴:**
- 에러 코드: `C[숫자]` (예: C0, C1, C2)
- 서브 코드: `C[숫자]A[숫자]` (예: C1A1)
- 각 코드는 간단한 설명과 해결 방법 포함

### 2.4 온톨로지 설계를 위한 인사이트

```
ErrorCode (엔티티)
├── code: string         # "C1"
├── sub_code: string     # "C1A1"
├── name: string         # "Outbuffer overflow"
├── description: string  # 설명
└── action: string       # 조치 방법
```

---

## 3. Service Manual 분석 결과

### 3.1 문서 구조

```
┌─────────────────────────────────────────────────────────────┐
│               e-Series_Service_Manual_en.pdf                │
├─────────────────────────────────────────────────────────────┤
│  페이지 1: 표지                                              │
│  페이지 2-3: 목차 (Contents)                                │
│  페이지 4~: 본문                                            │
├─────────────────────────────────────────────────────────────┤
│  TOC 항목: PDF에 없음 (텍스트 기반 목차)                     │
│  이미지: 501개                                              │
│  WARNING/CAUTION: 15개 페이지                               │
│  절차(Step): 99개 페이지                                    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 주요 챕터 (추정)

| 챕터 | 내용 |
|------|------|
| 1. Copyright and disclaimers | 저작권 |
| 2. Introduction | 문서 소개 |
| 3. Safety | 안전 지침 |
| 4. Recommended Inspection Activities | 점검 활동 |
| 5. Robot Arm / Control Box | 하드웨어 분해/조립 |

### 3.3 컴포넌트 언급 빈도

| 컴포넌트 | 언급 페이지 수 | 중요도 |
|----------|---------------|--------|
| Control Box | 34 | ★★★★★ |
| Joint | 33 | ★★★★★ |
| Teach Pendant | 24 | ★★★★ |
| Cable | 23 | ★★★★ |
| Robot Arm | 19 | ★★★★ |
| Connector | 16 | ★★★ |
| Safety | 12 | ★★★ |
| Board | 12 | ★★★ |
| PCB | 6 | ★★ |
| Power Supply | 6 | ★★ |

### 3.4 내용 패턴 예시

```
5.2.12. Dual Robot Calibration

Description
Dual Robot Calibration calibrates the robot in the full workspace...

NOTICE
If a joint is replaced on a calibrated robot the calibration...

To perform a Dual Robot Calibration, you need:
 - 2 robots (same size and same generation)
 - Dual Robot Calibration Tooling Complete (Part no: 185500)
```

**관찰된 구조:**
- `[번호]. [제목]`
- `Description` 섹션
- `NOTICE` / `WARNING` 경고
- 필요 도구/부품 목록
- 단계별 절차

### 3.5 온톨로지 설계를 위한 인사이트

```
Component (엔티티)
├── name: string            # "Control Box", "Joint"
├── type: string            # "hardware"
└── procedures: [Procedure] # 연결된 절차들

Procedure (엔티티)
├── title: string           # "Dual Robot Calibration"
├── description: string     # 설명
├── warnings: [string]      # NOTICE, WARNING 목록
├── required_tools: [string]# 필요 도구
└── steps: [string]         # 단계별 절차
```

---

## 4. User Manual 분석 결과

### 4.1 문서 구조

```
┌─────────────────────────────────────────────────────────────┐
│          710-965-00_UR5e_User_Manual_en_Global.pdf          │
├─────────────────────────────────────────────────────────────┤
│  페이지 1-3: 표지, 저작권, 면책조항                          │
│  페이지 4-6: Preface (서문)                                 │
│  페이지 7-10: Contents (목차)                               │
│  페이지 11~: 본문                                           │
├─────────────────────────────────────────────────────────────┤
│  TOC 항목: PDF에 없음 (텍스트 기반 목차)                     │
│  이미지: 774개                                              │
│  PolyScope 언급: 46개 페이지                                │
│  UI 관련 페이지: 24개                                       │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 주요 챕터

| 번호 | 챕터명 | 내용 |
|------|--------|------|
| 1 | Preface | 서문, 소개 |
| 2 | Liability and Intended Use | 책임 및 용도 |
| 3 | Your Robot | 로봇 소개 |
| 4 | Safety | 안전 지침 |
| 5 | Lifting and Handling | 운반 방법 |
| 6 | Assembly and Mounting | 조립 및 설치 |
| 7 | First Boot | 첫 부팅 |
| 8 | Installation | 설치 |
| 9 | End Effector Integration | 엔드 이펙터 |
| 10 | Configuration | 설정 |
| 11 | The First Program | 첫 프로그램 |
| 12 | Cybersecurity | 사이버 보안 |
| 13 | Communication Networks | 통신 네트워크 |
| 14 | Risk Assessment | 리스크 평가 |

### 4.3 주요 용어 언급 빈도

| 용어 | 페이지 수 | 중요도 |
|------|-----------|--------|
| Safety | 99 | ★★★★★ |
| Program | 88 | ★★★★★ |
| Installation | 72 | ★★★★★ |
| Button | 68 | ★★★★ |
| Screen | 58 | ★★★★ |
| Configuration | 52 | ★★★★ |
| Settings | 47 | ★★★ |
| Interface | 34 | ★★★ |
| Operation | 33 | ★★★ |

### 4.4 PolyScope 관련 분석

PolyScope는 UR 로봇의 제어 소프트웨어입니다.

| 기능 | 언급 페이지 수 |
|------|---------------|
| Program | 25 |
| Safety | 25 |
| Installation | 19 |
| Move | 19 |
| Waypoint | 3 |

### 4.5 내용 패턴 예시

```
11.2. Move Robot into Position

Description
Access the Move Robot into Position screen when the Robot Arm is in
particular start position before running a program, or to teach new
waypoint while modifying a program.
```

**관찰된 구조:**
- `[번호]. [제목]`
- `Description` 섹션
- 스크린샷 (이미지)
- UI 요소 설명 (버튼, 메뉴, 탭)

### 4.6 온톨로지 설계를 위한 인사이트

```
Feature (엔티티)
├── name: string           # "Move Robot into Position"
├── category: string       # "Program", "Safety", "Installation"
├── description: string    # 설명
└── ui_location: string    # UI 위치

UIElement (엔티티)
├── name: string           # "Move Button"
├── type: string           # "button", "screen", "menu"
├── location: string       # 화면 위치
└── function: string       # 기능 설명
```

---

## 5. PDF 구조 비교 요약

| 항목 | ErrorCodes | Service Manual | User Manual |
|------|------------|----------------|-------------|
| **페이지 수** | 167 | 123 | 249 |
| **파일 크기** | 1.27 MB | 22.16 MB | 19.70 MB |
| **이미지 수** | 334 | 501 | 774 |
| **TOC 유무** | O (232개) | X | X |
| **주요 내용** | 에러 코드 정의 | 수리/유지보수 절차 | 사용법 가이드 |
| **구조화 정도** | 매우 높음 | 중간 | 중간 |
| **청킹 난이도** | 쉬움 | 중간 | 중간 |

---

## 6. 청킹 전략 제안

### 6.1 ErrorCodes.pdf

```
청킹 단위: 에러 코드별 (C0, C1, C2...)
----------------------------------------
장점:
- TOC가 있어 자동 분리 가능
- 각 코드가 독립적인 의미 단위

예상 청크 수: ~231개 (에러 코드 수)
```

### 6.2 Service Manual

```
청킹 단위: 절차(Procedure)별
----------------------------------------
장점:
- 각 절차가 독립적인 작업 단위
- "Description", "NOTICE" 등 명확한 구분자

예상 청크 수: ~100개
```

### 6.3 User Manual

```
청킹 단위: 기능/화면별
----------------------------------------
장점:
- 각 기능이 사용자 task와 매핑
- UI 요소 중심으로 구조화

예상 청크 수: ~150개
```

---

## 7. 온톨로지 설계 초안

### 7.1 핵심 엔티티

```
                    ┌─────────────┐
                    │   Robot     │
                    │  (UR5e)     │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  Component  │ │  ErrorCode  │ │   Feature   │
    │ (하드웨어)   │ │ (에러코드)  │ │  (기능)      │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           ▼               │               ▼
    ┌─────────────┐        │        ┌─────────────┐
    │  Procedure  │◄───────┴───────►│  UIElement  │
    │ (절차)       │                 │ (UI요소)     │
    └─────────────┘                 └─────────────┘
```

### 7.2 관계(Relationship)

| 관계 | 설명 | 예시 |
|------|------|------|
| `HAS_COMPONENT` | 로봇 → 컴포넌트 | Robot → Control Box |
| `HAS_ERROR` | 컴포넌트 → 에러 | Joint → C10 |
| `RESOLVED_BY` | 에러 → 절차 | C10 → "Joint Replacement" |
| `REQUIRES_TOOL` | 절차 → 도구 | Procedure → "Screwdriver" |
| `HAS_FEATURE` | 로봇 → 기능 | Robot → "Move to Position" |
| `DISPLAYED_ON` | 기능 → UI | Feature → "Move Screen" |

---

## 8. 다음 단계 (Phase 2)

### 8.1 수행할 작업

```
Phase 2: PDF 파싱 및 텍스트 추출
├── PyMuPDF로 텍스트 추출
├── 청킹 전략 구현
├── 메타데이터 추출
└── 처리된 데이터 저장
```

### 8.2 필요한 파일

```
src/ingestion/
├── pdf_parser.py        ← PDF 파싱 클래스
├── chunker.py           ← 청킹 로직
└── text_cleaner.py      ← 텍스트 정제
```

---

## 9. Phase 1 완료 체크리스트

- [x] ErrorCodes.pdf 분석 완료
- [x] Service Manual 분석 완료
- [x] User Manual 분석 완료
- [x] 각 문서의 구조 파악
- [x] 청킹 전략 초안 작성
- [x] 온톨로지 설계 초안 작성
- [x] 분석 스크립트 작성 (4개)
- [x] 완료 보고서 작성

---

## 10. 생성된 파일

| 경로 | 설명 |
|------|------|
| `scripts/analyze_pdf.py` | 전체 PDF 기본 분석 스크립트 |
| `scripts/analyze_error_codes.py` | ErrorCodes.pdf 상세 분석 |
| `scripts/analyze_service_manual.py` | Service Manual 상세 분석 |
| `scripts/analyze_user_manual.py` | User Manual 상세 분석 |
| `docs/Phase1_완료보고서.md` | 본 문서 |

---

**Phase 1 완료!** 다음은 Phase 2 (PDF 파싱 및 텍스트 추출)로 진행합니다.
