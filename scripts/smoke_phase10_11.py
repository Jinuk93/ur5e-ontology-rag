"""Phase 10/11 smoke test.

Runs a minimal end-to-end flow:
- EntityExtractor → QueryClassifier → OntologyEngine.reason()

This is intentionally small and safe to run locally.
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

    from src.rag.entity_extractor import EntityExtractor
    from src.rag.query_classifier import QueryClassifier
    from src.ontology.ontology_engine import OntologyEngine

    queries = [
        "Fz가 -350N인데 이게 뭐야?",
        "C153이 왜 자꾸 떠?",
        "충돌이 왜 발생했어?",
        "Tx도 확인해줘",
    ]

    extractor = EntityExtractor()
    classifier = QueryClassifier(entity_extractor=extractor)
    engine = OntologyEngine()

    for q in queries:
        cls = classifier.classify(q)
        entities = [(e.text, e.entity_id, e.entity_type) for e in cls.entities]

        print("\nQ:", q)
        print("  type:", cls.query_type.value, "conf:", round(cls.confidence, 3), "scores:", cls.metadata.get("scores"))
        print("  entities:", entities)

        rr = engine.reason(q, [e.to_dict() for e in cls.entities])
        print(
            "  reasoning_steps:",
            len(rr.reasoning_chain),
            "conclusions:",
            len(rr.conclusions),
            "predictions:",
            len(rr.predictions),
        )
        print("  sample_paths:", rr.ontology_paths[:3])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
