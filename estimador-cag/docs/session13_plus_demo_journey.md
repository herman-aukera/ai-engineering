# Deterministic control-room journey

`scripts/session13_plus_demo_api.py` is a keyless local composition for product
demonstration. It uses the production reviewed FastAPI router, application
service, LangGraph topology, parallel retrieval path and both human interrupts.
Only the adapters and checkpointer are deterministic demo implementations.

The contract test starts a run, approves structure, approves the final estimate,
lists checkpoint history and exports the audit packet. It proves transport and
orchestration wiring without claiming provider or PostgreSQL behavior.

```bash
uv run pytest -q tests/test_session13_plus_demo_api.py
uv run uvicorn scripts.session13_plus_demo_api:app --port 8001
ESTIMADOR_BACKEND_URL=http://localhost:8001 \
  uv run streamlit run app/ui/review_control_room.py
```

## Browser proof

On 2026-07-16 the complete journey was exercised in Brave against the local
demo API at `http://localhost:8001` and the Streamlit control room at
`http://localhost:8502`.

- estimation id: `2047d38f-df6a-40a5-932a-c5018e9882e0`;
- the structure interrupt rendered the proposed requirements and component;
- `approve` resumed the same thread into the final-estimate interrupt;
- the final gate rendered the grounded 40-hour estimate, provenance, structured
  Critic result and deterministic Boss decision;
- actor `brave-smoke` approved the final gate;
- execution reached `completed` with zero pending nodes and `40.0` total hours;
- the UI rendered parallel retrieval events and final-review audit events;
- checkpoint history loaded as a table; and
- the audit export action completed from the control room.

This is browser/product wiring evidence, not PostgreSQL durability evidence:
the demo composition intentionally uses `InMemorySaver`. A separate real
PostgreSQL smoke used three checkpointer lifetimes and restored both gates plus
trace continuity. A separate credentialed workflow completed bounded DeepSeek
and Kimi turns and requested a Logfire remote flush; see
`docs/session13_plus_live_runtime_evidence.md`. The browser journey itself
remains deterministic and is not presented as browser-to-provider evidence.
