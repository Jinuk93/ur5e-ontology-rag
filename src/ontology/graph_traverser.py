"""
그래프 탐색기

온톨로지 그래프에서 관계 경로를 탐색합니다.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple

from .models import OntologySchema, Entity, Relationship
from .schema import RelationType

logger = logging.getLogger(__name__)


@dataclass
class PathStep:
    """경로의 한 단계"""
    entity_id: str
    entity_type: str
    entity_name: str
    relation: Optional[str] = None  # 이 노드로 오기 위한 관계
    direction: str = "outgoing"  # "outgoing" or "incoming"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "relation": self.relation,
            "direction": self.direction,
        }


@dataclass
class OntologyPath:
    """온톨로지 경로"""
    steps: List[PathStep] = field(default_factory=list)
    total_confidence: float = 1.0

    def add_step(self, step: PathStep, confidence: float = 1.0) -> None:
        """경로에 단계 추가"""
        self.steps.append(step)
        self.total_confidence *= confidence

    def to_string(self) -> str:
        """경로를 문자열로 변환"""
        if not self.steps:
            return ""

        parts = []
        for i, step in enumerate(self.steps):
            if i == 0:
                parts.append(step.entity_id)
            else:
                arrow = "→" if step.direction == "outgoing" else "←"
                parts.append(f"{arrow}[{step.relation}]{arrow} {step.entity_id}")

        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "total_confidence": self.total_confidence,
            "path_string": self.to_string(),
        }

    @property
    def length(self) -> int:
        return len(self.steps)

    @property
    def start_entity(self) -> Optional[str]:
        return self.steps[0].entity_id if self.steps else None

    @property
    def end_entity(self) -> Optional[str]:
        return self.steps[-1].entity_id if self.steps else None


@dataclass
class TraversalResult:
    """탐색 결과"""
    paths: List[OntologyPath] = field(default_factory=list)
    visited_entities: Set[str] = field(default_factory=set)
    related_entities: Dict[str, Entity] = field(default_factory=dict)
    relationships_found: List[Relationship] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paths": [p.to_dict() for p in self.paths],
            "visited_count": len(self.visited_entities),
            "related_entities": list(self.related_entities.keys()),
            "relationships_count": len(self.relationships_found),
        }


class GraphTraverser:
    """온톨로지 그래프 탐색기"""

    # 탐색 시 따라갈 관계 우선순위 (논리적 추론 순서)
    REASONING_RELATION_ORDER = [
        RelationType.HAS_STATE,      # 상태 확인
        RelationType.INDICATES,      # 패턴 → 원인
        RelationType.TRIGGERS,       # 패턴 → 에러
        RelationType.CAUSED_BY,      # 에러 → 원인
        RelationType.RESOLVED_BY,    # 원인 → 해결책
        RelationType.DOCUMENTED_IN,  # 문서 참조
        RelationType.PREVENTS,       # 해결책 → 에러 방지
        RelationType.AFFECTS,        # 에러 → 영향받는 컴포넌트
    ]

    def __init__(self, ontology: OntologySchema):
        """초기화

        Args:
            ontology: 온톨로지 스키마
        """
        self.ontology = ontology
        self._build_adjacency()
        logger.info(f"GraphTraverser 초기화: {len(self.ontology.entities)} 엔티티, {len(self.ontology.relationships)} 관계")

    def _build_adjacency(self) -> None:
        """인접 리스트 구축 (탐색 최적화)"""
        # outgoing: entity_id -> [(relation, target_id, confidence)]
        self._outgoing: Dict[str, List[Tuple[str, str, float]]] = {}
        # incoming: entity_id -> [(relation, source_id, confidence)]
        self._incoming: Dict[str, List[Tuple[str, str, float]]] = {}

        for rel in self.ontology.relationships:
            source = rel.source
            target = rel.target
            relation = rel.relation.value
            confidence = rel.properties.get("confidence", 1.0)

            if source not in self._outgoing:
                self._outgoing[source] = []
            self._outgoing[source].append((relation, target, confidence))

            if target not in self._incoming:
                self._incoming[target] = []
            self._incoming[target].append((relation, source, confidence))

    # ================================================================
    # BFS 탐색
    # ================================================================

    def bfs(
        self,
        start_id: str,
        max_depth: int = 3,
        relation_filter: Optional[List[RelationType]] = None,
        direction: str = "both"
    ) -> TraversalResult:
        """BFS로 관련 엔티티 탐색

        Args:
            start_id: 시작 엔티티 ID
            max_depth: 최대 탐색 깊이
            relation_filter: 탐색할 관계 타입 (None이면 모두)
            direction: "outgoing", "incoming", "both"

        Returns:
            TraversalResult
        """
        result = TraversalResult()
        filter_set = {r.value for r in relation_filter} if relation_filter else None

        # 시작 엔티티 확인
        start_entity = self.ontology.get_entity(start_id)
        if not start_entity:
            logger.warning(f"시작 엔티티 없음: {start_id}")
            return result

        result.related_entities[start_id] = start_entity
        result.visited_entities.add(start_id)

        # BFS 큐: (entity_id, depth, path)
        queue: deque = deque()
        queue.append((start_id, 0, OntologyPath(steps=[
            PathStep(
                entity_id=start_id,
                entity_type=start_entity.type.value,
                entity_name=start_entity.name,
            )
        ])))

        while queue:
            current_id, depth, current_path = queue.popleft()

            if depth >= max_depth:
                result.paths.append(current_path)
                continue

            neighbors_found = False

            # Outgoing 탐색
            if direction in ("outgoing", "both"):
                for rel, target_id, confidence in self._outgoing.get(current_id, []):
                    if filter_set and rel not in filter_set:
                        continue
                    if target_id in result.visited_entities:
                        continue

                    target_entity = self.ontology.get_entity(target_id)
                    if not target_entity:
                        continue

                    result.visited_entities.add(target_id)
                    result.related_entities[target_id] = target_entity
                    result.relationships_found.append(Relationship(
                        source=current_id,
                        relation=RelationType(rel),
                        target=target_id,
                        properties={"confidence": confidence}
                    ))

                    # 새 경로 생성
                    new_path = OntologyPath(
                        steps=current_path.steps.copy(),
                        total_confidence=current_path.total_confidence
                    )
                    new_path.add_step(PathStep(
                        entity_id=target_id,
                        entity_type=target_entity.type.value,
                        entity_name=target_entity.name,
                        relation=rel,
                        direction="outgoing",
                    ), confidence)

                    queue.append((target_id, depth + 1, new_path))
                    neighbors_found = True

            # Incoming 탐색
            if direction in ("incoming", "both"):
                for rel, source_id, confidence in self._incoming.get(current_id, []):
                    if filter_set and rel not in filter_set:
                        continue
                    if source_id in result.visited_entities:
                        continue

                    source_entity = self.ontology.get_entity(source_id)
                    if not source_entity:
                        continue

                    result.visited_entities.add(source_id)
                    result.related_entities[source_id] = source_entity
                    result.relationships_found.append(Relationship(
                        source=source_id,
                        relation=RelationType(rel),
                        target=current_id,
                        properties={"confidence": confidence}
                    ))

                    # 새 경로 생성
                    new_path = OntologyPath(
                        steps=current_path.steps.copy(),
                        total_confidence=current_path.total_confidence
                    )
                    new_path.add_step(PathStep(
                        entity_id=source_id,
                        entity_type=source_entity.type.value,
                        entity_name=source_entity.name,
                        relation=rel,
                        direction="incoming",
                    ), confidence)

                    queue.append((source_id, depth + 1, new_path))
                    neighbors_found = True

            if not neighbors_found:
                result.paths.append(current_path)

        return result

    # ================================================================
    # 경로 찾기
    # ================================================================

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[OntologyPath]:
        """두 엔티티 간 경로 찾기 (BFS)

        Args:
            source_id: 시작 엔티티 ID
            target_id: 목표 엔티티 ID
            max_depth: 최대 탐색 깊이

        Returns:
            OntologyPath 또는 None
        """
        source_entity = self.ontology.get_entity(source_id)
        if not source_entity:
            return None

        if source_id == target_id:
            return OntologyPath(steps=[PathStep(
                entity_id=source_id,
                entity_type=source_entity.type.value,
                entity_name=source_entity.name,
            )])

        visited = {source_id}
        queue: deque = deque()
        queue.append((source_id, OntologyPath(steps=[PathStep(
            entity_id=source_id,
            entity_type=source_entity.type.value,
            entity_name=source_entity.name,
        )])))

        while queue:
            current_id, current_path = queue.popleft()

            if current_path.length > max_depth:
                continue

            # Outgoing 탐색
            for rel, neighbor_id, confidence in self._outgoing.get(current_id, []):
                if neighbor_id in visited:
                    continue

                neighbor_entity = self.ontology.get_entity(neighbor_id)
                if not neighbor_entity:
                    continue

                visited.add(neighbor_id)
                new_path = OntologyPath(
                    steps=current_path.steps.copy(),
                    total_confidence=current_path.total_confidence
                )
                new_path.add_step(PathStep(
                    entity_id=neighbor_id,
                    entity_type=neighbor_entity.type.value,
                    entity_name=neighbor_entity.name,
                    relation=rel,
                    direction="outgoing",
                ), confidence)

                if neighbor_id == target_id:
                    return new_path

                queue.append((neighbor_id, new_path))

            # Incoming 탐색
            for rel, neighbor_id, confidence in self._incoming.get(current_id, []):
                if neighbor_id in visited:
                    continue

                neighbor_entity = self.ontology.get_entity(neighbor_id)
                if not neighbor_entity:
                    continue

                visited.add(neighbor_id)
                new_path = OntologyPath(
                    steps=current_path.steps.copy(),
                    total_confidence=current_path.total_confidence
                )
                new_path.add_step(PathStep(
                    entity_id=neighbor_id,
                    entity_type=neighbor_entity.type.value,
                    entity_name=neighbor_entity.name,
                    relation=rel,
                    direction="incoming",
                ), confidence)

                if neighbor_id == target_id:
                    return new_path

                queue.append((neighbor_id, new_path))

        return None

    # ================================================================
    # 특정 관계 체인 탐색
    # ================================================================

    def follow_relation_chain(
        self,
        start_id: str,
        relation_chain: List[RelationType],
        direction: str = "outgoing"
    ) -> List[OntologyPath]:
        """지정된 관계 체인을 따라 탐색

        예: INDICATES -> RESOLVED_BY 체인을 따라가면
        패턴 → 원인 → 해결책 경로 획득

        Args:
            start_id: 시작 엔티티 ID
            relation_chain: 따라갈 관계 체인
            direction: "outgoing" or "incoming"

        Returns:
            OntologyPath 리스트
        """
        start_entity = self.ontology.get_entity(start_id)
        if not start_entity:
            return []

        paths = [OntologyPath(steps=[PathStep(
            entity_id=start_id,
            entity_type=start_entity.type.value,
            entity_name=start_entity.name,
        )])]

        for rel_type in relation_chain:
            rel_value = rel_type.value
            new_paths = []

            for path in paths:
                current_id = path.end_entity

                neighbors = (
                    self._outgoing.get(current_id, [])
                    if direction == "outgoing"
                    else self._incoming.get(current_id, [])
                )

                for rel, neighbor_id, confidence in neighbors:
                    if rel != rel_value:
                        continue

                    neighbor_entity = self.ontology.get_entity(neighbor_id)
                    if not neighbor_entity:
                        continue

                    new_path = OntologyPath(
                        steps=path.steps.copy(),
                        total_confidence=path.total_confidence
                    )
                    new_path.add_step(PathStep(
                        entity_id=neighbor_id,
                        entity_type=neighbor_entity.type.value,
                        entity_name=neighbor_entity.name,
                        relation=rel,
                        direction=direction,
                    ), confidence)
                    new_paths.append(new_path)

            if not new_paths:
                break
            paths = new_paths

        # 체인 전체를 완료한 경로만 반환
        expected_length = len(relation_chain) + 1
        return [p for p in paths if p.length == expected_length]

    # ================================================================
    # 컨텍스트 수집
    # ================================================================

    def get_entity_context(
        self,
        entity_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """엔티티의 전체 컨텍스트 수집

        Args:
            entity_id: 엔티티 ID
            depth: 탐색 깊이

        Returns:
            컨텍스트 정보 딕셔너리
        """
        entity = self.ontology.get_entity(entity_id)
        if not entity:
            return {}

        # BFS로 관련 엔티티 수집
        traversal = self.bfs(entity_id, max_depth=depth)

        # 관계 타입별로 그룹화
        outgoing_by_type: Dict[str, List[str]] = {}
        incoming_by_type: Dict[str, List[str]] = {}

        for rel in traversal.relationships_found:
            if rel.source == entity_id:
                rel_type = rel.relation.value
                if rel_type not in outgoing_by_type:
                    outgoing_by_type[rel_type] = []
                outgoing_by_type[rel_type].append(rel.target)
            else:
                rel_type = rel.relation.value
                if rel_type not in incoming_by_type:
                    incoming_by_type[rel_type] = []
                incoming_by_type[rel_type].append(rel.source)

        return {
            "entity": {
                "id": entity.id,
                "type": entity.type.value,
                "name": entity.name,
                "domain": entity.domain.value,
                "properties": entity.properties,
            },
            "outgoing_relations": outgoing_by_type,
            "incoming_relations": incoming_by_type,
            "related_entities": {
                eid: {
                    "type": e.type.value,
                    "name": e.name,
                }
                for eid, e in traversal.related_entities.items()
                if eid != entity_id
            },
            "traversal_summary": {
                "visited_count": len(traversal.visited_entities),
                "paths_found": len(traversal.paths),
            }
        }

    # ================================================================
    # 추론 경로 생성
    # ================================================================

    def get_reasoning_path(
        self,
        pattern_id: str
    ) -> Dict[str, Any]:
        """패턴에서 시작하는 전체 추론 경로 생성

        패턴 → 원인 → 해결책 경로 + 패턴 → 에러 경로

        Args:
            pattern_id: 패턴 엔티티 ID (예: "PAT_COLLISION")

        Returns:
            추론 경로 정보
        """
        pattern = self.ontology.get_entity(pattern_id)
        if not pattern:
            return {"error": f"패턴 없음: {pattern_id}"}

        result = {
            "pattern": {
                "id": pattern_id,
                "name": pattern.name,
                "properties": pattern.properties,
            },
            "cause_paths": [],
            "error_paths": [],
            "resolution_paths": [],
        }

        # 패턴 → 원인 (INDICATES)
        cause_paths = self.follow_relation_chain(
            pattern_id,
            [RelationType.INDICATES]
        )
        for path in cause_paths:
            cause_id = path.end_entity
            result["cause_paths"].append({
                "cause_id": cause_id,
                "path": path.to_string(),
                "confidence": path.total_confidence,
            })

            # 원인 → 해결책 (RESOLVED_BY)
            resolution_paths = self.follow_relation_chain(
                cause_id,
                [RelationType.RESOLVED_BY]
            )
            for res_path in resolution_paths:
                result["resolution_paths"].append({
                    "resolution_id": res_path.end_entity,
                    "from_cause": cause_id,
                    "path": f"{pattern_id} → {path.to_string()} → {res_path.to_string()}",
                    "confidence": path.total_confidence * res_path.total_confidence,
                })

        # 패턴 → 에러 (TRIGGERS)
        error_paths = self.follow_relation_chain(
            pattern_id,
            [RelationType.TRIGGERS]
        )
        for path in error_paths:
            result["error_paths"].append({
                "error_id": path.end_entity,
                "path": path.to_string(),
                "confidence": path.total_confidence,
            })

        return result


# ================================================================
# 편의 함수
# ================================================================

def create_graph_traverser(ontology: OntologySchema) -> GraphTraverser:
    """GraphTraverser 인스턴스 생성"""
    return GraphTraverser(ontology)
