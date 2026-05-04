#!/bin/bash
# =============================================================================
# LIDR TASK 2 - SCRIPT DEFINITIVO (RAMA sesion-02-estimador-cag)
# Incluye: todo el ejercicio + extras + mejoras
# NO incluye: Task 3 (streamlit, provider wrapper, cache) — eso va en otra rama
# =============================================================================
set -e

echo "=========================================="
echo "TASK 2: CAG + FastAPI + Schemas + CI/CD"
echo "=========================================="

# Verificar que estamos en el fork oficial
if [ ! -d ".git" ]; then
    echo "❌ ERROR: No estás en un repo git. Ve a /workspaces/ai-engineering"
    exit 1
fi

# Verificar rama
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "sesion-02-estimador-cag" ]; then
    echo "❌ ERROR: No estás en la rama sesion-02-estimador-cag. Ejecuta: git checkout -b sesion-02-estimador-cag"
    exit 1
fi

echo ">>> Rama confirmada: $CURRENT_BRANCH"

# =============================================================================
# ESTRUCTURA
# =============================================================================
mkdir -p estimador-cag/app/schemas
mkdir -p estimador-cag/app/routers
mkdir -p estimador-cag/app/services
mkdir -p estimador-cag/app/context
mkdir -p estimador-cag/tests
mkdir -p estimador-cag/scripts
mkdir -p .github/workflows
mkdir -p .devcontainer
mkdir -p docs

echo ">>> Estructura creada"

# =============================================================================
# 1. app/__init__.py
# =============================================================================
cat << 'PYEOF' > estimador-cag/app/__init__.py
"""
LAYER: app (package root)
RESPONSIBILITY: Marks the Python package boundary for the FastAPI application
WHY IT EXISTS: Python requires __init__.py to treat a directory as a package,
               enabling absolute imports like `from app.config import Settings`
DEPENDS ON: Nothing (root package)
"""
# Package root for estimador-cag application
PYEOF

# =============================================================================
# 2. app/main.py
# =============================================================================
cat << 'PYEOF' > estimador-cag/app/main.py
"""
LAYER: main (application entry point)
RESPONSIBILITY: Bootstrap the FastAPI application, register routers, and expose health checks
WHY IT EXISTS: Centralizes app composition so routers and middleware are wired in one place,
               following the "composition root" pattern. Avoids circular imports.
DEPENDS ON: app.routers.estimations (HTTP routes)
"""

from fastapi import FastAPI
from app.routers.estimations import router as estimations_router

app = FastAPI(
    title="LIDR Estimador CAG",
    description="Context-Augmented Generation (CAG) estimator for software engineering tasks",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(estimations_router)


@app.get("/health", tags=["health"])
def health_check():
    """Health endpoint for Codespaces port forwarding verification."""
    return {"status": "ok", "version": "0.2.0"}
PYEOF

# =============================================================================
# 3. app/config.py
# =============================================================================
cat << 'PYEOF' > estimador-cag/app/config.py
"""
LAYER: config (settings & wiring)
RESPONSIBILITY: Load environment variables, validate them via Pydantic, and define tier routing
WHY IT EXISTS: Prevents secret leakage into source code and centralizes environment-dependent
               configuration. Fails fast on startup if configuration is invalid.
DEPENDS ON: pydantic_settings (BaseSettings), openai (OpenAI client factory)
"""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from openai import OpenAI

TierName = Literal["flash", "pro", "backup", "backup_pro"]


class Settings(BaseSettings):
    """Pydantic Settings validates env vars at import time. Fails fast on missing secrets."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_tier: TierName = "flash"

    deepseek_api_key: str = "dummy"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_model_pro: str = "deepseek-v4-pro"
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    kimi_api_key: str = "dummy"
    kimi_model: str = "kimi-k2.5"
    kimi_model_pro: str = "kimi-k2.6"
    kimi_base_url: str = "https://api.moonshot.ai/v1"

    database_url: str = "postgresql://dev:dev@localhost:5432/lidr"

    @model_validator(mode="after")
    def validate_api_keys(self):
        """Fail-fast automatico: si ambas keys son dummy, la app no arranca."""
        if self.deepseek_api_key == "dummy" and self.kimi_api_key == "dummy":
            raise ValueError(
                "Al menos una API key debe configurarse: DEEPSEEK_API_KEY o KIMI_API_KEY"
            )
        return self

    @property
    def tier_ladder(self) -> list[TierName]:
        """Ordered list of tiers for escalation logic."""
        return ["flash", "pro", "backup", "backup_pro"]


settings = Settings()


def get_model_config(tier: TierName | None = None) -> tuple[OpenAI, str]:
    """Factory: returns an (OpenAI-compatible client, model_name) tuple."""
    tier = tier or settings.llm_tier

    if tier == "flash":
        return OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url), settings.deepseek_model
    elif tier == "pro":
        return OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url), settings.deepseek_model_pro
    elif tier == "backup":
        return OpenAI(api_key=settings.kimi_api_key, base_url=settings.kimi_base_url), settings.kimi_model
    elif tier == "backup_pro":
        return OpenAI(api_key=settings.kimi_api_key, base_url=settings.kimi_base_url), settings.kimi_model_pro
    else:
        raise ValueError(f"Tier desconocido: {tier}")
PYEOF

# =============================================================================
# 4-6. schemas/
# =============================================================================
cat << 'PYEOF' > estimador-cag/app/schemas/__init__.py
"""LAYER: schemas (package root). Enables clean absolute imports."""
# Schemas package
PYEOF

cat << 'MDEOF' > estimador-cag/app/schemas/README.md
# Data Contracts Layer: `schemas/`

**Responsibility:** Pydantic models for request/response validation.

**WHY it exists:** Schemas act as the contract between HTTP layer (routers) and
business layer (services). Guarantees:
1. Incoming JSON matches expected shape (fail fast on bad input)
2. Outgoing JSON is serializable and typed
3. OpenAPI documentation generates automatically

**Rules:**
- No business logic
- No database models (those live in `models/` in future modules)
- Use Pydantic v2 syntax
MDEOF

cat << 'PYEOF' > estimador-cag/app/schemas/estimation.py
"""
LAYER: schemas (data contracts)
RESPONSIBILITY: Define Pydantic models for estimation requests and responses
WHY IT EXISTS: Validates HTTP payloads at the edge and auto-generates OpenAPI docs.
               Separado del router por decision arquitectonica (flag Heladia).
DEPENDS ON: pydantic (BaseModel, Field)
"""

from pydantic import BaseModel, Field


class EstimateRequest(BaseModel):
    """Inbound payload for POST /api/v1/estimate."""
    transcription: str = Field(..., min_length=10, description="Texto de la transcripcion de reunion")
    tier: str = Field(default="flash", description="Tier de LLM: flash, pro, backup, backup_pro")


class EstimateResponse(BaseModel):
    """
    Outbound payload with generated estimation and model metadata.
    MEJORA: Incluye provider (deepseek/kimi) y timestamp ISO.
            Esto alinea con el schema del ejercicio de LIDR que muestra 'provider'.
    """
    estimation: str = Field(..., description="Estimacion generada en markdown")
    model: str = Field(..., description="Modelo especifico que respondio")
    tier: str = Field(..., description="Tier logico utilizado")
    provider: str = Field(..., description="Proveedor de LLM: deepseek o kimi")
    input_tokens: int = Field(..., description="Tokens de entrada")
    output_tokens: int = Field(..., description="Tokens de salida")
    timestamp: str = Field(..., description="Timestamp ISO 8601 UTC de la respuesta")
PYEOF

# =============================================================================
# 7-9. services/
# =============================================================================
cat << 'PYEOF' > estimador-cag/app/services/__init__.py
"""LAYER: services (package root). Enables clean imports."""
# Services package
PYEOF

cat << 'MDEOF' > estimador-cag/app/services/README.md
# Business Logic Layer: `services/`

**Responsibility:** Prompts, LLM calls, processing.

**WHY it exists:** Separating prompt engineering from HTTP transport means:
1. Unit-test logic without spinning up a web server
2. Swap LLM providers without touching router code
3. Reuse logic in CLI tools, Streamlit apps, or background workers

**Rules:**
- Only import from `app.config` and `app.context`
- Return plain dicts, not HTTP responses
- Handle tier routing and fallback logic here
MDEOF

cat << 'PYEOF' > estimador-cag/app/services/llm_service.py
"""
LAYER: services (business logic)
RESPONSIBILITY: Build system prompts, execute LLM calls with tier routing, and parse responses
WHY IT EXISTS: Separates prompt engineering and LLM communication from HTTP transport.
DEPENDS ON: app.config (Settings, tier routing), app.context.examples (CAG data)
"""

import logging
from datetime import datetime, timezone
from app.config import settings, get_model_config, TierName
from app.context.examples import ESTIMATION_EXAMPLES

logger = logging.getLogger(__name__)


def _get_provider(tier: str) -> str:
    """Deriva el nombre del proveedor a partir del tier."""
    if tier in ("flash", "pro"):
        return "deepseek"
    elif tier in ("backup", "backup_pro"):
        return "kimi"
    return "unknown"


def build_system_prompt() -> str:
    """Constructs the CAG system prompt with few-shot examples."""
    examples_text = "\n\n---\n\n".join(
        f"TRANSCRIPCION:\n{ex['meeting_summary']}\n\nESTIMACION GENERADA:\n{ex['estimation']}"
        for ex in ESTIMATION_EXAMPLES
    )
    return f"""Eres un estimador de software senior con 15 anos de experiencia.
Generas estimaciones detalladas basandote en transcripciones de reuniones.

Reglas:
- Desglosa en tareas concretas (horas por tarea)
- Incluye total de horas, equipo recomendado y duracion estimada
- Se realista, no optimista
- Usa markdown para la estimacion

Ejemplos de referencia:

{examples_text}"""


def estimate(transcription: str, tier: TierName | None = None) -> dict:
    """
    Synchronous LLM call with automatic tier fallback.
    MEJORA: Incluye provider y timestamp en la respuesta.
    """
    system_prompt = build_system_prompt()
    effective_tier = tier or settings.llm_tier
    ladder = settings.tier_ladder
    start_idx = ladder.index(effective_tier)
    tiers_to_try = ladder[start_idx:]

    for attempt_tier in tiers_to_try:
        try:
            client, model = get_model_config(attempt_tier)
            logger.info(f"Llamando tier={attempt_tier}, model={model}")

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"TRANSCRIPCION DE REUNION:\n{transcription}"},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            usage = response.usage

            logger.info(f"Respuesta OK: tier={attempt_tier}, tokens={usage.prompt_tokens}/{usage.completion_tokens}")

            return {
                "estimation": content,
                "model": model,
                "tier": attempt_tier,
                "provider": _get_provider(attempt_tier),
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.warning(f"Tier {attempt_tier} fallo: {e}. Escalando...")
            continue

    raise RuntimeError("Todos los tiers de LLM fallaron. Verifica API keys y quotas.")
PYEOF

# =============================================================================
# 10-12. routers/
# =============================================================================
cat << 'PYEOF' > estimador-cag/app/routers/__init__.py
"""LAYER: routers (package root). Enables clean imports."""
# Routers package
PYEOF

cat << 'MDEOF' > estimador-cag/app/routers/README.md
# Transport Layer: `routers/`

**Responsibility:** HTTP in, HTTP out. Thin.

**WHY it exists:** Routers must contain zero business logic. They validate incoming
requests via Pydantic schemas, delegate to `services/`, and format outgoing responses.
This separation allows swapping FastAPI for another framework without touching business logic.

**Rules:**
- Only import from `app.schemas` and `app.services`
- No direct LLM client calls
- No database queries
MDEOF

cat << 'PYEOF' > estimador-cag/app/routers/estimations.py
"""
LAYER: routers (HTTP transport)
RESPONSIBILITY: Define endpoints for estimation requests and wire them to the service layer
WHY IT EXISTS: Isolates HTTP-specific concerns from prompt engineering and LLM logic.
               Schemas movidos a app/schemas/ por decision arquitectonica (Heladia).
DEPENDS ON: app.schemas.estimation, app.services.llm_service
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.estimation import EstimateRequest, EstimateResponse
from app.services.llm_service import estimate

router = APIRouter(prefix="/api/v1", tags=["estimations"])


@router.post("/estimate", response_model=EstimateResponse, status_code=status.HTTP_200_OK)
def create_estimation(request: EstimateRequest):
    """
    POST /api/v1/estimate
    MEJORA: respeta request.tier (tu version original lo ignoraba).
    MEJORA V2: captura RuntimeError cuando todos los tiers fallan -> HTTP 503.
    """
    try:
        result = estimate(request.transcription, tier=request.tier)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error en llamada a LLM: {str(e)}")
PYEOF

# =============================================================================
# 13-15. context/
# =============================================================================
cat << 'PYEOF' > estimador-cag/app/context/__init__.py
"""LAYER: context (package root). Enables clean imports."""
# Context package
PYEOF

cat << 'MDEOF' > estimador-cag/app/context/README.md
# CAG Context Layer: `context/`

**Responsibility:** Static few-shot examples for Context-Augmented Generation.

**WHY it exists:** Session 2 uses static context (few-shot examples baked into the prompt).
Future modules (3-4) will replace this with dynamic RAG retrieval.

**Rules:**
- Store only static, version-controlled data
- No database queries
- No LLM calls
MDEOF

cat << 'PYEOF' > estimador-cag/app/context/examples.py
"""
LAYER: context (static CAG data)
RESPONSIBILITY: Provide few-shot examples baked into the system prompt
WHY IT EXISTS: Demonstrates the CAG pattern before dynamic RAG is introduced.
DEPENDS ON: Nothing (pure data)
"""

ESTIMATION_EXAMPLES = [
    {
        "meeting_summary": "El cliente necesita una plataforma web de gestion de inventario con roles de usuario, dashboard de metricas y exportacion a Excel. 10 usuarios concurrentes.",
        "estimation": """## Estimacion: Plataforma de Gestion de Inventario

### Desglose de tareas:
1. Diseno UI/UX: 40 horas
2. Backend API (CRUD inventario): 60 horas
3. Autenticacion y roles: 20 horas
4. Dashboard con metricas: 30 horas
5. Testing y QA: 25 horas

**Total estimado: 175 horas**
**Equipo recomendado: 2 desarrolladores full-stack + 1 disenador UX (part-time)**
**Duracion estimada: 6-8 semanas**""",
    },
    {
        "meeting_summary": "Landing page con formulario de contacto, integracion HubSpot CRM, blog con editor WYSIWYG. Diseno en Figma. 4 semanas de plazo.",
        "estimation": """## Estimacion: Landing Page + Blog + CRM

### Desglose de tareas:
1. Maquetacion responsive (Figma -> HTML/CSS): 25 horas
2. Formulario de contacto + validaciones: 10 horas
3. Integracion HubSpot API: 15 horas
4. Blog con editor WYSIWYG: 30 horas
5. SEO basico + performance: 10 horas
6. Testing cross-browser: 10 horas

**Total estimado: 100 horas**
**Equipo recomendado: 1 desarrollador full-stack + 1 disenador (part-time)**
**Duracion estimada: 3-4 semanas**""",
    },
]
PYEOF

# =============================================================================
# 16-17. tests/
# =============================================================================
cat << 'PYEOF' > estimador-cag/tests/__init__.py
"""LAYER: tests (package root). Allows pytest discovery."""
# Tests package
PYEOF

cat << 'PYEOF' > estimador-cag/tests/test_health.py
"""
LAYER: tests
RESPONSIBILITY: Verify that the FastAPI application boots correctly
WHY IT EXISTS: Automated testing prevents regressions when refactoring.
DEPENDS ON: app.main (FastAPI app)
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test automatizado del endpoint /health. Corre con: uv run pytest tests/ -v"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
PYEOF

# =============================================================================
# 18. pyproject.toml
# =============================================================================
cat << 'TOMLEOF' > estimador-cag/pyproject.toml
[project]
name = "estimador-cag"
version = "0.2.0"
description = "LIDR Session 02: CAG Estimator with FastAPI"
requires-python = ">=3.11"
dependencies = [
    "fastapi[standard]>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic-settings>=2.6.0",
    "openai>=1.60.0",
    "anthropic>=0.40.0",
    "litellm>=1.55.0",
    "psycopg2-binary>=2.9.10",
    "pandas>=2.2.0",
    "sentence-transformers>=3.3.0",
    "python-dotenv>=1.0.0",
    "jupyter>=1.1.0",
    "ipykernel>=6.29.0",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.9.0",
    "pytest>=8.3.0",
    "httpx>=0.28.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
TOMLEOF

# =============================================================================
# 19-20. .env y .gitignore
# =============================================================================
cat << 'ENVEOF' > estimador-cag/.env.example
# Copy this to .env and fill in your keys
DEEPSEEK_API_KEY=sk-your-deepseek-key
KIMI_API_KEY=sk-your-kimi-key
DATABASE_URL=postgresql://dev:dev@localhost:5432/lidr
ENVEOF

cat << 'GITEOF' > estimador-cag/.gitignore
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.uv/
venv/
.env
.venv
.vscode/
.idea/
*.swp
*.swo
.pytest_cache/
.coverage
htmlcov/
.DS_Store
Thumbs.db
GITEOF

# =============================================================================
# 21. README.md
# =============================================================================
cat << 'MDEOF' > estimador-cag/README.md
# LIDR Session 02: Estimador CAG

**Architecture:** FastAPI + CAG (Context-Augmented Generation) + Tier Routing

## Layer Diagram

```
Frontend          | (Task 3: streamlit_app.py)
HTTP Transport    | routers/
Data Contracts    | schemas/
Business Logic    | services/
Static Context    | context/
Configuration     | config.py
```

## Tier Ladder

| Priority | Tier | Provider | Model | Use Case |
|---|---|---|---|---|
| 1 | flash | DeepSeek | V4-Flash | Default, cheapest |
| 2 | pro | DeepSeek | V4-Pro | Escalation |
| 3 | backup | Kimi | K2.5 | Fallback |
| 4 | backup_pro | Kimi | K2.6 | Heavy fallback |

## Quick Start

```bash
# Database (for future RAG modules)
docker compose up -d

# Backend
cd estimador-cag
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing

```bash
uv run pytest tests/ -v
uv run ruff check app/ tests/
```

## API Endpoints

- `GET /health` -> Health check
- `POST /api/v1/estimate` -> CAG estimation from transcription

## Session Roadmap

- **Session 2 (NOW):** Static CAG, FastAPI, Pydantic, schemas/
- **Session 3:** Streamlit wrapper, streaming, provider abstraction
- **Modules 3-4:** RAG with embeddings, retrieval, ingestion
- **Module 5:** Agents with orchestrator, tools, validators
MDEOF

# =============================================================================
# 22. docs/sample_transcription.md (EXTRA del ejercicio)
# =============================================================================
cat << 'MDEOF' > docs/sample_transcription.md
# Transcripcion de Ejemplo para Testing

Este archivo contiene la transcripcion de reunion que usa el ejercicio de LIDR
como parametro de prueba para el endpoint `/api/v1/estimate`.

## Contenido

> En la reunion con el equipo de marketing, el cliente explico que necesita una
> landing page con formulario de contacto, integracion con su CRM actual (HubSpot),
> y una seccion de blog con editor WYSIWYG. El plazo ideal seria tenerlo listo
> en 4 semanas. El diseno ya existe en Figma.

## Uso

```bash
# Via curl
curl -X POST http://localhost:8000/api/v1/estimate \\
  -H "Content-Type: application/json" \\
  -d '{"transcription": "En la reunion con el equipo de marketing...", "tier": "flash"}'

# Via script incluido
bash scripts/test_api.sh
```
MDEOF

# =============================================================================
# 23. docs/sample_request.json
# =============================================================================
cat << 'JSONEOF' > docs/sample_request.json
{
  "transcription": "En la reunion con el equipo de marketing, el cliente explico que necesita una landing page con formulario de contacto, integracion con su CRM actual (HubSpot), y una seccion de blog con editor WYSIWYG. El plazo ideal seria tenerlo listo en 4 semanas. El diseno ya existe en Figma.",
  "tier": "flash"
}
JSONEOF

# =============================================================================
# 24. scripts/test_api.sh
# =============================================================================
cat << 'SHEOF' > estimador-cag/scripts/test_api.sh
#!/bin/bash
# Script de testing rapido contra la API local
# Uso: bash scripts/test_api.sh
set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo ">>> Testing GET /health"
curl -s "${BASE_URL}/health" | python -m json.tool || curl -s "${BASE_URL}/health"

echo ""
echo ">>> Testing POST /api/v1/estimate"
curl -s -X POST "${BASE_URL}/api/v1/estimate" \\
  -H "Content-Type: application/json" \\
  -d @../docs/sample_request.json | python -m json.tool || curl -s -X POST "${BASE_URL}/api/v1/estimate" -H "Content-Type: application/json" -d @../docs/sample_request.json

echo ""
echo ">>> Done."
SHEOF
chmod +x estimador-cag/scripts/test_api.sh

# =============================================================================
# 25. scripts/verify.sh
# =============================================================================
cat << 'SHEOF' > estimador-cag/scripts/verify.sh
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
SHEOF
chmod +x estimador-cag/scripts/verify.sh

# =============================================================================
# 26. .devcontainer/devcontainer.json
# =============================================================================
cat << 'JSONEOF' > .devcontainer/devcontainer.json
{
  "name": "LIDR - Kimi/DeepSeek",
  "image": "mcr.microsoft.com/devcontainers/python:3.11-bookworm",
  "waitFor": "postCreateCommand",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": { "moby": false },
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "customizations": {
    "codespaces": {
      "openFiles": ["estimador-cag/README.md"]
    },
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "ms-toolsai.jupyter",
        "GitHub.copilot",
        "GitHub.copilot-chat",
        "GitHub.vscode-github-actions",
        "Google.gemini-code-assist",
        "JohnnyZ93.oai-compatible-copilot"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "github.copilot.enable": {
          "*": true,
          "plaintext": true,
          "markdown": true
        }
      }
    }
  },
  "postCreateCommand": "curl -LsSf https://astral.sh/uv/install.sh | sh && echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.bashrc && export PATH=\"$HOME/.local/bin:$PATH\" && cd estimador-cag && uv sync && uv run ipython kernel install --user --name=lidr && echo '>>> Entorno listo'",
  "postStartCommand": "docker --version && docker compose version && uv --version && cd estimador-cag && uv run fastapi --version && echo '>>> Todo listo'",
  "forwardPorts": [8000, 5432, 8888],
  "portsAttributes": {
    "8000": { "label": "FastAPI", "onAutoForward": "notify" },
    "5432": { "label": "PostgreSQL", "onAutoForward": "silent" },
    "8888": { "label": "Jupyter", "onAutoForward": "notify" }
  },
  "remoteUser": "root"
}
JSONEOF

# =============================================================================
# 27. .github/workflows/ci.yml
# =============================================================================
cat << 'YAMLEOF' > .github/workflows/ci.yml
name: CI - Estimador CAG

on:
  push:
    branches: [main, sesion-02-estimador-cag]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Check folder structure
        run: |
          test -d estimador-cag/app/routers || exit 1
          test -d estimador-cag/app/services || exit 1
          test -d estimador-cag/app/context || exit 1
          test -d estimador-cag/app/schemas || exit 1
          test -d estimador-cag/tests || exit 1
          test -f estimador-cag/app/config.py || exit 1
          test -f estimador-cag/app/main.py || exit 1
          test -f estimador-cag/.env.example || exit 1
          test -f estimador-cag/pyproject.toml || exit 1
          echo "✅ Folder structure OK"

      - name: Check .env not committed
        run: |
          if git ls-files | grep -q "^estimador-cag/\.env$"; then
            echo "❌ .env should not be committed!"
            exit 1
          fi
          echo "✅ .env not in repo"

      - name: Install dependencies
        working-directory: ./estimador-cag
        run: uv sync

      - name: Lint with ruff
        working-directory: ./estimador-cag
        run: uv run ruff check app/ tests/

      - name: Check Python syntax
        working-directory: ./estimador-cag
        run: |
          uv run python -m py_compile app/main.py
          uv run python -m py_compile app/config.py
          uv run python -m py_compile app/services/llm_service.py
          uv run python -m py_compile app/routers/estimations.py
          uv run python -m py_compile app/schemas/estimation.py
          echo "✅ Python syntax OK"

      - name: Run pytest
        working-directory: ./estimador-cag
        run: uv run pytest tests/ -v

      - name: Test health endpoint
        working-directory: ./estimador-cag
        run: |
          echo "LLM_TIER=flash" > .env
          echo "DEEPSEEK_API_KEY=dummy" >> .env
          echo "KIMI_API_KEY=dummy" >> .env
          uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 5
          curl -f http://localhost:8000/health || exit 1
          echo "✅ Health endpoint responds 200"
          pkill -f uvicorn || true
YAMLEOF

# =============================================================================
# 28. docker-compose.yml
# =============================================================================
cat << 'YAMLEOF' > docker-compose.yml
services:
  db:
    image: ankane/pgvector:latest
    restart: unless-stopped
    environment:
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: lidr
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev -d lidr"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres-data:
YAMLEOF

echo ""
echo "=========================================="
echo "✅ TASK 2 CREADO"
echo "=========================================="
echo ""
echo "28 archivos creados en estimador-cag/"
echo ""
echo "VERIFICAR AHORA:"
echo "  cd estimador-cag && bash scripts/verify.sh"
echo ""
echo "LUEGO COMMITEAR:"
echo "  git add ."
echo "  git commit -m 'feat: sesion 02 - CAG estimator completo'"
echo "  git push -u fork sesion-02-estimador-cag"
echo ""
echo "DESPUES CREAR RAMA TASK 3:"
echo "  git checkout -b sesion-03-streamlit"
echo ""
