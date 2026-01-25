"""
프로젝트 설정 관리 모듈

환경변수(.env)와 설정 파일(configs/settings.yaml)을 통합 로딩하여
타입 안전한 설정 객체를 제공합니다.

사용 예시:
    from src.config import get_settings
    settings = get_settings()
    print(settings.openai_api_key)
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class DocumentSettings:
    """문서 처리 설정"""
    chunk_size: int = 512
    chunk_overlap: int = 50


@dataclass
class EmbeddingSettings:
    """임베딩 설정"""
    model: str = "text-embedding-3-small"
    batch_size: int = 100


@dataclass
class RetrievalSettings:
    """검색 설정"""
    top_k: int = 5
    similarity_threshold: float = 0.7


@dataclass
class LLMSettings:
    """LLM 설정"""
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 1024


@dataclass
class VerifierSettings:
    """검증기 설정"""
    require_citation_for_action: bool = True
    min_evidence_score: float = 0.7
    max_graph_hops: int = 3


@dataclass
class APISettings:
    """API 서버 설정"""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True


@dataclass
class LoggingSettings:
    """로깅 설정"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class SupervisorTargetsSettings:
    """관리 감독자 대시보드 목표치(운영 기준)"""
    # 정상 운영률 목표(%)
    normal_rate_min: float = 90.0

    # 힘 크기(|F|) 분포 목표(N)
    force_magnitude_p95_max: float = 90.0
    force_magnitude_mean_max: float = 60.0

    # Fz 분포 목표(N)
    fz_p95_max_abs: float = 120.0

    # 이벤트 운영 목표(일 평균)
    events_daily_max: float = 2.0
    collision_daily_max: float = 0.5
    overload_daily_max: float = 0.5
    drift_daily_max: float = 0.3

    # MTBE 목표(분)
    mtbe_min_minutes: float = 60.0

    # 미해결 이벤트 백로그 허용치
    unresolved_events_max: int = 5


@dataclass
class PathSettings:
    """경로 설정"""
    project_root: Path = field(default_factory=lambda: PROJECT_ROOT)
    data_raw_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "raw" / "pdf")
    data_processed_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "processed")
    chunks_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "processed" / "chunks")
    ontology_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "processed" / "ontology")
    sensor_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "sensor")
    benchmark_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "benchmark")
    configs_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "configs")
    prompts_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "prompts")
    stores_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "stores")
    chroma_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "stores" / "chroma")
    neo4j_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "stores" / "neo4j")


@dataclass
class Settings:
    """
    프로젝트 전체 설정

    환경변수와 설정 파일을 통합하여 관리합니다.
    """
    # 환경변수 (민감 정보)
    openai_api_key: str = ""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # 설정 파일에서 로드
    document: DocumentSettings = field(default_factory=DocumentSettings)
    embedding: EmbeddingSettings = field(default_factory=EmbeddingSettings)
    retrieval: RetrievalSettings = field(default_factory=RetrievalSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    verifier: VerifierSettings = field(default_factory=VerifierSettings)
    api: APISettings = field(default_factory=APISettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    supervisor_targets: SupervisorTargetsSettings = field(default_factory=SupervisorTargetsSettings)
    paths: PathSettings = field(default_factory=PathSettings)


def _load_yaml_settings(settings_path: Path) -> dict:
    """YAML 설정 파일 로드"""
    if not settings_path.exists():
        return {}

    with open(settings_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _create_settings() -> Settings:
    """설정 객체 생성"""
    # .env 파일 로드
    load_dotenv(PROJECT_ROOT / ".env")

    # YAML 설정 로드
    yaml_config = _load_yaml_settings(PROJECT_ROOT / "configs" / "settings.yaml")

    # 환경변수에서 민감 정보 로드
    settings = Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
    )

    # YAML 설정 적용
    if "document" in yaml_config:
        settings.document = DocumentSettings(**yaml_config["document"])

    if "embedding" in yaml_config:
        settings.embedding = EmbeddingSettings(**yaml_config["embedding"])

    if "retrieval" in yaml_config:
        settings.retrieval = RetrievalSettings(**yaml_config["retrieval"])

    if "llm" in yaml_config:
        settings.llm = LLMSettings(**yaml_config["llm"])

    if "verifier" in yaml_config:
        settings.verifier = VerifierSettings(**yaml_config["verifier"])

    if "api" in yaml_config:
        settings.api = APISettings(**yaml_config["api"])

    if "logging" in yaml_config:
        settings.logging = LoggingSettings(**yaml_config["logging"])

    if "supervisor_targets" in yaml_config:
        settings.supervisor_targets = SupervisorTargetsSettings(**yaml_config["supervisor_targets"])

    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    설정 객체 반환 (싱글톤)

    처음 호출 시 설정을 로드하고, 이후 호출에서는 캐시된 객체를 반환합니다.

    Returns:
        Settings: 프로젝트 설정 객체

    Example:
        >>> settings = get_settings()
        >>> print(settings.llm.model)
        'gpt-4o-mini'
    """
    return _create_settings()


def reload_settings() -> Settings:
    """
    설정 다시 로드

    캐시를 무효화하고 설정을 다시 로드합니다.
    주로 테스트나 동적 설정 변경 시 사용합니다.

    Returns:
        Settings: 새로 로드된 설정 객체
    """
    get_settings.cache_clear()
    return get_settings()


# 모듈 로드 시 설정 검증
if __name__ == "__main__":
    settings = get_settings()
    print("=== Settings Loaded ===")
    print(f"Project Root: {settings.paths.project_root}")
    print(f"OpenAI API Key: {'SET' if settings.openai_api_key else 'NOT SET'}")
    print(f"Neo4j URI: {settings.neo4j_uri}")
    print(f"LLM Model: {settings.llm.model}")
    print(f"Embedding Model: {settings.embedding.model}")
    print(f"Chunk Size: {settings.document.chunk_size}")
    print(f"Top K: {settings.retrieval.top_k}")
