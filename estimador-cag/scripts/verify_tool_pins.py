from __future__ import annotations

import re
import sys
from pathlib import Path

IGNORED_PARTS = {".git", ".venv", "node_modules", "__pycache__"}
UV_TOOL_RUN = re.compile(r"\buv\s+tool\s+run\s+([^\s\\]+)")
UVX_FROM = re.compile(r"\buvx\s+--from\s+([^\s\\]+)")
UVX_DIRECT = re.compile(r"\buvx\s+([^\s\\]+)")
PIP_INSTALL = re.compile(r"\b(?:python\s+-m\s+)?pip\s+install\b")
NPM_INSTALL = re.compile(r"\bnpm\s+(?:install|i)\b")
SHELL_PIPE_INSTALL = re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sh|bash)\b")
FLOATING_OS_REFRESH = re.compile(r"\b(?:apt-get\s+(?:update|upgrade)|apk\s+upgrade)\b")
EXACT_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
EXACT_UV_REQUIRED = re.compile(r'^required-version\s*=\s*["\']==(?P<version>\d+\.\d+\.\d+)["\']\s*$')


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def _blocking_files(root: Path) -> list[Path]:
    files: list[Path] = []
    workflows = root / ".github" / "workflows"
    if workflows.exists():
        files.extend(sorted(workflows.glob("*.yml")))
        files.extend(sorted(workflows.glob("*.yaml")))
    product = root / "estimador-cag"
    if product.exists():
        files.extend(sorted(path for path in product.rglob("Dockerfile*") if path.is_file()))
        deploy = product / "deploy"
        if deploy.exists():
            files.extend(sorted(path for path in deploy.rglob("*.sh") if path.is_file()))
    return [path for path in dict.fromkeys(files) if not _is_ignored(path)]


def _exact_python_spec(spec: str) -> bool:
    return "==" in spec and not spec.endswith("==")


def _exact_npm_spec(spec: str) -> bool:
    if spec.startswith("@"):
        return spec.count("@") >= 2 and not spec.endswith("@")
    return "@" in spec and not spec.endswith("@")


def _direct_pip_specs(line: str) -> list[str]:
    match = PIP_INSTALL.search(line)
    if not match:
        return []
    tail = line[match.end():].replace("\\", " ")
    tokens = tail.split()
    specs: list[str] = []
    skip_next = False
    for token in tokens:
        token = token.strip(";&|")
        if not token:
            continue
        if skip_next:
            skip_next = False
            continue
        if token in {"-r", "--requirement", "-c", "--constraint", "--index-url", "--extra-index-url", "--python"}:
            skip_next = True
            continue
        if token.startswith("--python="):
            continue
        if token.startswith("-"):
            continue
        if token in {"&&", "||"}:
            break
        specs.append(token)
    return specs


def _direct_npm_specs(line: str) -> list[str]:
    match = NPM_INSTALL.search(line)
    if not match:
        return []
    tokens = line[match.end():].replace("\\", " ").split()
    specs: list[str] = []
    for token in tokens:
        token = token.strip(";&|")
        if not token or token.startswith("-"):
            continue
        if token in {"&&", "||"}:
            break
        specs.append(token)
    return specs


def find_root_toolchain_errors(root: Path) -> list[str]:
    errors: list[str] = []
    uv_path = root / "uv.toml"
    if not uv_path.is_file():
        errors.append("uv.toml: missing exact repository uv toolchain pin")
    else:
        matches = [
            EXACT_UV_REQUIRED.match(line.strip())
            for line in uv_path.read_text(encoding="utf-8").splitlines()
        ]
        if not any(matches):
            errors.append("uv.toml: required-version must be an exact ==X.Y.Z pin")

    python_path = root / ".python-version"
    if not python_path.is_file():
        errors.append(".python-version: missing exact repository Python toolchain pin")
    else:
        version = python_path.read_text(encoding="utf-8").strip()
        if not EXACT_VERSION.fullmatch(version):
            errors.append(".python-version: Python must be pinned to exact X.Y.Z")
    return errors


def find_mutable_tool_refs(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _blocking_files(root):
        rel = path.relative_to(root)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if SHELL_PIPE_INSTALL.search(line):
                errors.append(f"{rel}:{lineno}: shell-piped remote installer is forbidden")
            if path.name.startswith("Dockerfile") and FLOATING_OS_REFRESH.search(line):
                errors.append(f"{rel}:{lineno}: floating OS package refresh in pinned Docker build")

            match = UV_TOOL_RUN.search(line)
            if match and not _exact_python_spec(match.group(1)):
                errors.append(f"{rel}:{lineno}: mutable uv tool ref: {match.group(1)}")

            match = UVX_FROM.search(line)
            if match and not _exact_python_spec(match.group(1)):
                errors.append(f"{rel}:{lineno}: mutable uvx --from ref: {match.group(1)}")
            elif "uvx" in line:
                direct = UVX_DIRECT.search(line)
                if direct and direct.group(1) != "--from" and not _exact_python_spec(direct.group(1)):
                    errors.append(f"{rel}:{lineno}: mutable uvx ref: {direct.group(1)}")

            if PIP_INSTALL.search(line) and "--require-hashes" not in line:
                for spec in _direct_pip_specs(line):
                    if not _exact_python_spec(spec):
                        errors.append(f"{rel}:{lineno}: mutable direct pip install ref: {spec}")

            if NPM_INSTALL.search(line):
                for spec in _direct_npm_specs(line):
                    if not _exact_npm_spec(spec):
                        errors.append(f"{rel}:{lineno}: mutable direct npm install ref: {spec}")

    return sorted(set(errors))


def main() -> int:
    root = repository_root()
    errors = find_root_toolchain_errors(root) + find_mutable_tool_refs(root)
    if errors:
        print("\n".join(sorted(set(errors))))
        return 1
    print("EXECUTABLE_TOOL_PINS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
