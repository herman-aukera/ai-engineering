# Energy Aware Chat API smoke guide

Status: manual smoke path for reviewer demos and pre-recording checks.

This guide uses committed payloads under:

```text
demo_payloads/energy_chat/
```

Run from:

```bash
cd /workspaces/ai-engineering/estimador-cag
```

## 1. Start the API

```bash
bash scripts/start_energy_chat.sh
```

Health check:

```bash
curl -sS http://127.0.0.1:8000/health
```

## 2. Accept case

```bash
curl -sS \
  -X POST http://127.0.0.1:8000/energy-chat/evaluate \
  -H 'Content-Type: application/json' \
  --data-binary @demo_payloads/energy_chat/evaluate_accept.json \
  | python -m json.tool
```

Expected minimum proof:

```text
decision.decision = accept
energy_card.decision = accept
energy_card.hard_constraints_passed = true
```

## 3. One pass repair case

```bash
curl -sS \
  -X POST http://127.0.0.1:8000/energy-chat/evaluate/repair-once \
  -H 'Content-Type: application/json' \
  --data-binary @demo_payloads/energy_chat/evaluate_repair_once.json \
  | python -m json.tool
```

Expected minimum proof:

```text
initial_result.decision.decision = repair
repair_attempted = true
final_result.decision.decision = accept
```

## 4. Source-needed case

```bash
curl -sS \
  -X POST http://127.0.0.1:8000/energy-chat/source-needed \
  -H 'Content-Type: application/json' \
  --data-binary @demo_payloads/energy_chat/source_needed_project.json \
  | python -m json.tool
```

Expected minimum proof:

```text
decision = sources_required
requires_project_sources = true
missing_evidence = true
```

## 5. Evidence bundle case

```bash
curl -sS \
  -X POST http://127.0.0.1:8000/energy-chat/evidence/bundle \
  -H 'Content-Type: application/json' \
  --data-binary @demo_payloads/energy_chat/evidence_bundle_project.json \
  | python -m json.tool
```

Expected minimum proof:

```text
trusted_refs includes file:docs/energy_aware_chat_demo.md
trusted_refs includes git:status-clean
trusted_refs includes test:pytest-passed
can_support_project_claim = true
```

## 6. RAG grounding baseline case

```bash
curl -sS \
  -X POST http://127.0.0.1:8000/energy-chat/rag/search \
  -H 'Content-Type: application/json' \
  --data-binary @demo_payloads/energy_chat/rag_project_search.json \
  | python -m json.tool
```

Expected minimum proof:

```text
retrieval_strategy = deterministic_lexical_cosine_project_rag
evidence_refs includes source:final_project_requirements
```

## 7. End-to-end local chat MVP case

```bash
curl -sS \
  -X POST http://127.0.0.1:8000/energy-chat/chat \
  -H 'Content-Type: application/json' \
  --data-binary @demo_payloads/energy_chat/chat_project_mvp.json \
  | python -m json.tool
```

Expected minimum proof:

```text
rag.evidence_refs is non-empty
final_answer is non-empty
energy_card.decision = accept
metadata.mvp_layer = rag_plus_agent_orchestration
```

## 8. Benchmark payload caveat

The benchmark fixture is committed for contract and demo shape checks:

```text
demo_payloads/energy_chat/benchmark_measurement.json
```

Do not use it to claim quality improvement. It belongs to the measurement-only path and must retain this claim boundary:

```text
measurement_only_no_quality_claim
```

## 9. Required closing proof

After any demo changes, run:

```bash
bash scripts/validate_energy_chat.sh
```

Then prove the exact commit in GitHub Actions:

```bash
cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh
```
