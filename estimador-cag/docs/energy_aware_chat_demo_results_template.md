# Energy Aware Chat demo results template

Status: reusable reviewer-facing template for recording one demo run.

Branch under review: `gg-finalproject-energy-aware-chat`

Product target after Session 17: `herman-aukera/energy-aware-chat`

## 1. Validation proof

Fill this section immediately before recording or presenting the demo.

```text
Local command:
  bash scripts/validate_energy_chat.sh

Focused Energy Chat tests:
  <paste count>

Full suite:
  <paste count>

Working tree:
  clean
```

```text
CI command:
  bash estimador-cag/scripts/check_energy_chat_ci.sh

Workflow:
  Energy Aware Chat CI

Branch:
  gg-finalproject-energy-aware-chat

Commit:
  <paste short sha>

Conclusion:
  success
```

## 2. Endpoint proof table

| Step | Endpoint or UI path | Payload | Expected result | Observed result |
|---|---|---|---|---|
| Accept | `POST /energy-chat/evaluate` | `demo_payloads/energy_chat/evaluate_accept.json` | `decision=accept` | `<paste>` |
| Repair once | `POST /energy-chat/evaluate/repair-once` | `demo_payloads/energy_chat/evaluate_repair_once.json` | initial `repair`, final `accept` | `<paste>` |
| Source need | `POST /energy-chat/source-needed` | `demo_payloads/energy_chat/source_needed_project.json` | `sources_required` | `<paste>` |
| Evidence bundle | `POST /energy-chat/evidence/bundle` | `demo_payloads/energy_chat/evidence_bundle_project.json` | trusted file, git, and test refs | `<paste>` |
| Benchmark request shape | contract validation | `demo_payloads/energy_chat/benchmark_measurement.json` | measurement-only request is valid | `<paste>` |

## 3. Streamlit proof

Use the Energy Aware Chat Streamlit app.

```bash
cd /workspaces/ai-engineering/estimador-cag
streamlit run energy_chat_streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

Record these UI states:

1. Evaluation tab renders `accept` with energy `0` for the accept payload.
2. Evaluation tab renders a repair path for the repair payload.
3. Evidence bundle tab renders trusted project refs.
4. Benchmark tab is clearly labelled measurement-only.
5. No UI text claims production readiness or model quality improvement.

## 4. Claim boundary statement

Use this sentence in the demo narrative:

Energy Aware Chat currently demonstrates a deterministic, constraint-governed evaluator and measurement-only benchmark harness. It does not yet claim production readiness, RAG grounding, autonomous agent orchestration, deployment readiness, or DeepSeek quality improvement.

Benchmark token that must remain present in code and docs:

```text
measurement_only_no_quality_claim
```

## 5. Open backlog after demo

Record remaining work here instead of hiding it.

| Area | Current status | Next controlled step |
|---|---|---|
| RAG grounding | Not implemented | Add repository/doc retrieval after source-needed classifier is stable |
| Live provider benchmark | Provider seam exists | Run fixed cases with live key and save measurements separately |
| Agent layer | Not implemented | Add bounded planner only after deterministic gates stay green |
| Deployment | Not implemented | Prepare demo deployment or recording after Session 17 decisions |
| Standalone repo | Planned | Export after coursework branch stabilizes |
