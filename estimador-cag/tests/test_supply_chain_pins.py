from __future__ import annotations

from pathlib import Path

from scripts.verify_action_pins import find_mutable_action_refs
from scripts.verify_image_pins import find_mutable_image_refs

ACTION_SHA = "11d5960a326750d5838078e36cf38b85af677262"
IMAGE_DIGEST = "sha256:" + "a" * 64


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_action_pin_validator_accepts_full_sha_and_local_action(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github/workflows/ci.yml",
        f"steps:\n  - uses: actions/checkout@{ACTION_SHA}\n  - uses: ./.github/actions/local\n",
    )
    assert find_mutable_action_refs(tmp_path) == []


def test_action_pin_validator_rejects_tags_and_branches(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github/workflows/ci.yml",
        "steps:\n  - uses: actions/checkout@v4\n  - uses: acme/tool@main\n",
    )
    errors = find_mutable_action_refs(tmp_path)
    assert len(errors) == 2
    assert any("actions/checkout@v4" in error for error in errors)
    assert any("acme/tool@main" in error for error in errors)


def test_image_pin_validator_accepts_digest_pinned_runtime_images(tmp_path: Path) -> None:
    _write(
        tmp_path / "estimador-cag/Dockerfile",
        f"FROM python:3.11-slim@{IMAGE_DIGEST} AS runtime\nFROM runtime AS final\n",
    )
    _write(
        tmp_path / ".github/workflows/ci.yml",
        f"services:\n  postgres:\n    image: postgres:16@{IMAGE_DIGEST}\n",
    )
    assert find_mutable_image_refs(tmp_path) == []


def test_image_pin_validator_rejects_mutable_ci_and_base_images(tmp_path: Path) -> None:
    _write(tmp_path / "estimador-cag/Dockerfile", "FROM python:3.11-slim\n")
    _write(
        tmp_path / ".github/workflows/ci.yml",
        "services:\n  postgres:\n    image: postgres:16\n",
    )
    errors = find_mutable_image_refs(tmp_path)
    assert any("python:3.11-slim" in error for error in errors)
    assert any("postgres:16" in error for error in errors)


def test_image_pin_validator_rejects_mutable_docker_pull_and_run(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github/workflows/ci.yml",
        "steps:\n  - run: docker pull redis:7-alpine\n  - run: docker run --rm postgres:16\n",
    )
    errors = find_mutable_image_refs(tmp_path)
    assert any("redis:7-alpine" in error for error in errors)
    assert any("postgres:16" in error for error in errors)


def test_image_pin_validator_scans_shell_scripts_outside_deploy(tmp_path: Path) -> None:
    _write(tmp_path / "scripts/container-smoke.sh", "docker pull postgres:16\n")
    errors = find_mutable_image_refs(tmp_path)
    assert any("scripts/container-smoke.sh" in error for error in errors)


def test_image_pin_validator_allows_explicit_local_dev_classification(tmp_path: Path) -> None:
    _write(
        tmp_path / "docker-compose.yml",
        "services:\n  redis:\n    image: redis:7-alpine\n",
    )
    assert find_mutable_image_refs(tmp_path) == []
