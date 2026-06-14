# Energy Aware Chat final project proof packet

Status: reviewer entry packet for the Energy Aware Chat final project branch.

## Open first

1. `docs/energy_aware_chat_reviewer_index.md`
2. `docs/energy_aware_chat_live_demo_readiness.md`
3. `docs/energy_aware_chat_release_snapshot.md`
4. `docs/examples/energy_chat_release_snapshot_example.md`

## Run first

```text
bash scripts/validate_energy_chat.sh
bash scripts/check_energy_chat_ci.sh
```

## Demo first

1. Start FastAPI.
2. Start `energy_chat_streamlit_app.py`.
3. Use `demo_payloads/energy_chat/` for repeatable request examples.
4. Record the Energy Card, decision, energy score, and claim boundaries.

## Claim boundary

This packet proves the local reviewer path and deterministic demo surface. It does not claim production readiness, RAG grounding, deployment readiness, or live model quality improvement.
