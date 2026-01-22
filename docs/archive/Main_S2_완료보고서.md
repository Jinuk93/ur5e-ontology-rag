# Main-S2: 패턴 감지 - 완료 보고서

> **Phase**: Main-S2 (센서 통합 Phase 2)
> **목표**: 센서 데이터에서 이상 패턴 자동 감지
> **상태**: 완료
> **일자**: 2026-01-21

---

## 1. 구현 요약

### 1.1 완료 항목

| 항목 | 파일 | 상태 |
|------|------|------|
| PatternDetector 클래스 | `src/sensor/pattern_detector.py` | 완료 |
| SensorStore 클래스 | `src/sensor/sensor_store.py` | 완료 |
| 설정 파일 | `configs/pattern_thresholds.yaml` | 완료 |
| 배치 감지 스크립트 | `scripts/detect_patterns.py` | 완료 |
| 단위 테스트 | `tests/unit/test_pattern_detector.py` | 완료 (26개 통과) |

### 1.2 파일 구조

```
src/sensor/
├── __init__.py              # 패키지 초기화
├── pattern_detector.py      # 패턴 감지기 (350+ lines)
└── sensor_store.py          # 데이터 저장소 (370+ lines)

configs/
└── pattern_thresholds.yaml  # 감지 임계값 설정

scripts/
└── detect_patterns.py       # 배치 감지 스크립트

data/sensor/processed/
├── detected_patterns.json   # 감지 결과 (17개 패턴)
└── validation_results.json  # S1 이벤트 검증 결과
```

---

## 2. 구현 세부사항

### 2.1 PatternDetector 클래스

4가지 이상 패턴 감지 알고리즘 구현:

| 패턴 유형 | 알고리즘 | 임계값 | 연관 에러코드 |
|-----------|----------|--------|--------------|
| **collision** | Spike Detection | Fz > 500N, deviation > 300N | C153, C119 |
| **vibration** | Rolling STD | Tx/Ty noise > 2x baseline | C204 |
| **overload** | Threshold Duration | Fz > 300N for 5+ seconds | C189 |
| **drift** | Baseline Deviation | 10%+ shift over 0.5+ hours | - |

**주요 메서드:**
```python
detector = PatternDetector()
patterns = detector.detect(
    data=df,
    pattern_types=["collision", "overload"],
    start_time=datetime(2024, 1, 17, 10, 0),
    end_time=datetime(2024, 1, 17, 12, 0)
)
```

### 2.2 SensorStore 클래스

센서 데이터 및 패턴 조회 API:

| 메서드 | 기능 |
|--------|------|
| `load_data()` | Parquet 데이터 로드 |
| `get_data(start, end)` | 시간 범위 데이터 조회 |
| `get_patterns(error_code, pattern_type)` | 조건별 패턴 조회 |
| `get_statistics()` | 축별 통계 조회 |
| `get_summary()` | 전체 요약 정보 |

**사용 예시:**
```python
store = SensorStore()
patterns = store.get_patterns(
    error_code="C153",
    time_window="1h",
    reference_time=datetime(2024, 1, 17, 14, 0)
)
```

### 2.3 DetectedPattern 데이터클래스

```python
@dataclass
class DetectedPattern:
    pattern_id: str           # PAT-001
    pattern_type: str         # collision, vibration, overload, drift
    timestamp: datetime       # 감지 시점
    duration_ms: int          # 지속 시간
    confidence: float         # 0.0 ~ 1.0
    metrics: Dict             # peak_value, baseline 등
    related_error_codes: List # C153, C189 등
    event_id: Optional[str]   # S1 이벤트 매칭 (검증용)
    context: Dict             # 추가 컨텍스트
```

---

## 3. 감지 결과

### 3.1 배치 감지 실행

```bash
python scripts/detect_patterns.py --validate
```

### 3.2 감지 통계

| 패턴 유형 | 감지 건수 | 신뢰도 평균 |
|-----------|-----------|-------------|
| Collision | 2건 | 1.00 |
| Overload | 4건 | 1.00 |
| Drift | 11건 | 0.98 |
| **Total** | **17건** | - |

### 3.3 S1 이벤트 검증

Main-S1에서 주입한 이벤트와의 매칭 결과:

| 메트릭 | 값 |
|--------|-----|
| **Recall** | 100% (7/7) |
| **Precision** | 41.18% (7/17) |
| **F1 Score** | 58.33% |

**매칭 성공:**
| S1 이벤트 | 감지 패턴 | 유형 |
|-----------|-----------|------|
| EVT-001 | PAT-001 | collision |
| EVT-002 | PAT-002 | collision |
| EVT-003 | PAT-003 | overload |
| EVT-004 | PAT-004 | overload |
| EVT-005 | PAT-005 | overload |
| EVT-006 | PAT-006 | overload |
| EVT-010 | PAT-014 | drift |

**False Positives (10건):**
- 대부분 drift 패턴
- 정상 운영 중 발생한 baseline 변동
- S1에서 명시적으로 주입하지 않은 자연 발생 패턴

---

## 4. 단위 테스트

### 4.1 테스트 결과

```
26 passed in 1.93s
```

### 4.2 테스트 카테고리

| 카테고리 | 테스트 수 | 내용 |
|----------|----------|------|
| DetectedPattern | 4 | 생성, 직렬화, 역직렬화, 왕복 |
| CollisionDetection | 4 | 정상/단일/다중/이벤트ID |
| VibrationDetection | 2 | 정상/감지 |
| OverloadDetection | 3 | 정상/감지/짧은 미감지 |
| DriftDetection | 1 | 드리프트 감지 |
| Integration | 3 | 전체유형/시간필터/카운터리셋 |
| SensorStore | 5 | 싱글톤/로드/통계/요약/파싱 |
| EdgeCases | 3 | 빈데이터/단일행/컬럼누락 |

---

## 5. 설정 파일

### 5.1 pattern_thresholds.yaml

```yaml
collision:
  threshold_N: 500
  rise_time_ms: 100
  min_deviation: 300
  related_errors: [C153, C119]

vibration:
  freq_threshold_hz: 50
  amplitude_threshold: 2.0
  window_s: 5
  min_duration_s: 10
  related_errors: [C204]

overload:
  threshold_N: 300
  duration_s: 5
  axis: "Fz"
  related_errors: [C189]

drift:
  window_h: 1
  deviation_pct: 10
  min_duration_h: 0.5
  related_errors: []
```

---

## 6. 통합 포인트

### 6.1 Context Enricher (Main-S3)

PatternDetector → Context Enricher:
```python
# Context Enricher에서 패턴 정보 활용
detector = PatternDetector()
patterns = detector.detect(data, pattern_types=["collision"])

context = {
    "detected_patterns": [p.to_dict() for p in patterns],
    "error_code": "C153",
    "sensor_evidence": True
}
```

### 6.2 Verifier (Main-S5)

SensorStore → Verifier:
```python
# Verifier에서 센서 근거 조회
store = SensorStore()
related_patterns = store.get_patterns(
    error_code="C153",
    time_window="1h",
    reference_time=error_timestamp
)

if len(related_patterns) > 0:
    evidence.sensor_patterns = related_patterns
    evidence.has_sensor_support = True
```

---

## 7. 다음 단계

- [x] Main-S1: 센서 데이터 생성 (완료)
- [x] Main-S2: 패턴 감지 알고리즘 구현 (완료)
- [ ] Main-S3: Context Enricher 구현
- [ ] Main-S4: 온톨로지 확장
- [ ] Main-S5: Verifier 확장
- [ ] Main-S6: API/UI 확장

---

## 8. 참고사항

### 8.1 성능

- 604,800 레코드 (7일) 처리: ~2초
- 메모리 사용: ~100MB (Parquet 압축 효과)

### 8.2 한계점

1. **Drift 민감도**: 정상 운영 변동도 감지 (False Positive 높음)
   - 개선안: 시간대/컨텍스트 기반 필터링 추가

2. **Vibration 감지**: 현재 시간 도메인만 분석
   - 개선안: FFT 기반 주파수 분석 추가 (선택적)

### 8.3 데모 시나리오 지원

| 시나리오 | 지원 | 감지 결과 |
|----------|------|-----------|
| A: 전조→충돌 | O | EVT-001, EVT-002 감지 |
| B: 반복 재발 | O | EVT-003~006 감지 |
| C: 오탐/유사 | O | tool_change/recalibration 미감지 (정상) |

---

**작성**: Main-S2 패턴 감지
**참조**: Main_S2_패턴감지.md, Main_S1_센서데이터생성.md
