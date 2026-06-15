from __future__ import annotations

from pathlib import Path

from energy_core.review_gap_register import (
    build_review_gap_register,
    format_review_gap_register_text,
)


def main() -> int:
    register = build_review_gap_register(Path("."))
    print(format_review_gap_register_text(register))
    assert register["complete"] is True
    assert register["blocking_gap_total"] == 0
    assert register["gap_total"] >= 1
    print("Energy Core review gap register smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
