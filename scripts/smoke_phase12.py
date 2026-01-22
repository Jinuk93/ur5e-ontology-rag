"""Phase 12 smoke test.

End-to-end flow:
QueryClassifier -> OntologyEngine -> ResponseGenerator

This is a lightweight sanity check for local development.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_root_on_syspath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def main() -> int:
    _ensure_repo_root_on_syspath()

    from src.rag import QueryClassifier, ResponseGenerator
    from src.ontology import OntologyEngine

    classifier = QueryClassifier()
    engine = OntologyEngine()
    generator = ResponseGenerator()

    queries = [
        "Fz가 -350N인데 이게 뭐야?",
        "충돌이 왜 발생했어?",
        "C153이 왜 자꾸 떠?",
        "뭔가 이상해",
    ]

    for q in queries:
        cls = classifier.classify(q)
        entities = [e.to_dict() for e in cls.entities]
        reasoning = engine.reason(q, entities)
        resp = generator.generate(cls, reasoning)

        print("\nQ:", q)
        print("  type:", cls.query_type.value, "cls_conf:", round(cls.confidence, 3), "entities:", [(e.entity_id, e.entity_type) for e in cls.entities])
        print("  gate_abstain:", resp.abstain, "reason:", resp.abstain_reason)
        print("  answer:", resp.answer[:120])
        print("  reasoning:", resp.reasoning)
        print("  evidence_keys:", sorted(resp.evidence.keys()))
        print("  graph:", len(resp.graph.get("nodes", [])), "nodes /", len(resp.graph.get("edges", [])), "edges")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
