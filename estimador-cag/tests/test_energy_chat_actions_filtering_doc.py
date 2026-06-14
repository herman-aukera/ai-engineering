from pathlib import Path

ACTIONS_FILTERING = Path("docs/energy_aware_chat_actions_filtering.md").read_text(
    encoding="utf-8"
)


def test_actions_filtering_guide_names_exact_energy_chat_proof_target() -> None:
    assert "All workflows" in ACTIONS_FILTERING
    assert "Energy Aware Chat CI" in ACTIONS_FILTERING
    assert "gg-finalproject-energy-aware-chat" in ACTIONS_FILTERING
    assert "bash estimador-cag/scripts/check_energy_chat_ci.sh" in ACTIONS_FILTERING


def test_actions_filtering_guide_distinguishes_unrelated_runs() -> None:
    assert "unrelated red runs" in ACTIONS_FILTERING
    assert "exact commit SHA" in ACTIONS_FILTERING
