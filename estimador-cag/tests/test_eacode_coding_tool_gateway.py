from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from energy_core.beta_demo import BetaDemoRunner
from energy_core.coding_tool_gateway import (
    CodingToolIdentity,
    CodingToolProposalRequest,
    normalize_coding_tool_proposal,
)
from energy_core.identity import SessionSigner

TOOLS = (
    "claude-code",
    "kimi-code",
    "cline",
    "codex",
    "antigravity",
    "gemini-cli",
    "generic",
)
SIGNING_KEY = "test-eacode-gateway-signing-key-32-bytes"
client = TestClient(app)


def _request(tool: str, *, patch: str = "def health():\n    return 'ok'\n") -> CodingToolProposalRequest:
    return CodingToolProposalRequest(
        tool=CodingToolIdentity(name=tool, version="test", session_id=f"{tool}-session"),
        objective="Add a safe health check",
        spec_id="human-test-gateway",
        patch=patch,
        changed_files=("app/health.py",),
        proposed_commands=(("pytest", "-q", "tests/test_health.py"),),
    )


def _headers() -> dict[str, str]:
    token = SessionSigner(SIGNING_KEY.encode()).issue(
        user_id="gateway-tester",
        roles=("operator",),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    return {"Authorization": f"Bearer {token}"}


def test_named_coding_tools_normalize_to_identical_policy_input() -> None:
    proposals = [normalize_coding_tool_proposal(_request(tool)).proposal for tool in TOOLS]

    assert all(proposal == proposals[0] for proposal in proposals)
    assert proposals[0].proposal_id.startswith("gateway-")


def test_named_coding_tools_receive_identical_safe_governance() -> None:
    decisions = []
    gate_statuses = []
    for tool in TOOLS:
        result = BetaDemoRunner().prepare(normalize_coding_tool_proposal(_request(tool)).proposal)
        decisions.append(result.final_decision.disposition)
        gate_statuses.append(tuple(finding.status for finding in result.hard_gate.findings))

    assert decisions == ["accept"] * len(TOOLS)
    assert len(set(gate_statuses)) == 1
    assert all(status == "pass" for status in gate_statuses[0])


@pytest.mark.parametrize("tool", TOOLS)
def test_secret_exfiltration_is_rejected_independently_of_tool_name(tool: str) -> None:
    fake_secret = "sk-" + "A" * 32  # test-secret-fixture
    request = _request(tool, patch=f"API_KEY = '{fake_secret}'\n")

    result = BetaDemoRunner().prepare(normalize_coding_tool_proposal(request).proposal)

    secret_gate = next(
        finding for finding in result.hard_gate.findings if finding.finding_id == "secret-hygiene"
    )
    assert secret_gate.status == "fail"
    assert result.final_decision.disposition == "reject"


def test_gateway_api_preserves_provenance_without_granting_tool_authority(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EACODE_DEMO_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("EACODE_SESSION_SIGNING_KEY", SIGNING_KEY)
    payload = _request("claude-code").model_dump(mode="json")

    assert client.post("/eacode/gateway/proposals", json=payload).status_code == 401
    response = client.post("/eacode/gateway/proposals", headers=_headers(), json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["source_tool"]["name"] == "claude-code"
    assert body["normalization_version"] == "eacode-tool-gateway.v1"
    assert body["authority"] == "deterministic_eacode_governor"
    assert body["execution_mode"] == "simulated"
    assert body["governance"]["final_decision"]["decided_by"] == "deterministic-action-governor"
