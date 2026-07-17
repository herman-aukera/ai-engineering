from __future__ import annotations

import argparse
import json

from energy_core.evidence_recovery import recover_evidence_ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy valid evidence rows and quarantine invalid rows without mutation."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--recovered", required=True)
    parser.add_argument("--quarantine", required=True)
    parser.add_argument("--fail-on-quarantine", action="store_true")
    args = parser.parse_args(argv)
    report = recover_evidence_ledger(args.source, args.recovered, args.quarantine)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.fail_on_quarantine and report["quarantined_record_total"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
