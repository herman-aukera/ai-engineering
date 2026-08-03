"""HTTP product surface for the governed EACODE control plane."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from energy_core.beta_demo import BetaDemoResult, BetaDemoRunner
from energy_core.coding_agent import CodingProposal
from energy_core.provider_registry import ProviderSelection
from energy_core.provider_verified import (
    VerifiedCapabilityRegistry,
    VerifiedProviderSelector,
)

router = APIRouter(prefix="/eacode", tags=["eacode"])
_registry = VerifiedCapabilityRegistry()
_selector = VerifiedProviderSelector(_registry)
_demo_runner = BetaDemoRunner()
_demo_runs: dict[str, BetaDemoResult] = {}


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


class EACodeDemoRequest(CodingProposal):
    human_authorization: bool = False


@router.post("/demo", response_model=BetaDemoResult)
def run_beta_demo(request: EACodeDemoRequest) -> BetaDemoResult:
    """Run the keyless deterministic beta journey and retain its inspection record."""

    proposal = CodingProposal.model_validate(
        request.model_dump(exclude={"human_authorization"})
    )
    result = _demo_runner.run(
        proposal,
        human_authorization=request.human_authorization,
    )
    _demo_runs[proposal.proposal_id] = result
    return result


@router.get("/demo/{proposal_id}", response_model=BetaDemoResult)
def inspect_beta_demo(proposal_id: str) -> BetaDemoResult:
    """Inspect the complete authority, repair, evidence, and rollback record."""

    result = _demo_runs.get(proposal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Demo run not found.")
    return result


@router.get("/status")
def eacode_status() -> dict[str, object]:
    """Return an honest product and claim-boundary snapshot."""

    return {
        "status": "ok",
        "control_plane": "deterministic",
        "sdd_layer": True,
        "critic_boss_layer": True,
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
    """Serve a minimal same-origin selector interface."""

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
    button { padding: .7rem 1rem; cursor: pointer; }
    pre { white-space: pre-wrap; background: #111; color: #eee; padding: 1rem; border-radius: .4rem; }
    .boundary { border-left: 4px solid currentColor; padding-left: 1rem; }
  </style>
</head>
<body>
  <h1>EACODE ⚡</h1>
  <p class="boundary">The selector returns a governed plan. It does not claim a provider was called.</p>
  <form id="selector">
    <label>Provider
      <select name="provider"><option>auto</option><option>deepseek</option><option>kimi</option><option>openai</option></select>
    </label>
    <label>Profile
      <select name="profile"><option>minimal</option><option selected>medium</option><option>max</option></select>
    </label>
    <label>Maximum cost (USD)<input name="max_cost_usd" type="number" min="0" step="0.01" value="1.00"></label>
    <label>Premium reason<input name="premium_reason" placeholder="Required for premium escalation"></label>
    <label class="check"><input name="kimi_code_entitled" type="checkbox">Kimi Code membership confirmed</label>
    <button type="submit">Resolve governed route</button>
  </form>
  <h2>Decision evidence</h2>
  <pre id="result">No route resolved yet.</pre>
  <script>
    document.getElementById('selector').addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(event.target);
      const data = Object.fromEntries(form);
      data.max_cost_usd = Number(data.max_cost_usd);
      data.context_profile = data.profile;
      data.fallback_policy = 'none';
      data.entitled_surfaces = form.has('kimi_code_entitled') ? ['kimi_code'] : [];
      delete data.kimi_code_entitled;
      if (!data.premium_reason) data.premium_reason = null;
      const response = await fetch('/eacode/select', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
      });
      document.getElementById('result').textContent = JSON.stringify(await response.json(), null, 2);
    });
  </script>
</body>
</html>"""
    )
