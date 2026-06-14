# Energy Aware Code roadmap

Status: living roadmap for the incubator branch.

Central rule:

    Every proposed coding-agent step must lower verified constraint energy or be rejected, repaired, or escalated.

## Completed judge-layer milestones

1. Deterministic policy, candidate, evidence, violation, and decision contracts.
2. YAML policy loading.
3. JSON candidate state loading.
4. JSONL evidence loading with schema validation.
5. Deterministic critics for failed gates, missing evidence, scope creep, and unverified success claims.
6. Energy scoring and decider precedence.
7. Append-only decision ledger.
8. Text, JSON, and Markdown decision reports.
9. Evidence diagnostics and evidence summary CLI.
10. Dry-run evaluation mode.
11. Ledger summary CLI.
12. CI smoke for real CLI paths.
13. Package boundary check to keep `energy_core` independent from app, UI, provider, cache, and adapter layers.

## Near-term judge hardening

These slices stay inside the judge layer:

1. Policy validation error messages.
2. Spec coverage report: requirements, design, tasks, acceptance, policy, examples, and evidence completeness.
3. Decision comparison: compare two candidate decision outputs and show energy trend.
4. Evidence bundle export/import for reproducible reviews.
5. Human-readable repair plan formatting.
6. Policy version migration checks.

## Adapter design phase

After the judge layer is stable:

1. Define adapter input and output contracts.
2. Add adapter contract tests without integrating any real tool.
3. Model executor outputs as proposed candidate states and evidence records.
4. Keep executor approval impossible by design.

## Deferred executor integrations

Only after adapter contracts are proven:

1. Aider adapter as conservative git-oriented first executor candidate.
2. Cline adapter as preferred future IDE integration target.
3. OpenCode adapter only after license, maturity, and event capture are rechecked.
4. Shell adapter only with strict command allowlists, dry-run defaults, and human approval.

## Explicitly out of scope for the incubator judge branch

1. Autonomous shell execution.
2. Auto-commit or auto-push.
3. Model/provider calls.
4. FastAPI service wrapper.
5. Streamlit UI.
6. Energy Aware Chat bridge.
7. IDE plugin work.

## Current next best slice

Spec coverage report.

Reason: it strengthens the judge without adding hands. It lets the tool answer whether a spec package has enough artifacts before candidate evaluation starts.
