"""Apply the deterministic/live-provider CI boundary idempotently."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def update_provider_tests() -> None:
    relative = "estimador-cag/tests/test_session13_plus_provider_calibration.py"
    content = read(relative)
    old = '''def _has_deepseek_key() -> bool:\n    key = os.environ.get("DEEPSEEK_API_KEY", "")\n    return bool(key) and key not in ("dummy", "fake")\n'''
    new = '''_NON_LIVE_KEY_SENTINELS = {"", "test", "dummy", "fake", "placeholder", "example"}\n\n\ndef _has_deepseek_key() -> bool:\n    key = os.environ.get("DEEPSEEK_API_KEY", "").strip().lower()\n    return key not in _NON_LIVE_KEY_SENTINELS\n'''
    if old in content:
        content = content.replace(old, new, 1)
    elif "_NON_LIVE_KEY_SENTINELS" not in content:
        raise RuntimeError("Provider credential gate no longer matches audited source")

    output: list[str] = []
    marked = 0
    for line in content.splitlines():
        if line == "@pytest.mark.skipif(" and marked < 3:
            if not output or output[-1] != "@pytest.mark.live_provider":
                output.append("@pytest.mark.live_provider")
            marked += 1
        output.append(line)
    if marked != 3:
        raise RuntimeError(f"Expected three live-provider tests, found {marked}")
    write(relative, "\n".join(output) + "\n")


def update_pytest_config() -> None:
    relative = "estimador-cag/pyproject.toml"
    content = read(relative)
    marker = "live_provider: requires explicit real provider credentials"
    if marker in content:
        return
    addition = '''\n[tool.pytest.ini_options]\nmarkers = [\n    "live_provider: requires explicit real provider credentials and is excluded from deterministic CI",\n]\n'''
    write(relative, content.rstrip() + "\n" + addition)


def write_live_workflow() -> None:
    write(
        ".github/workflows/session13-plus-live-provider.yml",
        '''name: Session 13 Plus live provider smoke\n\non:\n  workflow_dispatch:\n\npermissions:\n  contents: read\n\njobs:\n  live-provider:\n    runs-on: ubuntu-latest\n    defaults:\n      run:\n        working-directory: estimador-cag\n    env:\n      DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}\n      KIMI_API_KEY: ${{ secrets.KIMI_API_KEY }}\n      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}\n    steps:\n      - uses: actions/checkout@v4\n      - uses: astral-sh/setup-uv@v5\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.11"\n      - run: uv sync --frozen --extra dev\n      - name: Run explicitly credentialed provider tests\n        run: uv run pytest -q -m live_provider\n''',
    )


def disable_legacy_ci_repair() -> None:
    relative = "scripts/session13_plus_stabilize.py"
    content = read(relative)
    old = "    repair_ci_boundary()\n"
    if old in content:
        content = content.replace(
            old,
            "    # CI boundary applied idempotently by session13_plus_ci_boundary.py\n",
            1,
        )
        write(relative, content)


def main() -> None:
    update_provider_tests()
    update_pytest_config()
    write_live_workflow()
    disable_legacy_ci_repair()


if __name__ == "__main__":
    main()
