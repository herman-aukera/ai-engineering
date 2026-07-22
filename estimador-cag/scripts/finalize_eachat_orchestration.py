"""One-time fail-closed migration for orchestration UI and maturity claims."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one marker in {path}, found {count}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_maturity() -> None:
    path = ROOT / "app" / "energy_chat" / "context_compaction.py"
    replace_once(
        path,
        '    multi_agent_orchestration: RuntimeMaturity = "contract_only"\n',
        '    multi_agent_orchestration: RuntimeMaturity = "implemented"\n',
    )
    replace_once(
        path,
        '        default_factory=lambda: ["critic"]\n',
        '        default_factory=lambda: ["critic", "committee", "adaptive"]\n',
    )
    replace_once(
        path,
        '            "Committee and adaptive orchestration remain deferred until runtime integration.",\n',
        '            "Committee and adaptive are deterministic-only; live multi-provider calibration remains deferred.",\n',
    )


def update_ui() -> None:
    path = ROOT / "docs" / "energy_chat_v2_demo.html"
    replace_once(
        path,
        ".selectors{display:grid;grid-template-columns:repeat(5,minmax(105px,1fr));",
        ".selectors{display:grid;grid-template-columns:repeat(6,minmax(100px,1fr));",
    )
    replace_once(
        path,
        '<span class="badge ok">Durable bounded memory</span><span class="badge ok">Context compaction active</span><span class="badge">Critic orchestration</span>\n        <span class="badge warn">Committee/adaptive: gated</span>',
        '<span class="badge ok">Durable bounded memory</span><span class="badge ok">Context compaction active</span><span class="badge ok">Bounded orchestration active</span>\n        <span class="badge warn">Live committee/adaptive: gated</span>',
    )
    replace_once(
        path,
        '        <div><label for="contextProfile">Context detail</label><select id="contextProfile"><option value="minimal">Minimal</option><option value="balanced" selected>Balanced</option><option value="max">Max</option></select></div>\n',
        '        <div><label for="contextProfile">Context detail</label><select id="contextProfile"><option value="minimal">Minimal</option><option value="balanced" selected>Balanced</option><option value="max">Max</option></select></div>\n        <div><label for="orchestrationMode">Orchestration</label><select id="orchestrationMode"><option value="critic" selected>Critic</option><option value="committee">Committee</option><option value="adaptive">Adaptive</option></select></div>\n',
    )
    replace_once(
        path,
        "context_profile:document.getElementById('contextProfile').value,orchestration_mode:'critic',execution_profile:",
        "context_profile:document.getElementById('contextProfile').value,orchestration_mode:document.getElementById('orchestrationMode').value,execution_profile:",
    )
    replace_once(
        path,
        "['Context snapshot',extra.context_snapshot_id],['Memory messages'",
        "['Context snapshot',extra.context_snapshot_id],['Requested orchestration',data.requested_orchestration_mode],['Resolved orchestration',data.resolved_orchestration_mode],['Orchestration candidates',String(data.orchestration_candidate_count||1)],['Orchestration reason',data.orchestration_reason],['Memory messages'",
    )


def update_tests() -> None:
    compaction = ROOT / "tests" / "test_energy_chat_context_compaction.py"
    replace_once(
        compaction,
        '    assert status.multi_agent_orchestration == "contract_only"\n',
        '    assert status.multi_agent_orchestration == "implemented"\n',
    )
    replace_once(
        compaction,
        '    assert status.active_orchestration_modes == ["critic"]\n',
        '    assert status.active_orchestration_modes == ["critic", "committee", "adaptive"]\n',
    )
    replace_once(
        compaction,
        '    assert any("Committee and adaptive" in item for item in status.limitations)\n',
        '    assert any("live multi-provider calibration" in item for item in status.limitations)\n',
    )

    runtime = ROOT / "tests" / "test_energy_chat_context_runtime.py"
    replace_once(
        runtime,
        '    assert status.multi_agent_orchestration == "contract_only"\n',
        '    assert status.multi_agent_orchestration == "implemented"\n',
    )
    replace_once(
        runtime,
        '    assert status.active_orchestration_modes == ["critic"]\n',
        '    assert status.active_orchestration_modes == ["critic", "committee", "adaptive"]\n',
    )

    product = ROOT / "tests" / "test_energy_chat_v2_product_ui.py"
    replace_once(
        product,
        '    assert "Critic orchestration" in html\n    assert "Committee/adaptive: gated" in html\n',
        '    assert "Bounded orchestration active" in html\n    assert "Live committee/adaptive: gated" in html\n',
    )
    replace_once(
        product,
        '    assert "revised_answer:revisedAnswer" in html\n',
        '    assert "revised_answer:revisedAnswer" in html\n    assert \'id="orchestrationMode"\' in html\n    assert \'<option value="committee">Committee</option>\' in html\n    assert \'<option value="adaptive">Adaptive</option>\' in html\n    assert "orchestration_mode:document.getElementById(\'orchestrationMode\').value" in html\n',
    )

    browser = ROOT / "scripts" / "smoke_eachat_v2_browser.mjs"
    replace_once(
        browser,
        '  await page.selectOption("#contextProfile", "minimal");\n',
        '  await page.selectOption("#contextProfile", "minimal");\n  await page.selectOption("#orchestrationMode", "adaptive");\n',
    )
    replace_once(
        browser,
        '  assert(status?.includes("Context profileminimal"), "Minimal context snapshot was not applied");\n',
        '  assert(status?.includes("Context profileminimal"), "Minimal context snapshot was not applied");\n  assert(status?.includes("Requested orchestrationadaptive"), "Adaptive orchestration was not requested");\n  assert(status?.includes("Resolved orchestrationcritic"), "Low-risk adaptive turn did not stay on critic");\n',
    )


def main() -> None:
    update_maturity()
    update_ui()
    update_tests()
    print("EACHAT_ORCHESTRATION_FINALIZATION_OK")


if __name__ == "__main__":
    main()
