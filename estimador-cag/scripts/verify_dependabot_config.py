from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_ECOSYSTEMS = {"github-actions", "pip", "docker"}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def validate_dependabot_config(root: Path) -> list[str]:
    path = root / ".github" / "dependabot.yml"
    if not path.is_file():
        return [".github/dependabot.yml is missing"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if not re.search(r"(?m)^version:\s*2\s*$", text):
        errors.append("Dependabot version must be 2")
    ecosystems = set(re.findall(r"package-ecosystem:\s*[\"']?([^\"'\s]+)", text))
    missing = REQUIRED_ECOSYSTEMS - ecosystems
    if missing:
        errors.append(f"missing package ecosystems: {sorted(missing)}")
    blocks = re.split(r"(?m)^\s*-\s+package-ecosystem:\s*", text)[1:]
    for block in blocks:
        ecosystem = re.match(r"[\"']?([^\"'\s]+)", block)
        name = ecosystem.group(1) if ecosystem else "unknown"
        if not re.search(r"interval:\s*[\"']?weekly[\"']?", block):
            errors.append(f"{name}: schedule must be weekly")
        limit = re.search(r"open-pull-requests-limit:\s*(\d+)", block)
        if not limit or int(limit.group(1)) > 5:
            errors.append(f"{name}: open-pull-requests-limit must be present and <= 5")
    if not re.search(r"package-ecosystem:\s*[\"']?github-actions[\"']?[\s\S]*?directory:\s*[\"']?/[\"']?", text):
        errors.append("github-actions updates must target repository root")
    return errors


def main() -> int:
    errors = validate_dependabot_config(repository_root())
    if errors:
        print("\n".join(errors))
        return 1
    print("DEPENDABOT_POLICY_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
