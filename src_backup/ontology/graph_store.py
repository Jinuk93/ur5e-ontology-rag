# ============================================================
# src/ontology/graph_store.py - Neo4j 그래프 저장소
# ============================================================
# Neo4j를 사용하여 엔티티와 관계를 저장하고 검색합니다.
#
# Neo4j란?
#   - 그래프 데이터베이스
#   - 노드(Entity)와 엣지(Relation)로 데이터 저장
#   - Cypher 쿼리 언어 사용
#
# 주요 기능:
#   - 엔티티(노드) 추가/조회
#   - 관계(엣지) 추가/조회
#   - Cypher 쿼리 실행
# ============================================================

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

from .schema import Entity, EntityType, Relation, RelationType

# 프로젝트 루트의 .env 파일 로드
load_dotenv()


# ============================================================
# [1] GraphStore 클래스
# ============================================================

class GraphStore:
    """
    Neo4j 기반 그래프 저장소

    사용 예시:
        store = GraphStore()
        store.add_entity(entity)
        store.add_relation(relation)
        results = store.query("MATCH (n) RETURN n LIMIT 10")
        store.close()
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        GraphStore 초기화

        Args:
            uri: Neo4j URI (기본값: .env의 NEO4J_URI)
            user: 사용자 이름 (기본값: .env의 NEO4J_USER)
            password: 비밀번호 (기본값: .env의 NEO4J_PASSWORD)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password123")

        # Neo4j 드라이버 생성
        self.driver: Driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
        )

        print(f"[OK] GraphStore initialized")
        print(f"     URI: {self.uri}")
        print(f"     User: {self.user}")

    def close(self):
        """연결 종료"""
        self.driver.close()
        print("[OK] GraphStore connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # --------------------------------------------------------
    # [1.1] 연결 테스트
    # --------------------------------------------------------

    def verify_connection(self) -> bool:
        """
        Neo4j 연결 확인

        Returns:
            bool: 연결 성공 시 True
        """
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                return record["test"] == 1
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    # --------------------------------------------------------
    # [1.2] 엔티티(노드) 추가
    # --------------------------------------------------------

    def add_entity(self, entity: Entity) -> bool:
        """
        엔티티(노드) 추가

        처리 흐름:
            1. Cypher MERGE 문으로 노드 생성 (이미 있으면 업데이트)
            2. 속성 설정

        Args:
            entity: 추가할 엔티티

        Returns:
            bool: 성공 시 True

        사용 예시:
            entity = Entity(id="comp_1", type=EntityType.COMPONENT, name="Control Box")
            store.add_entity(entity)
        """
        query = f"""
        MERGE (n:{entity.type.value} {{id: $id}})
        SET n.name = $name
        SET n += $properties
        RETURN n
        """

        try:
            with self.driver.session() as session:
                session.run(
                    query,
                    id=entity.id,
                    name=entity.name,
                    properties=entity.properties,
                )
            return True
        except Exception as e:
            print(f"[ERROR] Failed to add entity: {e}")
            return False

    def add_entities(self, entities: List[Entity]) -> int:
        """
        여러 엔티티 배치 추가

        Args:
            entities: 엔티티 리스트

        Returns:
            int: 추가된 엔티티 수
        """
        added = 0
        for entity in entities:
            if self.add_entity(entity):
                added += 1

        print(f"[OK] Added {added}/{len(entities)} entities")
        return added

    # --------------------------------------------------------
    # [1.3] 관계(엣지) 추가
    # --------------------------------------------------------

    def add_relation(self, relation: Relation) -> bool:
        """
        관계(엣지) 추가

        처리 흐름:
            1. 시작 노드와 끝 노드 찾기
            2. 관계 생성 (이미 있으면 업데이트)

        Args:
            relation: 추가할 관계

        Returns:
            bool: 성공 시 True

        사용 예시:
            relation = Relation(
                source_id="comp_1",
                target_id="error_c4",
                type=RelationType.HAS_ERROR
            )
            store.add_relation(relation)
        """
        query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{relation.type.value}]->(target)
        SET r += $properties
        RETURN r
        """

        try:
            with self.driver.session() as session:
                result = session.run(
                    query,
                    source_id=relation.source_id,
                    target_id=relation.target_id,
                    properties=relation.properties,
                )
                # 결과가 있는지 확인
                if result.single() is None:
                    print(f"[WARN] Relation not created: source or target not found")
                    return False
            return True
        except Exception as e:
            print(f"[ERROR] Failed to add relation: {e}")
            return False

    def add_relations(self, relations: List[Relation]) -> int:
        """
        여러 관계 배치 추가

        Args:
            relations: 관계 리스트

        Returns:
            int: 추가된 관계 수
        """
        added = 0
        for relation in relations:
            if self.add_relation(relation):
                added += 1

        print(f"[OK] Added {added}/{len(relations)} relations")
        return added

    # --------------------------------------------------------
    # [1.4] 조회
    # --------------------------------------------------------

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        ID로 엔티티 조회

        Args:
            entity_id: 엔티티 ID

        Returns:
            Dict or None: 엔티티 정보
        """
        query = """
        MATCH (n {id: $id})
        RETURN n, labels(n) as labels
        """

        try:
            with self.driver.session() as session:
                result = session.run(query, id=entity_id)
                record = result.single()
                if record:
                    node = record["n"]
                    return {
                        "id": node["id"],
                        "name": node.get("name"),
                        "type": record["labels"][0] if record["labels"] else None,
                        "properties": dict(node),
                    }
        except Exception as e:
            print(f"[ERROR] Failed to get entity: {e}")

        return None

    def get_entities_by_type(
        self,
        entity_type: EntityType,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        타입별 엔티티 조회

        Args:
            entity_type: 엔티티 타입
            limit: 최대 개수

        Returns:
            List[Dict]: 엔티티 리스트
        """
        query = f"""
        MATCH (n:{entity_type.value})
        RETURN n
        LIMIT $limit
        """

        entities = []
        try:
            with self.driver.session() as session:
                result = session.run(query, limit=limit)
                for record in result:
                    node = record["n"]
                    entities.append({
                        "id": node["id"],
                        "name": node.get("name"),
                        "type": entity_type.value,
                        "properties": dict(node),
                    })
        except Exception as e:
            print(f"[ERROR] Failed to get entities: {e}")

        return entities

    def get_related_entities(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
        direction: str = "outgoing",
    ) -> List[Dict[str, Any]]:
        """
        관련 엔티티 조회

        Args:
            entity_id: 시작 엔티티 ID
            relation_type: 관계 타입 (None이면 모든 관계)
            direction: 방향 ("outgoing", "incoming", "both")

        Returns:
            List[Dict]: 관련 엔티티 리스트
        """
        # 관계 패턴 구성
        rel_pattern = f"[r:{relation_type.value}]" if relation_type else "[r]"

        if direction == "outgoing":
            query = f"""
            MATCH (source {{id: $id}})-{rel_pattern}->(target)
            RETURN target, type(r) as rel_type, labels(target) as labels
            """
        elif direction == "incoming":
            query = f"""
            MATCH (source {{id: $id}})<-{rel_pattern}-(target)
            RETURN target, type(r) as rel_type, labels(target) as labels
            """
        else:  # both
            query = f"""
            MATCH (source {{id: $id}})-{rel_pattern}-(target)
            RETURN target, type(r) as rel_type, labels(target) as labels
            """

        entities = []
        try:
            with self.driver.session() as session:
                result = session.run(query, id=entity_id)
                for record in result:
                    node = record["target"]
                    entities.append({
                        "id": node["id"],
                        "name": node.get("name"),
                        "type": record["labels"][0] if record["labels"] else None,
                        "relation": record["rel_type"],
                        "properties": dict(node),
                    })
        except Exception as e:
            print(f"[ERROR] Failed to get related entities: {e}")

        return entities

    # --------------------------------------------------------
    # [1.5] Cypher 쿼리 실행
    # --------------------------------------------------------

    def query(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Cypher 쿼리 실행

        Args:
            cypher: Cypher 쿼리 문자열
            parameters: 쿼리 파라미터

        Returns:
            List[Dict]: 쿼리 결과

        사용 예시:
            results = store.query(
                "MATCH (n:Component) RETURN n.name LIMIT $limit",
                {"limit": 10}
            )
        """
        results = []
        try:
            with self.driver.session() as session:
                result = session.run(cypher, parameters or {})
                for record in result:
                    results.append(dict(record))
        except Exception as e:
            print(f"[ERROR] Query failed: {e}")

        return results

    # --------------------------------------------------------
    # [1.6] 통계 및 관리
    # --------------------------------------------------------

    def count_entities(self, entity_type: Optional[EntityType] = None) -> int:
        """엔티티 개수 반환"""
        if entity_type:
            query = f"MATCH (n:{entity_type.value}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"

        results = self.query(query)
        return results[0]["count"] if results else 0

    def count_relations(self, relation_type: Optional[RelationType] = None) -> int:
        """관계 개수 반환"""
        if relation_type:
            query = f"MATCH ()-[r:{relation_type.value}]->() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) as count"

        results = self.query(query)
        return results[0]["count"] if results else 0

    def clear_all(self) -> None:
        """
        모든 데이터 삭제 (주의: 복구 불가!)
        """
        query = "MATCH (n) DETACH DELETE n"
        self.query(query)
        print("[OK] All data cleared from Neo4j")

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        stats = {
            "total_entities": self.count_entities(),
            "total_relations": self.count_relations(),
            "entities_by_type": {},
            "relations_by_type": {},
        }

        # 엔티티 타입별 개수
        for entity_type in EntityType:
            count = self.count_entities(entity_type)
            if count > 0:
                stats["entities_by_type"][entity_type.value] = count

        # 관계 타입별 개수
        for relation_type in RelationType:
            count = self.count_relations(relation_type)
            if count > 0:
                stats["relations_by_type"][relation_type.value] = count

        return stats


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    import sys

    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 50)
    print("[*] GraphStore Test")
    print("=" * 50)

    # GraphStore 생성
    store = GraphStore()

    # 연결 테스트
    print("\n[Test 1] Connection test")
    if store.verify_connection():
        print("  [OK] Connected to Neo4j")
    else:
        print("  [FAIL] Cannot connect to Neo4j")
        print("  Please run: docker-compose up -d")
        sys.exit(1)

    # 테스트 데이터 추가
    print("\n[Test 2] Add entities")

    from .schema import create_component, create_error_code, create_procedure

    control_box = create_component("Control Box", component_type="main")
    error_c4 = create_error_code("C4", title="Communication error", severity="high")
    check_cable = create_procedure("Check Cable")

    store.add_entity(control_box)
    store.add_entity(error_c4)
    store.add_entity(check_cable)

    # 관계 추가
    print("\n[Test 3] Add relations")

    relation1 = Relation(
        source_id=control_box.id,
        target_id=error_c4.id,
        type=RelationType.HAS_ERROR,
    )
    relation2 = Relation(
        source_id=error_c4.id,
        target_id=check_cable.id,
        type=RelationType.RESOLVED_BY,
    )

    store.add_relation(relation1)
    store.add_relation(relation2)

    # 조회 테스트
    print("\n[Test 4] Query test")
    entity = store.get_entity(control_box.id)
    print(f"  Entity: {entity}")

    related = store.get_related_entities(control_box.id)
    print(f"  Related: {related}")

    # 통계
    print("\n[Test 5] Statistics")
    stats = store.get_statistics()
    print(f"  Total entities: {stats['total_entities']}")
    print(f"  Total relations: {stats['total_relations']}")

    # 정리
    store.close()

    print("\n" + "=" * 50)
    print("[OK] GraphStore test passed!")
    print("=" * 50)
