from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

DIGEST = re.compile(r"@sha256:[0-9a-fA-F]{64}$")
FROM = re.compile(r"^\s*FROM\s+(\S+)(?:\s+AS\s+(\S+))?", re.IGNORECASE)
IMAGE = re.compile(r"^\s*image:\s*(.+?)\s*$")
DOCKER_IMAGE_COMMAND = re.compile(r"\bdocker\s+(?:run|pull)\b")
IGNORED_PARTS = {".git", ".venv", "node_modules", "__pycache__"}
RUN_OPTIONS_WITH_VALUE = {
    "--add-host", "--cap-add", "--cap-drop", "--device", "--dns", "--entrypoint",
    "--env", "--env-file", "--hostname", "--label", "--mount", "--name", "--network",
    "--platform", "--publish", "--pull", "--security-opt", "--tmpfs", "--user", "--volume",
    "--workdir", "-e", "-h", "-l", "-p", "-u", "-v", "-w",
}
LOCAL_DEVELOPMENT_ONLY = {
    ("docker-compose.yml", "ghcr.io/astral-sh/uv:python3.11-bookworm"),
    ("docker-compose.yml", "pgvector/pgvector:pg16"),
    ("docker-compose.yml", "redis:7-alpine"),
    ("docker-compose.yml", "pgvector/pgvector:0.8.0-pg16"),
    ("docker-compose.yml", "redis:7.4-alpine"),
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def _is_external_image(value: str) -> bool:
    return ":" in value or "/" in value or "@sha256:" in value


def _check_image_value(path: Path, root: Path, lineno: int, value: str) -> str | None:
    value = value.strip().strip('"').strip("'")
    rel = path.relative_to(root).as_posix()
    if not value:
        return None
    if "$" in value:
        return None
    if (rel, value) in LOCAL_DEVELOPMENT_ONLY:
        return None
    if _is_external_image(value) and not DIGEST.search(value):
        return f"{rel}:{lineno}: mutable executable image ref: {value}"
    return None


def _logical_docker_commands(lines: list[str]) -> list[tuple[int, str]]:
    commands: list[tuple[int, str]] = []
    current: list[str] = []
    start = 0
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not current and not DOCKER_IMAGE_COMMAND.search(stripped):
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


def _docker_image_operand(command: str) -> str | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    try:
        docker = tokens.index("docker")
    except ValueError:
        return None
    if docker + 1 >= len(tokens) or tokens[docker + 1] not in {"run", "pull"}:
        return None
    index = docker + 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return tokens[index + 1] if index + 1 < len(tokens) else None
        if token.startswith("--"):
            option = token.split("=", 1)[0]
            if "=" in token:
                index += 1
            elif option in RUN_OPTIONS_WITH_VALUE:
                index += 2
            else:
                index += 1
            continue
        if token.startswith("-"):
            index += 2 if token in RUN_OPTIONS_WITH_VALUE else 1
            continue
        return token
    return None


def _candidate_files(root: Path, pattern: str) -> list[Path]:
    return sorted(path for path in root.rglob(pattern) if path.is_file() and not _is_ignored(path))


def find_mutable_image_refs(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _candidate_files(root, "Dockerfile*"):
        stages: set[str] = set()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = FROM.match(line)
            if not match:
                continue
            image, alias = match.groups()
            if image not in stages and _is_external_image(image) and not DIGEST.search(image):
                rel = path.relative_to(root).as_posix()
                errors.append(f"{rel}:{lineno}: mutable Dockerfile base image: {image}")
            if alias:
                stages.add(alias)

    yaml_paths: list[Path] = []
    workflow_dir = root / ".github" / "workflows"
    if workflow_dir.exists():
        yaml_paths.extend(sorted(workflow_dir.glob("*.yml")))
        yaml_paths.extend(sorted(workflow_dir.glob("*.yaml")))
    yaml_paths.extend(sorted(root.glob("docker-compose*.yml")))
    yaml_paths.extend(sorted(root.glob("docker-compose*.yaml")))
    deploy = root / "estimador-cag" / "deploy"
    if deploy.exists():
        yaml_paths.extend(sorted(path for path in deploy.rglob("*.yml") if path.is_file()))
        yaml_paths.extend(sorted(path for path in deploy.rglob("*.yaml") if path.is_file()))
    for path in dict.fromkeys(yaml_paths):
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, 1):
            match = IMAGE.match(line)
            if match:
                error = _check_image_value(path, root, lineno, match.group(1))
                if error:
                    errors.append(error)
        for lineno, command in _logical_docker_commands(lines):
            image = _docker_image_operand(command)
            if image:
                error = _check_image_value(path, root, lineno, image)
                if error:
                    errors.append(error)
    for path in _candidate_files(root, "*.sh"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, command in _logical_docker_commands(lines):
            image = _docker_image_operand(command)
            if image:
                error = _check_image_value(path, root, lineno, image)
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
