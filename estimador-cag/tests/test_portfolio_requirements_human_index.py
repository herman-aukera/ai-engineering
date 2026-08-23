from __future__ import annotations

from pathlib import Path

from scripts.verify_portfolio_requirements import validate_human_index


def _payload() -> dict[str, object]:
    return {
        "requirements": [
            {"status": "PASS"},
            {"status": "PASS"},
            {"status": "BLOCKED_EXTERNAL"},
        ]
    }


def test_human_rtm_accounting_matches_machine_rtm(tmp_path: Path) -> None:
    human = tmp_path / "PORTFOLIO_REQUIREMENTS_TRACEABILITY.md"
    human.write_text(
        """## Accounting

| Classification | Rows |
|---|---:|
| Total | 3 |
| PASS | 2 |
| N/A | 0 |
| BLOCKED_EXTERNAL | 1 |
| FAIL | 0 |
""",
        encoding="utf-8",
    )

    assert validate_human_index(human, _payload()) == []


def test_human_rtm_accounting_rejects_stale_count(tmp_path: Path) -> None:
    human = tmp_path / "PORTFOLIO_REQUIREMENTS_TRACEABILITY.md"
    human.write_text(
        """## Accounting

| Classification | Rows |
|---|---:|
| Total | 2 |
| PASS | 1 |
| N/A | 0 |
| BLOCKED_EXTERNAL | 1 |
| FAIL | 0 |
""",
        encoding="utf-8",
    )

    errors = validate_human_index(human, _payload())

    assert "human RTM accounting mismatch for Total: human=2 machine=3" in errors
    assert "human RTM accounting mismatch for PASS: human=1 machine=2" in errors
