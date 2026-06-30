# Session 11 Extra Branch Notes

Status: optional extra branch, not canonical delivery

Base commit:

- `a19e49e session11: chore(format): apply final ruff cleanup`

Branch:

- `gg-session-11/extras-quality-lab`

## Purpose

This branch preserves optional extra work after the canonical Session 11 delivery branch was made green.

It is intended as a safe seed for Session 12 prework, not as the branch to submit for Session 11.

## Added extras

- Pure helper contracts for a Session 11 Quality Lab.
- Deterministic tests for RAGAS metric rows and provider status rows.
- Standalone Streamlit viewer: `streamlit_session11_quality_lab.py`.
- Provider comparison status table that distinguishes official OpenAI baseline from DeepSeek/Kimi comparison paths.

## What remains to validate

Run this in the next Codespace before trusting the branch:

    cd /workspaces/ai-engineering/estimador-cag
    uv run ruff check --fix evals tests streamlit_session11_quality_lab.py
    uv run ruff check evals tests streamlit_session11_quality_lab.py
    uv run python -m py_compile evals/session11_generation/quality_lab_helpers_s11.py streamlit_session11_quality_lab.py tests/test_session11_quality_lab_helpers.py
    uv run pytest -q tests/test_session11_quality_lab_helpers.py

Manual UI smoke:

    cd /workspaces/ai-engineering/estimador-cag
    uv run streamlit run streamlit_session11_quality_lab.py

Expected UI checks:

- The RAGAS metrics tab shows five query rows and one average row.
- The Providers tab shows OpenAI as completed official baseline.
- The Providers tab shows DeepSeek and Kimi as comparison paths blocked for live RAGAS by multi-completion request behavior.
- The Report tab renders `RAGAS_BASELINE_S11.md`.

## Caveat

This branch was created through GitHub file operations after the Codespace was ready to be deleted. It has not received local py_compile, pytest, Streamlit smoke, or remote CI evidence at creation time.
