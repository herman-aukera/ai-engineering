"""Print the deterministic EACODE governance benchmark report as JSON."""

from __future__ import annotations

import json

from energy_core.governance_benchmark import run_governance_benchmark


def main() -> int:
    report = run_governance_benchmark()
    print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0 if report.governed_correct == report.total_cases else 1


if __name__ == "__main__":
    raise SystemExit(main())
