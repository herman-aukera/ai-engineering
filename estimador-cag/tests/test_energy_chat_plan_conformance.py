from pathlib import Path

VALIDATION_SCRIPT = Path("scripts/validate_energy_chat.sh").read_text(encoding="utf-8")
CI_WORKFLOW = Path("../.github/workflows/ci.yml").read_text(encoding="utf-8")


def test_validation_gate_discovers_energy_chat_tests_dynamically() -> None:
    assert "find tests -maxdepth 1 -name 'test_energy_chat_*.py'" in VALIDATION_SCRIPT
    assert "energy_chat_tests" in VALIDATION_SCRIPT
    assert 'uv run pytest -q "${energy_chat_tests[@]}"' in VALIDATION_SCRIPT


def test_validation_gate_fails_when_working_tree_is_dirty() -> None:
    assert "fail_on_dirty_tree" in VALIDATION_SCRIPT
    assert "git status --short" in VALIDATION_SCRIPT
    assert "DIRTY TREE DETECTED" in VALIDATION_SCRIPT
    assert "exit 1" in VALIDATION_SCRIPT


def test_ci_runs_energy_chat_gate_on_gg_branches() -> None:
    assert '- "gg-*"' in CI_WORKFLOW
    assert "fetch-depth: 0" in CI_WORKFLOW
    assert "Energy Chat validation gate" in CI_WORKFLOW
    assert "bash scripts/validate_energy_chat.sh" in CI_WORKFLOW


def test_every_energy_chat_test_is_covered_by_dynamic_gate_pattern() -> None:
    energy_chat_tests = sorted(Path("tests").glob("test_energy_chat_*.py"))

    assert energy_chat_tests
    assert "test_energy_chat_*.py" in VALIDATION_SCRIPT
    assert Path("tests/test_energy_chat_plan_conformance.py") in energy_chat_tests
