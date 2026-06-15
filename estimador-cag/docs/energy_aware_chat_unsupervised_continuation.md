# Energy Aware Chat continuation guard

Status: deterministic handoff guard for `EACHAT`.

## Purpose

This document keeps Energy Aware Chat continuation work aligned with the current branch scope.

It is used after a validated checkpoint when the next patch should remain limited to evidence, demo, reviewer, or handoff hardening.

## Canonical command

```bash
cd /workspaces/ai-engineering/estimador-cag
uv run python scripts/render_energy_chat_unsupervised_continuation.py --fail-on-incomplete
```

The renderer writes:

```text
/tmp/energy_aware_chat_unsupervised_continuation.md
```

## Required start state

Before a continuation patch, verify:

1. clean `git status --short`,
2. `bash scripts/validate_energy_chat.sh` passes from `estimador-cag`,
3. exact commit CI proof passes from repository root,
4. no live provider claim without the manual live-provider smoke workflow,
5. no production-readiness or quality-improvement claim.

## Safe scope

Preferred work:

1. reviewer navigation cleanup,
2. evidence and proof packet hardening,
3. demo readiness documentation,
4. deterministic validation scripts,
5. final-project handoff notes,
6. artifact registry consistency.

Avoid work that changes:

1. provider behavior,
2. benchmark semantics,
3. deployment assumptions,
4. runtime API contracts,
5. Streamlit or browser demo behavior,
6. Session 08 or Session 09 coursework code,
7. `EACODE` or bridge code.

## Claim boundary

Required token:

```text
measurement_only_no_quality_claim
```

Allowed claim:

```text
Energy Aware Chat is a browser-testable, production-oriented MVP candidate on the EACHAT incubator branch.
```

Forbidden claims:

```text
Energy Aware Chat is production ready.
Energy Aware Chat has proven quality improvement over plain DeepSeek.
Energy Aware Chat beats frontier models.
```

## Stop conditions

Stop and repair before continuing if:

1. Ruff fails,
2. focused Energy Chat tests fail,
3. full test suite fails,
4. demo payload validation fails,
5. `git diff --check origin/main...HEAD` fails,
6. exact commit CI proof is missing or red,
7. a required reviewer artifact disappears,
8. the next patch would mix Chat with Code or coursework branches.

## Non goals

This document does not run commands, call providers, mutate benchmark evidence, prove quality improvement, or authorize production-readiness claims.
