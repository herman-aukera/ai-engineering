from __future__ import annotations

from pathlib import Path

from energy_core.acceptance_trace import (
    build_acceptance_trace,
    format_acceptance_trace_text,
)


def main() -> int:
    trace = build_acceptance_trace(Path("."))
    print(format_acceptance_trace_text(trace))
    if not trace["complete"]:
        raise SystemExit("Acceptance trace is incomplete.")
    if trace["criterion_total"] < 9:
        raise SystemExit("Acceptance trace did not find all baseline criteria.")
    print("Energy Core acceptance trace smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
