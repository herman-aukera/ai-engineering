"""Build and validate a product-only source tree from the production import closure."""

from __future__ import annotations

import ast
import json
import shutil
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads(
    (PROJECT_ROOT / "docs" / "energy_aware_product_manifest.json").read_text(encoding="utf-8")
)
ROOTS = tuple(str(value) for value in MANIFEST["first_party_roots"])
FORBIDDEN = tuple(str(value) for value in MANIFEST.get("forbidden_peer_imports", []))


def _module_for_path(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_module(module: str) -> Path | None:
    if not any(module == root or module.startswith(root + ".") for root in ROOTS):
        return None
    relative = Path(*module.split("."))
    module_path = PROJECT_ROOT / relative.with_suffix(".py")
    if module_path.is_file():
        return module_path
    package_path = PROJECT_ROOT / relative / "__init__.py"
    if package_path.is_file():
        return package_path
    return None


def _absolute_from_import(path: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    module_parts = _module_for_path(path).split(".")
    if path.name != "__init__.py":
        module_parts = module_parts[:-1]
    ascend = max(0, node.level - 1)
    if ascend:
        module_parts = module_parts[:-ascend]
    if node.module:
        module_parts.extend(node.module.split("."))
    return ".".join(part for part in module_parts if part)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _absolute_from_import(path, node)
            if base:
                imports.add(base)
            if not node.module:
                for alias in node.names:
                    imports.add(f"{base}.{alias.name}" if base else alias.name)
    return imports


def _add_parent_packages(path: Path, collected: set[Path]) -> None:
    parent = path.parent
    while parent != PROJECT_ROOT and PROJECT_ROOT in parent.parents:
        init = parent / "__init__.py"
        if init.is_file():
            collected.add(init)
        parent = parent.parent


def _trace_closure(entrypoint: Path) -> tuple[set[Path], int]:
    pending = [entrypoint]
    collected: set[Path] = set()
    edges = 0
    unresolved: set[str] = set()
    while pending:
        path = pending.pop()
        if path in collected:
            continue
        collected.add(path)
        _add_parent_packages(path, collected)
        source = path.read_text(encoding="utf-8")
        leaked = [needle for needle in FORBIDDEN if needle in source]
        if leaked:
            raise AssertionError(f"peer-product dependency leaked into {path}: {leaked}")
        for module in _imports(path):
            if not any(module == root or module.startswith(root + ".") for root in ROOTS):
                continue
            resolved = _resolve_module(module)
            if resolved is None:
                # Imported symbols are allowed; only fail when a top-level first-party package vanished.
                root_path = PROJECT_ROOT / module.split(".")[0]
                if not root_path.exists():
                    unresolved.add(module)
                continue
            edges += 1
            pending.append(resolved)
    if unresolved:
        raise AssertionError(f"unresolved first-party imports: {sorted(unresolved)}")
    return collected, edges


def verify() -> dict[str, object]:
    entrypoint = PROJECT_ROOT / str(MANIFEST["production_entrypoint"])
    if not entrypoint.is_file():
        raise AssertionError(f"production entrypoint is missing: {entrypoint}")
    sources, edges = _trace_closure(entrypoint)

    support: set[Path] = set()
    for key in ("runtime_assets", "split_support_files"):
        for value in MANIFEST.get(key, []):
            path = PROJECT_ROOT / str(value)
            if not path.is_file():
                raise AssertionError(f"declared split file is missing: {value}")
            support.add(path)

    with tempfile.TemporaryDirectory(prefix="energy-aware-split-") as raw:
        root = Path(raw)
        for source in sorted(sources | support):
            relative = source.relative_to(PROJECT_ROOT)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for source in sources:
            compile(source.read_text(encoding="utf-8"), str(source), "exec")
        if not (root / entrypoint.relative_to(PROJECT_ROOT)).is_file():
            raise AssertionError("product-only tree lost its production entrypoint")

    return {
        "product": MANIFEST["product"],
        "protocol_version": MANIFEST["protocol_version"],
        "source_file_count": len(sources),
        "support_file_count": len(support),
        "first_party_import_edges": edges,
        "forbidden_peer_import_count": len(FORBIDDEN),
        "status": "pass",
    }


def main() -> None:
    print(json.dumps(verify(), sort_keys=True))


if __name__ == "__main__":
    main()
