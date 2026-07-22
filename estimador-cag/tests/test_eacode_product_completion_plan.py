from __future__ import annotations

from pathlib import Path

PLAN = Path(__file__).parents[1] / "docs" / "eacode_product_completion_plan.md"


def test_product_completion_plan_has_current_required_sections() -> None:
    text = PLAN.read_text(encoding="utf-8")
    required = {
        "## Executive status",
        "## Product vision",
        "## Capability matrix",
        "## Completed phases",
        "## Remaining manual and future phases",
        "## Risk register",
        "## Acceptance gates",
        "## Current merge target",
        "## Claim boundary",
    }

    assert required.issubset(set(text.splitlines()))


def test_product_completion_plan_anchors_authoritative_checkpoint() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "eacode_release_checkpoint_2026-07-22.md" in text
    assert "PR #15" in text
    assert "EACODE" in text
    assert "production-ready" in text
    assert "manual host" in text
    assert "deterministic alpha" in text
