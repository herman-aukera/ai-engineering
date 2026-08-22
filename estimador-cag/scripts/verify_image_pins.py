from __future__ import annotations

import re
import sys
from pathlib import Path

DIGEST = re.compile(r"@sha256:[0-9a-fA-F]{64}$")
FROM = re.compile(r"^\s*FROM\s+(\S+)(?:\s+AS\s+(\S+))?", re.IGNORECASE)
IMAGE = re.compile(r"^\s*image:\s*(.+?)\s*$")
IMAGE_TOKEN = re.compile(r"(?<![A-Za-z0-9_./-])([A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*:[A-Za-z0-9._-]+(?:@sha256:[0-9a-fA-F]{64})?)")
LOCAL_DEVELOPMENT_ONLY = {
    ("docker-compose.yml", "ghcr.io/astral-sh/uv:python3.11-bookworm"),
    ("docker-compose.yml", "pgvector/pgvector:pg16"),
    ("docker-compose.yml", "redis:7-alpine"),
    ("docker-compose.yml", "pgvector/pgvector:0.8.0-pg16"),
    ("docker-compose.yml", "redis:7.4-alpine"),
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_external_image(value: str) -> bool:
    return ":" in value or "/" in value or "@sha256:" in value


def _check_image_value(path: Path, root: Path, lineno: int, value: str) -> str | None:
    value = value.strip().strip('"').strip("'")
    rel = str(path.relative_to(root))
    if not value:
        return None
    if "${" in value:
        lowered = value.lower()
        if "immutable" in lowered and "digest" in lowered:
            return None
        return f"{rel}:{lineno}: runtime image variable does not require immutable digest: {value}"
    if (rel, value) in LOCAL_DEVELOPMENT_ONLY:
        return None
    if _is_external_image(value) and not DIGEST.search(value):
        return f"{rel}:{lineno}: mutable executable image ref: {value}"
    return None


def _logical_shell_commands(lines: list[str]) -> list[tuple[int, str]]:
    commands: list[tuple[int, str]] = []
    current: list[str] = []
    start = 0
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not current and "docker run" not in stripped:
            continue
        if not current:
            start = lineno
        current.append(stripped.rstrip("\\").strip())
        if not stripped.endswith("\\"):
            commands.append((start, " ".join(current)))
            current = []
    if current:
        commands.append((start, " ".join(current)))
    return commands


def find_mutable_image_refs(root: Path) -> list[str]:
    errors: list[str] = []
    product_root = root / "estimador-cag"
    dockerfiles = sorted(product_root.glob("Dockerfile*"))
    deploy = product_root / "deploy"
    if deploy.exists():
        dockerfiles.extend(sorted(p for p in deploy.rglob("Dockerfile*") if p.is_file()))
    for path in dockerfiles:
        stages: set[str] = set()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = FROM.match(line)
            if not match:
                continue
            image, alias = match.groups()
            if image not in stages and _is_external_image(image) and not DIGEST.search(image):
                errors.append(f"{path.relative_to(root)}:{lineno}: mutable Dockerfile base image: {image}")
            if alias:
                stages.add(alias)
    yaml_paths = sorted((root / ".github/workflows").glob("*.yml")) + sorted((root / ".github/workflows").glob("*.yaml"))
    yaml_paths += sorted(root.glob("docker-compose*.yml")) + sorted(root.glob("docker-compose*.yaml"))
    if deploy.exists():
        yaml_paths += sorted(p for p in deploy.rglob("*.yml") if p.is_file())
        yaml_paths += sorted(p for p in deploy.rglob("*.yaml") if p.is_file())
    for path in dict.fromkeys(yaml_paths):
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, 1):
            match = IMAGE.match(line)
            if match:
                error = _check_image_value(path, root, lineno, match.group(1))
                if error:
                    errors.append(error)
        for lineno, command in _logical_shell_commands(lines):
            for candidate in IMAGE_TOKEN.findall(command):
                if "${" in candidate or "$" in candidate:
                    continue
                name = candidate.split(":", 1)[0]
                if re.fullmatch(r"\d+(?:\.\d+){3}", name):
                    continue
                error = _check_image_value(path, root, lineno, candidate)
                if error:
                    errors.append(error)
    shell_paths = sorted(p for p in deploy.rglob("*.sh") if p.is_file()) if deploy.exists() else []
    for path in shell_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, command in _logical_shell_commands(lines):
            for candidate in IMAGE_TOKEN.findall(command):
                if "${" in candidate or "$" in candidate:
                    continue
                error = _check_image_value(path, root, lineno, candidate)
                if error:
                    errors.append(error)
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
