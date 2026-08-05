"""Workflow proof constants for Energy Aware Chat.

These constants define the narrow proof target for this product branch.
They intentionally do not describe every GitHub Actions run in the repository.
"""

ENERGY_CHAT_BRANCH = "EACHAT"
ENERGY_CHAT_WORKFLOW = "Energy Aware Chat CI"
ENERGY_CHAT_PROOF_SCRIPT = "scripts/check_energy_chat_ci.sh"
ENERGY_CHAT_VALIDATION_SCRIPT = "scripts/validate_energy_chat.sh"


def build_ci_proof_command() -> str:
    """Return the repository-root command that proves the exact current commit."""

    return f"bash estimador-cag/{ENERGY_CHAT_PROOF_SCRIPT}"


def build_local_gate_command() -> str:
    """Return the project-root command that runs the Energy Chat local gate."""

    return f"bash {ENERGY_CHAT_VALIDATION_SCRIPT}"
