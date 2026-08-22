from __future__ import annotations

from pathlib import Path

from scripts.verify_image_pins import find_mutable_image_refs
from scripts.verify_tool_pins import find_mutable_tool_refs, find_root_toolchain_errors

DIGEST = "sha256:" + "a" * 64


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_docker_run_parser_ignores_ports_and_database_urls(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github/workflows/canary.yml",
        "steps:\n"
        "  - run: |\n"
        "      docker run --detach --name app --publish 8010:8000 \\\n"
        "        --env DATABASE_URL=postgresql://user:pass@db:5432/app \\\n"
        f"        postgres:16@{DIGEST}\n",
    )
    assert find_mutable_image_refs(tmp_path) == []


def test_docker_run_parser_still_rejects_actual_mutable_image(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github/workflows/canary.yml",
        "steps:\n"
        "  - run: docker run --publish 8010:8000 --env DATABASE_URL=postgresql://db:5432/app postgres:16\n",
    )
    errors = find_mutable_image_refs(tmp_path)
    assert len(errors) == 1
    assert "postgres:16" in errors[0]


def test_root_toolchain_contract_requires_exact_uv_and_python(tmp_path: Path) -> None:
    _write(tmp_path / "uv.toml", 'required-version = "==0.12.5"\n')
    _write(tmp_path / ".python-version", "3.11.16\n")
    assert find_root_toolchain_errors(tmp_path) == []


def test_root_toolchain_contract_rejects_ranges(tmp_path: Path) -> None:
    _write(tmp_path / "uv.toml", 'required-version = ">=0.12"\n')
    _write(tmp_path / ".python-version", "3.11\n")
    errors = find_root_toolchain_errors(tmp_path)
    assert any("uv.toml" in error for error in errors)
    assert any(".python-version" in error for error in errors)


def test_uvx_filesystem_copy_is_not_treated_as_command(tmp_path: Path) -> None:
    _write(
        tmp_path / "estimador-cag/Dockerfile",
        f"FROM ghcr.io/astral-sh/uv:0.12.5@{DIGEST} AS uv-binary\n"
        f"FROM python:3.11-slim@{DIGEST}\n"
        "COPY --from=uv-binary /uv /uvx /bin/\n",
    )
    assert find_mutable_tool_refs(tmp_path) == []
