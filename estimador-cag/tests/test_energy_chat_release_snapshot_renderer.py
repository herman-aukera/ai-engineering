from pathlib import Path
import subprocess
import sys

SCRIPT_PATH = Path("scripts/render_energy_chat_release_snapshot.py")
SCRIPT = SCRIPT_PATH.read_text(encoding="utf-8")


def test_release_snapshot_renderer_exposes_expected_arguments() -> None:
    assert "--commit-sha" in SCRIPT
    assert "--focused-tests" in SCRIPT
    assert "--full-tests" in SCRIPT
    assert "--local-ref" in SCRIPT
    assert "--ci-ref" in SCRIPT
    assert "--output" in SCRIPT


def test_release_snapshot_renderer_writes_markdown() -> None:
    assert "build_release_snapshot_markdown" in SCRIPT
    assert "write_text" in SCRIPT
    assert "Wrote" in SCRIPT


def test_release_snapshot_renderer_executes_from_project_root(tmp_path: Path) -> None:
    output = tmp_path / "snapshot.md"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--commit-sha",
            "smoke-sha",
            "--focused-tests",
            "118",
            "--full-tests",
            "376",
            "--local-ref",
            "local-smoke",
            "--ci-ref",
            "ci-smoke",
            "--output",
            str(output),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )

    assert "Wrote" in result.stdout
    rendered = output.read_text(encoding="utf-8")
    assert "Energy Aware Chat release snapshot" in rendered
    assert "smoke-sha" in rendered
    assert "118" in rendered
    assert "376" in rendered
