from pathlib import Path


def test_energy_chat_evaluator_landing_page_exists() -> None:
    path = Path("docs/energy_aware_chat_evaluator_landing_page.md")
    assert path.exists()
    assert "/energy-chat/demo" in path.read_text(encoding="utf-8")
