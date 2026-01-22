"""
센서 모듈

Axia80 센서 데이터 로드, 저장, 조회, 패턴 감지, 온톨로지 연결 기능을 제공합니다.

사용 예시:
    from src.sensor import SensorStore, PatternDetector, OntologyConnector

    # 센서 저장소 생성
    store = SensorStore()

    # 데이터 조회
    data = store.get_data(start=start_time, end=end_time)

    # 통계 조회
    stats = store.get_statistics("Fz")

    # 현재 상태 조회
    states = store.get_current_state()

    # 이상치 조회
    anomalies = store.get_anomalies("Fz", threshold=300)

    # 패턴 감지
    detector = PatternDetector(store)
    patterns = detector.detect_all()

    # 온톨로지 연결
    connector = OntologyConnector()
    errors = connector.map_pattern_to_errors(patterns[0])
    causes = connector.map_pattern_to_causes(patterns[0])
"""

from .data_loader import (
    DataLoader,
    load_sensor_data,
)
from .sensor_store import (
    SensorStore,
    create_sensor_store,
)
from .patterns import (
    PatternType,
    DetectedPattern,
    DEFAULT_ERROR_MAPPING,
)
from .pattern_detector import (
    PatternDetector,
    create_pattern_detector,
)
from .ontology_connector import (
    OntologyConnector,
    create_ontology_connector,
)

__all__ = [
    # DataLoader
    "DataLoader",
    "load_sensor_data",
    # SensorStore
    "SensorStore",
    "create_sensor_store",
    # Patterns
    "PatternType",
    "DetectedPattern",
    "DEFAULT_ERROR_MAPPING",
    # PatternDetector
    "PatternDetector",
    "create_pattern_detector",
    # OntologyConnector
    "OntologyConnector",
    "create_ontology_connector",
]
