from pathlib import Path

VALIDATION_SCRIPT = Path("scripts/validate_energy_chat.sh").read_text(encoding="utf-8")
SHARED_CI_WORKFLOW = Path("../.github/workflows/ci.yml").read_text(encoding="utf-8")
DEDICATED_CI_WORKFLOW = Path("../.github/workflows/energy-chat-ci.yml").read_text(
    encoding="utf-8"
)
CI_PROOF_SCRIPT = Path("scripts/check_energy_chat_ci.sh").read_text(encoding="utf-8")


def test_validation_gate_discovers_energy_chat_tests_dynamically() -> None:
    assert "find tests -maxdepth 1 -name 'test_energy_chat_*.py'" in VALIDATION_SCRIPT
    assert "energy_chat_tests" in VALIDATION_SCRIPT
    assert 'uv run pytest -q "${energy_chat_tests[@]}"' in VALIDATION_SCRIPT


def test_validation_gate_runs_demo_payload_contracts_before_tests() -> None:
    assert "DEMO PAYLOAD CONTRACTS" in VALIDATION_SCRIPT
    assert "scripts/validate_energy_chat_demo_payloads.py" in VALIDATION_SCRIPT
    assert "uv run python scripts/validate_energy_chat_demo_payloads.py" in VALIDATION_SCRIPT
    assert VALIDATION_SCRIPT.index("DEMO PAYLOAD CONTRACTS") < VALIDATION_SCRIPT.index(
        "FOCUSED TEST DISCOVERY"
    )


def test_validation_gate_fails_when_working_tree_is_dirty() -> None:
    assert "fail_on_dirty_tree" in VALIDATION_SCRIPT
    assert "git status --short" in VALIDATION_SCRIPT
    assert "DIRTY TREE DETECTED" in VALIDATION_SCRIPT
    assert "exit 1" in VALIDATION_SCRIPT


def test_shared_ci_keeps_energy_chat_gate_as_backstop() -> None:
    assert '- "gg-*"' in SHARED_CI_WORKFLOW
    assert "fetch-depth: 0" in SHARED_CI_WORKFLOW
    assert "Energy Chat validation gate" in SHARED_CI_WORKFLOW
    assert "bash scripts/validate_energy_chat.sh" in SHARED_CI_WORKFLOW


def test_dedicated_energy_chat_ci_is_branch_scoped_and_unambiguous() -> None:
    assert "name: Energy Aware Chat CI" in DEDICATED_CI_WORKFLOW
    assert "EACHAT" in DEDICATED_CI_WORKFLOW
    assert "concurrency:" in DEDICATED_CI_WORKFLOW
    assert "cancel-in-progress: true" in DEDICATED_CI_WORKFLOW
    assert "fetch-depth: 0" in DEDICATED_CI_WORKFLOW
    assert "EXPECTED_HEAD_SHA: ${{ github.sha }}" in DEDICATED_CI_WORKFLOW
    assert "ref: ${{ env.EXPECTED_HEAD_SHA }}" in DEDICATED_CI_WORKFLOW
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD_SHA"' in DEDICATED_CI_WORKFLOW
    assert "bash scripts/validate_energy_chat.sh" in DEDICATED_CI_WORKFLOW
    assert "gg-energy-aware-code" not in DEDICATED_CI_WORKFLOW


def test_ci_proof_helper_uses_exact_commit_and_robust_workflow_lookup() -> None:
    assert "Energy Aware Chat CI" in CI_PROOF_SCRIPT
    assert "CI - Estimador CAG" in CI_PROOF_SCRIPT
    assert "GITHUB_REPOSITORY" in CI_PROOF_SCRIPT
    assert "/actions/runs?per_page=100" in CI_PROOF_SCRIPT
    assert "--paginate" in CI_PROOF_SCRIPT
    assert ".head_branch" in CI_PROOF_SCRIPT
    assert ".head_sha" in CI_PROOF_SCRIPT
    assert ".name ==" in CI_PROOF_SCRIPT
    assert '--workflow "$WORKFLOW"' not in CI_PROOF_SCRIPT
    assert '--commit "$SHA"' not in CI_PROOF_SCRIPT
    assert "Do not use the interactive gh run selector" in CI_PROOF_SCRIPT
    assert "gh run view --log-failed" not in CI_PROOF_SCRIPT
    assert "--log-failed" in CI_PROOF_SCRIPT


def test_every_energy_chat_test_is_covered_by_dynamic_gate_pattern() -> None:
    energy_chat_tests = sorted(Path("tests").glob("test_energy_chat_*.py"))

    assert energy_chat_tests
    assert "test_energy_chat_*.py" in VALIDATION_SCRIPT
    assert Path("tests/test_energy_chat_plan_conformance.py") in energy_chat_tests
