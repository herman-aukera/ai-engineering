# Estimation Control Room V2 product journey

Run the deterministic V2 composition with:

```bash
uv run uvicorn scripts.session13_plus_demo_api:app --port 8001
ESTIMADOR_BACKEND_URL=http://localhost:8001 \
  uv run streamlit run app/ui/control_room_v2.py --server.port 8503
```

The unified application presents an eight-stage product journey:

```text
Context -> Reformulation -> Structure -> Evidence -> Estimation
        -> Critic & Boss -> Human approval -> Audit
```

The structure gate uses a dynamic visual table. Reviewers can add, remove and
edit modules and tasks without editing JSON. Multi-task structure is persisted
inside the same checkpoint thread. After retrieval, Python allocates the
authoritative component total across its tasks using their reviewed expected
hours as weights (equal weights when none are supplied); the allocated task
hours always sum to the graph-owned component total.

The same application also exposes evidence, deterministic arithmetic, Critic,
Boss, final approval, reconnect, checkpoint history, scenarios and sanitized
audit export. Browser proof remains required before promotion.
