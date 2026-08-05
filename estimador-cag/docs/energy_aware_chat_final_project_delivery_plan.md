# Energy Aware Chat final project delivery plan

Status: final-project staging plan for `EACHAT` and future `finalproject-GGC` mirror.

This document defines the delivery path for Energy Aware Chat while it stays inside `herman-aukera/ai-engineering` until the course reaches the standalone extraction point.

## Product thesis

Energy Aware Chat is a constraint-governed assistant answer evaluator.

The product does not trust a model answer just because a provider returned it. Every answer candidate is evaluated against hard constraints, soft constraints, evidence requirements, source needs, safety boundaries, and task-specific quality rules before it is accepted, repaired, rejected, or escalated.

## Current implemented layers

1. Deterministic Energy Chat contracts.
2. Deterministic critics, scorer, and decider.
3. FastAPI evaluation endpoint.
4. Browser-visible same-origin demo.
5. Streamlit Energy Card demo.
6. One-pass deterministic repair seam.
7. DeepSeek baseline draft seam.
8. DeepSeek-to-Kimi fallback seam.
9. Deterministic project-source RAG grounding baseline.
10. Deterministic local agent orchestration.
11. Fixed deterministic benchmark dataset.
12. Measurement-only benchmark harness.
13. Benchmark Markdown report writer.
14. Source-needed classifier.
15. Evidence bundle builder.
16. Repository readiness and standalone extraction plan.
17. Local deployment skeleton and smoke documentation.
18. Local validation and exact-commit CI proof helpers.
19. Closeout pack for end-of-day reviewer handoff.

## Final project target scope

The final course delivery should include:

1. A working FastAPI service.
2. A Streamlit or browser-visible demo.
3. Typed request and response contracts.
4. Deterministic evaluation logic.
5. At least one model-provider seam.
6. A deterministic project-source RAG baseline.
7. A deterministic agent orchestration path.
8. A benchmark or evaluation harness.
9. Documentation explaining claim boundaries.
10. CI and local validation proof.
11. A future standalone repository extraction plan.

## Demo story

The demo should show this story in less than three minutes:

1. A user opens the evaluator landing page.
2. A user submits a draft answer.
3. The Energy Card evaluates the draft.
4. The system explains whether it accepts, repairs, rejects, or needs evidence.
5. A repairable answer is improved through one deterministic repair pass.
6. A project-source RAG answer shows committed source evidence.
7. A deterministic agent orchestration route shows retrieve, draft, critic, repair, and decider steps.
8. A benchmark panel shows measurement-only comparison data.
9. The demo clearly states that no DeepSeek quality improvement claim is made yet.

## Delivery checkpoint table

| Area | Current state | Delivery status |
| --- | --- | --- |
| FastAPI | `/energy-chat/*` endpoints exist | ready for demo |
| Browser demo | same-origin `/energy-chat/demo` path exists | ready for demo |
| Streamlit | evaluation, evidence, benchmark tabs | ready for demo |
| Provider seam | DeepSeek primary and Kimi fallback seam | ready for controlled smoke |
| Repair | deterministic one-pass repair | ready for demo |
| Evidence | deterministic evidence bundle | ready for project mode |
| Benchmark | measurement-only harness and reports | ready for fake and later live runs |
| RAG | deterministic project-source RAG grounding baseline | ready for demo |
| Agents | deterministic local agent orchestration | ready for demo |
| Deployment | local Docker and compose skeleton | local proof only |
| CI | local gate and exact-commit CI proof helper | ready for branch proof |

## Non-negotiable claim boundaries

Do not claim:

1. Production readiness.
2. Public deployment is live.
3. DeepSeek quality improvement.
4. Frontier-model superiority.
5. Deployment readiness beyond local smoke evidence.
6. Vector database RAG grounding.

Allowed claim:

    Energy Aware Chat has a deterministic evaluator, repair seam, evidence gate, deterministic RAG grounding baseline, deterministic agent orchestration, provider fallback seam, measurement-only benchmark harness, local validation gate, and exact-commit CI proof on the staging branch.

Benchmark claim token:

    measurement_only_no_quality_claim

This token is part of the benchmark contract. It means the benchmark records measurements only and must not be interpreted as a DeepSeek quality-improvement claim.

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

The staging branch should stay in the coursework repo until the extraction boundary is stable.
