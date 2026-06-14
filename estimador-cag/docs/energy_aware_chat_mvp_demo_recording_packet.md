# Energy Aware Chat MVP demo recording packet

Status: 2 to 3 minute final-project demo guide.
Branch: `EACHAT`.

## Purpose

This packet gives a compact recording plan for demonstrating the upgraded MVP candidate.
It focuses on what the evaluator must see: AI service, RAG grounding baseline, agent orchestration, eval/validation evidence, deployment path, and honest claim boundaries.

## Demo duration target

```text
2 to 3 minutes
```

## Recording sequence

### 1. Repository and branch proof

Show:

```text
Branch: EACHAT
PR: #5
Optional delivery mirror: finalproject-GGC
```

Say:

```text
This is a production-oriented MVP candidate, not a production-ready service.
```

### 2. Local validation proof

Show command:

```bash
cd /workspaces/ai-engineering/estimador-cag
bash scripts/validate_energy_chat.sh
```

Show expected evidence:

```text
focused Energy Chat tests pass
full pytest suite passes
status clean
```

### 3. API service proof

Start API:

```bash
cd /workspaces/ai-engineering/estimador-cag
bash scripts/start_energy_chat.sh
```

Open FastAPI docs or hit the route list.

### 4. Deterministic evaluator and Energy Card

Use:

```text
POST /energy-chat/evaluate
```

Show:

1. decision,
2. energy,
3. hard constraints,
4. evidence refs,
5. remaining caveats.

### 5. RAG grounding baseline

Use:

```text
POST /energy-chat/rag/search
```

Show that the answer is grounded in committed project-source chunks.
Say explicitly:

```text
This is deterministic project-source RAG, not vector database RAG.
```

### 6. Agent orchestration

Use:

```text
POST /energy-chat/chat
```

Show:

1. retrieval step,
2. draft answer,
3. critic findings,
4. decider result,
5. repaired or accepted final answer,
6. Energy Card.

### 7. Provider and live smoke boundary

Show:

```text
Energy Aware Chat Live Provider Smoke
```

Say:

```text
DeepSeek and Kimi are wired through a fallback seam, but live fallback claims require this manual workflow to pass with repository secrets.
```

### 8. Deployment skeleton

Show:

```bash
docker compose -f docker-compose.energy-chat.yml up --build
```

Say:

```text
This proves the deployment path exists. A public URL or video is still the final delivery evidence.
```

## Exact final line for the demo

```text
The MVP candidate implements deterministic RAG grounding, local agent orchestration, Energy Card validation, a DeepSeek-to-Kimi fallback seam, and a deployment skeleton, with no quality-improvement or production-readiness claim until live and benchmark evidence exists.
```

## Hard non-claims for narration

Do not say:

1. production-ready,
2. already deployed publicly,
3. beats DeepSeek,
4. live fallback is proven before smoke passes,
5. vector database RAG exists for Energy Aware Chat.

## Minimal demo payloads

Use the committed payloads under:

```text
demo_payloads/energy_chat/
```

Recommended order:

1. `evaluate_accept.json`
2. `evaluate_repair_once.json`
3. `rag_search_project_rules.json`
4. `chat_project_release_readiness.json`
5. `benchmark_measurement.json`
