# ============================================================
# src/rag/graph_retriever.py - GraphDB 검색기
# ============================================================
# Neo4j GraphDB에서 관계 기반 검색을 수행합니다.
#
# 주요 기능:
#   - 에러 해결 검색 (ErrorCode → RESOLVED_BY → Procedure)
#   - 부품 에러 검색 (Component → HAS_ERROR → ErrorCode)
#   - 에러 원인 검색 (ErrorCode → CAUSED_BY → Component)
# ============================================================

import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.ontology.graph_store import GraphStore
from src.ontology.schema import EntityType, RelationType


# ============================================================
# [1] GraphResult 데이터 클래스
# ============================================================

@dataclass
class GraphResult:
    """
    Graph 검색 결과

    Attributes:
        content: 텍스트 내용 (컨텍스트용)
        entity_type: 엔티티 타입 (ErrorCode, Component, Procedure)
        entity_name: 엔티티 이름
        related_entities: 관련 엔티티 리스트
        relation_type: 관계 타입
        metadata: 추가 메타데이터
        score: 관련성 점수 (Graph는 기본 1.0)
    """
    content: str
    entity_type: str
    entity_name: str
    related_entities: List[Dict[str, Any]] = field(default_factory=list)
    relation_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 1.0  # Graph 결과는 정확 매칭이므로 높은 점수

    def __repr__(self):
        return f"GraphResult(entity={self.entity_name}, type={self.entity_type}, relations={len(self.related_entities)})"


# ============================================================
# [2] GraphRetriever 클래스
# ============================================================

class GraphRetriever:
    """
    GraphDB 기반 검색기

    Neo4j에서 관계 기반 검색을 수행합니다.

    사용 예시:
        retriever = GraphRetriever()
        results = retriever.search_error_resolution("C4A15")
        for r in results:
            print(r.content)
    """

    def __init__(self):
        """GraphRetriever 초기화"""
        self.graph_store = GraphStore()
        print("[OK] GraphRetriever initialized")

    def close(self):
        """연결 종료"""
        self.graph_store.close()

    # --------------------------------------------------------
    # [2.1] 에러 해결 검색
    # --------------------------------------------------------

    def search_error_resolution(self, error_code: str) -> List[GraphResult]:
        """
        에러 코드의 해결 방법 검색

        Cypher:
            MATCH (e:ErrorCode)-[:RESOLVED_BY]->(p:Procedure)
            WHERE e.name CONTAINS $error_code
            RETURN e, p

        Args:
            error_code: 에러 코드 (예: "C4A15", "C50")

        Returns:
            List[GraphResult]: 검색 결과
        """
        # 에러 코드로 시작하는 모든 매칭 (C4 → C4, C4A1, C4A15 등)
        query = """
        MATCH (e:ErrorCode)-[:RESOLVED_BY]->(p:Procedure)
        WHERE e.name STARTS WITH $error_code OR e.name = $error_code
        RETURN e, p, 'RESOLVED_BY' as rel_type
        ORDER BY e.name
        """

        results = []
        try:
            raw_results = self.graph_store.query(query, {"error_code": error_code.upper()})

            for record in raw_results:
                error_node = record['e']
                procedure_node = record['p']

                # 컨텍스트 텍스트 구성
                content = self._format_error_resolution(error_node, procedure_node)

                result = GraphResult(
                    content=content,
                    entity_type="ErrorCode",
                    entity_name=error_node.get('name', ''),
                    related_entities=[{
                        "type": "Procedure",
                        "name": procedure_node.get('name', ''),
                        "properties": dict(procedure_node),
                    }],
                    relation_type="RESOLVED_BY",
                    metadata={
                        "error_code": error_node.get('name', ''),
                        "title": error_node.get('title', ''),
                        "source": "GraphDB",
                    },
                    score=1.0,
                )
                results.append(result)

        except Exception as e:
            print(f"[ERROR] search_error_resolution failed: {e}")

        return results

    def _format_error_resolution(self, error_node: dict, procedure_node: dict) -> str:
        """에러 해결 정보를 텍스트로 포맷팅"""
        error_name = error_node.get('name', 'Unknown')
        error_title = error_node.get('title', '')
        procedure_name = procedure_node.get('name', '')

        content = f"에러 코드: {error_name}\n"
        if error_title:
            content += f"설명: {error_title}\n"
        content += f"해결 방법: {procedure_name}"

        return content

    # --------------------------------------------------------
    # [2.2] 에러 정보 검색 (해결책 없이)
    # --------------------------------------------------------

    def search_error_info(self, error_code: str) -> List[GraphResult]:
        """
        에러 코드 정보만 검색 (해결책 없이)

        Args:
            error_code: 에러 코드

        Returns:
            List[GraphResult]: 검색 결과
        """
        query = """
        MATCH (e:ErrorCode)
        WHERE e.name STARTS WITH $error_code OR e.name = $error_code
        RETURN e
        ORDER BY e.name
        LIMIT 20
        """

        results = []
        try:
            raw_results = self.graph_store.query(query, {"error_code": error_code.upper()})

            for record in raw_results:
                error_node = record['e']

                content = f"에러 코드: {error_node.get('name', '')}\n"
                if error_node.get('title'):
                    content += f"설명: {error_node.get('title', '')}"

                result = GraphResult(
                    content=content,
                    entity_type="ErrorCode",
                    entity_name=error_node.get('name', ''),
                    metadata={
                        "error_code": error_node.get('name', ''),
                        "title": error_node.get('title', ''),
                        "source": "GraphDB",
                    },
                    score=0.9,  # 해결책 없으므로 약간 낮은 점수
                )
                results.append(result)

        except Exception as e:
            print(f"[ERROR] search_error_info failed: {e}")

        return results

    # --------------------------------------------------------
    # [2.3] 부품 에러 검색
    # --------------------------------------------------------

    def search_component_errors(self, component: str) -> List[GraphResult]:
        """
        부품 관련 에러 검색

        Cypher:
            MATCH (c:Component)-[:HAS_ERROR]->(e:ErrorCode)
            WHERE c.name CONTAINS $component
            RETURN c, e

        Args:
            component: 부품명 (예: "Control Box", "Joint")

        Returns:
            List[GraphResult]: 검색 결과
        """
        query = """
        MATCH (c:Component)-[:HAS_ERROR]->(e:ErrorCode)
        WHERE toLower(c.name) CONTAINS toLower($component)
        RETURN c, e, 'HAS_ERROR' as rel_type
        ORDER BY e.name
        """

        results = []
        try:
            raw_results = self.graph_store.query(query, {"component": component})

            # 부품별로 그룹화
            component_errors = {}
            for record in raw_results:
                comp_node = record['c']
                error_node = record['e']
                comp_name = comp_node.get('name', '')

                if comp_name not in component_errors:
                    component_errors[comp_name] = {
                        "component": comp_node,
                        "errors": [],
                    }
                component_errors[comp_name]["errors"].append(error_node)

            # 결과 생성
            for comp_name, data in component_errors.items():
                errors = data["errors"]
                content = self._format_component_errors(data["component"], errors)

                result = GraphResult(
                    content=content,
                    entity_type="Component",
                    entity_name=comp_name,
                    related_entities=[{
                        "type": "ErrorCode",
                        "name": e.get('name', ''),
                        "title": e.get('title', ''),
                    } for e in errors],
                    relation_type="HAS_ERROR",
                    metadata={
                        "component": comp_name,
                        "error_count": len(errors),
                        "source": "GraphDB",
                    },
                    score=1.0,
                )
                results.append(result)

        except Exception as e:
            print(f"[ERROR] search_component_errors failed: {e}")

        return results

    def _format_component_errors(self, component: dict, errors: list) -> str:
        """부품 에러 정보를 텍스트로 포맷팅"""
        comp_name = component.get('name', 'Unknown')

        content = f"부품: {comp_name}\n"
        content += f"관련 에러 코드 ({len(errors)}개):\n"

        for i, error in enumerate(errors[:10], 1):  # 최대 10개만
            error_name = error.get('name', '')
            error_title = error.get('title', '')
            content += f"  {i}. {error_name}"
            if error_title:
                content += f" - {error_title}"
            content += "\n"

        if len(errors) > 10:
            content += f"  ... 외 {len(errors) - 10}개\n"

        return content

    # --------------------------------------------------------
    # [2.4] 에러 원인 검색
    # --------------------------------------------------------

    def search_error_causes(self, error_code: str) -> List[GraphResult]:
        """
        에러의 원인(부품) 검색

        Cypher:
            MATCH (e:ErrorCode)-[:CAUSED_BY]->(c:Component)
            WHERE e.name CONTAINS $error_code
            RETURN e, c

        Args:
            error_code: 에러 코드

        Returns:
            List[GraphResult]: 검색 결과
        """
        query = """
        MATCH (e:ErrorCode)-[:CAUSED_BY]->(c:Component)
        WHERE e.name STARTS WITH $error_code OR e.name = $error_code
        RETURN e, c, 'CAUSED_BY' as rel_type
        ORDER BY e.name
        """

        results = []
        try:
            raw_results = self.graph_store.query(query, {"error_code": error_code.upper()})

            for record in raw_results:
                error_node = record['e']
                comp_node = record['c']

                content = f"에러 코드: {error_node.get('name', '')}\n"
                content += f"원인 부품: {comp_node.get('name', '')}"

                result = GraphResult(
                    content=content,
                    entity_type="ErrorCode",
                    entity_name=error_node.get('name', ''),
                    related_entities=[{
                        "type": "Component",
                        "name": comp_node.get('name', ''),
                    }],
                    relation_type="CAUSED_BY",
                    metadata={
                        "error_code": error_node.get('name', ''),
                        "caused_by": comp_node.get('name', ''),
                        "source": "GraphDB",
                    },
                    score=0.95,
                )
                results.append(result)

        except Exception as e:
            print(f"[ERROR] search_error_causes failed: {e}")

        return results

    # --------------------------------------------------------
    # [2.5] 통합 검색
    # --------------------------------------------------------

    def search(
        self,
        error_codes: List[str] = None,
        components: List[str] = None,
        include_resolutions: bool = True,
        include_causes: bool = True,
    ) -> List[GraphResult]:
        """
        통합 검색

        Args:
            error_codes: 에러 코드 리스트
            components: 부품명 리스트
            include_resolutions: 해결책 포함 여부
            include_causes: 원인 포함 여부

        Returns:
            List[GraphResult]: 검색 결과 (중복 제거됨)
        """
        results = []
        seen_keys = set()

        # 에러 코드 검색
        if error_codes:
            for error_code in error_codes:
                # 해결책 검색
                if include_resolutions:
                    for r in self.search_error_resolution(error_code):
                        key = f"resolution_{r.entity_name}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            results.append(r)

                # 원인 검색
                if include_causes:
                    for r in self.search_error_causes(error_code):
                        key = f"cause_{r.entity_name}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            results.append(r)

                # 기본 정보 (해결책 없을 때)
                if not results:
                    for r in self.search_error_info(error_code):
                        key = f"info_{r.entity_name}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            results.append(r)

        # 부품 검색
        if components:
            for component in components:
                for r in self.search_component_errors(component):
                    key = f"component_{r.entity_name}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(r)

        return results


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("[*] GraphRetriever Test")
    print("=" * 60)

    retriever = GraphRetriever()

    # 테스트 1: 에러 해결 검색
    print("\n[Test 1] Error Resolution Search: C4A15")
    print("-" * 40)
    results = retriever.search_error_resolution("C4A15")
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(f"\n{r.content}")

    # 테스트 2: 부품 에러 검색
    print("\n[Test 2] Component Errors Search: Control Box")
    print("-" * 40)
    results = retriever.search_component_errors("Control Box")
    print(f"Found {len(results)} results")
    for r in results[:2]:
        print(f"\n{r.content[:300]}...")

    # 테스트 3: 통합 검색
    print("\n[Test 3] Combined Search")
    print("-" * 40)
    results = retriever.search(
        error_codes=["C4A15", "C50"],
        components=["Safety"]
    )
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(f"  - {r.entity_type}: {r.entity_name}")

    retriever.close()

    print("\n" + "=" * 60)
    print("[OK] GraphRetriever test completed!")
    print("=" * 60)
