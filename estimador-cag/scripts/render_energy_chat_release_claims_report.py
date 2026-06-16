"""Render the Energy Aware Chat release-claim gate report."""

from __future__ import annotations

import json
from pathlib import Path

from app.energy_chat.release_claims import ReleaseClaimEvidence, evaluate_release_claims

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_PATH = (
    PROJECT_ROOT / "evals" / "energy_chat" / "release_claim_evidence_current.json"
)
DEFAULT_REPORT_PATH = PROJECT_ROOT / "docs" / "energy_aware_chat_release_claims_gate.md"
DEFAULT_RESULT_PATH = PROJECT_ROOT / "evals" / "energy_chat" / "release_claim_gate_result.json"


def load_evidence(path: Path = DEFAULT_EVIDENCE_PATH) -> ReleaseClaimEvidence:
    return ReleaseClaimEvidence.model_validate_json(path.read_text(encoding="utf-8"))


def render_markdown(evidence: ReleaseClaimEvidence) -> str:
    report = evaluate_release_claims(evidence)
    lines = [
        "# Energy Aware Chat release-claim gate",
        "",
        "Status: deterministic evidence gate for high-risk release claims.",
        "",
        "This report controls whether the project may use any of these phrases:",
        "",
        "1. production-ready",
        "2. public deployment is live",
        "3. quality improvement over plain DeepSeek",
        "4. frontier-model superiority",
        "",
        "These claims are blocked unless the matching evidence exists.",
        "",
        "## Current result",
        "",
        f"- overall_ready: `{str(report.overall_ready).lower()}`",
        f"- claim_status: `{report.claim_status}`",
        "",
        "## Claim gates",
        "",
        "| Claim | Decision | Missing evidence | Next action |",
        "|---|---|---|---|",
    ]
    for result in report.results:
        missing = ", ".join(result.missing_evidence) or "none"
        lines.append(
            "| "
            f"`{result.allowed_phrase}` | "
            f"`{result.decision}` | "
            f"{missing} | "
            f"{result.next_action} |"
        )

    lines.extend(
        [
            "",
            "## Correct current wording",
            "",
            "Allowed now:",
            "",
            "```text",
            "Energy Aware Chat is a browser-testable, production-oriented MVP candidate on the EACHAT incubator branch.",
            "```",
            "",
            "Blocked until evidence exists:",
            "",
            "```text",
            "production-ready",
            "public deployment is live",
            "quality improvement over plain DeepSeek",
            "frontier-model superiority",
            "```",
            "",
            "## Evidence policy",
            "",
            "The project may upgrade a claim only by updating `evals/energy_chat/release_claim_evidence_current.json`, rerendering this report, and passing the full Energy Chat validation gate plus CI.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    *,
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    result_path: Path = DEFAULT_RESULT_PATH,
) -> None:
    evidence = load_evidence(evidence_path)
    report = evaluate_release_claims(evidence)
    report_path.write_text(render_markdown(evidence), encoding="utf-8")
    result_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {report_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {result_path.relative_to(PROJECT_ROOT)}")
    print(json.dumps(report.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    write_outputs()
