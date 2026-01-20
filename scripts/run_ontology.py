# ============================================================
# scripts/run_ontology.py - 온톨로지 파이프라인 실행
# ============================================================
# 실행 방법: python scripts/run_ontology.py
#
# 전체 파이프라인:
#   1. 청크 로드 (data/processed/chunks/*.json)
#   2. LLM으로 엔티티 추출
#   3. Neo4j에 그래프 저장
#   4. 통계 및 테스트 쿼리
#
# 사전 요구사항:
#   - docker-compose up -d (Neo4j 실행)
#   - OPENAI_API_KEY 설정 (.env)
# ============================================================

import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.ingestion.models import load_chunks_from_json
from src.ontology.schema import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    create_component,
    create_error_code,
)
from src.ontology.graph_store import GraphStore
from src.ontology.entity_extractor import EntityExtractor


# ============================================================
# [1] 설정
# ============================================================

CHUNKS_DIR = os.path.join(project_root, "data", "processed", "chunks")

CHUNK_FILES = [
    "error_codes_chunks.json",
    "service_manual_chunks.json",
    "user_manual_chunks.json",
]

# 샘플링 설정 (전체 처리 시 비용 절감)
SAMPLE_SIZE = 10  # 각 문서에서 추출할 청크 수 (0 = 전체)


# ============================================================
# [2] 메인 파이프라인
# ============================================================

def run_ontology_pipeline():
    """온톨로지 구축 파이프라인 실행"""

    print("=" * 60)
    print("[*] UR5e Ontology Pipeline")
    print(f"    Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # --------------------------------------------------------
    # Step 1: Neo4j 연결 확인
    # --------------------------------------------------------
    print(f"\n[Step 1] Connecting to Neo4j")
    print("-" * 40)

    try:
        store = GraphStore()
        if not store.verify_connection():
            print("[ERROR] Cannot connect to Neo4j!")
            print("        Please run: docker-compose up -d")
            return None
        print("[OK] Neo4j connected")
    except Exception as e:
        print(f"[ERROR] Neo4j connection failed: {e}")
        print("        Please run: docker-compose up -d")
        return None

    # --------------------------------------------------------
    # Step 2: 청크 로드
    # --------------------------------------------------------
    print(f"\n[Step 2] Loading chunks")
    print("-" * 40)

    all_chunks = []
    chunks_by_type = {}

    for filename in CHUNK_FILES:
        filepath = os.path.join(CHUNKS_DIR, filename)
        if os.path.exists(filepath):
            chunks = load_chunks_from_json(filepath)
            doc_type = filename.replace("_chunks.json", "")
            chunks_by_type[doc_type] = chunks
            all_chunks.extend(chunks)
            print(f"    {filename}: {len(chunks)} chunks")

    print(f"\n    Total: {len(all_chunks)} chunks")

    if not all_chunks:
        print("[ERROR] No chunks found!")
        return None

    # --------------------------------------------------------
    # Step 3: 샘플링 (비용 절감)
    # --------------------------------------------------------
    if SAMPLE_SIZE > 0:
        print(f"\n[Step 3] Sampling {SAMPLE_SIZE} chunks per document")
        print("-" * 40)

        sampled_chunks = []
        for doc_type, chunks in chunks_by_type.items():
            sample = chunks[:SAMPLE_SIZE]
            sampled_chunks.extend(sample)
            print(f"    {doc_type}: {len(sample)} chunks (sampled)")

        all_chunks = sampled_chunks
        print(f"\n    Total sampled: {len(all_chunks)} chunks")

    # --------------------------------------------------------
    # Step 4: 엔티티 추출 (규칙 기반 + LLM)
    # --------------------------------------------------------
    print(f"\n[Step 4] Extracting entities (Rule-based + LLM)")
    print("-" * 40)

    extractor = EntityExtractor()

    all_entities = {}
    all_relations = []

    # 4-1. 에러 코드 청크는 규칙 기반 추출 (SUGGESTION 패턴)
    error_chunks = [c for c in all_chunks if hasattr(c.metadata, 'doc_type') and c.metadata.doc_type == 'error_code']
    other_chunks = [c for c in all_chunks if c not in error_chunks]

    if error_chunks:
        print(f"    [Rule-based] Processing {len(error_chunks)} error_code chunks...")
        err_entities, err_relations = extractor.extract_error_codes_from_chunks(error_chunks, show_progress=False)
        for e in err_entities:
            all_entities[e.id] = e
        all_relations.extend(err_relations)
        print(f"      → Extracted {len(err_entities)} entities, {len(err_relations)} relations")

    # 4-2. 나머지 청크는 LLM 추출
    if other_chunks:
        print(f"    [LLM] Processing {len(other_chunks)} other chunks...")
        other_entities, other_relations = extractor.extract_from_chunks(other_chunks, show_progress=True)
        for e in other_entities:
            if e.id not in all_entities:
                all_entities[e.id] = e
        all_relations.extend(other_relations)

    entities = list(all_entities.values())
    relations = all_relations

    print(f"\n    Entities extracted: {len(entities)}")
    print(f"    Relations extracted: {len(relations)}")

    # 엔티티 타입별 통계
    entity_stats = {}
    for e in entities:
        t = e.type.value
        entity_stats[t] = entity_stats.get(t, 0) + 1

    print("\n    By type:")
    for t, count in sorted(entity_stats.items()):
        print(f"      {t}: {count}")

    # --------------------------------------------------------
    # Step 5: Neo4j에 저장
    # --------------------------------------------------------
    print(f"\n[Step 5] Storing to Neo4j")
    print("-" * 40)

    # 기존 데이터 확인
    existing_stats = store.get_statistics()
    if existing_stats["total_entities"] > 0:
        print(f"    [INFO] Neo4j already has {existing_stats['total_entities']} entities")
        print(f"    [INFO] Adding new entities (duplicates will be merged)")

    # 엔티티 저장
    added_entities = store.add_entities(entities)

    # 관계 저장
    added_relations = store.add_relations(relations)

    # --------------------------------------------------------
    # Step 6: Document 및 Chunk 노드 추가
    # --------------------------------------------------------
    print(f"\n[Step 6] Adding Document and Chunk nodes")
    print("-" * 40)

    # Document 노드
    for doc_type in chunks_by_type.keys():
        doc_entity = Entity(
            id=f"document_{doc_type}",
            type=EntityType.DOCUMENT,
            name=f"{doc_type}.pdf",
            properties={"doc_type": doc_type}
        )
        store.add_entity(doc_entity)

    # Chunk 노드 (샘플만)
    chunk_count = 0
    for chunk in all_chunks:
        chunk_entity = Entity(
            id=chunk.id,
            type=EntityType.CHUNK,
            name=chunk.id,
            properties={
                "page": chunk.metadata.page if hasattr(chunk.metadata, 'page') else 0,
                "doc_type": chunk.metadata.doc_type if hasattr(chunk.metadata, 'doc_type') else "unknown",
            }
        )
        store.add_entity(chunk_entity)

        # Document → Chunk 관계
        doc_id = f"document_{chunk.metadata.doc_type}" if hasattr(chunk.metadata, 'doc_type') else "document_unknown"
        has_chunk_rel = Relation(
            source_id=doc_id,
            target_id=chunk.id,
            type=RelationType.HAS_CHUNK,
        )
        store.add_relation(has_chunk_rel)
        chunk_count += 1

    print(f"    Added {len(chunks_by_type)} Document nodes")
    print(f"    Added {chunk_count} Chunk nodes")

    # --------------------------------------------------------
    # Step 7: 최종 통계
    # --------------------------------------------------------
    print(f"\n[Step 7] Final Statistics")
    print("=" * 60)

    final_stats = store.get_statistics()

    print(f"\n    Total entities: {final_stats['total_entities']}")
    print(f"    Total relations: {final_stats['total_relations']}")

    print("\n    Entities by type:")
    for t, count in sorted(final_stats.get("entities_by_type", {}).items()):
        print(f"      {t}: {count}")

    print("\n    Relations by type:")
    for t, count in sorted(final_stats.get("relations_by_type", {}).items()):
        print(f"      {t}: {count}")

    print("\n" + "=" * 60)
    print(f"[OK] Ontology pipeline complete!")
    print(f"     Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return store


# ============================================================
# [3] 테스트 쿼리
# ============================================================

def run_test_queries(store: GraphStore):
    """테스트 쿼리 실행"""

    print("\n" + "=" * 60)
    print("[*] Test Queries")
    print("=" * 60)

    # 쿼리 1: 모든 에러 코드
    print("\n[Query 1] All error codes")
    print("-" * 40)
    results = store.query("""
        MATCH (e:ErrorCode)
        RETURN e.name as code, e.title as title
        LIMIT 10
    """)
    for r in results:
        print(f"    {r['code']}: {r.get('title', '')}")

    # 쿼리 2: 모든 부품
    print("\n[Query 2] All components")
    print("-" * 40)
    results = store.query("""
        MATCH (c:Component)
        RETURN c.name as name, c.component_type as type
        LIMIT 10
    """)
    for r in results:
        print(f"    {r['name']} ({r.get('type', 'unknown')})")

    # 쿼리 3: 에러와 관련된 부품
    print("\n[Query 3] Errors and related components")
    print("-" * 40)
    results = store.query("""
        MATCH (c:Component)-[:HAS_ERROR]->(e:ErrorCode)
        RETURN c.name as component, e.name as error
        LIMIT 10
    """)
    if results:
        for r in results:
            print(f"    {r['component']} → {r['error']}")
    else:
        print("    (no HAS_ERROR relations found yet)")

    # 쿼리 4: 에러 해결 절차
    print("\n[Query 4] Error resolution procedures")
    print("-" * 40)
    results = store.query("""
        MATCH (e:ErrorCode)-[:RESOLVED_BY]->(p:Procedure)
        RETURN e.name as error, p.name as procedure
        LIMIT 10
    """)
    if results:
        for r in results:
            print(f"    {r['error']} → {r['procedure']}")
    else:
        print("    (no RESOLVED_BY relations found yet)")

    # 쿼리 5: 문서별 청크 수
    print("\n[Query 5] Chunks per document")
    print("-" * 40)
    results = store.query("""
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
        RETURN d.name as document, count(c) as chunk_count
    """)
    for r in results:
        print(f"    {r['document']}: {r['chunk_count']} chunks")


# ============================================================
# [4] 실행
# ============================================================

if __name__ == "__main__":
    # 파이프라인 실행
    store = run_ontology_pipeline()

    # 테스트 쿼리 실행
    if store:
        run_test_queries(store)
        store.close()
