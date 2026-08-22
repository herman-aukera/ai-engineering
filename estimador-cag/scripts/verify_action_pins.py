from __future__ import annotations

import re
import sys
from pathlib import Path

FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def find_mutable_action_refs(root: Path) -> list[str]:
    errors: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    paths = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))
    for path in paths:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = USES.match(line)
            if not match:
                continue
            ref = match.group(1)
            if ref.startswith("./"):
                continue
            if "@" not in ref:
                errors.append(f"{path.relative_to(root)}:{lineno}: external action missing ref: {ref}")
                continue
            action, version = ref.rsplit("@", 1)
            if not FULL_SHA.fullmatch(version):
                errors.append(
                    f"{path.relative_to(root)}:{lineno}: mutable external action ref: {action}@{version}"
                )
    return errors


def main() -> int:
    errors = find_mutable_action_refs(repository_root())
    if errors:
        print("\n".join(errors))
        return 1
    print("GITHUB_ACTION_PINS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
