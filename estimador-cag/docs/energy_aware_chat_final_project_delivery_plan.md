# Energy Aware Chat final project delivery plan

Status: final-project staging plan for `gg-finalproject-energy-aware-chat`.

This document defines the delivery path for Energy Aware Chat while it stays inside `herman-aukera/ai-engineering` until the course reaches Session 17.

## Product thesis

Energy Aware Chat is a constraint-governed assistant answer evaluator.

The product does not trust a model answer just because a provider returned it. Every answer candidate is evaluated against hard constraints, soft constraints, evidence requirements, source needs, safety boundaries, and task-specific quality rules before it is accepted, repaired, rejected, or escalated.

## Current implemented layers

1. Deterministic Energy Chat contracts.
2. Deterministic critics, scorer, and decider.
3. FastAPI evaluation endpoint.
4. Streamlit Energy Card demo.
5. One-pass deterministic repair seam.
6. DeepSeek baseline draft seam.
7. Measurement-only benchmark harness.
8. Benchmark Markdown report writer.
9. Source-needed classifier.
10. Evidence bundle builder.
11. Repository readiness and standalone extraction plan.
12. Local validation and exact-commit CI proof helpers.

## Final project target scope

The final course delivery should include:

1. A working FastAPI service.
2. A Streamlit or browser-visible demo.
3. Typed request and response contracts.
4. Deterministic evaluation logic.
5. At least one model-provider seam.
6. A benchmark or evaluation harness.
7. Documentation explaining claim boundaries.
8. CI and local validation proof.
9. A future standalone repository extraction plan.

## Demo story

The demo should show this story in less than three minutes:

1. A user submits a draft answer.
2. The Energy Card evaluates the draft.
3. The system explains whether it accepts, repairs, rejects, or needs evidence.
4. A repairable answer is improved through one deterministic repair pass.
5. A benchmark panel shows measurement-only comparison data.
6. The demo clearly states that no RAG or quality-improvement claim is made yet.

## Delivery checkpoint table

| Area | Current state | Delivery status |
| --- | --- | --- |
| FastAPI | `/energy-chat/*` endpoints exist | ready for demo |
| Streamlit | evaluation, evidence, benchmark tabs | ready for demo |
| Provider seam | DeepSeek baseline draft seam | ready for controlled smoke |
| Repair | deterministic one-pass repair | ready for demo |
| Evidence | deterministic evidence bundle | ready for project mode preparation |
| Benchmark | measurement-only harness and reports | ready for fake and later live runs |
| RAG | not implemented | future layer |
| Agents | not implemented | future layer |
| Deployment | not implemented | future layer |
| CI | local gate and exact-commit CI proof helper | ready for branch proof |

## Non-negotiable claim boundaries

Do not claim:

1. Production readiness.
2. RAG grounding.
3. Agent orchestration.
4. DeepSeek quality improvement.
5. Frontier-model superiority.
6. Deployment readiness.

Allowed claim:

    Energy Aware Chat has a deterministic evaluator, repair seam, evidence gate, provider baseline seam, measurement-only benchmark harness, local validation gate, and exact-commit CI proof on the staging branch.

## Acceptance proof for each checkpoint

Every checkpoint must be accepted with:

1. `bash scripts/validate_energy_chat.sh`
2. `bash scripts/check_energy_chat_ci.sh`
3. A clean working tree.
4. No real secrets in committed files.
5. No claim beyond the implemented layer.

## Future standalone repository

The future standalone repository should be:

    herman-aukera/energy-aware-chat

The staging branch should stay in the coursework repo until Session 17, then be exported when the boundary is stable.
