from __future__ import annotations

from pathlib import Path

PLAN = Path(__file__).parents[1] / "docs" / "eacode_product_completion_plan.md"


def test_product_completion_plan_has_required_audit_sections() -> None:
    text = PLAN.read_text(encoding="utf-8")
    required = {
        "## Verified current state",
        "## Product vision",
        "## Capability matrix",
        "## Gap matrix",
        "## Dependency graph",
        "## Ordered phases",
        "## Risk register",
        "## Acceptance gates",
        "## Deferred capabilities",
        "## Evidence level",
        "## Current checkpoint",
        "## Next slice",
    }

    assert required.issubset(set(text.splitlines()))


def test_product_completion_plan_anchors_verified_remote_baseline() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "9482ef454ffae9eddcd24782dd7dcb9f5b21bc3b" in text
    assert "PR #4" in text
    assert "Do not merge" in text
    assert "Phase 1" in text
