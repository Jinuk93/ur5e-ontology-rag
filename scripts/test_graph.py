# ============================================================
# scripts/test_graph.py - Neo4j 그래프 테스트 및 시각화 쿼리
# ============================================================
# 실행 방법: python scripts/test_graph.py
#
# Neo4j Browser에서 시각적으로 확인:
#   1. http://localhost:7474 접속
#   2. 로그인: neo4j / password123
#   3. 아래 Cypher 쿼리를 복사하여 실행
# ============================================================

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.ontology.graph_store import GraphStore
from src.ontology.schema import EntityType, RelationType


def print_section(title):
    print("\n" + "=" * 60)
    print(f"[*] {title}")
    print("=" * 60)


def run_tests():
    """그래프 테스트 실행"""

    print_section("Neo4j Graph Test")

    store = GraphStore()
    if not store.verify_connection():
        print("[ERROR] Cannot connect to Neo4j")
        return

    # --------------------------------------------------------
    # 1. 기본 통계
    # --------------------------------------------------------
    print_section("1. Basic Statistics")

    stats = store.get_statistics()
    print(f"\n총 노드 수: {stats['total_entities']}")
    print(f"총 관계 수: {stats['total_relations']}")

    print("\n[노드 타입별]")
    for t, count in sorted(stats.get("entities_by_type", {}).items()):
        print(f"  {t:15} : {count:5}")

    print("\n[관계 타입별]")
    for t, count in sorted(stats.get("relations_by_type", {}).items()):
        print(f"  {t:15} : {count:5}")

    # --------------------------------------------------------
    # 2. 에러 코드 상세
    # --------------------------------------------------------
    print_section("2. Error Codes Detail")

    results = store.query("""
        MATCH (e:ErrorCode)
        RETURN e.name as code, e.title as title, e.description as desc
        ORDER BY e.name
        LIMIT 20
    """)

    print(f"\n에러 코드 목록 (상위 20개):")
    for r in results:
        code = r['code']
        title = r.get('title', '')[:40] if r.get('title') else ''
        print(f"  {code:10} : {title}")

    # --------------------------------------------------------
    # 3. 부품(Component) 상세
    # --------------------------------------------------------
    print_section("3. Components Detail")

    results = store.query("""
        MATCH (c:Component)
        RETURN c.name as name, c.component_type as type
        ORDER BY c.name
    """)

    print(f"\n부품 목록 ({len(results)}개):")
    for r in results:
        name = r['name']
        ctype = r.get('type', 'unknown')
        print(f"  {name:25} ({ctype})")

    # --------------------------------------------------------
    # 4. 부품 → 에러 관계
    # --------------------------------------------------------
    print_section("4. Component → Error Relations")

    results = store.query("""
        MATCH (c:Component)-[r:HAS_ERROR]->(e:ErrorCode)
        RETURN c.name as component, collect(e.name) as errors
        ORDER BY size(collect(e.name)) DESC
    """)

    print(f"\n부품별 연관 에러:")
    for r in results:
        comp = r['component']
        errors = r['errors'][:5]  # 최대 5개만 표시
        more = f" (+{len(r['errors'])-5} more)" if len(r['errors']) > 5 else ""
        print(f"  {comp:20} → {', '.join(errors)}{more}")

    # --------------------------------------------------------
    # 5. 에러 → 원인 관계
    # --------------------------------------------------------
    print_section("5. Error → Caused By Relations")

    results = store.query("""
        MATCH (e:ErrorCode)-[r:CAUSED_BY]->(c:Component)
        RETURN e.name as error, c.name as caused_by
        LIMIT 15
    """)

    print(f"\n에러 원인 관계:")
    for r in results:
        print(f"  {r['error']:10} ← caused by → {r['caused_by']}")

    # --------------------------------------------------------
    # 6. 그래프 탐색 예제
    # --------------------------------------------------------
    print_section("6. Graph Traversal Examples")

    # Control Box에서 시작하는 모든 경로
    print("\n[예제 1] Control Box 관련 모든 연결:")
    results = store.query("""
        MATCH (c:Component {name: 'Control Box'})-[r]-(target)
        RETURN type(r) as relation, labels(target)[0] as target_type, target.name as target_name
        LIMIT 10
    """)
    for r in results:
        print(f"  Control Box -[{r['relation']}]-> {r['target_type']}: {r['target_name']}")

    # 에러 C4 관련 모든 정보
    print("\n[예제 2] 에러 C4 관련 모든 연결:")
    results = store.query("""
        MATCH (e:ErrorCode)-[r]-(target)
        WHERE e.name STARTS WITH 'C4'
        RETURN e.name as error, type(r) as relation, labels(target)[0] as target_type, target.name as target_name
        LIMIT 15
    """)
    for r in results:
        print(f"  {r['error']} -[{r['relation']}]-> {r['target_type']}: {r['target_name']}")

    # --------------------------------------------------------
    # 7. Neo4j Browser 시각화 쿼리
    # --------------------------------------------------------
    print_section("7. Neo4j Browser Visualization Queries")

    print("""
아래 쿼리를 Neo4j Browser (http://localhost:7474)에 붙여넣기 하세요!

[쿼리 1] 전체 그래프 (100개 노드 제한)
─────────────────────────────────────
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 100

[쿼리 2] Component와 ErrorCode 관계만
─────────────────────────────────────
MATCH (c:Component)-[r:HAS_ERROR]->(e:ErrorCode)
RETURN c, r, e

[쿼리 3] 특정 에러 (C4로 시작하는) 관련 그래프
─────────────────────────────────────
MATCH (e:ErrorCode)-[r]-(target)
WHERE e.name STARTS WITH 'C4'
RETURN e, r, target

[쿼리 4] Control Box 중심 그래프
─────────────────────────────────────
MATCH (c:Component {name: 'Control Box'})-[r]-(target)
RETURN c, r, target

[쿼리 5] 모든 에러 코드 (색상별 구분)
─────────────────────────────────────
MATCH (e:ErrorCode)
RETURN e

[쿼리 6] 2-hop 관계 탐색 (더 넓은 그래프)
─────────────────────────────────────
MATCH path = (c:Component)-[*1..2]-(target)
WHERE c.name = 'Control Box'
RETURN path
LIMIT 50

[쿼리 7] Document → Chunk 관계
─────────────────────────────────────
MATCH (d:Document)-[r:HAS_CHUNK]->(c:Chunk)
RETURN d, r, c
""")

    # --------------------------------------------------------
    # 8. 고급 분석
    # --------------------------------------------------------
    print_section("8. Advanced Analysis")

    # 가장 많은 에러를 가진 부품
    print("\n[분석 1] 에러가 가장 많은 부품 TOP 5:")
    results = store.query("""
        MATCH (c:Component)-[:HAS_ERROR]->(e:ErrorCode)
        RETURN c.name as component, count(e) as error_count
        ORDER BY error_count DESC
        LIMIT 5
    """)
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['component']}: {r['error_count']}개 에러")

    # 에러 코드 접두사별 통계
    print("\n[분석 2] 에러 코드 접두사별 통계:")
    results = store.query("""
        MATCH (e:ErrorCode)
        WITH e,
             CASE
                WHEN e.name STARTS WITH 'C1' THEN 'C1x'
                WHEN e.name STARTS WITH 'C2' THEN 'C2x'
                WHEN e.name STARTS WITH 'C3' THEN 'C3x'
                WHEN e.name STARTS WITH 'C4' THEN 'C4x'
                WHEN e.name STARTS WITH 'C5' THEN 'C5x'
                ELSE 'Other'
             END as prefix
        RETURN prefix, count(e) as count
        ORDER BY prefix
    """)
    for r in results:
        print(f"  {r['prefix']}: {r['count']}개")

    store.close()
    print("\n" + "=" * 60)
    print("[OK] Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
