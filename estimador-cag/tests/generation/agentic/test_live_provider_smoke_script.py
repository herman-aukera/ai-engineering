import importlib.util
import subprocess
import sys
from pathlib import Path


def load_smoke_script():
    script_path = Path("scripts/session12_live_provider_smoke.py")
    spec = importlib.util.spec_from_file_location(
        "session12_live_provider_smoke",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_provider_specs_cheap_matrix_uses_current_low_cost_models():
    module = load_smoke_script()

    specs = module.resolve_provider_specs(
        provider="all",
        tier="cheap",
        model_override=None,
        env={},
    )

    assert [(spec.provider, spec.model) for spec in specs] == [
        ("deepseek", "deepseek-v4-flash"),
        ("kimi", "kimi-k2.6"),
        ("openai", "gpt-5.4-mini"),
    ]
    assert [spec.temperature for spec in specs] == [0.0, 1.0, 0.0]


def test_resolve_provider_specs_final_matrix_uses_current_final_models():
    module = load_smoke_script()

    specs = module.resolve_provider_specs(
        provider="all",
        tier="final",
        model_override=None,
        env={},
    )

    assert [(spec.provider, spec.model) for spec in specs] == [
        ("deepseek", "deepseek-v4-pro"),
        ("kimi", "kimi-k2.7-code"),
        ("openai", "gpt-5.5"),
    ]
    assert [spec.temperature for spec in specs] == [0.0, 1.0, None]


def test_dry_run_prints_matrix_without_creating_artifacts(tmp_path, capsys):
    module = load_smoke_script()

    exit_code = module.main(
        [
            "--provider",
            "all",
            "--tier",
            "cheap",
            "--dry-run",
            "--output-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No live calls executed." in captured.out
    assert "deepseek" in captured.out
    assert "kimi" in captured.out
    assert "openai" in captured.out
    assert list(tmp_path.iterdir()) == []


def test_live_mode_without_required_key_fails_without_secret_leak(tmp_path, capsys):
    module = load_smoke_script()
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text(
        "Client needs JWT authentication and audit logging for a finance app.",
        encoding="utf-8",
    )

    exit_code = module.main(
        [
            "--provider",
            "deepseek",
            "--tier",
            "cheap",
            "--live",
            "--transcript-file",
            str(transcript_path),
            "--output-dir",
            str(tmp_path),
        ],
        env={},
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Missing API key" in captured.out
    assert "DEEPSEEK_API_KEY" in captured.out
    assert "sk-" not in captured.out


def test_build_live_smoke_artifact_excludes_api_keys():
    module = load_smoke_script()

    spec = module.ProviderSpec(
        provider="openai",
        tier="cheap",
        model="gpt-5.4-mini",
        base_url=None,
        api_key_env_names=("OPENAI_API_KEY",),
        api_key="fake_api_key_this_must_not_appear",
    )

    artifact = module.build_live_smoke_artifact(
        spec=spec,
        steps=[],
        transcript="Client needs JWT authentication and audit logging.",
    )

    serialized = module.json.dumps(artifact)
    assert "fake_api_key_this_must_not_appear" not in serialized
    assert artifact["provider"] == "openai"
    assert artifact["tier"] == "cheap"
    assert artifact["model"] == "gpt-5.4-mini"


def test_script_can_run_as_direct_file_in_dry_run():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/session12_live_provider_smoke.py",
            "--provider",
            "all",
            "--tier",
            "cheap",
            "--dry-run",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Resolved provider matrix:" in completed.stdout
    assert "No live calls executed." in completed.stdout
    assert "ModuleNotFoundError" not in completed.stderr


def test_resolve_provider_specs_temperature_override_for_single_provider():
    module = load_smoke_script()

    specs = module.resolve_provider_specs(
        provider="kimi",
        tier="cheap",
        model_override=None,
        env={},
        temperature_override=0.7,
    )

    assert len(specs) == 1
    assert specs[0].provider == "kimi"
    assert specs[0].temperature == 0.7
