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

Browser evidence verified that the control room rendered against the demo
backend and displayed `http://localhost:8001`. A separate real PostgreSQL smoke
used three checkpointer lifetimes and restored both gates plus trace continuity.
Live-provider and hosted telemetry evidence remain separate credentialed gates.
