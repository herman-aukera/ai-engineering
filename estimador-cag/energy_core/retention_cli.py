from __future__ import annotations

import argparse
import json

from energy_core.evidence import read_evidence_records
from energy_core.retention import build_retention_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report evidence retention eligibility without deleting records."
    )
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args(argv)
    report = build_retention_report(read_evidence_records(args.evidence))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
