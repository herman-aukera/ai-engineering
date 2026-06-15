from __future__ import annotations

from pathlib import Path

from energy_core.surface_consistency import (
    build_surface_consistency,
    format_surface_consistency_text,
)


def main() -> None:
    report = build_surface_consistency(Path("."))
    print(format_surface_consistency_text(report))
    assert report["complete"] is True
    assert not report["missing_surface_ids"]
    assert report["complete_surface_total"] == report["surface_total"]
    print("Energy Core surface consistency smoke passed.")


if __name__ == "__main__":
    main()
