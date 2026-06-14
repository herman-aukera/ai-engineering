# Energy Aware Chat standalone export README draft

Target future repository:

    herman-aukera/energy-aware-chat

Current staging branch:

    herman-aukera/ai-engineering:gg-finalproject-energy-aware-chat

## Product thesis

Energy Aware Chat is a constraint-governed assistant answer evaluator. Every answer candidate is inspected through deterministic critics, an energy score, and an explicit decision path before acceptance.

It is not yet a production chatbot and must not claim model quality improvement without benchmark evidence.

## Current exported boundary

The future standalone repository should start from these paths:

    estimador-cag/app/energy_chat/
    estimador-cag/energy_chat_streamlit_app.py
    estimador-cag/demo_payloads/energy_chat/
    estimador-cag/docs/energy_aware_chat_*.md
    estimador-cag/scripts/validate_energy_chat.sh
    estimador-cag/scripts/check_energy_chat_ci.sh
    estimador-cag/scripts/export_energy_chat_manifest.sh
    estimador-cag/tests/test_energy_chat_*.py
    .github/workflows/energy-chat-ci.yml

## Required first standalone repository files

The standalone repository should include:

- `README.md`
- `LICENSE`
- `pyproject.toml`
- `.python-version`
- `.github/workflows/ci.yml`
- `app/energy_chat/`
- `tests/`
- `docs/`
- `demo_payloads/energy_chat/`
- `scripts/`

## Migration notes

The first extraction should preserve behavior, not redesign architecture.

Minimum acceptable extraction proof:

1. The deterministic evaluator imports successfully.
2. FastAPI routes expose the Energy Chat endpoints.
3. Streamlit demo loads the Energy Card.
4. Demo payload fixtures are copied.
5. Focused Energy Chat tests pass.
6. CI succeeds on the standalone repository default branch.

## Deferred until after extraction

- RAG implementation.
- Agent orchestration.
- Real provider benchmark claims.
- Hosted deployment.
- Multi-user persistence.

## Claim boundary

The benchmark contract must keep the token:

    measurement_only_no_quality_claim

until real benchmark data supports a stronger claim.
