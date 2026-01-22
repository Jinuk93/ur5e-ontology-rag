# Phase 18: Verifier 확장

> **상태**: ✅ 완료
> **도메인**: 검증 레이어 (Verification)
> **목표**: 문서 + 센서 + 온톨로지 3중 검증 시스템 구현
> **이전 명칭**: Main-S5

---

## 1. 개요

기존 문서 기반 검증에 센서 데이터 검증과 온톨로지 일관성 검증을 추가하여
답변의 신뢰도를 다각도로 평가하는 확장된 Verifier를 구현하는 단계.

---

## 2. 태스크

| # | 태스크 | 상태 |
|---|--------|------|
| 1 | SensorVerifier 구현 | ✅ |
| 2 | OntologyVerifier 구현 | ✅ |
| 3 | VerificationStatus 확장 (7단계) | ✅ |
| 4 | 통합 Verifier 확장 | ✅ |
| 5 | 단위 테스트 (24개) | ✅ |

---

## 3. 3중 검증 아키텍처

### 3.1 검증 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    Extended Verifier                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  입력: RAG 답변 (causes, actions, evidence, sensor_context) │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [1] DocumentVerifier (기존)                          │   │
│  │     └─▶ 문서 citation 확인                           │   │
│  │     └─▶ 점수: doc_score (0.0 ~ 1.0)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [2] SensorVerifier (신규)                            │   │
│  │     └─▶ 센서 패턴 ↔ 에러 매칭 확인                    │   │
│  │     └─▶ 시간 근접성 확인                             │   │
│  │     └─▶ 점수: sensor_score (0.0 ~ 1.0)              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [3] OntologyVerifier (신규)                          │   │
│  │     └─▶ 에러 → 원인 → 해결책 경로 확인                │   │
│  │     └─▶ 그래프 일관성 검증                           │   │
│  │     └─▶ 점수: ontology_score (0.0 ~ 1.0)            │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [4] Score Aggregation                                │   │
│  │     confidence = (doc × 0.50) + (sensor × 0.30)     │   │
│  │                + (ontology × 0.15) + bonus          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  출력: VerificationResult (status, confidence, details)    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 확장된 VerificationStatus

| 상태 | 설명 | 조건 |
|------|------|------|
| `VERIFIED` | 완전 검증 | doc + sensor + ontology 모두 통과 |
| `PARTIAL_BOTH` | 부분 검증 (문서+센서) | doc + sensor 통과, ontology 미통과 |
| `PARTIAL_DOC_ONLY` | 문서만 검증 | doc 통과, sensor/ontology 미통과 |
| `PARTIAL_SENSOR_ONLY` | 센서만 검증 | sensor 통과, doc 미통과 |
| `PARTIAL_ONTOLOGY_ONLY` | 온톨로지만 검증 | ontology 통과, doc/sensor 미통과 |
| `INSUFFICIENT` | 근거 부족 | 모든 검증 미통과 |
| `UNVERIFIED` | 검증 불가 | 검증 데이터 없음 |

---

## 4. 구현

### 4.1 SensorVerifier

```python
# src/rag/sensor_verifier.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta

@dataclass
class SensorVerificationResult:
    is_valid: bool
    score: float
    matched_patterns: List[str]
    time_proximity: Optional[float]  # 시간 근접성 (0-1)
    details: str

class SensorVerifier:
    def __init__(
        self,
        sensor_store: SensorStore,
        pattern_detector: PatternDetector,
        mapping_path: str = "configs/error_pattern_mapping.yaml"
    ):
        self.sensor_store = sensor_store
        self.pattern_detector = pattern_detector
        self.mappings = self._load_mappings(mapping_path)

    def verify(
        self,
        error_codes: List[str],
        sensor_context: Optional[SensorContext],
        query_time: Optional[datetime] = None
    ) -> SensorVerificationResult:
        """센서 데이터로 에러 검증"""

        if not sensor_context or not sensor_context.patterns:
            return SensorVerificationResult(
                is_valid=False,
                score=0.0,
                matched_patterns=[],
                time_proximity=None,
                details="No sensor data available"
            )

        # 1. 에러코드에 예상되는 패턴 조회
        expected_patterns = self._get_expected_patterns(error_codes)

        # 2. 실제 감지된 패턴과 매칭
        detected_types = {p.pattern_type for p in sensor_context.patterns}
        matched = set(expected_patterns) & detected_types

        # 3. 시간 근접성 계산
        time_proximity = self._calculate_time_proximity(
            sensor_context.patterns, query_time
        )

        # 4. 점수 계산
        match_ratio = len(matched) / len(expected_patterns) if expected_patterns else 0
        score = (match_ratio * 0.7) + (time_proximity * 0.3)

        return SensorVerificationResult(
            is_valid=score >= 0.5,
            score=score,
            matched_patterns=list(matched),
            time_proximity=time_proximity,
            details=f"Matched {len(matched)}/{len(expected_patterns)} patterns"
        )

    def _calculate_time_proximity(
        self, patterns: List[DetectedPattern], query_time: Optional[datetime]
    ) -> float:
        """패턴 발생 시간과 쿼리 시간의 근접성 계산"""
        if not query_time or not patterns:
            return 0.5  # 기본값

        min_gap = float('inf')
        for pattern in patterns:
            gap = abs((query_time - pattern.start_time).total_seconds())
            min_gap = min(min_gap, gap)

        # 1시간 이내면 1.0, 24시간이면 0.0
        max_gap = 24 * 3600  # 24시간
        proximity = max(0, 1 - (min_gap / max_gap))
        return proximity
```

### 4.2 OntologyVerifier

```python
# src/rag/ontology_verifier.py

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class OntologyVerificationResult:
    is_valid: bool
    score: float
    path_exists: bool
    consistency: float
    details: str

class OntologyVerifier:
    def __init__(self, graph_retriever: GraphRetriever):
        self.graph_retriever = graph_retriever

    def verify(
        self,
        error_codes: List[str],
        causes: List[str],
        resolutions: List[str]
    ) -> OntologyVerificationResult:
        """온톨로지 일관성 검증"""

        if not error_codes:
            return OntologyVerificationResult(
                is_valid=False,
                score=0.0,
                path_exists=False,
                consistency=0.0,
                details="No error codes to verify"
            )

        # 1. 에러 → 원인 경로 확인
        cause_paths = self._verify_cause_paths(error_codes, causes)

        # 2. 에러 → 해결책 경로 확인
        resolution_paths = self._verify_resolution_paths(error_codes, resolutions)

        # 3. 일관성 점수 계산
        consistency = (cause_paths + resolution_paths) / 2

        # 4. 전체 경로 존재 확인
        path_exists = self._check_full_path(error_codes, causes, resolutions)

        score = (consistency * 0.6) + (0.4 if path_exists else 0.0)

        return OntologyVerificationResult(
            is_valid=score >= 0.5,
            score=score,
            path_exists=path_exists,
            consistency=consistency,
            details=f"Consistency: {consistency:.2f}, Path exists: {path_exists}"
        )

    def _verify_cause_paths(
        self, error_codes: List[str], causes: List[str]
    ) -> float:
        """에러 → 원인 경로 검증"""
        valid_count = 0

        for code in error_codes:
            graph_causes = self.graph_retriever.search_error_causes(code)
            graph_cause_texts = {c.description.lower() for c in graph_causes}

            for cause in causes:
                if any(cause.lower() in gc for gc in graph_cause_texts):
                    valid_count += 1
                    break

        return valid_count / len(error_codes) if error_codes else 0.0
```

### 4.3 통합 Verifier 확장

```python
# src/rag/verifier.py (확장)

from enum import Enum

class VerificationStatus(Enum):
    VERIFIED = "verified"
    PARTIAL_BOTH = "partial_both"
    PARTIAL_DOC_ONLY = "partial_doc_only"
    PARTIAL_SENSOR_ONLY = "partial_sensor_only"
    PARTIAL_ONTOLOGY_ONLY = "partial_ontology_only"
    INSUFFICIENT = "insufficient"
    UNVERIFIED = "unverified"

@dataclass
class ExtendedVerificationResult:
    status: VerificationStatus
    confidence: float
    doc_score: float
    sensor_score: float
    ontology_score: float
    correlation_bonus: float
    citations: List[str]
    warnings: List[str]
    details: dict

class ExtendedVerifier:
    def __init__(
        self,
        document_verifier: Verifier,
        sensor_verifier: SensorVerifier,
        ontology_verifier: OntologyVerifier
    ):
        self.doc_verifier = document_verifier
        self.sensor_verifier = sensor_verifier
        self.ontology_verifier = ontology_verifier

        # 가중치 설정
        self.weights = {
            "document": 0.50,
            "sensor": 0.30,
            "ontology": 0.15,
            "correlation_max": 0.05
        }

    def verify(
        self,
        causes: List[str],
        actions: List[str],
        evidence: List[Evidence],
        sensor_context: Optional[SensorContext] = None,
        enriched_context: Optional[EnrichedContext] = None
    ) -> ExtendedVerificationResult:
        """3중 검증 실행"""

        # 1. 문서 검증
        doc_result = self.doc_verifier.verify(causes, actions, evidence)
        doc_score = doc_result.confidence if doc_result.status == VerificationStatus.PASS else 0.3

        # 2. 센서 검증
        error_codes = self._extract_error_codes(evidence)
        sensor_result = self.sensor_verifier.verify(
            error_codes, sensor_context
        )
        sensor_score = sensor_result.score

        # 3. 온톨로지 검증
        ontology_result = self.ontology_verifier.verify(
            error_codes, causes, actions
        )
        ontology_score = ontology_result.score

        # 4. 상관관계 보너스
        correlation_bonus = 0.0
        if enriched_context and enriched_context.correlation.value == "strong":
            correlation_bonus = self.weights["correlation_max"]

        # 5. 최종 신뢰도 계산
        confidence = (
            (doc_score * self.weights["document"]) +
            (sensor_score * self.weights["sensor"]) +
            (ontology_score * self.weights["ontology"]) +
            correlation_bonus
        )

        # 6. 상태 결정
        status = self._determine_status(
            doc_score, sensor_score, ontology_score
        )

        return ExtendedVerificationResult(
            status=status,
            confidence=confidence,
            doc_score=doc_score,
            sensor_score=sensor_score,
            ontology_score=ontology_score,
            correlation_bonus=correlation_bonus,
            citations=doc_result.citations,
            warnings=self._aggregate_warnings(doc_result, sensor_result),
            details={
                "document": doc_result,
                "sensor": sensor_result,
                "ontology": ontology_result
            }
        )

    def _determine_status(
        self, doc: float, sensor: float, ontology: float
    ) -> VerificationStatus:
        """검증 상태 결정"""
        threshold = 0.5

        doc_pass = doc >= threshold
        sensor_pass = sensor >= threshold
        ontology_pass = ontology >= threshold

        if doc_pass and sensor_pass and ontology_pass:
            return VerificationStatus.VERIFIED
        elif doc_pass and sensor_pass:
            return VerificationStatus.PARTIAL_BOTH
        elif doc_pass:
            return VerificationStatus.PARTIAL_DOC_ONLY
        elif sensor_pass:
            return VerificationStatus.PARTIAL_SENSOR_ONLY
        elif ontology_pass:
            return VerificationStatus.PARTIAL_ONTOLOGY_ONLY
        else:
            return VerificationStatus.INSUFFICIENT
```

---

## 5. 신뢰도 계산 공식

```
confidence = (doc_score × 0.50)      // 문서 검증 (50%)
           + (sensor_score × 0.30)    // 센서 검증 (30%)
           + (ontology_score × 0.15)  // 온톨로지 검증 (15%)
           + correlation_bonus        // 상관관계 보너스 (최대 5%)

최대 confidence = 1.0
```

---

## 6. 산출물

### 6.1 파일 목록

| 파일 | 내용 | Lines |
|------|------|-------|
| `src/rag/sensor_verifier.py` | 센서 검증기 | ~200 |
| `src/rag/ontology_verifier.py` | 온톨로지 검증기 | ~150 |
| `src/rag/verifier.py` | 통합 검증기 (확장) | ~250 |
| `tests/test_verifier_extended.py` | 단위 테스트 | 24개 |

### 6.2 테스트 결과

```
========================= test session starts ==========================
tests/test_verifier_extended.py::test_sensor_verification PASSED
tests/test_verifier_extended.py::test_ontology_verification PASSED
tests/test_verifier_extended.py::test_verified_status PASSED
tests/test_verifier_extended.py::test_partial_both_status PASSED
tests/test_verifier_extended.py::test_confidence_calculation PASSED
tests/test_verifier_extended.py::test_correlation_bonus PASSED
...
========================= 24 passed in 0.91s ===========================
```

---

## 7. 검증 체크리스트

- [x] SensorVerifier 구현
- [x] OntologyVerifier 구현
- [x] VerificationStatus 7단계 확장
- [x] 가중치 기반 신뢰도 계산
- [x] 상관관계 보너스 적용
- [x] 24개 단위 테스트 100% 통과

---

## 8. 다음 단계

→ [Phase 19: API/UI 확장](19_API_UI확장.md)

---

**Phase**: 18 / 19
**작성일**: 2026-01-22
