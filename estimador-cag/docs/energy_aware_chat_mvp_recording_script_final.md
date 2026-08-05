# Energy Aware Chat Final MVP Recording Script

status: demo-script
recommended_length: 2 to 3 minutes
branch: EACHAT
claim_boundary: production-oriented MVP candidate, not production-ready

## Recording objective

Show that Energy Aware Chat is a complete local MVP candidate for the final project path:

1. FastAPI service.
2. Browser UI.
3. Streamlit UI.
4. Project-source RAG baseline.
5. Live provider draft path.
6. Critic and decider Energy Card.
7. Fixed deterministic benchmark evidence.
8. Honest limitations.

## Opening, 15 seconds

Say:

```text
This is Energy Aware Chat, a constraint-governed RAG assistant for AI project and release-readiness decisions. The branch is EACHAT. This is a production-oriented MVP candidate, not a production-ready public service.
```

Show:

1. Git branch and head.
2. Browser URL on port 8000.
3. Energy Aware Chat demo page.

## Product flow, 45 seconds

Say:

```text
The main flow is user question, project-source retrieval, provider draft, deterministic critics, energy scoring, decider, optional repair, and Energy Card.
```

Show:

1. Chat mode selector.
2. Execution mode selector.
3. Required constraint field.
4. Run Energy Aware Chat button.
5. Energy Card.
6. Visible execution audit.
7. RAG evidence and provider metadata.

Important note:

```text
The execution audit is visible evidence. It is not hidden chain-of-thought.
```

## Live provider proof, 30 seconds

Use a question like:

```text
Is deployment evidence mandatory for the Energy Aware Chat final project MVP?
```

Say:

```text
Live mode calls DeepSeek as the primary draft provider and keeps Kimi available as fallback. The critics and repair loop are deterministic in this MVP, so normal CI does not require real keys.
```

Show provider metadata when available:

1. provider
2. model
3. tier
4. fallback_used
5. input/output tokens
6. cost estimate if present

## Benchmark evidence, 30 seconds

Click fixed benchmark evidence.

Say:

```text
This benchmark is deterministic and provider-free. It measures the evaluator and repair seam over fixed cases. It is measurement-only evidence and does not claim live provider quality improvement.
```

Show:

1. cases_total
2. accepted_baseline
3. accepted_after_repair
4. claim_status: measurement_only_no_quality_claim
5. per-case table or raw evidence

## Streamlit UI, 30 seconds

Open port 8501.

Say:

```text
The Streamlit UI is the richer reviewer surface. It exposes the same mode selector, execution selector, Energy Card, execution audit, RAG evidence, provider metadata, and fixed benchmark evidence.
```

Show:

1. Backend URL.
2. Execution mode.
3. Chat mode.
4. Run Energy Aware Chat.
5. Fixed benchmark evidence.

## Validation proof, 30 seconds

Say:

```text
The deterministic gate and dedicated Energy Aware Chat CI are the acceptance proof. The last accepted checkpoint must show focused Energy Chat tests, full suite, root diff check, and exact workflow success for the branch and SHA.
```

Show terminal output or cite the proof packet:

```text
UV_HTTP_TIMEOUT=600 bash scripts/validate_energy_chat.sh
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

## Closing, 15 seconds

Say:

```text
The remaining gaps are public deployment, real-user production readiness, and live-provider quality-improvement benchmarking. Those are deliberately not claimed yet.
```

End on the readiness matrix or benchmark boundary.

## Must not say

1. This is production-ready.
2. This improves over plain DeepSeek.
3. This beats frontier models.
4. This is deployed publicly.
5. The model reasons in visible hidden chain-of-thought.

## Good final sentence

```text
Energy Aware Chat is now demo-ready as a local final-project MVP candidate, with explicit evidence, visible limitations, and repeatable validation gates.
```
