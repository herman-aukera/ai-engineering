"""Vendor-neutral ingress contract for coding tools governed by EACODE.

Tool identity is provenance only. Deterministic governance evaluates only the
normalized proposal, so a caller cannot obtain weaker policy by claiming to be
Claude Code, Kimi Code, Cline, Codex, Gemini CLI, Antigravity, or another tool.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, field_validator

from energy_core.coding_agent import CodingProposal
from energy_core.models import EnergyModel

KnownCodingTool = Literal[
    "claude-code",
    "kimi-code",
    "cline",
    "codex",
    "antigravity",
    "gemini-cli",
    "generic",
]


class CodingToolIdentity(EnergyModel):
    """Untrusted provenance supplied by an external coding tool."""

    name: str = Field(min_length=1, max_length=80)
    version: str | None = Field(default=None, max_length=80)
    session_id: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip().lower().replace("_", "-")


class CodingToolProposalRequest(EnergyModel):
    """Tool-neutral proposal envelope accepted at the EACODE governance boundary."""

    tool: CodingToolIdentity
    proposal_id: str | None = Field(default=None, min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=4000)
    spec_id: str = Field(min_length=1, max_length=500)
    patch: str = Field(max_length=20_000)
    changed_files: tuple[str, ...] = Field(default_factory=tuple, max_length=200)
    proposed_commands: tuple[tuple[str, ...], ...] = Field(default_factory=tuple, max_length=50)


class NormalizedCodingToolProposal(EnergyModel):
    """Provenance plus the authority-neutral CodingProposal used by policy."""

    source_tool: CodingToolIdentity
    proposal: CodingProposal
    normalization_version: str = "eacode-tool-gateway.v1"


def normalize_coding_tool_proposal(request: CodingToolProposalRequest) -> NormalizedCodingToolProposal:
    """Normalize any supported tool without granting its identity policy authority."""

    proposal_id = request.proposal_id or _stable_proposal_id(request)
    proposal = CodingProposal(
        proposal_id=proposal_id,
        objective=request.objective,
        spec_id=request.spec_id,
        patch=request.patch,
        changed_files=request.changed_files,
        proposed_commands=request.proposed_commands,
    )
    return NormalizedCodingToolProposal(source_tool=request.tool, proposal=proposal)


def _stable_proposal_id(request: CodingToolProposalRequest) -> str:
    """Build an idempotent ID from proposal semantics, deliberately excluding tool identity."""

    semantic_payload = {
        "objective": request.objective,
        "spec_id": request.spec_id,
        "patch": request.patch,
        "changed_files": request.changed_files,
        "proposed_commands": request.proposed_commands,
    }
    encoded = json.dumps(semantic_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "gateway-" + hashlib.sha256(encoded).hexdigest()[:32]


__all__ = [
    "CodingToolIdentity",
    "CodingToolProposalRequest",
    "KnownCodingTool",
    "NormalizedCodingToolProposal",
    "normalize_coding_tool_proposal",
]
