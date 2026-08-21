"""Build and validate a product-only source tree from the production import closure."""

from __future__ import annotations

import ast
import json
import shutil
import tempfile
from pathlib import Path

PROJECT_ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((PROJECT_ROOT/"docs"/"energy_aware_product_manifest.json").read_text(encoding="utf-8"))
ROOTS=tuple(str(v) for v in MANIFEST["first_party_roots"])
FORBIDDEN=tuple(str(v) for v in MANIFEST.get("forbidden_peer_imports",[]))


def _module_for_path(path:Path)->str:
    parts=list(path.relative_to(PROJECT_ROOT).with_suffix("").parts)
    if parts[-1]=="__init__": parts.pop()
    return ".".join(parts)


def _resolve(module:str)->Path|None:
    if not any(module==root or module.startswith(root+".") for root in ROOTS): return None
    rel=Path(*module.split("."))
    for candidate in (PROJECT_ROOT/rel.with_suffix(".py"),PROJECT_ROOT/rel/"__init__.py"):
        if candidate.is_file(): return candidate
    return None


def _absolute(path:Path,node:ast.ImportFrom)->str:
    if node.level==0:return node.module or ""
    parts=_module_for_path(path).split(".")
    if path.name!="__init__.py":parts=parts[:-1]
    ascend=max(0,node.level-1)
    if ascend:parts=parts[:-ascend]
    if node.module:parts.extend(node.module.split("."))
    return ".".join(p for p in parts if p)


def _imports(path:Path)->set[str]:
    tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path)); result:set[str]=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):result.update(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom):
            base=_absolute(path,node)
            if base:result.add(base)
            if not node.module:
                for alias in node.names:result.add(f"{base}.{alias.name}" if base else alias.name)
    return result


def _parents(path:Path,collected:set[Path])->None:
    parent=path.parent
    while parent!=PROJECT_ROOT and PROJECT_ROOT in parent.parents:
        init=parent/"__init__.py"
        if init.is_file():collected.add(init)
        parent=parent.parent


def _trace(entrypoint:Path)->tuple[set[Path],int]:
    pending=[entrypoint];collected:set[Path]=set();edges=0
    while pending:
        path=pending.pop()
        if path in collected:continue
        collected.add(path);_parents(path,collected)
        source=path.read_text(encoding="utf-8")
        leaked=[n for n in FORBIDDEN if n in source]
        if leaked:raise AssertionError(f"peer-product dependency leaked into {path}: {leaked}")
        for module in _imports(path):
            resolved=_resolve(module)
            if resolved is not None:edges+=1;pending.append(resolved)
    return collected,edges


def verify()->dict[str,object]:
    entrypoint=PROJECT_ROOT/str(MANIFEST["production_entrypoint"]);sources,edges=_trace(entrypoint);support:set[Path]=set()
    for key in ("runtime_assets","split_support_files"):
        for value in MANIFEST.get(key,[]):
            path=PROJECT_ROOT/str(value)
            if not path.is_file():raise AssertionError(f"declared split file is missing: {value}")
            support.add(path)
    with tempfile.TemporaryDirectory(prefix="energy-aware-split-") as raw:
        root=Path(raw)
        for source in sorted(sources|support):
            target=root/source.relative_to(PROJECT_ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        for source in sources:compile(source.read_text(encoding="utf-8"),str(source),"exec")
        if not (root/entrypoint.relative_to(PROJECT_ROOT)).is_file():raise AssertionError("product-only tree lost its production entrypoint")
    return {"product":MANIFEST["product"],"protocol_version":MANIFEST["protocol_version"],"source_file_count":len(sources),"support_file_count":len(support),"first_party_import_edges":edges,"forbidden_peer_import_count":len(FORBIDDEN),"status":"pass"}


def main()->None:print(json.dumps(verify(),sort_keys=True))


if __name__=="__main__":main()
