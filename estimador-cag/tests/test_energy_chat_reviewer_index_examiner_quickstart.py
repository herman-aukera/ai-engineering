from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEWER_INDEX = (ROOT / "docs/energy_aware_chat_reviewer_index.md").read_text(
    encoding="utf-8"
)


def test_reviewer_index_starts_with_examiner_quickstart() -> None:
    assert "1. `docs/energy_aware_chat_examiner_quickstart.md`" in REVIEWER_INDEX
    assert "| Examiner quickstart |" in REVIEWER_INDEX
