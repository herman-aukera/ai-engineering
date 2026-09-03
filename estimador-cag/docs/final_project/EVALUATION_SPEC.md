# EACHAT Final Project Evaluation Specification

Status: final-project SDD

## Objective

Measure the complete support behavior, not only pytest success: retrieval relevance, evidence propagation, support disposition, clarification/escalation behavior, provider calls, latency and cost. Semantic groundedness is not assigned a fake numeric score without a defined judge.

## Golden set

The committed 11-case set covers Spring Boot health/configuration, PostgreSQL connections/locks, Docker logs/networking, a cross-domain incident, version/source conflict, insufficient evidence, L3 source-code escalation and unsupported Kubernetes escalation.

## Evaluation layers

### Deterministic CI

Keyless CI verifies source manifest contracts, chunking/embedding seams, no-silent-fallback behavior, evidence reaching the graph, disposition regressions, monitoring aggregation and Compose syntax. It never requires a paid provider.

### Real persisted retrieval

`evals/energy_chat/final_project_eval.py` evaluates the fixed cases against the real persisted pgvector corpus. It reports `retrieval_hit_at_k` and keeps its claim boundary to retrieval.

### Full-system live evaluation

`evals/energy_chat/final_project_system_eval.py --live` runs the golden set through the actual EACHAT runtime with the real support RAG and a selected live provider. Its sanitized report measures directly observable fields:

- disposition accuracy
- clarification accuracy
- escalation accuracy
- retrieval hit@5 from graph-retained source refs
- evidence-reference presence
- answer presence
- error rate
- mean and p95 wall latency
- provider-call count
- mean and total estimated cost

`unsupported_claim_rate` remains explicitly `not_measured_without_external_judge` until a fixed semantic judge/manual rubric is executed. Prompt and answer bodies are omitted from the machine-readable artifact.

## Mandatory regressions

- No logs/error + demand exact PostgreSQL root cause → `clarify` rather than fabricate.
- Explicit Spring Boot 2.7.18 behavior while corpus is current-only → `clarify` and require version-matched evidence.
- Request to patch Java source → `escalate` beyond L2 authority.
- Kubernetes diagnosis/mutation → `escalate` as unsupported scope.

## Monitoring

The production router records a bounded rolling window for chat requests. Protected endpoints:

```text
GET /energy-chat/v2/monitoring
GET /energy-chat/v2/monitoring/dashboard
```

Expose request/success/error counts, error rate, mean latency, p95 latency, mean provider cost, provider-call count and disposition counts. No conversation content is stored in this monitor.

## Live workflow

`.github/workflows/final-project-live-rag.yml` is manual-only and performs:

```text
real source acquisition
→ real embeddings
→ pgvector persistence/index
→ retrieval evaluation
→ bounded live answer smoke
→ full 11-case live system evaluation
→ secret scan
→ sanitized artifacts
```

Numeric live results are claims only after that workflow succeeds for the exact final SHA.
