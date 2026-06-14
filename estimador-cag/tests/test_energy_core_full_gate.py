from __future__ import annotations

from scripts.energy_core_full_gate import build_gate_commands


def test_full_gate_plan_includes_all_smoke_families() -> None:
    labels = [command.label for command in build_gate_commands(include_ruff_fix=False)]

    assert "Ruff check" in labels
    assert "Python compile" in labels
    assert "Energy Core boundary" in labels
    assert "Pytest" in labels
    assert "Energy Core smoke" in labels
    assert "Energy Core example smoke" in labels
    assert "Energy Core constraint smoke" in labels
    assert "Energy Core critic coverage smoke" in labels
    assert "Energy Core ledger integrity smoke" in labels
    assert "Energy Core release smoke" in labels
    assert "Energy Core schema smoke" in labels
    assert "Energy Core package smoke" in labels
    assert "Energy Core reviewer smoke" in labels
    assert "Energy Core command catalog smoke" in labels
    assert "Energy Core review pack smoke" in labels
    assert "Energy Core scaffold smoke" in labels
    assert "Energy Core export plan smoke" in labels
    assert "Energy Core root smoke" in labels
    assert "Git diff check" in labels
    assert "Git status check" in labels


def test_full_gate_plan_can_include_ruff_autofix() -> None:
    labels = [command.label for command in build_gate_commands(include_ruff_fix=True)]

    assert labels[0] == "Ruff autofix"
    assert "Ruff check" in labels


def test_full_gate_runs_from_project_and_repo_roots() -> None:
    commands = build_gate_commands(include_ruff_fix=False)
    by_label = {command.label: command for command in commands}

    assert by_label["Pytest"].cwd.name == "estimador-cag"
    assert by_label["Energy Core root smoke"].cwd.name == "ai-engineering"
    assert by_label["Git status check"].cwd.name == "ai-engineering"
