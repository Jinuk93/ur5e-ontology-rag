#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
온톨로지 빌드 및 검증 스크립트

OntologyLoader를 사용하여 ontology.json을 로드하고 검증합니다.

실행:
    python scripts/build_ontology.py
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Windows 콘솔 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.ontology import (
    Domain, EntityType, RelationType,
    Entity, Relationship, OntologySchema,
    get_domain_for_entity_type,
    validate_relationship,
)
from src.ontology.loader import (
    OntologyLoader,
    load_ontology,
    load_lexicon,
    resolve_alias,
)


def print_header(title: str):
    """섹션 헤더 출력"""
    print("\n" + "=" * 60)
    print(f"[*] {title}")
    print("=" * 60)


def print_subheader(title: str):
    """서브 섹션 헤더 출력"""
    print(f"\n[{title}]")
    print("-" * 40)


def main():
    """메인 함수"""
    print_header("UR5e Ontology Builder & Validator")

    # --------------------------------------------------------
    # 1. 온톨로지 로드
    # --------------------------------------------------------
    print_subheader("Step 1: Load Ontology")

    try:
        schema = load_ontology()
        print(f"  Version: {schema.version}")
        print(f"  Description: {schema.description}")
        print(f"  Entities: {len(schema.entities)}")
        print(f"  Relationships: {len(schema.relationships)}")
    except Exception as e:
        print(f"  [ERROR] Failed to load ontology: {e}")
        return 1

    # --------------------------------------------------------
    # 2. 통계 출력
    # --------------------------------------------------------
    print_subheader("Step 2: Statistics")

    stats = schema.get_statistics()

    print("\n  Entities by Domain:")
    for domain, count in stats["entities_by_domain"].items():
        print(f"    {domain}: {count}")

    print("\n  Relationships by Type:")
    for rel_type, count in stats["relationships_by_type"].items():
        print(f"    {rel_type}: {count}")

    # --------------------------------------------------------
    # 3. 도메인별 엔티티 상세
    # --------------------------------------------------------
    print_subheader("Step 3: Entities by Domain")

    for domain in Domain:
        entities = schema.get_entities_by_domain(domain)
        if entities:
            print(f"\n  [{domain.value.upper()}] ({len(entities)} entities)")
            for e in entities[:5]:  # 최대 5개만 출력
                print(f"    - {e.id}: {e.name} ({e.type.value})")
            if len(entities) > 5:
                print(f"    ... and {len(entities) - 5} more")

    # --------------------------------------------------------
    # 4. 관계 검증
    # --------------------------------------------------------
    print_subheader("Step 4: Relationship Validation")

    valid_count = 0
    invalid_count = 0
    invalid_rels = []

    for rel in schema.relationships:
        source = schema.get_entity(rel.source)
        target = schema.get_entity(rel.target)

        if source and target:
            is_valid = validate_relationship(
                rel.relation, source.type, target.type
            )
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                invalid_rels.append((rel, source, target))
        else:
            invalid_count += 1
            invalid_rels.append((rel, source, target))

    print(f"\n  Valid relationships: {valid_count}")
    print(f"  Invalid relationships: {invalid_count}")

    if invalid_rels and invalid_count <= 10:
        print("\n  Invalid relationship details:")
        for rel, src, tgt in invalid_rels:
            src_info = f"{src.id}({src.type.value})" if src else f"{rel.source}(NOT_FOUND)"
            tgt_info = f"{tgt.id}({tgt.type.value})" if tgt else f"{rel.target}(NOT_FOUND)"
            print(f"    - {src_info} --[{rel.relation.value}]--> {tgt_info}")

    # --------------------------------------------------------
    # 5. Lexicon 로드 및 테스트
    # --------------------------------------------------------
    print_subheader("Step 5: Lexicon Test")

    try:
        lexicon = load_lexicon()
        print(f"  Lexicon loaded successfully")

        # 에러 코드 카테고리
        error_codes = lexicon.get("error_codes", {})
        components = lexicon.get("components", {})
        print(f"  Error codes: {len(error_codes)}")
        print(f"  Components: {len(components)}")

        # 동의어 테스트
        test_terms = ["c153", "C-153", "control box", "컨트롤 박스", "joint 0"]
        print("\n  Alias Resolution Test:")
        for term in test_terms:
            resolved = resolve_alias(term)
            print(f"    '{term}' -> '{resolved}'")

    except Exception as e:
        print(f"  [WARN] Lexicon not available: {e}")

    # --------------------------------------------------------
    # 6. 샘플 쿼리
    # --------------------------------------------------------
    print_subheader("Step 6: Sample Queries")

    # 쿼리 1: UR5e의 모든 컴포넌트
    print("\n  Query 1: UR5e Components")
    ur5e_rels = schema.get_relationships_for_entity("UR5e", direction="outgoing")
    for rel in ur5e_rels:
        if rel.relation == RelationType.HAS_COMPONENT:
            target = schema.get_entity(rel.target)
            if target:
                print(f"    - {target.name} ({target.type.value})")

    # 쿼리 2: Axia80이 측정하는 축
    print("\n  Query 2: Axia80 Measurement Axes")
    axia_rels = schema.get_relationships_for_entity("Axia80", direction="outgoing")
    for rel in axia_rels:
        if rel.relation == RelationType.MEASURES:
            target = schema.get_entity(rel.target)
            if target:
                print(f"    - {target.name}")

    # 쿼리 3: C153 에러의 원인
    print("\n  Query 3: C153 Error Causes")
    c153_rels = schema.get_relationships_for_entity("C153", direction="outgoing")
    for rel in c153_rels:
        if rel.relation == RelationType.CAUSED_BY:
            target = schema.get_entity(rel.target)
            if target:
                print(f"    - {target.name}")

    # 쿼리 4: 충돌 패턴이 트리거하는 에러
    print("\n  Query 4: Collision Pattern Triggers")
    collision_rels = schema.get_relationships_for_entity("PAT_COLLISION", direction="outgoing")
    for rel in collision_rels:
        if rel.relation == RelationType.TRIGGERS:
            target = schema.get_entity(rel.target)
            props = rel.properties
            prob = props.get("probability", "N/A")
            if target:
                print(f"    - {target.name} (probability: {prob})")

    # --------------------------------------------------------
    # 완료
    # --------------------------------------------------------
    print_header("Build Complete")
    print(f"\n  Total Entities: {len(schema.entities)}")
    print(f"  Total Relationships: {len(schema.relationships)}")
    print(f"  Validation: {'PASS' if invalid_count == 0 else 'WARN'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
