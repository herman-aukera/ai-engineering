from __future__ import annotations

from energy_core.acceptance_trace import TRACE_VERSION


def main() -> int:
    print(f"Energy Aware Code Acceptance Trace {TRACE_VERSION}")
    print("Energy Core acceptance trace smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
