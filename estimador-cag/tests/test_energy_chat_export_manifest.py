import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCRIPT = ROOT / "scripts" / "export_energy_chat_manifest.sh"


def _bash_executable() -> str:
    if sys.platform == "win32":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            program_files = os.getenv(variable)
            if program_files:
                candidate = Path(program_files) / "Git" / "bin" / "bash.exe"
                if candidate.is_file():
                    return str(candidate)
        git = shutil.which("git")
        if git:
            for parent in Path(git).resolve().parents:
                candidate = parent / "bin" / "bash.exe"
                if candidate.is_file():
                    return str(candidate)
    return "bash"


def _manifest_output() -> str:
    result = subprocess.run(
        [_bash_executable(), str(MANIFEST_SCRIPT)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_export_manifest_script_runs_and_names_target_repository() -> None:
    output = _manifest_output()

    assert "Energy Aware Chat standalone export manifest" in output
    assert "herman-aukera/energy-aware-chat" in output
    assert "EACHAT" in output
    assert "gg-finalproject-energy-aware-chat" not in output


def test_export_manifest_includes_runtime_demo_and_test_boundaries() -> None:
    output = _manifest_output()
    required_paths = [
        "app/energy_chat/",
        "energy_chat_streamlit_app.py",
        "demo_payloads/energy_chat/",
        "scripts/validate_energy_chat.sh",
        "scripts/check_energy_chat_ci.sh",
        "scripts/smoke_energy_chat_live_provider.py",
        "scripts/start_energy_chat.sh",
        "scripts/export_energy_chat_manifest.sh",
        "scripts/render_energy_chat_release_snapshot.py",
        "Dockerfile.energy-chat",
        "docker-compose.energy-chat.yml",
        "tests/test_energy_chat_*.py",
        "../.github/workflows/energy-chat-ci.yml",
        "../.github/workflows/energy-chat-live-provider-smoke.yml",
    ]

    for path in required_paths:
        assert path in output


def test_export_manifest_includes_reviewer_docs_and_claim_boundary() -> None:
    output = _manifest_output()
    required_docs = [
        "docs/energy_aware_chat_demo.md",
        "docs/energy_aware_chat_live_demo_readiness.md",
        "docs/energy_aware_chat_api_smoke_guide.md",
        "docs/energy_aware_chat_demo_results_template.md",
        "docs/energy_aware_chat_reviewer_index.md",
        "docs/energy_aware_chat_final_project_proof_packet.md",
        "docs/energy_aware_chat_mvp_upgrade.md",
        "docs/energy_aware_chat_repository_readiness.md",
        "docs/energy_aware_chat_final_project_delivery_plan.md",
        "docs/energy_aware_chat_demo_walkthrough.md",
        "docs/energy_aware_chat_session17_backlog.md",
        "docs/energy_aware_chat_standalone_export_readme.md",
    ]

    for doc in required_docs:
        assert doc in output

    assert "measurement_only_no_quality_claim" in output
    assert "quality improvement over DeepSeek" in output
    assert "public deployment is live" in output


def test_export_manifest_requires_local_and_ci_proof_before_export() -> None:
    output = _manifest_output()

    assert "bash scripts/validate_energy_chat.sh" in output
    assert "bash scripts/check_energy_chat_ci.sh" in output
    assert "git status --short" in output
