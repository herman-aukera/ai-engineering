from __future__ import annotations

import argparse
import json

from energy_core.ledger_recovery import recover_decision_ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy valid decision rows and quarantine invalid rows without changing source."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--recovered", required=True)
    parser.add_argument("--quarantine", required=True)
    parser.add_argument(
        "--fail-on-quarantine",
        action="store_true",
        help="Exit non-zero when any source row is quarantined.",
    )
    args = parser.parse_args(argv)
    report = recover_decision_ledger(args.source, args.recovered, args.quarantine)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_on_quarantine and report["quarantined_record_total"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
