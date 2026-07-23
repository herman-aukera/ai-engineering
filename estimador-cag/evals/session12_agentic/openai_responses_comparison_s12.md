# Session 12 OpenAI Responses Live Comparison

Scope: exact OpenAI Responses API manual-loop run for `sample_transcript_complex`.

Evidence level: manual live OpenAI Responses API execution plus deterministic local tool execution.

## Result

| Metric | Previous deterministic retrieval trace | OpenAI Responses live trace | Delta |
|---|---:|---:|---:|
| Components | 4 | 8 | 4 |
| search_budgets calls | 2 | 8 | 6 |
| calculate_estimate calls | 1 | 1 | 0 |
| validate_estimate calls | 1 | 1 | 0 |
| Total hours | 182.4 | 223.2 | 40.8 / 22.37% |
| Total cost EUR | 13680.0 | 21204.0 | 7524.0 / 55.0% |

## Previous components

- JWT authentication
- Audit logging
- Admin dashboard
- CSV import

## OpenAI Responses components

- JWT authentication and RBAC (admins, analysts)
- Audit logging for sensitive actions and exports
- Admin dashboard for reviewing uploads and failed validations
- CSV import for monthly reconciliation (parsing, validation, error reporting)
- Basic deployment documentation and handoff notes
- Project setup and app scaffolding (monolith, UI shell, routing)
- QA and automated tests (auth, RBAC, CSV, dashboard)
- Project management and client handoff

## Interpretation

The OpenAI Responses run is coherent and closer to the assignment's intended agent behavior than the deterministic baseline because it performs one search_budgets call per identified component.

The hours increase is plausible: the live run expands the estimate from four feature components to eight components, adding delivery-support work such as setup, QA, deployment documentation, and project handoff.

The cost increase is larger than the hours increase because the live run appears to use a higher effective hourly rate than the deterministic baseline.

This evidence proves that the exact OpenAI Responses API manual loop works and produces a coherent trace. It does not prove model-quality superiority or calibrated estimation accuracy.
