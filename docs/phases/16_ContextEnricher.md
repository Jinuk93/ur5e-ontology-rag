# Phase 16: Context Enricher

> **상태**: ✅ 완료
> **도메인**: 검색 레이어 (Retrieval)
> **목표**: 문서 검색 결과에 센서 맥락을 통합
> **이전 명칭**: Main-S3

---

## 1. 개요

문서 기반 검색 결과(원인, 해결책)와 센서 데이터(패턴, 타임스탬프)를
결합하여 더 풍부한 맥락을 제공하는 ContextEnricher를 구현하는 단계.

---

## 2. 태스크

| # | 태스크 | 상태 |
|---|--------|------|
| 1 | ContextEnricher 클래스 설계 | ✅ |
| 2 | 에러-패턴 매핑 구현 | ✅ |
| 3 | 상관관계 분석 구현 | ✅ |
| 4 | error_pattern_mapping.yaml 작성 | ✅ |
| 5 | 단위 테스트 (23개) | ✅ |

---

## 3. Context Enrichment 아키텍처

### 3.1 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│                    Context Enricher                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  입력:                                                       │
│  ├─ 문서 검색 결과 (DocumentContext)                         │
│  │   └─ ErrorCode, Cause, Resolution                        │
│  └─ 센서 패턴 (SensorPatterns)                               │
│      └─ collision, vibration, overload, drift               │
│                                                             │
│  처리:                                                       │
│  [1] 에러코드 ↔ 센서패턴 매핑                                 │
│      └─ error_pattern_mapping.yaml 기반                     │
│                                                             │
│  [2] 상관관계 분석                                           │
│      └─ STRONG / MODERATE / WEAK / NONE                     │
│                                                             │
│  [3] 시간 근접성 확인                                         │
│      └─ 패턴 발생 시간 ↔ 에러 발생 시간                        │
│                                                             │
│  출력:                                                       │
│  └─ EnrichedContext                                         │
│      ├─ 문서 맥락 + 센서 맥락                                │
│      ├─ 상관관계 점수                                        │
│      └─ 통합 근거                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 상관관계 수준

| 수준 | 점수 | 조건 |
|------|------|------|
| `STRONG` | 0.9 | 에러-패턴 직접 매핑 + 시간 근접 |
| `MODERATE` | 0.6 | 에러-패턴 간접 매핑 |
| `WEAK` | 0.3 | 같은 컴포넌트 관련 |
| `NONE` | 0.0 | 관련성 없음 |

---

## 4. 에러-패턴 매핑

### 4.1 error_pattern_mapping.yaml

```yaml
# configs/error_pattern_mapping.yaml

# 에러코드 → 관련 센서 패턴 매핑
mappings:
  # Control Box 관련
  C154A3:  # Fan malfunction
    patterns: []  # 센서로 감지 안됨
    correlation: none

  C15402:  # Voltage error
    patterns: []
    correlation: none

  # 조인트 관련 (센서로 감지 가능)
  J0A501:  # Joint 0 overcurrent
    patterns:
      - overload
    correlation: strong
    affected_axes: ["Tz"]

  J1A505:  # Joint 1 position error
    patterns:
      - collision
      - drift
    correlation: strong
    affected_axes: ["Fx", "Fy"]

  J3A507:  # Joint 3 brake error
    patterns:
      - overload
    correlation: moderate
    affected_axes: ["Fz"]

  # 안전 관련
  S10001:  # Emergency stop
    patterns:
      - collision
      - overload
    correlation: strong
    affected_axes: ["Fx", "Fy", "Fz"]

# 패턴 → 가능한 에러코드 역매핑
reverse_mappings:
  collision:
    possible_errors:
      - J1A505
      - J2A505
      - S10001
    severity_indication: high

  vibration:
    possible_errors:
      - J0A510
      - J1A510
    severity_indication: medium

  overload:
    possible_errors:
      - J0A501
      - J3A507
      - S10001
    severity_indication: high

  drift:
    possible_errors:
      - J1A505
      - "calibration_needed"
    severity_indication: low
```

---

## 5. 구현

### 5.1 ContextEnricher 클래스

```python
# src/rag/context_enricher.py

from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum
import yaml

class CorrelationLevel(Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"

@dataclass
class SensorContext:
    patterns: List[DetectedPattern]
    time_range: tuple
    summary: str

@dataclass
class EnrichedContext:
    document_context: DocumentContext
    sensor_context: Optional[SensorContext]
    correlation: CorrelationLevel
    correlation_score: float
    integrated_evidence: List[str]
    recommendations: List[str]

class ContextEnricher:
    def __init__(
        self,
        mapping_path: str = "configs/error_pattern_mapping.yaml",
        sensor_store: Optional[SensorStore] = None
    ):
        self.mappings = self._load_mappings(mapping_path)
        self.sensor_store = sensor_store or SensorStore()

    def enrich(
        self,
        doc_context: DocumentContext,
        query_time: Optional[datetime] = None,
        time_window_hours: int = 24
    ) -> EnrichedContext:
        """문서 맥락에 센서 정보 추가"""

        # 1. 관련 에러코드 추출
        error_codes = self._extract_error_codes(doc_context)

        # 2. 에러코드에 매핑된 패턴 찾기
        expected_patterns = self._get_expected_patterns(error_codes)

        # 3. 시간 범위 내 감지된 패턴 조회
        detected_patterns = self._get_recent_patterns(
            query_time, time_window_hours
        )

        # 4. 상관관계 분석
        correlation, score = self._analyze_correlation(
            expected_patterns, detected_patterns
        )

        # 5. 센서 맥락 구성
        sensor_context = self._build_sensor_context(
            detected_patterns, expected_patterns
        )

        # 6. 통합 근거 생성
        integrated_evidence = self._generate_integrated_evidence(
            doc_context, sensor_context, correlation
        )

        # 7. 권장 사항 생성
        recommendations = self._generate_recommendations(
            error_codes, detected_patterns, correlation
        )

        return EnrichedContext(
            document_context=doc_context,
            sensor_context=sensor_context,
            correlation=correlation,
            correlation_score=score,
            integrated_evidence=integrated_evidence,
            recommendations=recommendations
        )

    def _analyze_correlation(
        self,
        expected: List[str],
        detected: List[DetectedPattern]
    ) -> tuple:
        """상관관계 분석"""
        if not expected or not detected:
            return CorrelationLevel.NONE, 0.0

        detected_types = {p.pattern_type for p in detected}
        matches = set(expected) & detected_types

        if len(matches) >= 2:
            return CorrelationLevel.STRONG, 0.9
        elif len(matches) == 1:
            return CorrelationLevel.MODERATE, 0.6
        elif any(p.pattern_type in ["collision", "overload"] for p in detected):
            return CorrelationLevel.WEAK, 0.3
        else:
            return CorrelationLevel.NONE, 0.0

    def _generate_integrated_evidence(
        self,
        doc_ctx: DocumentContext,
        sensor_ctx: Optional[SensorContext],
        correlation: CorrelationLevel
    ) -> List[str]:
        """통합 근거 생성"""
        evidence = []

        # 문서 근거
        for source in doc_ctx.sources:
            evidence.append(f"📄 {source.citation}: {source.text_preview}")

        # 센서 근거
        if sensor_ctx and correlation != CorrelationLevel.NONE:
            for pattern in sensor_ctx.patterns:
                evidence.append(
                    f"📊 센서 패턴 감지: {pattern.pattern_type} "
                    f"({pattern.start_time.strftime('%Y-%m-%d %H:%M')})"
                )

        return evidence

    def _generate_recommendations(
        self,
        error_codes: List[str],
        patterns: List[DetectedPattern],
        correlation: CorrelationLevel
    ) -> List[str]:
        """권장 사항 생성"""
        recommendations = []

        if correlation == CorrelationLevel.STRONG:
            recommendations.append(
                "⚠️ 센서 데이터와 에러가 강하게 연관됩니다. "
                "즉시 점검을 권장합니다."
            )
        elif correlation == CorrelationLevel.MODERATE:
            recommendations.append(
                "📋 센서 데이터와 에러가 연관될 수 있습니다. "
                "추가 모니터링을 권장합니다."
            )

        # 패턴별 권장 사항
        for pattern in patterns:
            if pattern.pattern_type == "collision":
                recommendations.append(
                    "🔴 충돌 감지됨: 로봇 경로와 작업 환경을 확인하세요."
                )
            elif pattern.pattern_type == "overload":
                recommendations.append(
                    "🟠 과부하 감지됨: 페이로드와 작업 속도를 확인하세요."
                )

        return recommendations
```

### 5.2 EnrichedContext 스키마

```python
# src/rag/schemas/enriched_context.py

from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class CorrelationLevel(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"

class SensorPatternInfo(BaseModel):
    pattern_type: str
    start_time: str
    end_time: str
    severity: str
    affected_axes: List[str]

class SensorContextSchema(BaseModel):
    patterns: List[SensorPatternInfo]
    time_range_start: str
    time_range_end: str
    summary: str

class EnrichedContextSchema(BaseModel):
    correlation: CorrelationLevel
    correlation_score: float
    sensor_context: Optional[SensorContextSchema]
    integrated_evidence: List[str]
    recommendations: List[str]
```

---

## 6. 산출물

### 6.1 파일 목록

| 파일 | 내용 | Lines/크기 |
|------|------|-----------|
| `src/rag/context_enricher.py` | ContextEnricher 클래스 | ~300 lines |
| `src/rag/schemas/enriched_context.py` | 스키마 정의 | ~50 lines |
| `configs/error_pattern_mapping.yaml` | 에러-패턴 매핑 | 3.5KB |
| `tests/test_context_enricher.py` | 단위 테스트 | 23개 |

### 6.2 테스트 결과

```
========================= test session starts ==========================
tests/test_context_enricher.py::test_enrich_with_strong_correlation PASSED
tests/test_context_enricher.py::test_enrich_with_no_patterns PASSED
tests/test_context_enricher.py::test_correlation_analysis PASSED
tests/test_context_enricher.py::test_integrated_evidence PASSED
tests/test_context_enricher.py::test_recommendations PASSED
...
========================= 23 passed in 0.67s ===========================
```

---

## 7. 사용 예시

```python
# 사용 예시
enricher = ContextEnricher()

# 문서 검색 결과
doc_context = DocumentContext(
    error_codes=["J1A505"],
    causes=["Position error in Joint 1"],
    resolutions=["Recalibrate joint"]
)

# 센서 맥락 통합
enriched = enricher.enrich(
    doc_context,
    query_time=datetime.now(),
    time_window_hours=24
)

print(f"상관관계: {enriched.correlation.value}")  # "strong"
print(f"점수: {enriched.correlation_score}")       # 0.9
print(f"근거: {enriched.integrated_evidence}")
print(f"권장: {enriched.recommendations}")
```

---

## 8. 검증 체크리스트

- [x] ContextEnricher 클래스 구현
- [x] 상관관계 분석 (STRONG/MODERATE/WEAK/NONE)
- [x] error_pattern_mapping.yaml 작성
- [x] 통합 근거 생성 기능
- [x] 권장 사항 생성 기능
- [x] 23개 단위 테스트 100% 통과

---

## 9. 다음 단계

→ [Phase 17: 온톨로지 확장](17_온톨로지확장.md)

---

**Phase**: 16 / 19
**작성일**: 2026-01-22
