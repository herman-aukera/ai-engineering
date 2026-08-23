"""HTTP product surface for the governed EACODE control plane."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from energy_core.beta_demo import BetaDemoResult, BetaDemoRunner
from energy_core.beta_store import DemoAuthorizationReceipt
from energy_core.beta_store_runtime import build_beta_demo_store
from energy_core.coding_agent import CodingProposal
from energy_core.coding_tool_gateway import (
    CodingToolIdentity,
    CodingToolProposalRequest,
    normalize_coding_tool_proposal,
)
from energy_core.identity import BackendSession, SessionSigner
from energy_core.provider_registry import ProviderSelection
from energy_core.provider_verified import VerifiedCapabilityRegistry, VerifiedProviderSelector

router = APIRouter(prefix="/eacode", tags=["eacode"])
_registry = VerifiedCapabilityRegistry()
_selector = VerifiedProviderSelector(_registry)
_demo_runner = BetaDemoRunner()
_READ_ROLES = {"viewer", "reviewer", "operator", "admin"}
_EXECUTION_ROLES = {"operator", "admin"}


class EACodeSelectRequest(BaseModel):
    provider: str = "auto"
    profile: str = "medium"
    context_profile: str = "medium"
    fallback_policy: str = "none"
    expected_input_tokens: int = Field(default=50_000, ge=1)
    expected_cached_input_tokens: int = Field(default=0, ge=0)
    expected_output_tokens: int = Field(default=4_000, ge=1)
    max_cost_usd: Decimal = Field(default=Decimal("1.00"), ge=0)
    max_latency_ms: int | None = Field(default=None, ge=1)
    premium_reason: str | None = None
    entitled_surfaces: tuple[str, ...] = Field(default_factory=tuple)


class EACodeExecuteRequest(BaseModel):
    receipt_id: str = Field(min_length=20, max_length=200)


class EACodeAuthorizationResponse(BaseModel):
    receipt_id: str
    proposal_id: str
    actor: str
    issued_at: datetime
    expires_at: datetime


class EACodeGatewayResponse(BaseModel):
    """Public provenance plus the same governed result used by the native beta API."""

    source_tool: CodingToolIdentity
    normalization_version: str
    governance: BetaDemoResult
    execution_mode: str = "simulated"
    authority: str = "deterministic_eacode_governor"


@router.post(
    "/demo",
    response_model=BetaDemoResult,
    status_code=status.HTTP_201_CREATED,
)
def prepare_beta_demo(
    request: CodingProposal,
    authorization: str | None = Header(default=None),
) -> BetaDemoResult:
    """Evaluate and persist an inert proposal owned by the signed session."""

    session = _require_session(authorization, allowed_roles=_READ_ROLES)
    result = _demo_runner.prepare(request)
    _persist_result(result, owner_id=session.user_id)
    return result


@router.post(
    "/gateway/proposals",
    response_model=EACodeGatewayResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_coding_tool_proposal(
    request: CodingToolProposalRequest,
    authorization: str | None = Header(default=None),
) -> EACodeGatewayResponse:
    """Govern a proposal from any coding tool through one authority-neutral contract.

    Tool name/version/session are provenance only. They are deliberately excluded
    from the CodingProposal passed to hard gates, critics, repair, authorization,
    and the deterministic governor.
    """

    session = _require_session(authorization, allowed_roles=_READ_ROLES)
    normalized = normalize_coding_tool_proposal(request)
    result = _demo_runner.prepare(normalized.proposal)
    _persist_result(result, owner_id=session.user_id)
    return EACodeGatewayResponse(
        source_tool=normalized.source_tool,
        normalization_version=normalized.normalization_version,
        governance=result,
    )


@router.post(
    "/demo/{proposal_id}/authorize",
    response_model=EACodeAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def authorize_beta_demo(
    proposal_id: str,
    authorization: str | None = Header(default=None),
) -> EACodeAuthorizationResponse:
    """Issue a short-lived exact-scope receipt for a verified operator session."""

    session = _require_session(authorization, allowed_roles=_EXECUTION_ROLES)
    owner_id = _owner_filter(session)
    store = _demo_store()
    result = _load_result(store, proposal_id, owner_id=owner_id)
    try:
        receipt = store.issue_authorization(
            proposal_id=proposal_id,
            actor=session.user_id,
            owner_id=owner_id,
            scope=_demo_runner.authorization_scope(result),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _public_receipt(receipt)


@router.post("/demo/{proposal_id}/execute", response_model=BetaDemoResult)
def execute_beta_demo(
    proposal_id: str,
    request: EACodeExecuteRequest,
    authorization: str | None = Header(default=None),
) -> BetaDemoResult:
    """Atomically reserve one transition, consume its receipt, and persist reevaluation."""

    session = _require_session(authorization, allowed_roles=_EXECUTION_ROLES)
    owner_id = _owner_filter(session)
    store = _demo_store()
    result = _load_result(store, proposal_id, owner_id=owner_id)
    try:
        scope = _demo_runner.authorization_scope(result)
        receipt = store.consume_authorization(
            receipt_id=request.receipt_id,
            proposal_id=proposal_id,
            actor=session.user_id,
            owner_id=owner_id,
            scope=scope,
        )
        completed = _demo_runner.execute(
            result,
            authorization_id=receipt.receipt_id,
            actor=receipt.actor,
        )
        store.update_result(completed, owner_id=owner_id)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return completed


@router.get("/demo/{proposal_id}", response_model=BetaDemoResult)
def inspect_beta_demo(
    proposal_id: str,
    authorization: str | None = Header(default=None),
) -> BetaDemoResult:
    """Inspect a durable record only within the signed session's ownership boundary."""

    session = _require_session(authorization, allowed_roles=_READ_ROLES)
    return _load_result(
        _demo_store(),
        proposal_id,
        owner_id=_owner_filter(session),
    )


@router.get("/status")
def eacode_status() -> dict[str, object]:
    return {
        "status": "ok",
        "control_plane": "deterministic",
        "sdd_layer": True,
        "critic_boss_layer": True,
        "coding_tool_gateway": "vendor_neutral_normalized_proposal_v1",
        "tool_identity_authority": False,
        "demo_persistence": "tenant_scoped_runtime_store_integrity_checked",
        "production_authority_store": "postgresql_required",
        "demo_authorization": "signed_session_exact_scope_one_time_receipt",
        "execution_reservation": "atomic_single_transition",
        "provider_selection": "planned_only",
        "served_provider_evidence": "requires_opt_in_live_call",
        "live_process_execution_enabled": False,
        "final_authority": "deterministic_boss",
        "dispositions": ["accept", "repair", "reject", "clarify", "escalate"],
    }


@router.get("/capabilities")
def list_capabilities() -> dict[str, object]:
    models = [
        {
            "provider": capability.provider,
            "surface": capability.surface,
            "model_id": capability.model_id,
            "context_window": capability.context_window,
            "max_output_tokens": capability.max_output_tokens,
            "reasoning_efforts": list(capability.reasoning_efforts),
            "availability_state": capability.availability_state,
            "entitlement_state": capability.entitlement_state,
            "freshness_state": capability.freshness_state,
            "source_id": capability.source_id,
            "source_version": capability.source_version,
        }
        for capability in _registry.list_available_models()
    ]
    return {"status": "ok", "models": models, "count": len(models)}


@router.post("/select")
def select_provider(request: EACodeSelectRequest) -> dict[str, object]:
    """Resolve a deterministic planned route without calling a provider."""

    try:
        selection = ProviderSelection.model_validate(
            request.model_dump(exclude={"entitled_surfaces"})
        )
        planned = _selector.select(selection)
        capability = _registry.get(planned.model_id)
        if capability is None:
            raise ValueError("Resolved capability is missing.")
        if capability.availability_state != "available":
            raise ValueError("Resolved capability is unavailable.")
        if capability.freshness_state != "current":
            raise ValueError("Resolved capability is stale or unverified.")
        if (
            capability.entitlement_state != "open"
            and capability.surface not in request.entitled_surfaces
        ):
            raise ValueError(
                f"Entitlement required for provider surface: {capability.surface}"
            )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "status": "ok",
        "requested": request.model_dump(mode="json"),
        "planned": planned.model_dump(mode="json"),
        "served": None,
        "claim_boundary": (
            "This response is a deterministic plan, not proof of the provider or "
            "model actually served."
        ),
    }


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def selector_ui() -> HTMLResponse:
    """Serve a same-origin beta interface with no client-owned authority switch."""

    return HTMLResponse(
        r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EACODE Control Plane</title>
  <style>
    :root { color-scheme: light dark; font-family: system-ui, sans-serif; }
    body { max-width: 980px; margin: 2rem auto; padding: 0 1rem 4rem; }
    form, .card { display: grid; gap: .8rem; padding: 1rem; border: 1px solid #8886; border-radius: .7rem; margin: 1rem 0; }
    .grid { display: grid; gap: .8rem; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
    label { display: grid; gap: .25rem; font-weight: 600; }
    .check { display: flex; gap: .5rem; align-items: center; }
    button, input, select, textarea { padding: .65rem; font: inherit; }
    textarea { min-height: 9rem; font-family: ui-monospace, monospace; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #111; color: #eee; padding: 1rem; border-radius: .4rem; }
    .boundary { border-left: 4px solid currentColor; padding-left: 1rem; }
    .hint { opacity: .8; font-size: .92rem; }
  </style>
</head>
<body>
  <h1>EACODE ⚡</h1>
  <p class="boundary">Coding tools propose; EACODE governs. Tool identity is provenance only and cannot weaken hard gates, authorization, or the deterministic final decision.</p>

  <section class="card">
    <h2>Planned model route</h2>
    <p class="hint">Planning only. This section does not call a provider.</p>
    <form id="selector">
      <div class="grid">
        <label>Provider<select name="provider"><option>auto</option><option>deepseek</option><option>kimi</option><option>openai</option></select></label>
        <label>Profile<select name="profile"><option>minimal</option><option selected>medium</option><option>max</option></select></label>
        <label>Maximum cost (USD)<input name="max_cost_usd" type="number" min="0" step="0.01" value="1.00"></label>
      </div>
      <label class="check"><input name="kimi_code_entitled" type="checkbox">Kimi Code membership confirmed</label>
      <button type="submit">Resolve governed route</button>
    </form>
    <pre id="result">No route resolved yet.</pre>
  </section>

  <section class="card">
    <h2>Coding-tool gateway</h2>
    <p>Use the same gateway for Claude Code, Kimi Code, Cline, Codex, Gemini CLI, Antigravity, or another tool that can provide a proposed diff plus bounded validation commands.</p>
    <p class="hint">The signed EACODE session is separate from any model/provider key. Execution remains simulated until the sandbox contract is proven.</p>
    <label>Signed EACODE session token<input id="operator-token" type="password" autocomplete="off" spellcheck="false"></label>
    <div class="grid">
      <label>Coding tool<select id="tool-name"><option value="claude-code">Claude Code</option><option value="kimi-code">Kimi Code</option><option value="cline">Cline</option><option value="codex">Codex</option><option value="gemini-cli">Gemini CLI</option><option value="antigravity">Antigravity</option><option value="generic">Other / generic</option></select></label>
      <label>Tool version (optional)<input id="tool-version" autocomplete="off"></label>
      <label>Tool session ID (optional)<input id="tool-session" autocomplete="off"></label>
      <label>Specification ID<input id="spec-id" value="human-test-safe-change"></label>
      <label>Changed file<input id="changed-file" value="app/health.py"></label>
      <label>Validation command<input id="validation-command" value="pytest -q tests/test_health.py"></label>
    </div>
    <label>Objective<input id="objective" value="Add a safe health check"></label>
    <label>Proposed patch<textarea id="proposal-patch">def health():
    return 'ok'
</textarea></label>
    <button id="gateway-submit" type="button">Govern proposal</button>
    <button id="gateway-authorize" type="button" disabled>Authorize + simulate execution</button>
    <h3>Governance result</h3>
    <pre id="demo-result">No proposal submitted yet.</pre>
  </section>

  <script>
    const state = { proposalId: null };
    const bearerHeaders = (token) => ({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
    const token = () => document.getElementById('operator-token').value.trim();
    document.getElementById('selector').addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(event.target);
      const data = Object.fromEntries(form);
      data.max_cost_usd = Number(data.max_cost_usd);
      data.context_profile = data.profile;
      data.fallback_policy = 'none';
      data.entitled_surfaces = form.has('kimi_code_entitled') ? ['kimi_code'] : [];
      delete data.kimi_code_entitled;
      const response = await fetch('./select', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
      });
      document.getElementById('result').textContent = JSON.stringify(await response.json(), null, 2);
    });
    document.getElementById('gateway-submit').addEventListener('click', async () => {
      const output = document.getElementById('demo-result');
      if (!token()) { output.textContent = 'A signed EACODE session is required.'; return; }
      const command = document.getElementById('validation-command').value.trim();
      const payload = {
        tool: {
          name: document.getElementById('tool-name').value,
          version: document.getElementById('tool-version').value.trim() || null,
          session_id: document.getElementById('tool-session').value.trim() || null
        },
        objective: document.getElementById('objective').value,
        spec_id: document.getElementById('spec-id').value,
        patch: document.getElementById('proposal-patch').value,
        changed_files: [document.getElementById('changed-file').value],
        proposed_commands: command ? [command.split(/\s+/)] : []
      };
      const response = await fetch('./gateway/proposals', {
        method: 'POST', headers: bearerHeaders(token()), body: JSON.stringify(payload)
      });
      const body = await response.json();
      output.textContent = JSON.stringify(body, null, 2);
      if (!response.ok) return;
      state.proposalId = body.governance.proposal.proposal_id;
      document.getElementById('gateway-authorize').disabled = false;
    });
    document.getElementById('gateway-authorize').addEventListener('click', async () => {
      const output = document.getElementById('demo-result');
      if (!state.proposalId || !token()) return;
      const headers = bearerHeaders(token());
      const authResponse = await fetch(`./demo/${state.proposalId}/authorize`, {method: 'POST', headers});
      const receipt = await authResponse.json();
      output.textContent = JSON.stringify(receipt, null, 2);
      if (!authResponse.ok) return;
      const executionResponse = await fetch(`./demo/${state.proposalId}/execute`, {
        method: 'POST', headers, body: JSON.stringify({receipt_id: receipt.receipt_id})
      });
      output.textContent = JSON.stringify(await executionResponse.json(), null, 2);
    });
  </script>
</body>
</html>"""
    )


def _persist_result(result: BetaDemoResult, *, owner_id: str) -> None:
    try:
        _demo_store().create_result(result, owner_id=owner_id)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _demo_store():
    """Use PostgreSQL when configured; SQLite remains local/coursework compatibility."""

    return build_beta_demo_store(require_durable=False)


def _require_session(
    authorization: str | None,
    *,
    allowed_roles: set[str],
) -> BackendSession:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer signed session required.",
        )
    signing_key = os.getenv("EACODE_SESSION_SIGNING_KEY", "")
    if len(signing_key.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EACODE session signing is not configured.",
        )
    try:
        session = SessionSigner(signing_key.encode("utf-8")).verify(
            authorization.removeprefix("Bearer ").strip()
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired signed session.",
        ) from exc
    if not allowed_roles.intersection(session.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session role is not authorized for this operation.",
        )
    return session


def _owner_filter(session: BackendSession) -> str | None:
    return None if "admin" in session.roles else session.user_id


def _load_result(
    store,
    proposal_id: str,
    *,
    owner_id: str | None,
) -> BetaDemoResult:
    try:
        result = store.get_result(proposal_id, owner_id=owner_id)
    except PermissionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Demo run not found.")
    return result


def _public_receipt(receipt: DemoAuthorizationReceipt) -> EACodeAuthorizationResponse:
    return EACodeAuthorizationResponse(
        receipt_id=receipt.receipt_id,
        proposal_id=receipt.proposal_id,
        actor=receipt.actor,
        issued_at=receipt.issued_at,
        expires_at=receipt.expires_at,
    )
