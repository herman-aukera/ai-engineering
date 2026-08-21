"""HTTP product surface for the governed EACODE control plane."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from energy_core.beta_demo import BetaDemoResult, BetaDemoRunner
from energy_core.beta_store import DemoAuthorizationReceipt, SQLiteBetaDemoStore
from energy_core.coding_agent import CodingProposal
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
    try:
        _demo_store().create_result(result, owner_id=session.user_id)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result


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
        "demo_persistence": "tenant_scoped_sqlite_integrity_checked",
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
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EACODE Control Plane</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 880px; margin: 2rem auto; padding: 0 1rem; }
    form { display: grid; gap: .8rem; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
    label { display: grid; gap: .25rem; font-weight: 600; }
    .check { display: flex; gap: .5rem; align-items: center; }
    button, input, select { padding: .65rem; }
    pre { white-space: pre-wrap; background: #111; color: #eee; padding: 1rem; border-radius: .4rem; }
    .boundary { border-left: 4px solid currentColor; padding-left: 1rem; }
  </style>
</head>
<body>
  <h1>EACODE ⚡</h1>
  <p class="boundary">Provider selection is a deterministic plan and does not claim a provider was called.</p>
  <form id="selector">
    <label>Provider<select name="provider"><option>auto</option><option>deepseek</option><option>kimi</option><option>openai</option></select></label>
    <label>Profile<select name="profile"><option>minimal</option><option selected>medium</option><option>max</option></select></label>
    <label>Maximum cost (USD)<input name="max_cost_usd" type="number" min="0" step="0.01" value="1.00"></label>
    <label class="check"><input name="kimi_code_entitled" type="checkbox">Kimi Code membership confirmed</label>
    <button type="submit">Resolve governed route</button>
  </form>
  <pre id="result">No route resolved yet.</pre>
  <hr>
  <h2>Governed coding journey</h2>
  <p>Preparation and inspection require a signed session. Execution additionally requires
     operator authority and a one-time server-issued receipt. Execution remains simulated.</p>
  <label>Signed session token<input id="operator-token" type="password" autocomplete="off"></label>
  <button id="beta-demo" type="button">Prepare, authorize, and run beta demo</button>
  <h3>Repair and authority timeline</h3>
  <pre id="demo-result">No demo run yet.</pre>
  <script>
    const bearerHeaders = (token) => ({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
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
    document.getElementById('beta-demo').addEventListener('click', async () => {
      const output = document.getElementById('demo-result');
      const proposalId = `browser-demo-${Date.now()}`;
      const token = document.getElementById('operator-token').value.trim();
      if (!token) { output.textContent = 'A signed operator session is required.'; return; }
      const headers = bearerHeaders(token);
      const preparedResponse = await fetch('./demo', {
        method: 'POST', headers,
        body: JSON.stringify({
          proposal_id: proposalId,
          objective: 'Add a safe health check',
          spec_id: '0012-production-hardening',
          patch: "def health():\n    return 'todo'\n",
          changed_files: ['app/health.py'],
          proposed_commands: [['pytest', '-q', 'tests/test_health.py']]
        })
      });
      const prepared = await preparedResponse.json();
      output.textContent = JSON.stringify(prepared, null, 2);
      if (!preparedResponse.ok) return;
      const authorizationResponse = await fetch(`./demo/${proposalId}/authorize`, {
        method: 'POST', headers
      });
      const receipt = await authorizationResponse.json();
      output.textContent = JSON.stringify(receipt, null, 2);
      if (!authorizationResponse.ok) return;
      const executionResponse = await fetch(`./demo/${proposalId}/execute`, {
        method: 'POST', headers, body: JSON.stringify({receipt_id: receipt.receipt_id})
      });
      output.textContent = JSON.stringify(await executionResponse.json(), null, 2);
    });
  </script>
</body>
</html>"""
    )


def _demo_store() -> SQLiteBetaDemoStore:
    return SQLiteBetaDemoStore(
        os.getenv(
            "EACODE_DEMO_DB_PATH",
            str(Path(".eacode") / "eacode-demo.sqlite3"),
        )
    )


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
    store: SQLiteBetaDemoStore,
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
