from __future__ import annotations

from typing import Any

CATALOG_VERSION = "1.0.0"

COMMANDS: list[dict[str, Any]] = [
    {
        "id": "evaluate",
        "entrypoint": "python -m energy_core.cli evaluate",
        "purpose": "Evaluate one candidate state against policy and evidence.",
        "mutates_ledger": True,
        "supports_dry_run": True,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_smoke.py and scripts/energy_core_root_smoke.py",
        "category": "decision",
    },
    {
        "id": "policy_validate",
        "entrypoint": "python -m energy_core.cli policy-validate",
        "purpose": "Validate policy structure, evidence declarations, thresholds, and required constraints.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_smoke.py",
        "category": "validation",
    },
    {
        "id": "candidate_validate",
        "entrypoint": "python -m energy_core.cli candidate-validate",
        "purpose": "Validate a candidate state before evaluation.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_smoke.py",
        "category": "validation",
    },
    {
        "id": "candidate_readiness",
        "entrypoint": "python -m energy_core.candidate_readiness_cli",
        "purpose": "Report whether bundled candidates are structurally ready for judgment.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "focused pytest coverage",
        "category": "examples",
    },
    {
        "id": "evidence_summary",
        "entrypoint": "python -m energy_core.cli evidence-summary",
        "purpose": "Summarize evidence records without evaluating a candidate.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_smoke.py",
        "category": "evidence",
    },
    {
        "id": "ledger_summary",
        "entrypoint": "python -m energy_core.cli ledger-summary",
        "purpose": "Summarize decision history from an append-only ledger.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_smoke.py",
        "category": "ledger",
    },
    {
        "id": "ledger_integrity",
        "entrypoint": "python -m energy_core.ledger_integrity_cli",
        "purpose": "Inspect JSONL decision ledger integrity without mutation.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_ledger_integrity_smoke.py",
        "category": "ledger",
    },
    {
        "id": "spec_coverage",
        "entrypoint": "python -m energy_core.cli spec-coverage",
        "purpose": "Check that the spec package has required files and bundled examples.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_smoke.py",
        "category": "spec",
    },
    {
        "id": "audit_pack",
        "entrypoint": "python -m energy_core.cli audit-pack",
        "purpose": "Build one non-mutating review packet for a candidate, policy, evidence, and ledger context.",
        "mutates_ledger": False,
        "supports_dry_run": True,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_smoke.py and scripts/energy_core_root_smoke.py",
        "category": "review",
    },
    {
        "id": "schema_bundle",
        "entrypoint": "python -m energy_core.schema_cli",
        "purpose": "Expose machine-readable JSON schemas for Energy Core contracts.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_schema_smoke.py",
        "category": "schema",
    },
    {
        "id": "constraint_index",
        "entrypoint": "python -m energy_core.constraints_cli",
        "purpose": "Expose hard reject, hard repair, soft constraints, evidence types, and decision rules.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_constraint_smoke.py",
        "category": "policy",
    },
    {
        "id": "critic_coverage",
        "entrypoint": "python -m energy_core.critic_coverage_cli",
        "purpose": "Classify which policy constraints are enforced by deterministic critics versus policy-only.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_critic_coverage_smoke.py",
        "category": "policy",
    },
    {
        "id": "nightly_status",
        "entrypoint": "python -m energy_core.nightly_status_cli",
        "purpose": "Build a five-section overnight status pack for maintainers.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_nightly_status_smoke.py",
        "category": "review",
    },
    {
        "id": "example_matrix",
        "entrypoint": "python -m energy_core.examples_cli",
        "purpose": "Evaluate bundled examples against their expected decisions.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_example_smoke.py",
        "category": "examples",
    },
    {
        "id": "release_readiness",
        "entrypoint": "python -m energy_core.release_cli",
        "purpose": "Check whether the incubator package is ready for extraction review.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_release_smoke.py",
        "category": "release",
    },
    {
        "id": "package_manifest",
        "entrypoint": "python -m energy_core.package_cli",
        "purpose": "List extraction copy roots, required artifacts, hashes, and non-goals.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_package_smoke.py",
        "category": "release",
    },
    {
        "id": "reviewer_snapshot",
        "entrypoint": "python -m energy_core.reviewer_cli",
        "purpose": "Provide a reviewer-facing index of proof surfaces and review commands.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_reviewer_smoke.py",
        "category": "review",
    },
    {
        "id": "review_pack",
        "entrypoint": "python -m energy_core.review_pack_cli",
        "purpose": "Export generated Markdown artifacts for human review into an output directory.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_review_pack_smoke.py",
        "category": "review",
    },
    {
        "id": "review_gap_register",
        "entrypoint": "python -m energy_core.review_gap_register_cli",
        "purpose": "List blocking gaps, planned boundaries, and accepted non-blocking review gaps.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_review_gap_register_smoke.py",
        "category": "review",
    },
    {
        "id": "scaffold",
        "entrypoint": "python -m energy_core.scaffold_cli",
        "purpose": "Generate a standalone repository scaffold without copying source files.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_scaffold_smoke.py",
        "category": "release",
    },
    {
        "id": "export_plan",
        "entrypoint": "python -m energy_core.export_plan_cli",
        "purpose": "Build a non-executing copy plan for future standalone repository extraction.",
        "mutates_ledger": False,
        "supports_dry_run": False,
        "repo_root_supported": True,
        "smoke": "scripts/energy_core_export_plan_smoke.py",
        "category": "release",
    },
]


def build_command_catalog() -> dict[str, Any]:
    mutating = [command for command in COMMANDS if command["mutates_ledger"]]
    dry_run = [command for command in COMMANDS if command["supports_dry_run"]]
    unsupported_root = [command for command in COMMANDS if not command["repo_root_supported"]]

    return {
        "catalog_version": CATALOG_VERSION,
        "complete": not unsupported_root and len(COMMANDS) >= 1,
        "command_total": len(COMMANDS),
        "mutating_command_ids": [command["id"] for command in mutating],
        "non_mutating_command_total": len(COMMANDS) - len(mutating),
        "dry_run_command_ids": [command["id"] for command in dry_run],
        "repo_root_supported": not unsupported_root,
        "unsupported_root_command_ids": [command["id"] for command in unsupported_root],
        "commands": COMMANDS,
        "non_goals": [
            "The command catalog does not execute shell actions.",
            "The command catalog does not call LLM providers.",
            "The command catalog does not approve adapter execution.",
        ],
    }


def format_command_catalog_text(catalog: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Command Catalog",
            f"Catalog version: {catalog['catalog_version']}",
            f"Complete: {catalog['complete']}",
            f"Commands: {catalog['command_total']}",
            f"Mutating commands: {_inline_list(catalog['mutating_command_ids'])}",
            f"Dry-run commands: {_inline_list(catalog['dry_run_command_ids'])}",
            f"Repo-root supported: {catalog['repo_root_supported']}",
        ]
    )


def format_command_catalog_markdown(catalog: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Command Catalog",
        "",
        f"- Catalog version: {catalog['catalog_version']}",
        f"- Complete: {catalog['complete']}",
        f"- Commands: {catalog['command_total']}",
        f"- Non-mutating commands: {catalog['non_mutating_command_total']}",
        f"- Repo-root supported: {catalog['repo_root_supported']}",
        "",
        "## Mutating commands",
        "",
    ]
    lines.extend(_bullet_list(catalog["mutating_command_ids"]))
    lines.extend(["", "## Dry-run capable commands", ""])
    lines.extend(_bullet_list(catalog["dry_run_command_ids"]))
    lines.extend(["", "## Commands", ""])
    for command in catalog["commands"]:
        lines.extend(
            [
                f"### {command['id']}",
                "",
                f"- Entrypoint: `{command['entrypoint']}`",
                f"- Category: {command['category']}",
                f"- Purpose: {command['purpose']}",
                f"- Mutates ledger: {command['mutates_ledger']}",
                f"- Supports dry-run: {command['supports_dry_run']}",
                f"- Repo-root supported: {command['repo_root_supported']}",
                f"- Smoke: {command['smoke']}",
                "",
            ]
        )
    lines.extend(["## Non goals", ""])
    lines.extend(_bullet_list(catalog["non_goals"]))
    return "\n".join(lines)


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
