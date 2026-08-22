from __future__ import annotations

import re
import sys
from pathlib import Path

DIGEST = re.compile(r"@sha256:[0-9a-fA-F]{64}$")
FROM = re.compile(r"^\s*FROM\s+(\S+)(?:\s+AS\s+(\S+))?", re.I)
IMAGE = re.compile(r"^\s*image:\s*(.+?)\s*$")
TOKEN = re.compile(r"([A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*:[A-Za-z0-9._-]+(?:@sha256:[0-9a-fA-F]{64})?)")
LOCAL_DEV = {
    ("docker-compose.yml", "pgvector/pgvector:0.8.0-pg16"),
    ("docker-compose.yml", "redis:7.4-alpine"),
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _error(path: Path, root: Path, line: int, value: str) -> str | None:
    value = value.strip().strip('"').strip("'")
    rel = str(path.relative_to(root))
    if "${" in value:
        if "immutable" in value.lower() and "digest" in value.lower():
            return None
        return f"{rel}:{line}: image variable lacks immutable-digest contract: {value}"
    if (rel, value) in LOCAL_DEV:
        return None
    if (":" in value or "/" in value) and not DIGEST.search(value):
        return f"{rel}:{line}: mutable executable image ref: {value}"
    return None


def find_mutable_image_refs(root: Path) -> list[str]:
    errors: list[str] = []
    product = root / "estimador-cag"
    deploy = product / "deploy"
    dockerfiles = list(product.glob("Dockerfile*"))
    if deploy.exists():
        dockerfiles += [p for p in deploy.rglob("Dockerfile*") if p.is_file()]
    for path in sorted(dockerfiles):
        stages: set[str] = set()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = FROM.match(line)
            if not match:
                continue
            image, alias = match.groups()
            if image not in stages and not DIGEST.search(image):
                errors.append(f"{path.relative_to(root)}:{line_no}: mutable Dockerfile base image: {image}")
            if alias:
                stages.add(alias)

    files = list((root / ".github/workflows").glob("*.y*ml")) + list(root.glob("docker-compose*.y*ml"))
    if deploy.exists():
        files += [p for p in deploy.rglob("*.y*ml") if p.is_file()]
        files += [p for p in deploy.rglob("*.sh") if p.is_file()]
    for path in sorted(set(files)):
        in_run = False
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = IMAGE.match(line)
            if match:
                problem = _error(path, root, line_no, match.group(1))
                if problem:
                    errors.append(problem)
            if "docker run" in line:
                in_run = True
            if in_run:
                for candidate in TOKEN.findall(line):
                    if "$" in candidate:
                        continue
                    problem = _error(path, root, line_no, candidate)
                    if problem:
                        errors.append(problem)
                if not line.rstrip().endswith("\\"):
                    in_run = False
    return sorted(set(errors))


def main() -> int:
    errors = find_mutable_image_refs(repository_root())
    if errors:
        print("\n".join(errors))
        return 1
    print("EXECUTABLE_IMAGE_PINS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
