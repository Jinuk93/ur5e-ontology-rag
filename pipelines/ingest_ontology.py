"""
ontology.json을 Neo4j에 적재하는 파이프라인
"""
import json
from pathlib import Path
from neo4j import GraphDatabase


class OntologyIngestor:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        self.driver.close()
    
    def load_ontology(self, ontology_path: Path) -> dict:
        """ontology.json 파일 로드"""
        with open(ontology_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def create_nodes(self, tx, node_data: dict):
        """노드 생성"""
        query = """
        MERGE (n:Entity {id: $id})
        SET n.name = $name,
            n.type = $type,
            n.description = $description
        RETURN n
        """
        tx.run(query, **node_data)
    
    def create_relationships(self, tx, rel_data: dict):
        """관계 생성"""
        query = """
        MATCH (a:Entity {id: $from_id})
        MATCH (b:Entity {id: $to_id})
        MERGE (a)-[r:RELATES_TO {type: $rel_type}]->(b)
        RETURN r
        """
        tx.run(query, **rel_data)
    
    def ingest(self, ontology_path: Path):
        """온톨로지 데이터를 Neo4j에 적재"""
        ontology = self.load_ontology(ontology_path)
        
        with self.driver.session() as session:
            # 노드 생성
            if "nodes" in ontology:
                for node in ontology["nodes"]:
                    session.execute_write(self.create_nodes, node)
                print(f"Created {len(ontology['nodes'])} nodes")
            
            # 관계 생성
            if "relationships" in ontology:
                for rel in ontology["relationships"]:
                    session.execute_write(self.create_relationships, rel)
                print(f"Created {len(ontology['relationships'])} relationships")


if __name__ == "__main__":
    import os
    
    ingestor = OntologyIngestor(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password")
    )
    
    try:
        ingestor.ingest(Path("data/processed/ontology/ontology.json"))
    finally:
        ingestor.close()
