"""Render the deterministic Energy Aware Chat fixed benchmark report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.energy_chat.fixed_benchmark import (  # noqa: E402
    render_fixed_benchmark_markdown,
    run_fixed_benchmark,
)

REPORT_PATH = PROJECT_ROOT / "docs" / "energy_aware_chat_fixed_benchmark_report.md"
JSON_PATH = PROJECT_ROOT / "evals" / "energy_chat" / "fixed_benchmark_result.json"


def main() -> None:
    result = run_fixed_benchmark()
    REPORT_PATH.write_text(render_fixed_benchmark_markdown(result), encoding="utf-8")
    JSON_PATH.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {JSON_PATH.relative_to(PROJECT_ROOT)}")
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "cases_total": result.cases_total,
                "accepted_baseline": result.accepted_baseline,
                "accepted_after_repair": result.accepted_after_repair,
                "claim_status": result.metadata["claim_status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
