# ============================================================
# src/rag/__init__.py - RAG 패키지
# ============================================================

# Phase 5: 기본 RAG
from .retriever import Retriever, RetrievalResult
from .prompt_builder import PromptBuilder
from .generator import Generator

# Phase 6: 온톨로지 추론
from .query_analyzer import QueryAnalyzer, QueryAnalysis
from .graph_retriever import GraphRetriever, GraphResult
from .hybrid_retriever import HybridRetriever, HybridResult

# Phase 7: Verifier (검증)
from .verifier import Verifier, VerificationResult, VerificationStatus

# Main-S5: Sensor/Ontology Verifier (센서 검증)
from .sensor_verifier import SensorVerifier, SensorVerificationResult
from .ontology_verifier import OntologyVerifier, OntologyVerificationResult

# Main-S3: Context Enricher (센서 통합)
from .context_enricher import ContextEnricher, get_context_enricher
from .schemas.enriched_context import (
    EnrichedContext,
    DocEvidence,
    SensorEvidence,
    AxisStats,
    CorrelationResult,
    CorrelationLevel,
)

__all__ = [
    # Phase 5
    "Retriever",
    "RetrievalResult",
    "PromptBuilder",
    "Generator",
    # Phase 6
    "QueryAnalyzer",
    "QueryAnalysis",
    "GraphRetriever",
    "GraphResult",
    "HybridRetriever",
    "HybridResult",
    # Phase 7
    "Verifier",
    "VerificationResult",
    "VerificationStatus",
    # Main-S5: Sensor/Ontology Verifier
    "SensorVerifier",
    "SensorVerificationResult",
    "OntologyVerifier",
    "OntologyVerificationResult",
    # Main-S3
    "ContextEnricher",
    "get_context_enricher",
    "EnrichedContext",
    "DocEvidence",
    "SensorEvidence",
    "AxisStats",
    "CorrelationResult",
    "CorrelationLevel",
]
