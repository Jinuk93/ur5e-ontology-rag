# ============================================================
# src/dashboard/services/graph_service.py - Neo4j Graph Service
# ============================================================

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.utils.config import config


@dataclass
class GraphNode:
    """Graph node representation"""
    id: str
    label: str
    node_type: str
    properties: Dict[str, Any]


@dataclass
class GraphEdge:
    """Graph edge representation"""
    source: str
    target: str
    edge_type: str
    properties: Dict[str, Any]


@dataclass
class GraphData:
    """Graph data for visualization"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: Dict[str, Any]


class GraphService:
    """
    Service for querying Neo4j and preparing graph data for visualization
    """

    def __init__(self):
        self.uri = config.NEO4J_URI
        self.user = config.NEO4J_USER
        self.password = config.NEO4J_PASSWORD
        self._driver = None

    def _get_driver(self):
        """Get Neo4j driver (lazy initialization)"""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password)
                )
            except Exception as e:
                print(f"Failed to connect to Neo4j: {e}")
                return None
        return self._driver

    def close(self):
        """Close the driver connection"""
        if self._driver:
            self._driver.close()
            self._driver = None

    def test_connection(self) -> bool:
        """Test Neo4j connection"""
        driver = self._get_driver()
        if not driver:
            return False
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        driver = self._get_driver()
        if not driver:
            return {"error": "Not connected"}

        try:
            with driver.session() as session:
                # Node count by type
                node_counts = {}
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as label, count(n) as count
                    ORDER BY count DESC
                """)
                for record in result:
                    node_counts[record["label"]] = record["count"]

                # Relationship count by type
                edge_counts = {}
                result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(r) as count
                    ORDER BY count DESC
                """)
                for record in result:
                    edge_counts[record["type"]] = record["count"]

                # Total counts
                total_nodes = sum(node_counts.values())
                total_edges = sum(edge_counts.values())

                return {
                    "total_nodes": total_nodes,
                    "total_edges": total_edges,
                    "node_types": len(node_counts),
                    "edge_types": len(edge_counts),
                    "node_counts": node_counts,
                    "edge_counts": edge_counts,
                }
        except Exception as e:
            return {"error": str(e)}

    def get_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """Get a specific node by its code/name"""
        driver = self._get_driver()
        if not driver:
            return None

        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    WHERE n.code = $id OR n.name = $id
                    RETURN n, labels(n)[0] as label
                    LIMIT 1
                """, id=node_id)

                record = result.single()
                if record:
                    node = record["n"]
                    return GraphNode(
                        id=node_id,
                        label=node.get("code", node.get("name", node_id)),
                        node_type=record["label"],
                        properties=dict(node),
                    )
        except Exception:
            pass
        return None

    def get_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        limit: int = 50,
    ) -> GraphData:
        """
        Get neighbors of a node up to specified depth

        Args:
            node_id: Node code/name
            depth: How many hops to traverse
            limit: Maximum number of nodes

        Returns:
            GraphData with nodes and edges
        """
        driver = self._get_driver()
        if not driver:
            return GraphData(nodes=[], edges=[], stats={})

        try:
            with driver.session() as session:
                result = session.run(f"""
                    MATCH path = (n)-[*1..{depth}]-(m)
                    WHERE n.code = $id OR n.name = $id
                    WITH n, m, relationships(path) as rels
                    UNWIND rels as r
                    WITH DISTINCT n, m, r
                    RETURN
                        n.code as source_code, n.name as source_name,
                        labels(n)[0] as source_type,
                        m.code as target_code, m.name as target_name,
                        labels(m)[0] as target_type,
                        type(r) as rel_type,
                        startNode(r).code as rel_start,
                        endNode(r).code as rel_end
                    LIMIT {limit}
                """, id=node_id)

                nodes_dict = {}
                edges = []

                for record in result:
                    # Source node
                    source_id = record["source_code"] or record["source_name"]
                    if source_id not in nodes_dict:
                        nodes_dict[source_id] = GraphNode(
                            id=source_id,
                            label=source_id,
                            node_type=record["source_type"],
                            properties={},
                        )

                    # Target node
                    target_id = record["target_code"] or record["target_name"]
                    if target_id not in nodes_dict:
                        nodes_dict[target_id] = GraphNode(
                            id=target_id,
                            label=target_id,
                            node_type=record["target_type"],
                            properties={},
                        )

                    # Edge
                    rel_start = record["rel_start"] or source_id
                    rel_end = record["rel_end"] or target_id
                    edges.append(GraphEdge(
                        source=rel_start,
                        target=rel_end,
                        edge_type=record["rel_type"],
                        properties={},
                    ))

                return GraphData(
                    nodes=list(nodes_dict.values()),
                    edges=edges,
                    stats={"node_count": len(nodes_dict), "edge_count": len(edges)},
                )

        except Exception as e:
            return GraphData(nodes=[], edges=[], stats={"error": str(e)})

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> GraphData:
        """
        Find shortest path between two nodes

        Args:
            source_id: Source node code/name
            target_id: Target node code/name
            max_depth: Maximum path length

        Returns:
            GraphData with path nodes and edges
        """
        driver = self._get_driver()
        if not driver:
            return GraphData(nodes=[], edges=[], stats={})

        try:
            with driver.session() as session:
                result = session.run(f"""
                    MATCH path = shortestPath(
                        (a)-[*1..{max_depth}]-(b)
                    )
                    WHERE (a.code = $source OR a.name = $source)
                    AND (b.code = $target OR b.name = $target)
                    RETURN path
                    LIMIT 1
                """, source=source_id, target=target_id)

                record = result.single()
                if not record:
                    return GraphData(nodes=[], edges=[], stats={"error": "No path found"})

                path = record["path"]
                nodes_dict = {}
                edges = []

                for node in path.nodes:
                    node_id = node.get("code", node.get("name", str(node.id)))
                    nodes_dict[node_id] = GraphNode(
                        id=node_id,
                        label=node_id,
                        node_type=list(node.labels)[0] if node.labels else "Unknown",
                        properties=dict(node),
                    )

                for rel in path.relationships:
                    start_id = rel.start_node.get("code", rel.start_node.get("name"))
                    end_id = rel.end_node.get("code", rel.end_node.get("name"))
                    edges.append(GraphEdge(
                        source=start_id,
                        target=end_id,
                        edge_type=rel.type,
                        properties=dict(rel),
                    ))

                return GraphData(
                    nodes=list(nodes_dict.values()),
                    edges=edges,
                    stats={"path_length": len(edges)},
                )

        except Exception as e:
            return GraphData(nodes=[], edges=[], stats={"error": str(e)})

    def run_cypher(self, query: str, limit: int = 100) -> GraphData:
        """
        Run arbitrary Cypher query and return graph data

        Args:
            query: Cypher query string
            limit: Maximum results

        Returns:
            GraphData extracted from query results
        """
        driver = self._get_driver()
        if not driver:
            return GraphData(nodes=[], edges=[], stats={"error": "Not connected"})

        try:
            with driver.session() as session:
                result = session.run(query)

                nodes_dict = {}
                edges = []

                for record in result:
                    for value in record.values():
                        # Handle node
                        if hasattr(value, 'labels'):
                            node_id = value.get("code", value.get("name", str(value.id)))
                            if node_id not in nodes_dict:
                                nodes_dict[node_id] = GraphNode(
                                    id=node_id,
                                    label=node_id,
                                    node_type=list(value.labels)[0] if value.labels else "Unknown",
                                    properties=dict(value),
                                )
                        # Handle relationship
                        elif hasattr(value, 'type'):
                            start_id = value.start_node.get("code", value.start_node.get("name"))
                            end_id = value.end_node.get("code", value.end_node.get("name"))
                            edges.append(GraphEdge(
                                source=start_id,
                                target=end_id,
                                edge_type=value.type,
                                properties=dict(value),
                            ))

                return GraphData(
                    nodes=list(nodes_dict.values()),
                    edges=edges,
                    stats={"node_count": len(nodes_dict), "edge_count": len(edges)},
                )

        except Exception as e:
            return GraphData(nodes=[], edges=[], stats={"error": str(e)})

    def get_all_error_codes(self, limit: int = 100) -> GraphData:
        """Get all error code nodes"""
        return self.run_cypher(f"""
            MATCH (e:ErrorCode)
            OPTIONAL MATCH (e)-[r]-(n)
            RETURN e, r, n
            LIMIT {limit}
        """)

    def get_component_graph(self, component_name: str) -> GraphData:
        """Get graph centered on a component"""
        return self.get_neighbors(component_name, depth=2)

    def get_top_connected_nodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get nodes with most connections"""
        driver = self._get_driver()
        if not driver:
            return []

        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH (n)-[r]-()
                    WITH n, labels(n)[0] as type, count(r) as connections
                    RETURN
                        coalesce(n.code, n.name) as name,
                        type,
                        connections
                    ORDER BY connections DESC
                    LIMIT $limit
                """, limit=limit)

                return [dict(record) for record in result]
        except Exception:
            return []


# Global service instance
graph_service = GraphService()
