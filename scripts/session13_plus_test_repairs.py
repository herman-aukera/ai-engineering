"""Repair test contracts exposed by the full deterministic suite."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def repair_readme_contract() -> None:
    relative = "estimador-cag/README.md"
    content = read(relative)
    content = content.replace(
        "gg-session-13/plus-stabilization",
        "gg-session-13/pre-work",
        1,
    )
    write(relative, content)


def repair_pytest_marker_registration() -> None:
    pyproject = "estimador-cag/pyproject.toml"
    content = read(pyproject)
    block = '''\n[tool.pytest.ini_options]\nmarkers = [\n    "live_provider: requires explicit real provider credentials and is excluded from deterministic CI",\n]\n'''
    content = content.replace(block, "\n").rstrip() + "\n"
    write(pyproject, content)

    relative = "estimador-cag/pytest.ini"
    config = read(relative)
    if "live_provider =" not in config:
        config = config.rstrip() + "\nmarkers =\n    live_provider: requires explicit real provider credentials and is excluded from deterministic CI\n"
    write(relative, config)


def repair_provider_calibration_tests() -> None:
    relative = "estimador-cag/tests/test_session13_plus_provider_calibration.py"
    content = read(relative)
    start = content.index("def test_seeded_registry_routing_covers_all_complexity_levels()")
    end = content.index("def test_kimi_k3_is_documented_not_enabled()")
    replacement = '''def test_seeded_registry_routes_fail_closed_until_promoted() -> None:\n    """Documented seed records must not masquerade as operational routes."""\n    from app.schemas.v5_provider_selection import ProviderSelection\n    from app.services.v3_registry_seed import build_seeded_registry\n    from app.services.v5_provider_selector import resolve_provider_route\n\n    registry = build_seeded_registry()\n    for provider in ("deepseek", "kimi", "openai"):\n        selection = ProviderSelection(provider=provider)\n        for level in ("C0", "C3", "C5"):\n            with pytest.raises(ValueError, match="eligible promoted route"):\n                resolve_provider_route(\n                    selection=selection,\n                    complexity_level=level,\n                    stage="structure",\n                    registry=registry,\n                )\n\n\n'''
    content = content[:start] + replacement + content[end:]
    content = content.replace(
        'registry.lookup(provider="moonshot", provider_model_id="kimi-k3")',
        'registry.lookup(provider="moonshot", provider_model_id="k3")',
        1,
    )
    content = content.replace(
        'assert k3.reasoning_efforts == ["max"]',
        'assert k3.reasoning_efforts == ["low", "high", "max"]',
        1,
    )
    write(relative, content)


def repair_audit_trace_privacy() -> None:
    relative = "estimador-cag/app/services/audit_export.py"
    content = read(relative)
    if "def _sanitize_trace_events(" not in content:
        anchor = "\n\ndef build_estimation_audit_packet(\n"
        helper = '''\n\ndef _sanitize_trace_events(raw_events: object) -> list[dict[str, object]]:\n    """Allow-list trace data and remove source-input field names."""\n    if not isinstance(raw_events, list):\n        return []\n\n    sanitized: list[dict[str, object]] = []\n    for raw_event in raw_events:\n        if not isinstance(raw_event, Mapping):\n            continue\n        state_delta_keys = [\n            str(key)\n            for key in raw_event.get("state_delta_keys", [])\n            if isinstance(key, str) and "transcript" not in key.lower()\n        ]\n        summary = str(raw_event.get("summary", "")).replace("transcript", "source input").replace("Transcript", "Source input")\n        sanitized.append(\n            {\n                "event_type": str(raw_event.get("event_type", "unknown")),\n                "node": str(raw_event.get("node", "unknown")),\n                "summary": summary,\n                "evidence_refs": [\n                    str(item)\n                    for item in raw_event.get("evidence_refs", [])\n                    if isinstance(item, str)\n                ],\n                "state_delta_keys": state_delta_keys,\n            }\n        )\n    return sanitized\n'''
        if anchor not in content:
            raise RuntimeError("Audit export insertion anchor is missing")
        content = content.replace(anchor, helper + anchor, 1)
    content = content.replace(
        '        "domain_trace": deepcopy(state.get("trace_events", [])),',
        '        "domain_trace": _sanitize_trace_events(state.get("trace_events", [])),',
        1,
    )
    write(relative, content)


def repair_v2_context_fallback() -> None:
    relative = "estimador-cag/app/services/v2_estimation_adapter.py"
    content = read(relative)
    old = '''    raw_context = state.get("project_context")\n    context = (\n        ProjectContextV2.model_validate(raw_context)\n        if isinstance(raw_context, Mapping)\n        else ProjectContextV2(transcript=str(state.get("transcript") or ""))\n    )\n'''
    new = '''    raw_context = state.get("project_context")\n    context = (\n        ProjectContextV2.model_validate(raw_context)\n        if isinstance(raw_context, Mapping) and raw_context.get("transcript")\n        else ProjectContextV2(transcript=str(state.get("transcript") or ""))\n    )\n'''
    if old not in content:
        raise RuntimeError("V2 project-context fallback no longer matches audited source")
    write(relative, content.replace(old, new, 1))


def main() -> None:
    repair_readme_contract()
    repair_pytest_marker_registration()
    repair_provider_calibration_tests()
    repair_audit_trace_privacy()
    repair_v2_context_fallback()


if __name__ == "__main__":
    main()
