import json
import subprocess
import sys
from pathlib import Path


def _write_executed_artifact(
    path: Path,
    *,
    provider: str,
    tier: str,
    model: str,
    total_hours: float,
    total_cost_eur: float,
):
    path.write_text(
        json.dumps(
            {
                "schema_version": "session12.executed_provider_plan.v1",
                "provider": provider,
                "tier": tier,
                "model": model,
                "temperature": None,
                "result": {
                    "estimate": {
                        "total_hours": total_hours,
                        "total_cost_eur": total_cost_eur,
                    },
                    "validation": {
                        "valid": True,
                        "warnings": [],
                        "errors": [],
                    },
                    "terminated": True,
                },
            }
        ),
        encoding="utf-8",
    )


def test_summarize_executed_provider_plans_writes_sanitized_markdown(tmp_path):
    input_dir = tmp_path / "executed"
    input_dir.mkdir()
    output_file = tmp_path / "summary.md"

    _write_executed_artifact(
        input_dir / "cheap_deepseek_plan_executed.json",
        provider="deepseek",
        tier="cheap",
        model="deepseek-v4-flash",
        total_hours=288.0,
        total_cost_eur=21600.0,
    )
    _write_executed_artifact(
        input_dir / "final_openai_plan_executed.json",
        provider="openai",
        tier="final",
        model="gpt-5.5",
        total_hours=432.0,
        total_cost_eur=32400.0,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/session12_summarize_executed_provider_plans.py",
            "--input-dir",
            str(input_dir),
            "--output-file",
            str(output_file),
            "--expected-count",
            "2",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    content = output_file.read_text(encoding="utf-8")

    assert "# Session 12 Executed Provider Plan Summary" in content
    assert "| deepseek | cheap | deepseek-v4-flash | 288.0 | 21600.0 | True | True |" in content
    assert "| openai | final | gpt-5.5 | 432.0 | 32400.0 | True | True |" in content
    assert "api_key" not in content.lower()
    assert "bearer" not in content.lower()


def test_summarize_executed_provider_plans_fails_on_count_mismatch(tmp_path):
    input_dir = tmp_path / "executed"
    input_dir.mkdir()
    output_file = tmp_path / "summary.md"

    _write_executed_artifact(
        input_dir / "cheap_kimi_plan_executed.json",
        provider="kimi",
        tier="cheap",
        model="kimi-k2.6",
        total_hours=230.4,
        total_cost_eur=17280.0,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/session12_summarize_executed_provider_plans.py",
            "--input-dir",
            str(input_dir),
            "--output-file",
            str(output_file),
            "--expected-count",
            "6",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "expected 6 executed artifacts" in completed.stdout
