"""One-time fail-closed migration wiring committee/adaptive into V2."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one marker in {path}, found {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def wire_contracts() -> None:
    path = ROOT / "app" / "energy_chat" / "api_v2_contracts.py"
    replace_once(
        path,
        '    routing_reason: str = ""\n    provider_metrics_summary: ProviderMetricsSummary = Field(\n',
        '    routing_reason: str = ""\n'
        '    requested_orchestration_mode: OrchestrationMode = "critic"\n'
        '    resolved_orchestration_mode: Literal["critic", "committee"] = "critic"\n'
        '    orchestration_candidate_count: int = Field(default=1, ge=1, le=8)\n'
        '    orchestration_reason: str = ""\n'
        '    provider_metrics_summary: ProviderMetricsSummary = Field(\n',
    )


def wire_application() -> None:
    path = ROOT / "app" / "energy_chat" / "graph_application.py"
    replace_once(
        path,
        "from app.energy_chat.candidate_provider import (\n"
        "    BaselineCandidateProvider,\n"
        "    CandidateProvider,\n"
        "    DeterministicCandidateProvider,\n"
        "    ProviderBudget,\n"
        ")\n",
        "from app.energy_chat.candidate_provider import (\n"
        "    BaselineCandidateProvider,\n"
        "    CandidateProvider,\n"
        "    DeterministicCandidateProvider,\n"
        "    ProviderBudget,\n"
        ")\n"
        "from app.energy_chat.committee_orchestration import (\n"
        "    CommitteeCandidateProvider,\n"
        "    resolve_adaptive_orchestration,\n"
        ")\n",
    )
    replace_once(
        path,
        "    _validate_v2_selectors(request, active_execution_profile)\n"
        "    thread_id = request.thread_id or active_id_factory.new_thread_id()\n",
        "    _validate_v2_selectors(request, active_execution_profile)\n"
        "    resolved_orchestration, orchestration_reason = _resolve_orchestration(\n"
        "        request, active_execution_profile\n"
        "    )\n"
        "    thread_id = request.thread_id or active_id_factory.new_thread_id()\n",
    )
    replace_once(
        path,
        '            "execution_profile": active_execution_profile,\n'
        "        }\n"
        "    )\n",
        '            "execution_profile": active_execution_profile,\n'
        '            "metadata": {\n'
        '                **request.metadata,\n'
        '                "resolved_orchestration_mode": resolved_orchestration,\n'
        '                "orchestration_reason": orchestration_reason,\n'
        '            },\n'
        "        }\n"
        "    )\n",
    )
    replace_once(
        path,
        '    if request.orchestration_mode != "critic":\n'
        "        raise UnsupportedProfileError(\n"
        '            field="orchestration_mode",\n'
        "            value=request.orchestration_mode,\n"
        "            detail=(\n"
        "                f\"Orchestration mode '{request.orchestration_mode}' is not implemented; \"\n"
        "                \"only 'critic' is active\"\n"
        "            ),\n"
        "        )\n",
        '    if request.orchestration_mode == "single":\n'
        "        raise UnsupportedProfileError(\n"
        '            field="orchestration_mode",\n'
        "            value=request.orchestration_mode,\n"
        '            detail="Single mode is not a distinct runtime; use critic.",\n'
        "        )\n"
        '    if execution_profile == "live_bounded" and request.orchestration_mode != "critic":\n'
        "        raise UnsupportedProfileError(\n"
        '            field="orchestration_mode",\n'
        "            value=request.orchestration_mode,\n"
        "            detail=(\n"
        "                \"Live committee/adaptive orchestration is blocked until matched \"\n"
        "                \"quality, cost, and latency calibration exists.\"\n"
        "            ),\n"
        "        )\n",
    )
    replace_once(
        path,
        "\ndef _resolve_provider(\n",
        "\ndef _resolve_orchestration(\n"
        "    request: EnergyChatV2Request,\n"
        "    execution_profile: ExecutionProfile,\n"
        ") -> tuple[str, str]:\n"
        "    if execution_profile == \"live_bounded\":\n"
        "        return \"critic\", \"live route uses calibrated critic orchestration only\"\n"
        "    if request.orchestration_mode == \"committee\":\n"
        "        return (\n"
        "            \"committee\",\n"
        "            \"caller selected bounded three-proposal deterministic committee\",\n"
        "        )\n"
        "    if request.orchestration_mode == \"adaptive\":\n"
        "        decision = resolve_adaptive_orchestration(\n"
        "            user_request=request.user_message,\n"
        "            mode=request.mode,\n"
        "            constraints=request.required_constraints,\n"
        "            required_sections=request.required_sections,\n"
        "        )\n"
        "        return (\n"
        "            decision.resolved_mode,\n"
        "            \"adaptive policy: \" + \",\".join(decision.reason_codes),\n"
        "        )\n"
        "    return \"critic\", \"caller selected the standard critic pipeline\"\n"
        "\n\n"
        "def _resolve_provider(\n",
    )
    replace_once(
        path,
        '    if execution_profile == "deterministic":\n'
        "        return DeterministicCandidateProvider()\n",
        '    if execution_profile == "deterministic":\n'
        '        if request.metadata.get("resolved_orchestration_mode") == "committee":\n'
        "            return CommitteeCandidateProvider()\n"
        "        return DeterministicCandidateProvider()\n",
    )
    replace_once(
        path,
        "    metrics_list = result.provider_metrics\n",
        "    metrics_list = result.provider_metrics\n"
        "    resolved_orchestration = request.metadata.get(\n"
        '        "resolved_orchestration_mode", "critic"\n'
        "    )\n"
        "    orchestration_reason = request.metadata.get(\n"
        '        "orchestration_reason", "standard critic pipeline"\n'
        "    )\n"
        "    orchestration_candidate_count = (\n"
        '        3 if resolved_orchestration == "committee" else 1\n'
        "    )\n",
    )
    replace_once(
        path,
        '        elif execution_profile == "deterministic":\n'
        '            routing_reason = "deterministic route used the local template provider"\n',
        '        elif execution_profile == "deterministic":\n'
        "            routing_reason = (\n"
        "                f\"{orchestration_reason}; deterministic provider={last.provider}\"\n"
        "            )\n",
    )
    replace_once(
        path,
        "        routing_reason=routing_reason,\n"
        "        provider_metrics_summary=provider_summary,\n",
        "        routing_reason=routing_reason,\n"
        "        requested_orchestration_mode=request.orchestration_mode,\n"
        "        resolved_orchestration_mode=resolved_orchestration,\n"
        "        orchestration_candidate_count=orchestration_candidate_count,\n"
        "        orchestration_reason=orchestration_reason,\n"
        "        provider_metrics_summary=provider_summary,\n",
    )


def main() -> None:
    wire_contracts()
    wire_application()
    print("EACHAT_ORCHESTRATION_WIRING_OK")


if __name__ == "__main__":
    main()
