from pathlib import Path

EXAMPLE = Path("docs/examples/energy_chat_release_snapshot_example.md").read_text(
    encoding="utf-8"
)


def test_release_snapshot_example_has_green_gate_table() -> None:
    assert "# Energy Aware Chat release snapshot" in EXAMPLE
    assert "| local gate | green |" in EXAMPLE
    assert "| ci gate | green |" in EXAMPLE


def test_release_snapshot_example_preserves_claim_boundary() -> None:
    assert "measurement_only_no_quality_claim" in EXAMPLE
    assert "production release checklist" in EXAMPLE
