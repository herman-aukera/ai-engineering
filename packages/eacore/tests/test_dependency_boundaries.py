from __future__ import annotations

import ast
from pathlib import Path

PROHIBITED = {
    "langgraph",
    "fastapi",
    "streamlit",
    "openai",
    "anthropic",
    "litellm",
    "psycopg",
    "sqlalchemy",
    "redis",
    "pgvector",
    "subprocess",
}


def test_runtime_has_no_prohibited_imports() -> None:
    package = Path(__file__).parents[1] / "src" / "eacore"
    violations: list[str] = []
    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                root = name.split(".", 1)[0]
                if root in PROHIBITED:
                    violations.append(f"{path.relative_to(package)} imports {name}")
                if name.startswith("app.") or name.startswith("energy_core"):
                    violations.append(f"{path.relative_to(package)} imports product module {name}")
    assert violations == []
