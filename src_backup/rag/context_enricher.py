# ============================================================
# src/rag/context_enricher.py - 컨텍스트 인리처
# ============================================================
# Main-S3에서 구현
#
# 문서 검색 결과에 센서 맥락을 추가합니다.
# 에러코드 기반으로 관련 센서 패턴을 조회하고,
# 문서 증거와 센서 증거 간의 상관관계를 분석합니다.
# ============================================================

import logging
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.rag.schemas.enriched_context import (
    EnrichedContext,
    DocEvidence,
    SensorEvidence,
    AxisStats,
    CorrelationResult,
    CorrelationLevel,
)
from src.sensor.pattern_detector import PatternDetector, DetectedPattern
from src.sensor.sensor_store import SensorStore

logger = logging.getLogger(__name__)


class ContextEnricher:
    """
    컨텍스트 인리처

    문서 검색 결과에 센서 맥락을 추가합니다.

    사용 예시:
        enricher = ContextEnricher()
        enriched = enricher.enrich(
            query="C153 에러 원인",
            doc_chunks=[{"chunk_id": "...", "content": "...", "score": 0.9}],
            error_code="C153",
            reference_time=datetime(2024, 1, 17, 14, 0)
        )
    """

    def __init__(
        self,
        sensor_store: Optional[SensorStore] = None,
        pattern_detector: Optional[PatternDetector] = None,
        mapping_path: str = "configs/error_pattern_mapping.yaml"
    ):
        """
        Args:
            sensor_store: 센서 데이터 저장소 (None이면 기본 생성)
            pattern_detector: 패턴 감지기 (None이면 기본 생성)
            mapping_path: 에러-패턴 매핑 설정 파일 경로
        """
        self.sensor_store = sensor_store or SensorStore()
        self.pattern_detector = pattern_detector or PatternDetector()
        self.mapping = self._load_mapping(mapping_path)

        # 센서 데이터 로드 상태
        self._sensor_loaded = False

    def _load_mapping(self, path: str) -> Dict:
        """매핑 설정 로드"""
        mapping_path = Path(path)
        if mapping_path.exists():
            with open(mapping_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return self._default_mapping()

    def _default_mapping(self) -> Dict:
        """기본 매핑"""
        return {
            "error_to_pattern": {
                "C153": {"expected_patterns": ["collision"]},
                "C119": {"expected_patterns": ["collision"]},
                "C189": {"expected_patterns": ["overload"]},
                "C204": {"expected_patterns": ["vibration"]},
            },
            "time_windows": {
                "default": "1h",
                "collision": "30m",
                "vibration": "2h",
                "overload": "1h",
                "drift": "4h",
            }
        }

    # --------------------------------------------------------
    # [1] 메인 Enrich 메서드
    # --------------------------------------------------------

    def enrich(
        self,
        query: str,
        doc_chunks: List[Dict[str, Any]],
        error_code: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        time_window: Optional[str] = None
    ) -> EnrichedContext:
        """
        문서 청크에 센서 맥락 추가

        Args:
            query: 사용자 질문
            doc_chunks: 검색된 문서 청크 목록
            error_code: 관련 에러코드
            reference_time: 기준 시점 (None이면 최신 데이터 기준)
            time_window: 조회 시간 윈도우 (예: "1h", "30m")

        Returns:
            EnrichedContext: 통합 컨텍스트
        """
        logger.info(f"Enriching context for query: {query[:50]}... error_code={error_code}")

        # 1. 문서 증거 변환
        doc_evidence = self._convert_doc_chunks(doc_chunks)

        # 2. 센서 증거 조회
        sensor_evidence = self._get_sensor_evidence(
            error_code=error_code,
            reference_time=reference_time,
            time_window=time_window
        )

        # 3. 문서에서 원인 추출
        doc_causes = self._extract_causes_from_docs(doc_evidence)

        # 4. 상관관계 분석
        patterns = sensor_evidence.patterns if sensor_evidence else []
        correlation = self.analyze_correlation(
            error_code=error_code,
            patterns=patterns,
            doc_causes=doc_causes
        )

        # 5. 통합 컨텍스트 생성
        enriched = EnrichedContext(
            doc_evidence=doc_evidence,
            sensor_evidence=sensor_evidence,
            correlation=correlation,
            error_code=error_code,
            query=query
        )

        logger.info(f"Enrichment complete: {enriched.evidence_summary}, correlation={correlation.level.value}")
        return enriched

    # --------------------------------------------------------
    # [2] 문서 증거 변환
    # --------------------------------------------------------

    def _convert_doc_chunks(self, doc_chunks: List[Dict[str, Any]]) -> List[DocEvidence]:
        """문서 청크를 DocEvidence로 변환"""
        evidence_list = []

        for chunk in doc_chunks:
            try:
                evidence = DocEvidence.from_retrieval_result(chunk)
                evidence_list.append(evidence)
            except Exception as e:
                logger.warning(f"Failed to convert chunk: {e}")
                continue

        return evidence_list

    def _extract_causes_from_docs(self, doc_evidence: List[DocEvidence]) -> List[str]:
        """문서 증거에서 원인 키워드 추출"""
        causes = []

        # 원인 관련 키워드
        cause_keywords = [
            "원인", "cause", "reason", "because", "due to",
            "발생", "occur", "result", "문제", "problem"
        ]

        for doc in doc_evidence:
            content_lower = doc.content.lower()
            for keyword in cause_keywords:
                if keyword in content_lower:
                    # 간단한 원인 추출 (해당 문장 추출)
                    causes.append(doc.content[:200])  # 처음 200자
                    break

        return causes[:3]  # 최대 3개

    # --------------------------------------------------------
    # [3] 센서 증거 조회
    # --------------------------------------------------------

    def _get_sensor_evidence(
        self,
        error_code: Optional[str],
        reference_time: Optional[datetime],
        time_window: Optional[str]
    ) -> Optional[SensorEvidence]:
        """센서 데이터에서 증거 조회"""

        # 센서 데이터 로드 (최초 1회)
        if not self._sensor_loaded:
            try:
                self.sensor_store.load_data()
                self._sensor_loaded = True
            except FileNotFoundError:
                logger.warning("Sensor data not found, skipping sensor evidence")
                return None
            except Exception as e:
                logger.error(f"Failed to load sensor data: {e}")
                return None

        # 시간 윈도우 결정
        if time_window is None:
            time_window = self._get_time_window_for_error(error_code)

        # 기준 시간 결정
        if reference_time is None:
            # 센서 데이터의 마지막 시점 사용
            df = self.sensor_store.get_data()
            if df is not None and len(df) > 0:
                reference_time = df["timestamp"].max().to_pydatetime()
            else:
                reference_time = datetime.now()

        # 시간 범위 계산
        window_delta = self._parse_time_window(time_window)
        start_time = reference_time - window_delta
        end_time = reference_time

        try:
            # 데이터 조회
            df = self.sensor_store.get_data(
                start=start_time.isoformat(),
                end=end_time.isoformat()
            )

            if df is None or len(df) == 0:
                logger.info(f"No sensor data found for time range: {start_time} ~ {end_time}")
                return None

            # 패턴 조회 (기 감지된 패턴에서)
            patterns = self._get_patterns_in_range(start_time, end_time, error_code)

            # 통계 계산
            statistics = self._calculate_statistics(df)

            # SensorEvidence 생성
            return SensorEvidence(
                patterns=patterns,
                statistics=statistics,
                time_range=(start_time, end_time),
                has_anomaly=len(patterns) > 0
            )

        except Exception as e:
            logger.error(f"Failed to get sensor evidence: {e}")
            return None

    def _get_patterns_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        error_code: Optional[str]
    ) -> List[Dict[str, Any]]:
        """시간 범위 내 패턴 조회"""
        patterns = []

        try:
            # 에러코드로 패턴 조회
            if error_code:
                stored_patterns = self.sensor_store.get_patterns(error_code=error_code)
            else:
                stored_patterns = self.sensor_store.load_patterns()

            # 시간 범위 필터링
            for p in stored_patterns:
                ts = p.get("timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)

                if start_time <= ts <= end_time:
                    patterns.append(p)

        except Exception as e:
            logger.warning(f"Failed to get patterns: {e}")

        return patterns

    def _calculate_statistics(self, df) -> Dict[str, AxisStats]:
        """축별 통계 계산"""
        stats = {}
        axes = ["Fx", "Fy", "Fz", "Tx", "Ty", "Tz"]

        for axis in axes:
            if axis in df.columns:
                stats[axis] = AxisStats(
                    mean=float(df[axis].mean()),
                    std=float(df[axis].std()),
                    min=float(df[axis].min()),
                    max=float(df[axis].max())
                )

        return stats

    def _get_time_window_for_error(self, error_code: Optional[str]) -> str:
        """에러코드에 맞는 시간 윈도우 반환"""
        if not error_code:
            return self.mapping.get("time_windows", {}).get("default", "1h")

        # 에러코드 → 예상 패턴 → 시간 윈도우
        error_mapping = self.mapping.get("error_to_pattern", {})
        if error_code in error_mapping:
            expected_patterns = error_mapping[error_code].get("expected_patterns", [])
            if expected_patterns:
                pattern_type = expected_patterns[0]
                return self.mapping.get("time_windows", {}).get(pattern_type, "1h")

        return self.mapping.get("time_windows", {}).get("default", "1h")

    def _parse_time_window(self, window: str) -> timedelta:
        """시간 윈도우 파싱"""
        unit = window[-1].lower()
        value = int(window[:-1])

        if unit == "s":
            return timedelta(seconds=value)
        elif unit == "m":
            return timedelta(minutes=value)
        elif unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)
        return timedelta(hours=1)

    # --------------------------------------------------------
    # [4] 상관관계 분석
    # --------------------------------------------------------

    def analyze_correlation(
        self,
        error_code: Optional[str],
        patterns: List[Any],
        doc_causes: List[str]
    ) -> CorrelationResult:
        """
        에러코드-패턴-문서원인 간 상관관계 분석

        Args:
            error_code: 에러코드
            patterns: 감지된 센서 패턴 (list of dict or DetectedPattern)
            doc_causes: 문서에서 추출한 원인 목록

        Returns:
            CorrelationResult: 상관관계 분석 결과
        """
        # 패턴을 dict로 변환
        pattern_dicts = []
        for p in patterns:
            if isinstance(p, DetectedPattern):
                pattern_dicts.append(p.to_dict())
            elif isinstance(p, dict):
                pattern_dicts.append(p)

        # 상관관계 레벨 결정
        level, confidence, reason = self._determine_correlation_level(
            error_code=error_code,
            patterns=pattern_dicts,
            doc_causes=doc_causes
        )

        # 지지 증거 수집
        supporting_evidence = []
        if doc_causes:
            supporting_evidence.append(f"문서 원인 {len(doc_causes)}건 확인")
        if pattern_dicts:
            pattern_types = set(p.get("pattern_type", "unknown") for p in pattern_dicts)
            supporting_evidence.append(f"센서 패턴 감지: {', '.join(pattern_types)}")

        return CorrelationResult(
            level=level,
            confidence=confidence,
            reason=reason,
            supporting_evidence=supporting_evidence
        )

    def _determine_correlation_level(
        self,
        error_code: Optional[str],
        patterns: List[Dict],
        doc_causes: List[str]
    ) -> Tuple[CorrelationLevel, float, str]:
        """상관관계 레벨 결정"""

        # 센서 데이터 없음
        if not patterns:
            if doc_causes:
                return (
                    CorrelationLevel.MODERATE,
                    0.70,
                    "문서 원인 확인, 센서 패턴 없음"
                )
            return (
                CorrelationLevel.NONE,
                0.0,
                "센서 데이터 없음"
            )

        # 에러코드가 없는 경우
        if not error_code:
            if patterns:
                pattern_type = patterns[0].get("pattern_type", "unknown")
                return (
                    CorrelationLevel.WEAK,
                    0.55,
                    f"에러코드 없음, {pattern_type} 패턴 감지"
                )
            return (CorrelationLevel.NONE, 0.0, "분석 대상 없음")

        # 에러코드 → 예상 패턴 매핑
        expected_patterns = self._get_expected_patterns(error_code)

        # 매칭되는 패턴 찾기
        matching_patterns = [
            p for p in patterns
            if p.get("pattern_type") in expected_patterns
        ]

        # 신뢰도 부스트
        confidence_boost = self._get_confidence_boost(error_code)

        if matching_patterns and doc_causes:
            # 문서 + 센서 모두 일치 → STRONG
            pattern_type = matching_patterns[0].get("pattern_type")
            return (
                CorrelationLevel.STRONG,
                min(1.0, 0.85 + confidence_boost),
                f"문서 원인 확인 + {pattern_type} 패턴 감지"
            )

        elif matching_patterns:
            # 센서 패턴만 일치 → MODERATE
            pattern_type = matching_patterns[0].get("pattern_type")
            return (
                CorrelationLevel.MODERATE,
                min(1.0, 0.70 + confidence_boost),
                f"{pattern_type} 패턴 감지, 문서 원인 미확인"
            )

        elif doc_causes:
            # 문서 원인만 있음 → MODERATE
            return (
                CorrelationLevel.MODERATE,
                0.70,
                "문서 원인 확인, 예상 센서 패턴 미감지"
            )

        elif patterns:
            # 다른 패턴 있음 → WEAK
            pattern_type = patterns[0].get("pattern_type", "unknown")
            return (
                CorrelationLevel.WEAK,
                0.55,
                f"예상 외 패턴 감지: {pattern_type}"
            )

        return (CorrelationLevel.WEAK, 0.50, "관련 패턴 없음")

    def _get_expected_patterns(self, error_code: str) -> List[str]:
        """에러코드에서 예상 패턴 목록 조회"""
        error_mapping = self.mapping.get("error_to_pattern", {})
        if error_code in error_mapping:
            return error_mapping[error_code].get("expected_patterns", [])
        return []

    def _get_confidence_boost(self, error_code: str) -> float:
        """에러코드별 신뢰도 부스트 조회"""
        error_mapping = self.mapping.get("error_to_pattern", {})
        if error_code in error_mapping:
            return error_mapping[error_code].get("confidence_boost", 0.0)
        return 0.0


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_context_enricher: Optional[ContextEnricher] = None


def get_context_enricher() -> ContextEnricher:
    """ContextEnricher 싱글톤 반환"""
    global _context_enricher
    if _context_enricher is None:
        _context_enricher = ContextEnricher()
    return _context_enricher


# ============================================================
# CLI 테스트
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ContextEnricher Test")
    print("=" * 60)

    enricher = ContextEnricher()

    # 테스트 문서 청크
    test_chunks = [
        {
            "chunk_id": "ec_15_001",
            "content": "C153: Safety Stop - 충돌 감지로 인한 정지. 원인: 물리적 접촉",
            "score": 0.92,
            "source": "error_codes"
        }
    ]

    print("\n[1] Testing with error code C153...")
    result = enricher.enrich(
        query="C153 에러 원인",
        doc_chunks=test_chunks,
        error_code="C153"
    )

    print(f"    Doc evidence: {len(result.doc_evidence)}건")
    print(f"    Sensor evidence: {'있음' if result.sensor_evidence else '없음'}")
    print(f"    Correlation: {result.correlation.level.value}")
    print(f"    Confidence: {result.correlation.confidence:.2f}")
    print(f"    Reason: {result.correlation.reason}")

    print("\n[2] Testing without error code...")
    result2 = enricher.enrich(
        query="로봇 작업 반경",
        doc_chunks=[{"chunk_id": "um_001", "content": "작업반경 850mm", "score": 0.8, "source": "user_manual"}],
        error_code=None
    )
    print(f"    Correlation: {result2.correlation.level.value}")

    print("\n" + "=" * 60)
    print("[OK] ContextEnricher test completed!")
    print("=" * 60)
