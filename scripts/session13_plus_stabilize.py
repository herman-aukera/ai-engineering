"""Apply the approved Session 13 Plus stabilization repairs.

This script is intentionally exact-string driven. It aborts when the audited
source no longer matches, preventing a blind patch against a moved branch.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _path(relative: str) -> Path:
    return ROOT / relative


def _read(relative: str) -> str:
    return _path(relative).read_text(encoding="utf-8")


def _write(relative: str, content: str) -> None:
    path = _path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def _replace_once(relative: str, old: str, new: str) -> None:
    content = _read(relative)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match in {relative}, found {count}: {old[:80]!r}")
    _write(relative, content.replace(old, new, 1))


def _append_once(relative: str, marker: str, addition: str) -> None:
    content = _read(relative)
    if marker in content:
        return
    _write(relative, content.rstrip() + "\n\n" + addition.strip() + "\n")


def repair_service_contract() -> None:
    relative = "estimador-cag/app/services/reviewed_graph_estimation.py"
    _replace_once(
        relative,
        "class ReviewedGraphEstimationApplication(Protocol):\n    async def start(",
        "class ReviewedGraphEstimationApplication(Protocol):\n    graph: ReviewedGraphRunner\n\n    async def start(",
    )
    _replace_once(
        relative,
        "        execution_metadata: dict[str, object] | None = None,\n    ) -> ReviewedGraphRun:\n        resolved_estimation_id = str(estimation_id or uuid4())",
        "        execution_metadata: dict[str, object] | None = None,\n"
        "        provider: str | None = None,\n"
        "        reasoning: str | None = None,\n"
        "        context_detail: str | None = None,\n"
        "    ) -> ReviewedGraphRun:\n        resolved_estimation_id = str(estimation_id or uuid4())",
    )
    _replace_once(
        relative,
        "    async def aupdate_state(\n        self,\n        config: dict[str, object],\n        values: dict[str, object],\n        as_node: str | None = None,\n    ) -> dict[str, object]:\n        \"\"\"Create a checkpoint on the selected thread.\"\"\"\n",
        "    async def aupdate_state(\n        self,\n        config: dict[str, object],\n        values: dict[str, object],\n        as_node: str | None = None,\n    ) -> dict[str, object]:\n        \"\"\"Create a checkpoint on the selected thread.\"\"\"\n\n"
        "    def astream(\n"
        "        self,\n"
        "        input: ReviewedEstimationGraphState,\n"
        "        config: dict[str, object] | None = None,\n"
        "        *,\n"
        "        stream_mode: str,\n"
        "    ) -> AsyncIterator[Mapping[str, object]]:\n"
        "        \"\"\"Stream graph updates for one reviewed execution.\"\"\"\n",
    )


def repair_ci_boundary() -> None:
    _replace_once(
        ".github/workflows/ci.yml",
        "      - name: Tests\n        run: uv run pytest -q\n",
        "      - name: Tests\n        run: uv run pytest -q -m \"not live_provider\"\n",
    )

    pyproject = "estimador-cag/pyproject.toml"
    _append_once(
        pyproject,
        "live_provider: requires explicit real provider credentials",
        """
[tool.pytest.ini_options]
markers = [
    "live_provider: requires explicit real provider credentials and is excluded from deterministic CI",
]
""",
    )

    relative = "estimador-cag/tests/test_session13_plus_provider_calibration.py"
    content = _read(relative)
    old = '''def _has_deepseek_key() -> bool:\n    key = os.environ.get("DEEPSEEK_API_KEY", "")\n    return bool(key) and key not in ("dummy", "fake")\n'''
    new = '''_NON_LIVE_KEY_SENTINELS = {"", "test", "dummy", "fake", "placeholder", "example"}\n\n\ndef _has_deepseek_key() -> bool:\n    key = os.environ.get("DEEPSEEK_API_KEY", "").strip().lower()\n    return key not in _NON_LIVE_KEY_SENTINELS\n'''
    if old not in content:
        raise RuntimeError("DeepSeek live-key gate no longer matches audited source")
    content = content.replace(old, new, 1)
    for _ in range(3):
        marker = "@pytest.mark.skipif(\n"
        index = content.find(marker)
        if index < 0:
            raise RuntimeError("Expected three live-provider skip markers")
        content = content[:index] + "@pytest.mark.live_provider\n" + content[index:]
        # Avoid finding the same marker again by replacing only the first unmarked form.
        content = content[: index + len("@pytest.mark.live_provider\n")] + content[index + len("@pytest.mark.live_provider\n"):]
        # Protect the just-marked occurrence during the next search.
        content = content.replace(
            "@pytest.mark.live_provider\n@pytest.mark.skipif(\n",
            "@pytest.mark.live_provider\n@pytest.mark.skipif(\n",
            1,
        )
        # Search starts after this point on the next loop.
        next_pos = content.find(marker, index + len("@pytest.mark.live_provider\n") + len(marker))
        if _ < 2 and next_pos < 0:
            raise RuntimeError("Missing remaining live-provider marker")
        if _ < 2:
            prefix = content[:next_pos]
            suffix = content[next_pos:]
            suffix = suffix.replace(marker, "__NEXT_LIVE_SKIP__", 1)
            content = prefix + suffix
            content = content.replace("__NEXT_LIVE_SKIP__", marker, 1)
    # The loop above can re-target earlier markers in some Python string layouts; normalize idempotently.
    content = content.replace(
        "@pytest.mark.live_provider\n@pytest.mark.live_provider\n",
        "@pytest.mark.live_provider\n",
    )
    # Ensure exactly the first three skip blocks are marked.
    lines = content.splitlines()
    skip_indexes = [i for i, line in enumerate(lines) if line == "@pytest.mark.skipif("]
    for index in skip_indexes[:3]:
        if index == 0 or lines[index - 1] != "@pytest.mark.live_provider":
            lines.insert(index, "@pytest.mark.live_provider")
            skip_indexes = [i + 1 if i >= index else i for i in skip_indexes]
    _write(relative, "\n".join(lines) + "\n")

    _write(
        ".github/workflows/session13-plus-live-provider.yml",
        '''name: Session 13 Plus live provider smoke\n\non:\n  workflow_dispatch:\n\npermissions:\n  contents: read\n\njobs:\n  live-provider:\n    runs-on: ubuntu-latest\n    defaults:\n      run:\n        working-directory: estimador-cag\n    env:\n      DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}\n      KIMI_API_KEY: ${{ secrets.KIMI_API_KEY }}\n      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}\n    steps:\n      - uses: actions/checkout@v4\n      - uses: astral-sh/setup-uv@v5\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.11"\n      - run: uv sync --frozen --extra dev\n      - name: Run explicitly credentialed provider tests\n        run: uv run pytest -q -m live_provider\n''',
    )


def repair_sse() -> None:
    relative = "estimador-cag/app/routers/reviewed_graph_estimations.py"
    content = _read(relative)
    content = content.replace("import json\nimport logging\n", "import asyncio\nimport json\nimport logging\n", 1)
    content = content.replace(
        "from collections.abc import AsyncIterator\nfrom typing import Any, cast\nfrom uuid import UUID\n",
        "from collections.abc import AsyncIterator, Mapping\nfrom typing import Any, cast\nfrom uuid import UUID, uuid4\n",
        1,
    )
    content = content.replace(
        "from app.services.graph_estimation import",
        "from app.services.graph_estimation import",
        1,
    )
    if "from app.services.graph_estimation import thread_id_from_estimation_id" not in content:
        insert_after = "from app.services.audit_export import build_estimation_audit_packet\n"
        if insert_after not in content:
            raise RuntimeError("Router import anchor missing")
        content = content.replace(
            insert_after,
            insert_after + "from app.services.graph_estimation import thread_id_from_estimation_id\n",
            1,
        )

    marker = '@router.post("/estimate/graph/reviewed/stream")\n'
    if marker not in content:
        raise RuntimeError("SSE endpoint marker missing")
    prefix = content.split(marker, 1)[0]
    safe_block = r'''_SSE_ALLOWED_SCALAR_KEYS = frozenset(
    {
        "status",
        "review_required",
        "structure_review_revision",
        "structure_review_status",
        "final_review_revision",
        "final_review_status",
    }
)


def _stream_identity(estimation_id: UUID | None) -> tuple[UUID, str]:
    resolved = estimation_id or uuid4()
    return resolved, thread_id_from_estimation_id(str(resolved))


def _safe_activity_delta(node_name: str, delta: object) -> dict[str, object]:
    """Project one graph update into an allow-listed public activity event."""
    if not isinstance(delta, Mapping):
        return {"node": node_name, "updated_keys": []}

    payload: dict[str, object] = {
        "node": node_name,
        "updated_keys": sorted(str(key) for key in delta if key in _SSE_ALLOWED_SCALAR_KEYS),
    }
    for key in _SSE_ALLOWED_SCALAR_KEYS:
        value = delta.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            if key in delta:
                payload[key] = value

    trace_events = delta.get("trace_events")
    if isinstance(trace_events, list):
        payload["trace_events"] = [
            {
                "event_type": str(event.get("event_type", "unknown")),
                "node": str(event.get("node", node_name)),
                "state_delta_keys": [
                    str(item) for item in event.get("state_delta_keys", []) if isinstance(item, str)
                ],
            }
            for event in trace_events
            if isinstance(event, Mapping)
        ]
    return payload


def _terminal_event_payload(run: ReviewedGraphRun) -> dict[str, object]:
    return {
        "status": run.execution_status,
        "estimation_id": run.estimation_id,
        "thread_id": run.thread_id,
        "next_nodes": list(run.next_nodes),
        "interrupt_count": len(run.interrupts),
    }


@router.post("/estimate/graph/reviewed/stream")
async def stream_reviewed_graph_estimation(
    payload: ReviewedGraphStartRequest,
    request: Request,
) -> EventSourceResponse:
    """Stream allow-listed reviewed-graph activity without exposing graph state."""
    service = get_reviewed_graph_estimation_service(request)
    resolved_id, thread_id = _stream_identity(payload.estimation_id)

    initial_state = ReviewedEstimationGraphState(
        **new_estimation_graph_state(
            transcript=payload.transcript,
            estimation_id=str(resolved_id),
            graph_version="session13.plus.v1",
        )
    )
    initial_state.update(
        {
            "human_review_mode": payload.human_review_mode,
            "structure_review_revision": 0,
            "final_review_revision": 0,
            "execution_budgets": ExecutionBudgetSnapshot().model_dump(mode="json"),
        }
    )
    if payload.provider or payload.reasoning or payload.context_detail:
        initial_state["provider_selection"] = {
            "provider": payload.provider or "deepseek",
            "reasoning": payload.reasoning or "medium",
            "context_detail": payload.context_detail or "medium",
        }

    config: dict[str, object] = {"configurable": {"thread_id": thread_id}}

    async def event_generator() -> AsyncIterator[ServerSentEvent]:
        try:
            if payload.estimation_id is not None:
                try:
                    existing = await service.inspect(estimation_id=resolved_id)
                except ReviewedGraphNotFoundError:
                    existing = None
                if existing is not None:
                    yield ServerSentEvent(
                        event=existing.execution_status,
                        data=json.dumps(_terminal_event_payload(existing)),
                    )
                    return

            if await request.is_disconnected():
                return

            async for event in service.graph.astream(
                initial_state,
                config,
                stream_mode="updates",
            ):
                if await request.is_disconnected():
                    logger.info("reviewed_graph_stream_client_disconnected", extra={"thread_id": thread_id})
                    return
                if isinstance(event, Mapping):
                    for node_name, state_delta in event.items():
                        yield ServerSentEvent(
                            event="activity",
                            data=json.dumps(_safe_activity_delta(str(node_name), state_delta)),
                        )

            run = await service.inspect(estimation_id=resolved_id)
            yield ServerSentEvent(
                event=run.execution_status,
                data=json.dumps(_terminal_event_payload(run)),
            )
        except asyncio.CancelledError:
            logger.info("reviewed_graph_stream_cancelled", extra={"thread_id": thread_id})
            raise
        except Exception:
            logger.exception("reviewed_graph_stream_failed", extra={"thread_id": thread_id})
            yield ServerSentEvent(
                event="error",
                data=json.dumps({"status": "error", "code": "reviewed_graph_stream_failed"}),
            )

    return EventSourceResponse(event_generator())
'''
    _write(relative, prefix + safe_block)


def repair_routing_authority() -> None:
    relative = "estimador-cag/app/schemas/v3_routing.py"
    _replace_once(
        relative,
        'ReasoningEffort = Literal["none", "high", "max"]',
        'ReasoningEffort = Literal["none", "low", "high", "max"]',
    )

    relative = "estimador-cag/app/schemas/v3_registry.py"
    _replace_once(
        relative,
        'ReasoningEffort = Literal[\n    "none",\n    "high",\n    "max",\n]',
        'ReasoningEffort = Literal[\n    "none",\n    "low",\n    "high",\n    "max",\n]',
    )

    relative = "estimador-cag/app/services/v3_complexity_router.py"
    _replace_once(
        relative,
        'def build_model_routing_plan(\n    assessment: ComplexityAssessment,\n    *,\n    profile: ExecutionProfileV3 = "balanced",\n) -> ModelRoutingPlan:\n    """Build a deterministic per-stage plan; models never select their own tier."""\n\n    routes: dict[RoutingStage, ModelRoute] = {}',
        'def build_model_routing_plan(\n    assessment: ComplexityAssessment,\n    *,\n    profile: ExecutionProfileV3 = "balanced",\n    authoritative_level: ComplexityLevel | None = None,\n) -> ModelRoutingPlan:\n    """Build a deterministic per-stage plan from explicit routing authority.\n\n    ``assessment`` remains the immutable deterministic evidence record.  A\n    separately arbitrated level may control routing without fabricating a\n    contradictory score/dimension assessment.\n    """\n\n    effective_level = authoritative_level or assessment.level\n    routes: dict[RoutingStage, ModelRoute] = {}',
    )
    _replace_once(relative, "        spec = _route_spec(stage, assessment.level, profile)", "        spec = _route_spec(stage, effective_level, profile)")
    _replace_once(relative, '                f"complexity:{assessment.level}",', '                f"complexity:{effective_level}",')
    _replace_once(
        relative,
        '        "complexity": assessment.model_dump(mode="json"),\n        "routes":',
        '        "complexity": assessment.model_dump(mode="json"),\n        "authoritative_level": effective_level,\n        "routes":',
    )

    relative = "estimador-cag/app/generation/graph/nodes/semantic_classify.py"
    content = _read(relative)
    old = '''        # 4. Route plan from the arbitrated (authoritative) level\n        authoritative = ComplexityAssessment(\n            level=arbitrated.arbitrated_level,\n            score=deterministic.score,\n            confidence=deterministic.confidence,\n            dimensions=deterministic.dimensions,\n            reasons=deterministic.reasons,\n            missing_information=deterministic.missing_information,\n            detected_languages=deterministic.detected_languages,\n            classifier_version=deterministic.classifier_version,\n            human_review_required=arbitrated.human_review_required,\n        )\n        route_plan = build_model_routing_plan(authoritative)\n'''
    new = '''        # 4. Route plan uses explicit arbitration authority while retaining the\n        # deterministic assessment as the immutable score/dimension evidence.\n        route_plan = build_model_routing_plan(\n            deterministic,\n            authoritative_level=arbitrated.arbitrated_level,\n        )\n'''
    if old not in content:
        raise RuntimeError("Synthetic authoritative assessment block not found")
    content = content.replace(old, new, 1)
    content = content.replace(
        "from app.schemas.v3_routing import ComplexityAssessment, ComplexitySignals\n",
        "from app.schemas.v3_routing import ComplexitySignals\n",
        1,
    )
    content = content.replace(
        "    ) -> ReviewedEstimationGraphState:\n",
        "    ) -> Command:\n",
        1,
    )
    _write(relative, content)

    _replace_once(
        "estimador-cag/app/generation/graph/reviewed_build.py",
        '    builder.add_edge("semantic_classify", "structure_phase")\n',
        "",
    )


def repair_provider_truthfulness() -> None:
    _replace_once(
        "estimador-cag/app/ui/provider_selector.py",
        '    "auto": "Auto (least expensive verified)",',
        '    "auto": "Auto (policy preview; not live calibrated)",',
    )
    _replace_once(
        "estimador-cag/app/ui/provider_selector.py",
        '    "minimal": "Minimal (no explicit reasoning)",',
        '    "minimal": "Minimal (provider-specific lowest supported effort)",',
    )
    _replace_once(
        "estimador-cag/app/ui/provider_selector.py",
        '    st.caption("Session 13 Plus — provider, reasoning, and context-detail routing preview.")',
        '    st.caption("Session 13 Plus routing preview. Selection persistence is implemented; live per-stage switching remains capability-gated.")',
    )

    _write(
        "estimador-cag/app/services/v3_registry_seed.py",
        '''"""Seed documented provider capability records without promoting them.\n\nSeed data is a policy catalogue, not live reachability or benchmark evidence.\nOperational promotion must happen through explicit capability evidence.\n"""\n\nfrom __future__ import annotations\n\nfrom app.schemas.v3_registry import ModelRecord\nfrom app.services.v3_model_registry import ModelRegistry\n\n\ndef build_seeded_registry() -> ModelRegistry:\n    """Return deterministic documented records; none are enabled by seeding."""\n    return ModelRegistry(\n        [\n            ModelRecord(\n                provider="deepseek",\n                provider_model_id="deepseek-v4-flash",\n                display_name="DeepSeek V4 Flash",\n                capability_tier="flash",\n                context_window=128_000,\n                max_output=8_192,\n                input_modalities=["text"],\n                tool_support=True,\n                structured_output_support=True,\n                reasoning_efforts=["none", "high"],\n                speed_class="fast",\n                cost_metadata_version="session13-v1",\n                availability="available",\n                calibration_status="documented",\n            ),\n            ModelRecord(\n                provider="deepseek",\n                provider_model_id="deepseek-v4-pro",\n                display_name="DeepSeek V4 Pro",\n                capability_tier="pro",\n                context_window=128_000,\n                max_output=8_192,\n                input_modalities=["text"],\n                tool_support=True,\n                structured_output_support=True,\n                reasoning_efforts=["none", "high", "max"],\n                speed_class="fast",\n                cost_metadata_version="session13-v1",\n                availability="available",\n                calibration_status="documented",\n            ),\n            ModelRecord(\n                provider="moonshot",\n                provider_model_id="kimi-for-coding",\n                display_name="Kimi K2.7 Code",\n                capability_tier="pro",\n                context_window=256_000,\n                max_output=8_192,\n                input_modalities=["text"],\n                tool_support=True,\n                structured_output_support=True,\n                reasoning_efforts=["high"],\n                speed_class="medium",\n                cost_metadata_version="session13-v2",\n                availability="available",\n                calibration_status="documented",\n            ),\n            ModelRecord(\n                provider="moonshot",\n                provider_model_id="kimi-for-coding-highspeed",\n                display_name="Kimi K2.7 Code HighSpeed",\n                capability_tier="pro",\n                context_window=256_000,\n                max_output=8_192,\n                input_modalities=["text"],\n                tool_support=True,\n                structured_output_support=True,\n                reasoning_efforts=["high"],\n                speed_class="fast",\n                cost_metadata_version="session13-v2",\n                availability="available",\n                calibration_status="documented",\n            ),\n            ModelRecord(\n                provider="moonshot",\n                provider_model_id="k3",\n                display_name="Kimi K3",\n                capability_tier="max",\n                context_window=1_000_000,\n                max_output=8_192,\n                input_modalities=["text", "image"],\n                tool_support=True,\n                structured_output_support=True,\n                reasoning_efforts=["low", "high", "max"],\n                speed_class="medium",\n                cost_metadata_version="session13-v2",\n                availability="available",\n                calibration_status="documented",\n            ),\n            ModelRecord(\n                provider="openai",\n                provider_model_id="gpt-5.6-luna",\n                display_name="GPT-5.6 Luna",\n                capability_tier="flash",\n                context_window=128_000,\n                max_output=16_384,\n                input_modalities=["text"],\n                tool_support=True,\n                structured_output_support=True,\n                reasoning_efforts=["none", "high"],\n                speed_class="fast",\n                cost_metadata_version="session13-v1",\n                availability="available",\n                calibration_status="documented",\n            ),\n            ModelRecord(\n                provider="openai",\n                provider_model_id="gpt-5.6-terra",\n                display_name="GPT-5.6 Terra",\n                capability_tier="pro",\n                context_window=128_000,\n                max_output=16_384,\n                input_modalities=["text"],\n                tool_support=True,\n                structured_output_support=True,\n                reasoning_efforts=["none", "high", "max"],\n                speed_class="medium",\n                cost_metadata_version="session13-v1",\n                availability="available",\n                calibration_status="documented",\n            ),\n            ModelRecord(\n                provider="openai",\n                provider_model_id="gpt-5.6-sol",\n                display_name="GPT-5.6 Sol",\n                capability_tier="max",\n                context_window=200_000,\n                max_output=16_384,\n                input_modalities=["text", "image"],\n                tool_support=True,\n                structured_output_support=True,\n                reasoning_efforts=["none", "high", "max"],\n                speed_class="slow",\n                cost_metadata_version="session13-v1",\n                availability="available",\n                calibration_status="documented",\n            ),\n        ]\n    )\n''',
    )

    _write(
        "estimador-cag/app/services/v5_provider_selector.py",
        '''"""Provider-route preview for Session 13 Plus V5.\n\nThe resolver is deterministic policy preview unless supplied an explicitly\npromoted registry. It does not claim live reachability or price optimality.\n"""\n\nfrom __future__ import annotations\n\nfrom typing import TYPE_CHECKING\n\nfrom app.schemas.v3_routing import ComplexityLevel, ReasoningEffort\nfrom app.schemas.v5_provider_selection import ProviderOption, ProviderSelection\n\nif TYPE_CHECKING:\n    from app.services.v3_model_registry import ModelRegistry\n\n_VALID_STAGES = {"complexity", "structure", "recovery", "reliability", "proposal"}\n\n_DEFAULTS: dict[ProviderOption, tuple[str, list[dict[str, str]]]] = {\n    "auto": ("deepseek", [{"model": "deepseek-v4-flash", "tier": "flash"}, {"model": "deepseek-v4-pro", "tier": "pro"}]),\n    "deepseek": ("deepseek", [{"model": "deepseek-v4-flash", "tier": "flash"}, {"model": "deepseek-v4-pro", "tier": "pro"}]),\n    "kimi": ("moonshot", [{"model": "kimi-for-coding", "tier": "pro"}, {"model": "kimi-for-coding-highspeed", "tier": "pro"}, {"model": "k3", "tier": "max"}]),\n    "openai": ("openai", [{"model": "gpt-5.6-luna", "tier": "flash"}, {"model": "gpt-5.6-terra", "tier": "pro"}, {"model": "gpt-5.6-sol", "tier": "max"}]),\n}\n\n_TIER_FOR_COMPLEXITY = {"C0": "flash", "C1": "flash", "C2": "flash", "C3": "pro", "C4": "pro", "C5": "max"}\n\n\ndef _select(candidates: list[dict[str, str]], preferred_tier: str) -> dict[str, str] | None:\n    for tier in (preferred_tier, "pro", "flash", "max"):\n        for candidate in candidates:\n            if candidate.get("tier") == tier:\n                return dict(candidate)\n    return None\n\n\ndef _effort(provider: str, model: str, intent: str) -> ReasoningEffort:\n    if provider == "moonshot":\n        if model == "k3":\n            return {"minimal": "low", "medium": "high", "max": "max"}[intent]\n        return "high"\n    return {"minimal": "none", "medium": "high", "max": "max"}[intent]\n\n\ndef resolve_provider_route(\n    *,\n    selection: ProviderSelection,\n    complexity_level: ComplexityLevel,\n    stage: str,\n    registry: ModelRegistry | None = None,\n) -> dict[str, str]:\n    """Resolve an eligible route or fail closed when a registry has no promotion."""\n    if stage not in _VALID_STAGES:\n        raise ValueError(f"Unknown stage: {stage!r}. Valid stages: {', '.join(sorted(_VALID_STAGES))}")\n\n    preferred_tier = _TIER_FOR_COMPLEXITY[complexity_level]\n    if registry is not None:\n        records = registry.list_enabled() if selection.provider == "auto" else registry.list_by_provider(_provider_name(selection.provider))\n        candidates = [\n            {"provider": record.provider, "model": record.provider_model_id, "tier": record.capability_tier}\n            for record in records\n            if record.calibration_status == "enabled" and record.availability == "available"\n        ]\n        chosen = _select(candidates, preferred_tier)\n        if chosen is None:\n            raise ValueError(\n                f"No eligible promoted route for provider={selection.provider}, "\n                f"complexity={complexity_level}, stage={stage}"\n            )\n    else:\n        provider, raw = _DEFAULTS[selection.provider]\n        chosen = _select(\n            [{"provider": provider, "model": item["model"], "tier": item["tier"]} for item in raw],\n            preferred_tier,\n        )\n        if chosen is None:\n            raise ValueError(f"No policy preview route for provider={selection.provider}")\n\n    chosen["effort"] = _effort(chosen["provider"], chosen["model"], selection.reasoning)\n    chosen["routing_status"] = "promoted" if registry is not None else "preview"\n    chosen["stage"] = stage\n    return chosen\n\n\ndef _provider_name(option: ProviderOption) -> str:\n    return {"deepseek": "deepseek", "kimi": "moonshot", "openai": "openai", "auto": "deepseek"}[option]\n''',
    )


def add_tests() -> None:
    _write(
        "estimador-cag/tests/test_session13_plus_stabilization.py",
        '''"""Stabilization regression tests for the final Session 13 Plus gate."""\n\nfrom __future__ import annotations\n\nimport inspect\nfrom types import SimpleNamespace\nfrom uuid import UUID, uuid4\n\nimport pytest\nfrom langgraph.types import Command\n\nfrom app.generation.graph.nodes.proposal import build_proposal_node\nfrom app.generation.graph.nodes.semantic_classify import build_semantic_classify_node\nfrom app.schemas.v3_routing import ComplexitySignals\nfrom app.services.reviewed_graph_estimation import ReviewedGraphEstimationService\nfrom app.services.v3_complexity_router import assess_complexity, build_model_routing_plan\n\n\nclass _Runner:\n    def __init__(self) -> None:\n        self.input_state = None\n        self.config = None\n\n    async def ainvoke(self, input, config=None):\n        self.input_state = input\n        self.config = config\n        return {}\n\n    async def aget_state(self, config):\n        return SimpleNamespace(values=self.input_state, next=(), interrupts=())\n\n\n@pytest.mark.asyncio\nasync def test_service_start_accepts_and_checkpoints_provider_selection() -> None:\n    runner = _Runner()\n    service = ReviewedGraphEstimationService(graph=runner)\n    estimation_id = uuid4()\n    run = await service.start(\n        transcript="Build a secure reviewed estimator with enough detail for validation.",\n        human_review_mode="risk_based",\n        estimation_id=estimation_id,\n        provider="kimi",\n        reasoning="max",\n        context_detail="minimal",\n    )\n    assert run.estimation_id == str(estimation_id)\n    assert run.state["provider_selection"] == {\n        "provider": "kimi",\n        "reasoning": "max",\n        "context_detail": "minimal",\n    }\n\n\ndef test_live_key_sentinel_test_is_not_a_real_credential(monkeypatch) -> None:\n    from tests import test_session13_plus_provider_calibration as calibration\n\n    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")\n    assert calibration._has_deepseek_key() is False\n\n\ndef test_authoritative_level_controls_routes_without_fabricating_assessment() -> None:\n    deterministic = assess_complexity(ComplexitySignals(requirement_count=1))\n    assert deterministic.level == "C1"\n    plan = build_model_routing_plan(deterministic, authoritative_level="C4")\n    assert plan.project_complexity.level == "C1"\n    assert "complexity:C4" in plan.routes_by_stage["structure"].reason_codes\n    assert plan.routes_by_stage["structure"].model == "deepseek-v4-pro"\n\n\n@pytest.mark.asyncio\nasync def test_classifier_handover_is_command_only() -> None:\n    node = build_semantic_classify_node()\n    result = await node(\n        {\n            "transcript": "Build a simple API with authentication and database integration.",\n            "errors": [],\n            "trace_events": [],\n        }\n    )\n    assert isinstance(result, Command)\n    assert result.goto == "structure_phase"\n\n    from app.generation.graph import reviewed_build\n\n    source = inspect.getsource(reviewed_build.build_reviewed_estimation_graph)\n    assert 'add_edge("semantic_classify", "structure_phase")' not in source\n\n\ndef test_sse_activity_projection_excludes_sensitive_state() -> None:\n    from app.routers.reviewed_graph_estimations import _safe_activity_delta\n\n    projected = _safe_activity_delta(\n        "semantic_classify",\n        {\n            "transcript": "secret customer transcript",\n            "errors": [{"message": "internal stack"}],\n            "status": "pending",\n            "review_required": True,\n            "trace_events": [\n                {\n                    "event_type": "semantic_classification_completed",\n                    "node": "semantic_classify",\n                    "summary": "contains private rationale",\n                    "evidence_refs": ["private-id"],\n                    "state_delta_keys": ["status"],\n                }\n            ],\n        },\n    )\n    assert projected["status"] == "pending"\n    assert projected["review_required"] is True\n    assert "transcript" not in projected\n    assert "errors" not in projected\n    event = projected["trace_events"][0]\n    assert "summary" not in event\n    assert "evidence_refs" not in event\n\n\ndef test_stream_identity_uses_one_uuid() -> None:\n    from app.routers.reviewed_graph_estimations import _stream_identity\n\n    estimation_id = uuid4()\n    resolved, thread_id = _stream_identity(estimation_id)\n    assert resolved == estimation_id\n    assert str(estimation_id) in thread_id\n    assert UUID(str(resolved)) == estimation_id\n\n\n@pytest.mark.asyncio\nasync def test_proposal_preserves_human_review_blocker() -> None:\n    node = build_proposal_node()\n    update = await node(\n        {\n            "estimate": {"total_hours": 40.0, "total_cost_eur": 4000.0, "currency": "EUR", "components": []},\n            "reliability_report": {"overall_score": 0.3, "requires_human_review": True},\n            "critic_report": {"verdict": "needs_iteration"},\n            "boss_decision": {"action": "human_review"},\n            "arbitrated_assessment": {"arbitrated_level": "C4", "human_review_required": True},\n        }\n    )\n    proposal = update["proposal"]\n    assert proposal["human_review_required"] is True\n    assert "Estimate is ready for acceptance. No blockers." not in proposal["recommendations"]\n''',
    )


def update_docs() -> None:
    _replace_once(
        "estimador-cag/README.md",
        "gg-session-13/pre-work",
        "gg-session-13/plus-stabilization",
    )
    _append_once(
        "README.md",
        "Session 13 Plus stabilization boundary",
        '''## Session 13 Plus stabilization boundary\n\nThe direct stabilization branch repairs the reviewed-service API contract, separates deterministic and live-provider CI, hardens the SSE activity projection, removes contradictory routing evidence, and labels provider selection as a capability-gated preview until live per-stage routing is proven. PR #10 remains draft and unmerged.''',
    )
    _append_once(
        "estimador-cag/CLAUDE.md",
        "Direct stabilization correction gate",
        '''## 11. Direct stabilization correction gate\n\nThe stabilization branch supersedes stale 125-test and green-CI claims. Completion requires the exact final head to pass Ruff, compilation, deterministic tests excluding `live_provider`, diff/line-ending checks, and a secret scan. Live provider tests run only through the explicit manual workflow. The provider selector persists user intent and displays a policy preview; operational per-stage switching remains unclaimed.''',
    )
    _append_once(
        "estimador-cag/docs/session13_plus_v3_foundation.md",
        "Stabilization correction record",
        '''## 13. Stabilization correction record\n\nThe final repair pass separates deterministic complexity evidence from arbitrated routing authority, removes the redundant static classifier edge, fixes the reviewed-service provider-selection signature, adds a safe allow-listed SSE activity projection, and moves live-provider tests behind an explicit marker/workflow. Reliability and proposal nodes are implemented; provider selection remains a routing preview until runtime adapters consume the selection per stage. Current proof is the exact stabilization-branch CI result, not earlier test-count claims.''',
    )
    _append_once(
        "estimador-cag/docs/energy_aware_model_context_and_multiagent_policy.md",
        "Operational claim correction",
        '''## Operational claim correction\n\nProvider records seeded from documentation are not automatically enabled. `Auto` is a deterministic policy preview unless a registry snapshot contains explicitly promoted, available models. Current Kimi Code catalogue IDs are `k3`, `kimi-for-coding`, and `kimi-for-coding-highspeed`; K3 exposes low/high/max effort, while K2.7 Code requires thinking to remain enabled. Runtime superiority and least-cost claims require matched evidence.''',
    )


def main() -> None:
    repair_service_contract()
    repair_ci_boundary()
    repair_sse()
    repair_routing_authority()
    repair_provider_truthfulness()
    add_tests()
    update_docs()


if __name__ == "__main__":
    main()
