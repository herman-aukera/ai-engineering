"""Scan current tracked files and branch history for obvious committed secrets.

The scanner reports only redacted metadata. It is intentionally deterministic and
stdlib-only so it can run before application dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 2_000_000
PLACEHOLDERS = {"test", "dummy", "placeholder", "changeme", "example"}


@dataclass(frozen=True)
class Finding:
    source: str
    path: str
    line: int
    rule: str
    redacted_match: str


def _patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    private_key = "-" * 5 + r"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY" + "-" * 5
    return (
        ("provider_api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
        ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
        ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
        ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{24,}")),
        ("private_key", re.compile(private_key)),
        (
            "configured_provider_key",
            re.compile(
                r"\b(?:OPENAI|DEEPSEEK|KIMI|MOONSHOT|ANTHROPIC)(?:_AUTH_TOKEN|_API_KEY)"
                r"[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_.-]{16,})",
                re.IGNORECASE,
            ),
        ),
    )


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def _redact(value: str) -> str:
    compact = value.strip().replace("\n", " ")
    if len(compact) <= 8:
        return "[REDACTED]"
    return f"{compact[:4]}…{compact[-4:]}"


def _is_placeholder(match: re.Match[str]) -> bool:
    if match.lastindex:
        candidate = match.group(match.lastindex).strip("\"'").casefold()
        return candidate in PLACEHOLDERS
    return False


def _scan_text(*, source: str, path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in _patterns():
            for match in pattern.finditer(line):
                if _is_placeholder(match):
                    continue
                findings.append(
                    Finding(
                        source=source,
                        path=path,
                        line=line_number,
                        rule=rule,
                        redacted_match=_redact(match.group(0)),
                    )
                )
    return findings


def _tracked_files() -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    return [item.decode("utf-8") for item in output.split(b"\0") if item]


def _scan_worktree() -> tuple[int, list[Finding]]:
    findings: list[Finding] = []
    scanned = 0
    for relative_path in _tracked_files():
        path = ROOT / relative_path
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            continue
        payload = path.read_bytes()
        if b"\0" in payload:
            continue
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        findings.extend(_scan_text(source="worktree", path=relative_path, text=text))
    return scanned, findings


def _scan_branch_history(base_ref: str) -> list[Finding]:
    try:
        patch = _run_git("log", "--format=commit:%H", "--unified=0", f"{base_ref}..HEAD")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Unable to resolve security scan base ref: {base_ref}") from exc

    findings: list[Finding] = []
    commit = "unknown"
    path = "unknown"
    added_line = 0
    for raw_line in patch.splitlines():
        if raw_line.startswith("commit:"):
            commit = raw_line.removeprefix("commit:")[:12]
        elif raw_line.startswith("+++ b/"):
            path = raw_line.removeprefix("+++ b/")
        elif raw_line.startswith("@@"):
            added_match = re.search(r"\+(\d+)", raw_line)
            added_line = int(added_match.group(1)) - 1 if added_match else 0
        elif raw_line.startswith("+") and not raw_line.startswith("+++"):
            added_line += 1
            findings.extend(
                _scan_text(
                    source=f"history:{commit}",
                    path=path,
                    text=raw_line[1:],
                )
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="origin/EACHAT")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    scanned_files, worktree_findings = _scan_worktree()
    history_findings = _scan_branch_history(args.base_ref)
    findings = [*worktree_findings, *history_findings]
    report = {
        "status": "failed" if findings else "passed",
        "base_ref": args.base_ref,
        "head": _run_git("rev-parse", "HEAD").strip(),
        "tracked_files_scanned": scanned_files,
        "history_findings": len(history_findings),
        "worktree_findings": len(worktree_findings),
        "findings": [asdict(item) for item in findings],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"EACHAT_SECURITY_SCAN status={report['status']} "
        f"tracked_files={scanned_files} findings={len(findings)}"
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
