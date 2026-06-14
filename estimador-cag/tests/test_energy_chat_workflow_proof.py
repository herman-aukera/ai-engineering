from app.energy_chat.workflow_proof import (
    ENERGY_CHAT_BRANCH,
    ENERGY_CHAT_PROOF_SCRIPT,
    ENERGY_CHAT_VALIDATION_SCRIPT,
    ENERGY_CHAT_WORKFLOW,
    build_ci_proof_command,
    build_local_gate_command,
)


def test_energy_chat_workflow_proof_targets_dedicated_branch_and_workflow() -> None:
    assert ENERGY_CHAT_BRANCH == "gg-finalproject-energy-aware-chat"
    assert ENERGY_CHAT_WORKFLOW == "Energy Aware Chat CI"


def test_energy_chat_workflow_proof_commands_are_non_interactive() -> None:
    assert ENERGY_CHAT_PROOF_SCRIPT == "scripts/check_energy_chat_ci.sh"
    assert ENERGY_CHAT_VALIDATION_SCRIPT == "scripts/validate_energy_chat.sh"
    assert build_ci_proof_command() == "bash estimador-cag/scripts/check_energy_chat_ci.sh"
    assert build_local_gate_command() == "bash scripts/validate_energy_chat.sh"
