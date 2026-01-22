"""
온톨로지 데이터 모델

Entity, Relationship 데이터 클래스를 정의합니다.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .schema import Domain, EntityType, RelationType, get_domain_for_entity_type


@dataclass
class Entity:
    """온톨로지 엔티티"""
    id: str                     # 엔티티 ID (예: "UR5e", "Fz", "C153")
    type: EntityType            # 엔티티 타입
    name: str                   # 표시 이름
    domain: Optional[Domain] = None  # 소속 도메인 (자동 설정)
    properties: Dict[str, Any] = field(default_factory=dict)  # 속성

    def __post_init__(self):
        """초기화 후 처리"""
        if self.domain is None:
            self.domain = get_domain_for_entity_type(self.type)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "type": self.type.value,
            "domain": self.domain.value,
            "name": self.name,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """딕셔너리에서 생성"""
        return cls(
            id=data["id"],
            type=EntityType(data["type"]),
            name=data["name"],
            domain=Domain(data["domain"]) if "domain" in data else None,
            properties=data.get("properties", {}),
        )


@dataclass
class Relationship:
    """온톨로지 관계"""
    source: str                 # 소스 엔티티 ID
    relation: RelationType      # 관계 타입
    target: str                 # 타겟 엔티티 ID
    properties: Dict[str, Any] = field(default_factory=dict)  # 속성 (confidence 등)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        result = {
            "source": self.source,
            "relation": self.relation.value,
            "target": self.target,
        }
        if self.properties:
            result["properties"] = self.properties
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        """딕셔너리에서 생성"""
        return cls(
            source=data["source"],
            relation=RelationType(data["relation"]),
            target=data["target"],
            properties=data.get("properties", {}),
        )


@dataclass
class OntologySchema:
    """온톨로지 스키마"""
    version: str
    description: str
    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        """엔티티 추가"""
        self.entities.append(entity)

    def add_relationship(self, relationship: Relationship) -> None:
        """관계 추가"""
        self.relationships.append(relationship)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """ID로 엔티티 조회"""
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """타입별 엔티티 조회"""
        return [e for e in self.entities if e.type == entity_type]

    def get_entities_by_domain(self, domain: Domain) -> List[Entity]:
        """도메인별 엔티티 조회"""
        return [e for e in self.entities if e.domain == domain]

    def get_relationships_for_entity(
        self,
        entity_id: str,
        direction: str = "both"
    ) -> List[Relationship]:
        """엔티티의 관계 조회

        Args:
            entity_id: 엔티티 ID
            direction: "outgoing", "incoming", "both"
        """
        result = []
        for rel in self.relationships:
            if direction in ("outgoing", "both") and rel.source == entity_id:
                result.append(rel)
            if direction in ("incoming", "both") and rel.target == entity_id:
                result.append(rel)
        return result

    def get_relationships_by_type(
        self,
        relation_type: RelationType
    ) -> List[Relationship]:
        """타입별 관계 조회"""
        return [r for r in self.relationships if r.relation == relation_type]

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "version": self.version,
            "description": self.description,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OntologySchema":
        """딕셔너리에서 생성"""
        schema = cls(
            version=data["version"],
            description=data["description"],
        )
        for entity_data in data.get("entities", []):
            schema.add_entity(Entity.from_dict(entity_data))
        for rel_data in data.get("relationships", []):
            schema.add_relationship(Relationship.from_dict(rel_data))
        return schema

    def get_statistics(self) -> Dict[str, Any]:
        """온톨로지 통계"""
        entity_counts = {}
        for domain in Domain:
            entity_counts[domain.value] = len(self.get_entities_by_domain(domain))

        relation_counts = {}
        for rel_type in RelationType:
            count = len(self.get_relationships_by_type(rel_type))
            if count > 0:
                relation_counts[rel_type.value] = count

        return {
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
            "entities_by_domain": entity_counts,
            "relationships_by_type": relation_counts,
        }
