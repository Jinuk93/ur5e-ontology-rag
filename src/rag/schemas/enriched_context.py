# ============================================================
# src/rag/schemas/enriched_context.py - 통합 컨텍스트 스키마
# ============================================================
# Main-S3에서 구현
#
# ContextEnricher가 반환하는 데이터 구조를 정의합니다.
# 문서 증거 + 센서 증거 + 상관관계 분석 결과를 포함합니다.
# ============================================================

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# [1] 상관관계 레벨 Enum
# ============================================================

class CorrelationLevel(str, Enum):
    """상관관계 레벨"""
    STRONG = "STRONG"       # 문서 + 센서 모두 지지
    MODERATE = "MODERATE"   # 한쪽만 확인
    WEAK = "WEAK"           # 관련 가능성
    NONE = "NONE"           # 센서 데이터 없음/무관


# ============================================================
# [2] 축별 통계 데이터클래스
# ============================================================

@dataclass
class AxisStats:
    """
    축별 통계

    Attributes:
        mean: 평균값
        std: 표준편차
        min: 최소값
        max: 최대값
    """
    mean: float
    std: float
    min: float
    max: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "AxisStats":
        return cls(
            mean=data.get("mean", 0.0),
            std=data.get("std", 0.0),
            min=data.get("min", 0.0),
            max=data.get("max", 0.0)
        )


# ============================================================
# [3] 문서 증거 데이터클래스
# ============================================================

@dataclass
class DocEvidence:
    """
    문서 증거

    Attributes:
        chunk_id: 청크 ID
        content: 청크 내용
        score: 유사도 점수
        source: 문서명
        page: 페이지 번호 (옵션)
        section: 섹션명 (옵션)
    """
    chunk_id: str
    content: str
    score: float
    source: str
    page: Optional[int] = None
    section: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "page": self.page,
            "section": self.section
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocEvidence":
        return cls(
            chunk_id=data.get("chunk_id", ""),
            content=data.get("content", ""),
            score=data.get("score", 0.0),
            source=data.get("source", ""),
            page=data.get("page"),
            section=data.get("section")
        )

    @classmethod
    def from_retrieval_result(cls, result: Dict[str, Any]) -> "DocEvidence":
        """검색 결과에서 DocEvidence 생성"""
        return cls(
            chunk_id=result.get("chunk_id", result.get("id", "")),
            content=result.get("content", result.get("text", "")),
            score=result.get("score", result.get("similarity", 0.0)),
            source=result.get("source", result.get("doc_id", "")),
            page=result.get("page"),
            section=result.get("section")
        )


# ============================================================
# [4] 센서 증거 데이터클래스
# ============================================================

@dataclass
class SensorEvidence:
    """
    센서 증거

    Attributes:
        patterns: 감지된 패턴 목록
        statistics: 축별 통계 (Dict[axis, AxisStats])
        time_range: 조회 시간 범위 (start, end)
        has_anomaly: 이상 패턴 존재 여부
    """
    patterns: List[Dict[str, Any]]
    statistics: Dict[str, AxisStats]
    time_range: Tuple[datetime, datetime]
    has_anomaly: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patterns": self.patterns,
            "statistics": {
                axis: stats.to_dict()
                for axis, stats in self.statistics.items()
            },
            "time_range": {
                "start": self.time_range[0].isoformat(),
                "end": self.time_range[1].isoformat()
            },
            "has_anomaly": self.has_anomaly
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SensorEvidence":
        time_range_data = data.get("time_range", {})
        start = datetime.fromisoformat(time_range_data.get("start", datetime.now().isoformat()))
        end = datetime.fromisoformat(time_range_data.get("end", datetime.now().isoformat()))

        stats = {}
        for axis, stat_data in data.get("statistics", {}).items():
            stats[axis] = AxisStats.from_dict(stat_data)

        return cls(
            patterns=data.get("patterns", []),
            statistics=stats,
            time_range=(start, end),
            has_anomaly=data.get("has_anomaly", False)
        )


# ============================================================
# [5] 상관관계 결과 데이터클래스
# ============================================================

@dataclass
class CorrelationResult:
    """
    상관관계 분석 결과

    Attributes:
        level: 상관관계 레벨 (STRONG, MODERATE, WEAK, NONE)
        confidence: 신뢰도 (0.0 ~ 1.0)
        reason: 판정 근거 설명
        supporting_evidence: 지지 증거 목록
    """
    level: CorrelationLevel
    confidence: float
    reason: str
    supporting_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "supporting_evidence": self.supporting_evidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorrelationResult":
        level_str = data.get("level", "NONE")
        try:
            level = CorrelationLevel(level_str)
        except ValueError:
            level = CorrelationLevel.NONE

        return cls(
            level=level,
            confidence=data.get("confidence", 0.0),
            reason=data.get("reason", ""),
            supporting_evidence=data.get("supporting_evidence", [])
        )

    @property
    def is_strong(self) -> bool:
        return self.level == CorrelationLevel.STRONG

    @property
    def has_sensor_support(self) -> bool:
        return self.level in (CorrelationLevel.STRONG, CorrelationLevel.MODERATE)


# ============================================================
# [6] 통합 컨텍스트 데이터클래스
# ============================================================

@dataclass
class EnrichedContext:
    """
    통합 컨텍스트

    문서 증거 + 센서 증거 + 상관관계 분석 결과를 통합합니다.

    Attributes:
        doc_evidence: 문서 증거 목록
        sensor_evidence: 센서 증거 (옵션)
        correlation: 상관관계 분석 결과
        error_code: 관련 에러코드 (옵션)
        query: 원본 쿼리
    """
    doc_evidence: List[DocEvidence]
    sensor_evidence: Optional[SensorEvidence]
    correlation: CorrelationResult
    error_code: Optional[str] = None
    query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_evidence": [d.to_dict() for d in self.doc_evidence],
            "sensor_evidence": self.sensor_evidence.to_dict() if self.sensor_evidence else None,
            "correlation": self.correlation.to_dict(),
            "error_code": self.error_code,
            "query": self.query
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnrichedContext":
        doc_evidence = [
            DocEvidence.from_dict(d)
            for d in data.get("doc_evidence", [])
        ]

        sensor_evidence = None
        if data.get("sensor_evidence"):
            sensor_evidence = SensorEvidence.from_dict(data["sensor_evidence"])

        correlation = CorrelationResult.from_dict(data.get("correlation", {}))

        return cls(
            doc_evidence=doc_evidence,
            sensor_evidence=sensor_evidence,
            correlation=correlation,
            error_code=data.get("error_code"),
            query=data.get("query", "")
        )

    @property
    def has_doc_evidence(self) -> bool:
        return len(self.doc_evidence) > 0

    @property
    def has_sensor_evidence(self) -> bool:
        return self.sensor_evidence is not None and self.sensor_evidence.has_anomaly

    @property
    def evidence_summary(self) -> str:
        """증거 요약 문자열"""
        parts = []
        if self.has_doc_evidence:
            parts.append(f"문서 {len(self.doc_evidence)}건")
        if self.has_sensor_evidence:
            parts.append(f"센서 패턴 {len(self.sensor_evidence.patterns)}건")
        return ", ".join(parts) if parts else "증거 없음"
