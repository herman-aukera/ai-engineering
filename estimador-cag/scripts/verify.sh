#!/bin/bash
# Script de verificacion rapida despues de setup
set -e

echo ">>> Verificando entorno LIDR Task 2..."
cd "$(dirname "$0")/.."

# 1. Dependencias
uv sync

# 2. Lint
uv run ruff check app/ tests/

# 3. Tests
uv run pytest tests/ -v

# 4. Syntax
uv run python -m py_compile app/main.py
uv run python -m py_compile app/config.py
uv run python -m py_compile app/services/llm_service.py
uv run python -m py_compile app/routers/estimations.py
uv run python -m py_compile app/schemas/estimation.py

# 5. Import check
uv run python -c "from app.main import app; print('✅ FastAPI import OK')"
uv run python -c "from app.services.llm_service import estimate; print('✅ LLM service import OK')"

echo ""
echo ">>> ✅ TASK 2 VERIFICADO. Listo para push."
