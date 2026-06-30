"""
Offline Session 11 citation verification demo.

This script intentionally plants one dangling citation so reviewers can verify
that the post-generation citation audit detects a source id that was not passed
to the model as retrieved context.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.estimation import EstimateLineItem, SourceReference  # noqa: E402
from app.services.citation_verification import verify_citations  # noqa: E402


def build_demo_payload() -> dict:
    retrieved_chunk_ids = {"chunk-001"}

    estimate_lines = [
        EstimateLineItem(
            component="Payments module",
            hours=24,
            rationale="Grounded in the retrieved historical payment module.",
            grounded=True,
            sources=[
                SourceReference(
                    chunk_id="chunk-001",
                    document_id="BUDGET-2024-0001",
                    evidence="Payments module: 24 hours",
                )
            ],
        ),
        EstimateLineItem(
            component="Invented reporting module",
            hours=16,
            rationale="This line intentionally cites a chunk that was not retrieved.",
            grounded=True,
            sources=[
                SourceReference(
                    chunk_id="chunk-999",
                    document_id="BUDGET-DOES-NOT-EXIST",
                    evidence="Reporting module: 16 hours",
                )
            ],
        ),
    ]

    report = verify_citations(
        estimate_lines,
        retrieved_chunk_ids,
    )

    report_payload = report.model_dump(mode="json")
    report_payload["has_dangling"] = report.has_dangling

    return {
        "scenario": "session11_planted_dangling_citation",
        "retrieved_chunk_ids": sorted(retrieved_chunk_ids),
        "citation_report": report_payload,
    }


def main() -> None:
    print(json.dumps(build_demo_payload(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
