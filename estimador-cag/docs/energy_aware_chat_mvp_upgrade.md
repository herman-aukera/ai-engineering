# Energy Aware Chat MVP upgrade

Status: production-oriented MVP candidate, not production-ready.

## What changed after the first certified evaluator demo

This branch now includes the minimum layers that were missing from a real final-project MVP candidate:

1. deterministic project RAG baseline,
2. local agent orchestration path,
3. DeepSeek primary plus Kimi backup fallback seam,
4. manual live-provider smoke workflow,
5. Docker and compose deployment path,
6. explicit claim boundaries.

## Implemented MVP flow

```text
user question
→ project-source retrieval
→ grounded deterministic draft
→ deterministic critic pipeline
→ one repair pass when needed
→ decider
→ final answer plus Energy Card
```

API route:

```text
POST /energy-chat/chat
```

RAG route:

```text
POST /energy-chat/rag/search
```

## Provider fallback

The baseline provider path now uses the existing LiteLLM fallback ladder:

```text
flash → pro → backup → backup_pro
```

Meaning:

1. DeepSeek flash is the normal first tier.
2. DeepSeek pro is the stronger DeepSeek tier.
3. Kimi backup is available when the DeepSeek path fails.
4. Kimi backup_pro is the last configured backup tier.

Manual live smoke:

```bash
uv run python scripts/smoke_energy_chat_live_provider.py
```

GitHub Actions workflow:

```text
Energy Aware Chat Live Provider Smoke
```

This workflow is manual because it requires real `DEEPSEEK_API_KEY` and `KIMI_API_KEY` secrets.

## Deployment path

Local API:

```bash
bash scripts/start_energy_chat.sh
```

Docker:

```bash
docker build -f Dockerfile.energy-chat -t energy-aware-chat .
docker run --rm -p 8000:8000 energy-aware-chat
```

Compose:

```bash
docker compose -f docker-compose.energy-chat.yml up --build
```

Health check:

```bash
curl http://localhost:8000/health
```

## Claim boundary

Allowed:

```text
production-oriented MVP candidate
```

Allowed after local and CI proof:

```text
deterministic RAG baseline works
deterministic agent orchestration works
DeepSeek-to-Kimi fallback seam is implemented and tested
Docker deployment path is documented
```

Not allowed yet:

```text
production-ready
public deployment is live
quality improvement over DeepSeek is proven
provider fallback has live proof unless the manual live smoke workflow passes
vector database RAG is implemented for Energy Aware Chat
```

Benchmark wording remains:

```text
measurement_only_no_quality_claim
```

## Next hardening slices

1. Run manual live-provider smoke with real GitHub secrets.
2. Build and smoke the Docker image.
3. Add persistent vector RAG using the course pgvector pattern.
4. Add a fixed eval set for project-source questions.
5. Deploy to a public environment or record a 2 to 3 minute demo video.
