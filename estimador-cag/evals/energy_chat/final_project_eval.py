"""Manual final-project retrieval evaluation over the real persisted support corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.energy_chat.contracts import ProjectRagRequest  # noqa: E402
from app.energy_chat.support_pgvector import (  # noqa: E402
    build_pgvector_support_rag_service_from_env,
)

DEFAULT_CASES = Path("evals/energy_chat/final_project_golden.json")
DEFAULT_OUTPUT = Path("evals/energy_chat/final_project_retrieval_report.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate final-project support retrieval.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    payload = json.loads(args.cases.read_text(encoding="utf-8"))
    service = build_pgvector_support_rag_service_from_env()
    results: list[dict[str, object]] = []
    evaluated = 0
    hits = 0

    for case in payload["cases"]:
        expected = set(case.get("expected_source_ids", []))
        if not expected:
            results.append(
                {
                    "case_id": case["case_id"],
                    "metric_status": "not_applicable_no_expected_internal_source",
                    "expected_disposition": case["expected_disposition"],
                }
            )
            continue
        rag = service.retrieve(ProjectRagRequest(query=case["query"], k=args.k))
        retrieved = [chunk.source_id for chunk in rag.results]
        hit = bool(expected.intersection(retrieved))
        evaluated += 1
        hits += int(hit)
        results.append(
            {
                "case_id": case["case_id"],
                "expected_source_ids": sorted(expected),
                "retrieved_source_ids": retrieved,
                "retrieval_hit_at_k": hit,
                "expected_disposition": case["expected_disposition"],
            }
        )

    report = {
        "schema_version": "1.1.0",
        "metric": f"retrieval_hit_at_{args.k}",
        "vector_backend": "postgresql_pgvector_hnsw",
        "cases_total": len(payload["cases"]),
        "cases_evaluated_for_retrieval": evaluated,
        "retrieval_hits": hits,
        "retrieval_hit_rate": hits / evaluated if evaluated else None,
        "claim_boundary": (
            "This report measures pgvector retrieval only. Expected dispositions are fixtures for "
            "the separate full-system agent evaluation and are not scored here."
        ),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if evaluated and hits == evaluated else 1


if __name__ == "__main__":
    raise SystemExit(main())
