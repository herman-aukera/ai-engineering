from __future__ import annotations

from pathlib import Path

from energy_core.policy_roadmap import (
    build_policy_roadmap,
    format_policy_roadmap_markdown,
)

POLICY = Path(".energy/specs/0001-energy-policy-ledger/energy-policy.yaml")


def main() -> int:
    roadmap = build_policy_roadmap(POLICY)
    markdown = format_policy_roadmap_markdown(roadmap)

    assert roadmap["complete"] is True
    assert roadmap["coverage_level"] == "partial"
    assert roadmap["policy_only_total"] == 4
    assert "# Energy Aware Code Policy Roadmap" in markdown
    assert "unsafe_command" in markdown
    assert "wrong_branch" in markdown

    print("Energy Core policy roadmap smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
