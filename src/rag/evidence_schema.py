"""
Evidence 스키마 정의

질의 응답의 근거(Evidence)를 표현하는 데이터 모델을 제공합니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class QueryType(str, Enum):
    """질문 유형"""
    ONTOLOGY = "ontology"   # 온톨로지성 질문 (관계/맥락 추론 필요)
    HYBRID = "hybrid"       # 하이브리드 질문 (온톨로지 + 문서)
    RAG = "rag"            # 일반 RAG 질문 (문서 검색만)


@dataclass
class DocumentReference:
    """문서 참조"""
    doc_id: str             # 문서 ID (예: "service_manual")
    page: Optional[int] = None      # 페이지 번호
    chunk_id: Optional[str] = None  # 청크 ID (예: "SM-045-01")
    relevance: float = 1.0  # 관련도 (0.0 ~ 1.0)
    snippet: str = ""       # 관련 텍스트 스니펫

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "doc_id": self.doc_id,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "relevance": self.relevance,
            "snippet": self.snippet,
        }


@dataclass
class OntologyPath:
    """온톨로지 경로 (추론 근거)"""
    path: List[str]         # 경로 노드 리스트 (예: ["Fz", "CRITICAL", "PAT_OVERLOAD", "C189"])
    relations: List[str]    # 관계 리스트 (예: ["HAS_STATE", "INDICATES", "TRIGGERS"])
    confidence: float = 1.0
    description: str = ""   # 경로 설명

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "path": self.path,
            "relations": self.relations,
            "confidence": self.confidence,
            "description": self.description,
            "path_string": self._format_path_string(),
        }

    def _format_path_string(self) -> str:
        """경로 문자열 포맷"""
        if not self.path:
            return ""
        result = self.path[0]
        for i, rel in enumerate(self.relations):
            if i + 1 < len(self.path):
                result += f" --[{rel}]--> {self.path[i + 1]}"
        return result


@dataclass
class Evidence:
    """질의 응답 근거"""
    ontology_paths: List[OntologyPath] = field(default_factory=list)
    document_refs: List[DocumentReference] = field(default_factory=list)
    similar_events: List[str] = field(default_factory=list)  # 유사 이벤트 ID
    sensor_data: Optional[Dict[str, Any]] = None  # 관련 센서 데이터

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "ontology_paths": [p.to_dict() for p in self.ontology_paths],
            "document_refs": [d.to_dict() for d in self.document_refs],
            "similar_events": self.similar_events,
            "sensor_data": self.sensor_data,
        }

    def add_ontology_path(self, path: OntologyPath) -> None:
        """온톨로지 경로 추가"""
        self.ontology_paths.append(path)

    def add_document_ref(self, ref: DocumentReference) -> None:
        """문서 참조 추가"""
        self.document_refs.append(ref)

    def has_evidence(self) -> bool:
        """근거가 있는지 확인"""
        return bool(self.ontology_paths or self.document_refs)

    @property
    def primary_path(self) -> Optional[OntologyPath]:
        """주요 온톨로지 경로 (가장 높은 신뢰도)"""
        if not self.ontology_paths:
            return None
        return max(self.ontology_paths, key=lambda x: x.confidence)


@dataclass
class ExtractedEntity:
    """추출된 엔티티"""
    text: str               # 원본 텍스트 (예: "Fz", "-350N")
    entity_id: str          # 온톨로지 엔티티 ID (예: "Fz", "CRITICAL")
    entity_type: str        # 엔티티 타입 (예: "MeasurementAxis", "Value")
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "text": self.text,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "confidence": self.confidence,
            "properties": self.properties,
        }


@dataclass
class ClassificationResult:
    """질문 분류 결과"""
    query: str              # 원본 질문
    query_type: QueryType   # 분류된 유형
    confidence: float       # 분류 신뢰도
    entities: List[ExtractedEntity] = field(default_factory=list)  # 추출된 엔티티
    indicators: List[str] = field(default_factory=list)  # 분류 근거 지표
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "query": self.query,
            "query_type": self.query_type.value,
            "confidence": self.confidence,
            "entities": [e.to_dict() for e in self.entities],
            "indicators": self.indicators,
            "metadata": self.metadata,
        }

    def has_entities(self) -> bool:
        """엔티티가 추출되었는지 확인"""
        return bool(self.entities)

    def get_entities_by_type(self, entity_type: str) -> List[ExtractedEntity]:
        """타입별 엔티티 조회"""
        return [e for e in self.entities if e.entity_type == entity_type]
