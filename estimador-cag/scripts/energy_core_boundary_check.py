from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENERGY_CORE = ROOT / "energy_core"

FORBIDDEN_IMPORT_ROOTS = {
    "anthropic",
    "app",
    "fastapi",
    "litellm",
    "openai",
    "redis",
    "streamlit",
    "uvicorn",
}

FORBIDDEN_ADAPTER_IMPORT_ROOTS = {
    "aider",
    "cline",
    "opencode",
}


@dataclass(frozen=True)
class BoundaryViolation:
    path: Path
    line: int
    imported_root: str
    reason: str

    def format(self) -> str:
        relative_path = self.path.relative_to(ROOT)
        return f"{relative_path}:{self.line}: {self.imported_root} :: {self.reason}"


def find_boundary_violations() -> list[BoundaryViolation]:
    if not ENERGY_CORE.is_dir():
        return [
            BoundaryViolation(
                path=ENERGY_CORE,
                line=0,
                imported_root="energy_core",
                reason="energy_core package is missing",
            )
        ]

    violations: list[BoundaryViolation] = []
    for path in sorted(ENERGY_CORE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported_roots = _imported_roots(node)
            for root in imported_roots:
                reason = _reason_for_forbidden_root(root)
                if reason is not None:
                    violations.append(
                        BoundaryViolation(
                            path=path,
                            line=getattr(node, "lineno", 0),
                            imported_root=root,
                            reason=reason,
                        )
                    )
    return violations


def _imported_roots(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name.split(".", maxsplit=1)[0] for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return [node.module.split(".", maxsplit=1)[0]]
    return []


def _reason_for_forbidden_root(root: str) -> str | None:
    if root in FORBIDDEN_IMPORT_ROOTS:
        return "energy_core must not depend on app, UI, provider, server, or cache runtime layers"
    if root in FORBIDDEN_ADAPTER_IMPORT_ROOTS:
        return "adapters are deferred until the deterministic judge boundary is stable"
    return None


def main() -> int:
    violations = find_boundary_violations()
    if violations:
        print("Energy Core boundary check failed:")
        for violation in violations:
            print(f"- {violation.format()}")
        return 1

    print("Energy Core boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
