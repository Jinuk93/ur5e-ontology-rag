"""
패턴 데이터 모델

감지된 패턴의 데이터 클래스를 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional


class PatternType(Enum):
    """패턴 타입"""
    COLLISION = "collision"    # 충돌 (급격한 피크)
    OVERLOAD = "overload"      # 과부하 (임계값 초과 지속)
    DRIFT = "drift"            # 드리프트 (baseline 이동)
    VIBRATION = "vibration"    # 진동 (표준편차 증가)


@dataclass
class DetectedPattern:
    """감지된 패턴"""
    pattern_id: str                                    # PAT-001, PAT-002, ...
    pattern_type: PatternType                          # 패턴 타입
    timestamp: datetime                                # 패턴 발생 시각
    duration_ms: int = 0                               # 지속 시간 (ms)
    confidence: float = 1.0                            # 신뢰도 (0.0 ~ 1.0)
    metrics: Dict[str, Any] = field(default_factory=dict)  # 패턴별 메트릭
    related_error_codes: List[str] = field(default_factory=list)  # 관련 에러 코드
    event_id: str = ""                                 # 이벤트 ID
    context: Dict[str, Any] = field(default_factory=dict)  # 컨텍스트 정보

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "confidence": self.confidence,
            "metrics": self.metrics,
            "related_error_codes": self.related_error_codes,
            "event_id": self.event_id,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectedPattern":
        """딕셔너리에서 생성"""
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            pattern_id=data["pattern_id"],
            pattern_type=PatternType(data["pattern_type"]),
            timestamp=timestamp,
            duration_ms=data.get("duration_ms", 0),
            confidence=data.get("confidence", 1.0),
            metrics=data.get("metrics", {}),
            related_error_codes=data.get("related_error_codes", []),
            event_id=data.get("event_id", ""),
            context=data.get("context", {}),
        )

    @property
    def duration_seconds(self) -> float:
        """지속 시간 (초)"""
        return self.duration_ms / 1000.0

    @property
    def duration_hours(self) -> float:
        """지속 시간 (시간)"""
        return self.duration_ms / (1000.0 * 3600.0)

    def __repr__(self) -> str:
        return (
            f"DetectedPattern(id={self.pattern_id}, "
            f"type={self.pattern_type.value}, "
            f"timestamp={self.timestamp.isoformat()}, "
            f"confidence={self.confidence:.2f})"
        )


# 패턴 타입별 관련 에러 코드 기본 매핑
DEFAULT_ERROR_MAPPING = {
    PatternType.COLLISION: ["C153", "C119"],  # 보호 정지, 관절 위치 이탈
    PatternType.OVERLOAD: ["C189"],            # 과부하 감지
    PatternType.DRIFT: [],                     # 경고 수준, 에러 코드 없음
    PatternType.VIBRATION: [],                 # 경고 수준, 에러 코드 없음
}
