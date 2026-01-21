# Main-S1: ATI Axia80 센서 데이터 생성

> **Phase**: Main-S1 (센서 통합 Phase 1)
> **목표**: 7일치 시뮬레이션 센서 데이터 생성
> **상태**: 완료

---

## 1. 개요

### 1.1 목적
- ATI Axia80 Force/Torque 센서의 현실적인 시뮬레이션 데이터 생성
- 데모 퍼포먼스 중심 설계 (정확·안전·추적·무할루시네이션)
- RAG 시스템의 이중 검증(문서+센서) 테스트용 데이터

### 1.2 설계 원칙
1. **센서값 ↔ 컨텍스트 일관성**: 측정값과 작업 상황이 논리적으로 맞아야 함
2. **시나리오 기반 이상 패턴**: 단발 이벤트가 아닌 "전개가 있는 스토리"
3. **Verifier 테스트용 케이스**: 의도적인 근거 부족 케이스 포함
4. **현장 현실성**: 데이터 품질 이슈(결측, 지연) 포함

---

## 2. 생성 결과 요약

### 2.1 기본 정보
| 항목 | 값 |
|------|-----|
| 기간 | 2024-01-15 ~ 2024-01-21 (7일) |
| 총 레코드 | 604,800 |
| 샘플링 레이트 | 1 Hz (1초 평균) |
| 파일 크기 | 34.15 MB |
| 파일 형식 | Parquet (snappy 압축) |

### 2.2 파일 위치
```
data/sensor/
├── raw/
│   └── axia80_week_01.parquet    # 원본 데이터 (34.15 MB)
├── processed/
│   └── anomaly_events.json       # 이상 이벤트 메타데이터
└── metadata/
    └── sensor_config.yaml        # 생성 설정
```

---

## 3. 데이터 스키마 (21개 컬럼)

### 3.1 센서 측정값 (6개)
| 컬럼명 | 타입 | 단위 | 범위 | 설명 |
|--------|------|------|------|------|
| `timestamp` | datetime64 | UTC | - | 측정 시각 |
| `Fx` | float32 | N | ±500 | X축 힘 |
| `Fy` | float32 | N | ±500 | Y축 힘 |
| `Fz` | float32 | N | ±1000 | Z축 힘 (메인 작업축) |
| `Tx` | float32 | Nm | ±20 | X축 토크 |
| `Ty` | float32 | Nm | ±20 | Y축 토크 |
| `Tz` | float32 | Nm | ±20 | Z축 토크 |

### 3.2 작업 컨텍스트 (7개)
| 컬럼명 | 타입 | 예시값 | 설명 |
|--------|------|--------|------|
| `task_mode` | string | idle, pick, place, approach, retract, stop | 현재 작업 모드 |
| `work_order_id` | string | WO-20240115-001 | 작업 지시 번호 |
| `product_id` | string | PART-A, PART-B, PART-C | 제품 종류 |
| `shift` | string | A, B, C | 근무조 |
| `operator_id` | string | OP-001, OP-002, OP-003 | 작업자 ID |
| `gripper_state` | string | open, closed, holding | 그리퍼 상태 |
| `payload_class` | string | none, light, normal, heavy | 하중 분류 |

### 3.3 장비 상태 (2개)
| 컬럼명 | 타입 | 예시값 | 설명 |
|--------|------|--------|------|
| `payload_kg` | float32 | 0.0, 1.0, 2.5, 4.2 | 현재 하중 (kg) |
| `tool_id` | string | GRIPPER-01, GRIPPER-02 | 장착 툴 ID |

### 3.4 데이터 품질 (2개)
| 컬럼명 | 타입 | 예시값 | 설명 |
|--------|------|--------|------|
| `clock_skew_ms` | int16 | -50 ~ +50 | UR vs 센서 시간 오차 |
| `data_quality` | string | good, delayed, interpolated | 데이터 품질 플래그 |

### 3.5 상태/이벤트 (3개)
| 컬럼명 | 타입 | 예시값 | 설명 |
|--------|------|--------|------|
| `status` | string | normal, warning, anomaly | 센서 상태 |
| `event_id` | string | EVT-001 | 연관 이벤트 ID |
| `error_code` | string | C119, C153, C189 | 발생 에러코드 |

---

## 4. 데이터 분포

### 4.1 Task Mode 분포
| Mode | 레코드 수 | 비율 | 설명 |
|------|----------|------|------|
| idle | 417,239 | 69.0% | 대기 상태 |
| retract | 56,270 | 9.3% | 복귀 중 |
| approach | 56,265 | 9.3% | 접근 중 |
| place | 37,512 | 6.2% | 배치 중 |
| pick | 37,511 | 6.2% | 파지 중 |
| stop | 3 | 0.0% | 정지 (에러) |

### 4.2 Status 분포
| Status | 레코드 수 | 비율 |
|--------|----------|------|
| normal | 596,800 | 98.68% |
| warning | 7,997 | 1.32% |
| anomaly | 3 | 0.00% |

### 4.3 데이터 품질 분포
| Quality | 레코드 수 | 비율 |
|---------|----------|------|
| good | 595,458 | 98.46% |
| delayed | 6,014 | 0.99% |
| interpolated | 3,328 | 0.55% |

### 4.4 센서값 통계
| 축 | 평균 | 표준편차 | 최소 | 최대 |
|----|------|---------|------|------|
| Fx | -0.00 | 2.57 | -20.81 | 23.74 |
| Fy | 0.01 | 2.57 | -21.74 | 24.60 |
| Fz | -20.15 | 15.30 | **-829.24** | 10.67 |
| Tx | 0.00 | 0.20 | -2.03 | 2.28 |
| Ty | -0.00 | 0.20 | -2.14 | 2.12 |
| Tz | -0.00 | 0.08 | -0.88 | 0.94 |

> Fz 최소값 -829N은 충돌 이벤트(시나리오 A)에서 발생

---

## 5. 이상 시나리오

### 5.1 시나리오 A: 전조 → 충돌 → 정지 (2건)
```
[스토리] 그리퍼 마모로 인한 점진적 악화 후 충돌 정지

[타임라인]
T-20분: 진동 미세 증가 (Tx, Ty 노이즈 +30%)
T-0분 : 충돌 발생 (Fz 급증 600~900N)
T+0초 : Safety Stop (C153)

[데모 포인트]
- "전조 패턴을 감지했으면 예방 가능했다"
- 문서 근거 + 센서 근거 모두 확인 → PASS
```

| Event ID | 발생 시점 | Fz 피크 | 에러코드 |
|----------|----------|---------|----------|
| EVT-001 | Day 2 | ~800N | C153 |
| EVT-002 | Day 5 | ~750N | C153 |

### 5.2 시나리오 B: 반복 재발 (4건, 4일 연속)
```
[스토리] 특정 시간대/제품에서만 반복 발생

[패턴]
- 매일 14:00~15:00 사이 과부하 경고
- shift B, product PART-C에서만 발생
- 원인: 해당 제품이 스펙보다 무거움

[데모 포인트]
- "같은 시간대, 같은 제품에서 반복" → 공정 원인 암시
- Day 4에 Safety Stop (C189) 발생
```

| Event ID | 발생 일차 | Fz 값 | 지속 시간 | 에러코드 |
|----------|----------|-------|----------|----------|
| EVT-003 | Day 1 | ~350N | 15초 | - |
| EVT-004 | Day 2 | ~380N | 20초 | - |
| EVT-005 | Day 3 | ~360N | 18초 | - |
| EVT-006 | Day 4 | ~400N | 22초 | **C189** |

### 5.3 시나리오 C: 오탐/유사 증상 (4건)
```
[목적] Verifier가 "이상"과 "정상 운영 변화"를 구분하는지 테스트

[케이스]
1. 툴 교체 후 baseline 이동 (정상) - 2회
2. 캘리브레이션 후 값 점프 (정상) - 1회
3. 드리프트 패턴 (문서에 조치 없음) - 1회 → ABSTAIN 예상
```

| Event ID | 유형 | 설명 | 예상 결과 |
|----------|------|------|----------|
| EVT-007 | tool_change | GRIPPER-01 → GRIPPER-02 | 정상 판정 |
| EVT-008 | tool_change | GRIPPER-02 → GRIPPER-01 | 정상 판정 |
| EVT-009 | recalibration | 센서 영점 조정 | 정상 판정 |
| EVT-010 | drift_no_doc | 4시간 드리프트 | **ABSTAIN** |

---

## 6. 센서값 ↔ 컨텍스트 매핑 규칙

데이터 생성 시 적용된 일관성 규칙:

| task_mode | gripper_state | payload_class | Fz 범위 |
|-----------|---------------|---------------|---------|
| `idle` | open | none | -15 ± 5N |
| `approach` | open | none | -15 ± 5N |
| `pick` | holding | light/normal/heavy | -30 ~ -80N |
| `place` | holding | light/normal/heavy | -30 ~ -80N |
| `retract` | open | none | -15 ± 5N |
| `stop` | any | any | any |

### Payload별 Fz 설정
| payload_class | payload_kg | Fz mean | Fz std |
|---------------|------------|---------|--------|
| none | 0 | -15N | 3N |
| light | 0.5-1.5 | -30N | 5N |
| normal | 1.5-3.0 | -50N | 8N |
| heavy | 3.0-5.0 | -75N | 10N |

---

## 7. Verifier 테스트 케이스

데이터에 의도적으로 포함된 케이스:

| 케이스 | 센서 상태 | 문서 근거 | 예상 결과 |
|--------|----------|----------|----------|
| 시나리오 A | 충돌 패턴 O | C153 조치 O | **PASS** |
| 시나리오 B | 과부하 패턴 O | C189 조치 O | **PASS** |
| 시나리오 C (툴교체) | baseline 이동 | 이상 아님 | **정상 판정** |
| 시나리오 C (드리프트) | 드리프트 O | 해당 조치 없음 | **ABSTAIN** |

---

## 8. 사용 방법

### 8.1 데이터 로드
```python
import pandas as pd

# Parquet 로드
df = pd.read_parquet('data/sensor/raw/axia80_week_01.parquet')
print(f"레코드 수: {len(df):,}")
print(f"컬럼: {list(df.columns)}")
```

### 8.2 이상 이벤트 조회
```python
import json

with open('data/sensor/processed/anomaly_events.json', 'r') as f:
    events = json.load(f)

for e in events:
    print(f"{e['event_id']}: {e['scenario']} - {e['event_type']}")
```

### 8.3 특정 시나리오 데이터 필터
```python
# 시나리오 A (충돌) 구간 조회
collision_events = df[df['event_id'].str.startswith('EVT-001', na=False)]

# 시나리오 B (반복 재발) 구간 조회
overload_events = df[df['status'] == 'warning']

# 이상 구간만 조회
anomaly_data = df[df['status'] == 'anomaly']
```

---

## 9. 다음 단계

- [x] Main-S1: 센서 데이터 생성 (완료)
- [ ] Main-S2: 패턴 감지 알고리즘 구현
- [ ] Main-S3: Context Enricher 구현
- [ ] Main-S4: 온톨로지 확장
- [ ] Main-S5: Verifier 확장
- [ ] Main-S6: API/UI 확장

---

**참조**: Main__Spec.md, Main__ROADMAP.md
