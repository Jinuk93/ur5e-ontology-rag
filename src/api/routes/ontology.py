"""
온톨로지 그래프 탐색 API

팔란티어 스타일의 동적 그래프 탐색을 위한 엔드포인트
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from src.ontology import OntologyEngine

logger = logging.getLogger(__name__)

# 싱글톤 인스턴스
_ontology_engine: Optional[OntologyEngine] = None


def get_ontology_engine() -> OntologyEngine:
    """OntologyEngine 싱글톤"""
    global _ontology_engine
    if _ontology_engine is None:
        _ontology_engine = OntologyEngine()
    return _ontology_engine

router = APIRouter(prefix="/api/ontology", tags=["ontology"])


# ================================================================
# Response Models
# ================================================================

class GraphNode(BaseModel):
    """그래프 노드"""
    id: str
    type: str
    label: str
    domain: Optional[str] = None
    properties: Optional[dict] = None


class GraphEdge(BaseModel):
    """그래프 엣지"""
    source: str
    target: str
    relation: str
    properties: Optional[dict] = None


class EntityDetailResponse(BaseModel):
    """엔티티 상세 정보"""
    id: str
    type: str
    name: str
    domain: Optional[str] = None
    properties: Optional[dict] = None
    description: Optional[str] = None


class NeighborsResponse(BaseModel):
    """이웃 노드 응답"""
    center: GraphNode
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_neighbors: int


class SubgraphResponse(BaseModel):
    """서브그래프 응답"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    center_id: str
    depth: int
    total_nodes: int
    total_edges: int


class AllEntitiesResponse(BaseModel):
    """전체 엔티티 목록"""
    entities: List[GraphNode]
    total: int
    by_type: dict
    by_domain: dict


# ================================================================
# Endpoints
# ================================================================

@router.get("/entities", response_model=AllEntitiesResponse)
async def get_all_entities():
    """
    전체 엔티티 목록 조회

    그래프 탐색의 시작점을 선택하기 위한 전체 엔티티 목록
    """
    try:
        engine = get_ontology_engine()
        ontology = engine.ontology

        nodes = []
        by_type = {}
        by_domain = {}

        for entity in ontology.entities:
            node = GraphNode(
                id=entity.id,
                type=entity.type.value,
                label=entity.name,
                domain=entity.domain.value if entity.domain else None,
                properties=entity.properties,
            )
            nodes.append(node)

            # Count by type
            type_key = entity.type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            # Count by domain
            if entity.domain:
                domain_key = entity.domain.value
                by_domain[domain_key] = by_domain.get(domain_key, 0) + 1

        return AllEntitiesResponse(
            entities=nodes,
            total=len(nodes),
            by_type=by_type,
            by_domain=by_domain,
        )
    except Exception as e:
        logger.error(f"Failed to get entities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_detail(entity_id: str):
    """
    특정 엔티티 상세 정보 조회
    """
    try:
        engine = get_ontology_engine()
        entity = engine.ontology.get_entity(entity_id)

        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        # 엔티티 설명 생성
        description = None
        if entity.type.value == "ErrorCode":
            description = f"UR5e 에러 코드: {entity.name}"
        elif entity.type.value == "Pattern":
            description = f"센서 패턴: {entity.name}"
        elif entity.type.value == "MeasurementAxis":
            props = entity.properties or {}
            unit = props.get("unit", "")
            description = f"측정축 ({unit})"
        elif entity.type.value == "Cause":
            description = f"원인 분류: {entity.name}"
        elif entity.type.value == "Resolution":
            description = f"해결 방안: {entity.name}"

        return EntityDetailResponse(
            id=entity.id,
            type=entity.type.value,
            name=entity.name,
            domain=entity.domain.value if entity.domain else None,
            properties=entity.properties,
            description=description,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity {entity_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neighbors/{entity_id}", response_model=NeighborsResponse)
async def get_neighbors(
    entity_id: str,
    direction: str = Query(default="both", description="outgoing, incoming, both"),
):
    """
    특정 엔티티의 이웃 노드 조회

    클릭한 노드의 직접 연결된 이웃들을 반환
    """
    try:
        engine = get_ontology_engine()
        traverser = engine.traverser
        ontology = engine.ontology

        # 중심 엔티티 확인
        center_entity = ontology.get_entity(entity_id)
        if not center_entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        center_node = GraphNode(
            id=center_entity.id,
            type=center_entity.type.value,
            label=center_entity.name,
            domain=center_entity.domain.value if center_entity.domain else None,
        )

        # BFS로 depth=1 이웃 탐색
        result = traverser.bfs(entity_id, max_depth=1, direction=direction)

        nodes = []
        edges = []

        for ent_id, entity in result.related_entities.items():
            if ent_id == entity_id:
                continue  # 중심 노드 제외
            nodes.append(GraphNode(
                id=entity.id,
                type=entity.type.value,
                label=entity.name,
                domain=entity.domain.value if entity.domain else None,
            ))

        for rel in result.relationships_found:
            edges.append(GraphEdge(
                source=rel.source,
                target=rel.target,
                relation=rel.relation.value,
                properties=rel.properties,
            ))

        return NeighborsResponse(
            center=center_node,
            nodes=nodes,
            edges=edges,
            total_neighbors=len(nodes),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get neighbors for {entity_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph", response_model=SubgraphResponse)
async def get_subgraph(
    center: str = Query(..., description="중심 노드 ID"),
    depth: int = Query(default=2, ge=1, le=4, description="탐색 깊이 (1-4)"),
    direction: str = Query(default="both", description="outgoing, incoming, both"),
):
    """
    중심 노드 기준 서브그래프 조회

    팔란티어 스타일의 그래프 탐색: 중심 노드에서 depth만큼 확장된 서브그래프
    """
    try:
        engine = get_ontology_engine()
        traverser = engine.traverser
        ontology = engine.ontology

        # 중심 엔티티 확인
        center_entity = ontology.get_entity(center)
        if not center_entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {center}")

        # BFS로 서브그래프 탐색
        result = traverser.bfs(center, max_depth=depth, direction=direction)

        nodes = []
        edges = []

        for ent_id, entity in result.related_entities.items():
            nodes.append(GraphNode(
                id=entity.id,
                type=entity.type.value,
                label=entity.name,
                domain=entity.domain.value if entity.domain else None,
                properties=entity.properties,
            ))

        for rel in result.relationships_found:
            edges.append(GraphEdge(
                source=rel.source,
                target=rel.target,
                relation=rel.relation.value,
                properties=rel.properties,
            ))

        return SubgraphResponse(
            nodes=nodes,
            edges=edges,
            center_id=center,
            depth=depth,
            total_nodes=len(nodes),
            total_edges=len(edges),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subgraph from {center}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
