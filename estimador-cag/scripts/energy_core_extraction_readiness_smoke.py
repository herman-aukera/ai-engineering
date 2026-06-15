from __future__ import annotations

from pathlib import Path

from energy_core.extraction_readiness import (
    build_extraction_readiness,
    format_extraction_readiness_text,
)


def main() -> int:
    report = build_extraction_readiness(Path("."))
    print(format_extraction_readiness_text(report))
    if not report["complete"]:
        raise SystemExit("Extraction readiness report is incomplete.")
    if report["complete_check_total"] != report["check_total"]:
        raise SystemExit("Extraction readiness checks are incomplete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
