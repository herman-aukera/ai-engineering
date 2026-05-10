# Session 03 Canonical Baseline

Branch:

gg-sesion-03-canonical-compliance

Baseline status:

- ruff passed
- pytest passed
- py_compile passed
- GET /health passed
- GET /metrics passed
- POST /api/v1/estimate passed
- POST /api/v1/estimate/stream passed
- FastAPI / opened in browser
- FastAPI /demo opened in browser
- Streamlit 8501 opened in browser after process start and port visibility check

Known canonical gaps:

- Redis exact cache missing
- structlog and richer metrics partial or missing
- LiteLLM provider abstraction missing
- Streamlit still calls local service directly
- Tests are minimal
- Teacher live version not yet fully compared
