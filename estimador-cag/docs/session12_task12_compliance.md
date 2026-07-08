# Session 12 Task 12 Compliance Audit

## Purpose

This document maps the current Session 12 implementation against the mandatory Task 12 requirements.

It separates proven evidence from remaining gaps. It also explains why live-provider estimates differ so much.

## Mandatory requirement mapping

| Official requirement | Current implementation/evidence | Status |
| --- | --- | --- |
| Agent receives a meeting transcript | AgentRunRequest and Session 12 scripts accept transcript input. | Likely covered |
| Agent decomposes the problem into components | Provider/fake plans produce component lists before estimation. | Likely covered |
| Agent uses search_budgets | The loop supports search_budgets and records function_call/function_call_output trace items. | Covered by deterministic tests and trace artifacts |
| Agent uses calculate_estimate | calculate_estimate is deterministic and invoked from planned steps. | Covered |
| Agent manually drives reason, act, observe, repeat | Trace items represent reasoning, function_call, function_call_output, and final output. | Covered at local loop level |
| Each function_call_output references call_id | Tool output trace records call_id from the matching function call. | Covered |
| Max iteration safety exists | AgentRunRequest.max_iterations is enforced by the executor. | Covered |
| Agent returns structured estimate plus trace | AgentRunResult includes estimate, validation, trace, provider, model, and terminated. | Covered |
| sample_transcript_complex.txt identifies more than one component | The committed sample_transcript_complex trace has four components: JWT authentication, Audit logging, Admin dashboard, and CSV import. | Covered |
| sample_transcript_complex.txt makes more than one search_budgets call | The committed sample_transcript_complex trace has two search_budgets calls: call_search_auth and call_search_audit. | Covered |
| Trace shows reasoning, action, and observation | JSON trace artifacts contain reasoning, function_call, function_call_output, and final roles. | Likely covered |
| search_budgets wraps S9-S10 retrieval, not a separate retrieval reimplementation | Retrieval bridge is covered with injected service; deterministic fallback remains for CI safety. | Covered with caveat |
| Uses OpenAI Responses API with gpt-5 reasoning medium | Current implementation uses an OpenAI-compatible chat-completions planning adapter. Exact OpenAI Responses API loop remains not implemented. | Not covered |
| Optional validate_estimate tool | validate_estimate exists and is called in executed provider-plan smokes. | Extra covered |
| Delivery branch is session-12/pre-work | Current working branch is gg-session-12/pre-work. Mirror to session-12/pre-work after final gates if required. | Delivery gap |

## Current evidence files

| File | Meaning |
| --- | --- |
| evals/session12_agentic/agent_trace_fake_s12.json | Deterministic fake-provider trace artifact |
| evals/session12_agentic/agent_trace_fake_retrieval_s12.json | Deterministic retrieval-backed trace artifact |
| evals/session12_agentic/session12_live_provider_matrix_summary.md | Sanitized live-provider planning summary |
| evals/session12_agentic/session12_executed_provider_plan_summary.md | Sanitized executed provider-plan summary |
| docs/session12_agentic_handoff.md | Reviewer handoff with commands and limitations |

## Model variance explanation

The live-provider totals are different because each provider produced a different estimation plan.

The deterministic executor did not decide the numbers. It calculated totals from each provider's selected components, reference hours, and assumptions.

Observed executed-plan totals:

| Provider | Tier | Total hours | Total cost EUR |
| --- | --- | ---: | ---: |
| DeepSeek | cheap | 288.0 | 21600.0 |
| DeepSeek | final | 228.0 | 17100.0 |
| Kimi | cheap | 230.4 | 17280.0 |
| Kimi | final | 249.6 | 18720.0 |
| OpenAI | cheap | 216.0 | 16200.0 |
| OpenAI | final | 432.0 | 32400.0 |

## Not a model-quality benchmark

This spread is useful integration evidence, but it is not a model-quality benchmark.

It proves that live providers can emit executable plans and that those plans can drive deterministic local tools.

It does not prove that any model is more accurate, better calibrated, cheaper, or superior.

A fair model-quality comparison would need a fixed rubric, expected reference estimate, component-level scoring, repeated runs, and saved benchmark data.

## Remaining gaps

1. Verify the final trace for sample_transcript_complex.txt explicitly shows more than one component and more than one search_budgets call.
2. Verify whether the OpenAI path uses the exact Responses API loop requested by the official task or an OpenAI-compatible planning adapter.
3. Verify search_budgets wraps the S9-S10 retrieval path and does not silently rely only on a fake fallback.
4. Mirror or create session-12/pre-work after final green gates if the teacher requires that exact branch.
5. Remote CI green observed for 97c0630 in GitHub Actions. Devcontainer validation observed green. Live provider smoke observed green.
6. Prepare the final email with repository branch URL and trace artifact reference.

## Current claim allowed

Allowed:

The current branch has deterministic local evidence, manual live-provider planning evidence, deterministic provider-plan execution evidence, and reviewer handoff documentation.

Not allowed yet:

The task is fully delivered with no remaining gaps.

Not allowed yet:

Model variance is integration evidence, not benchmark evidence.

Not allowed yet:

remote CI green is not proven.

## Final compliance closure

Complex transcript evidence is covered.

The committed `sample_transcript_complex` trace contains four components and two search_budgets calls. It then calls calculate_estimate and validate_estimate, and validation returns valid true.

Retrieval bridge is covered with injected service.

The bridge adapts the existing Session 08-10 search-service boundary into the Session 12 search_budgets contract. The deterministic fallback remains intentionally available for CI safety.

Task 12 validate_estimate extra is covered.

The validate_estimate tool is implemented and appears in deterministic traces, executed provider-plan evidence, and live provider plan summaries.

Remote validation status:

- Remote CI green observed for 97c0630.
- Devcontainer validation observed green.
- Live provider smoke observed green.

Session 11 live Quality Lab UI diagnostics remain optional.

The Session 11 live extras and the draft quality-lab branch are useful inspiration, but they are not mandatory Task 12 core delivery. They were not merged into Session 12 as a UI path because UI changes would require browser smoke evidence.

Exact OpenAI Responses API loop remains not implemented.

The current implementation supports OpenAI-compatible live planning through chat completions. It does not implement the exact Responses API continuation loop with previous_response_id. Submit with this caveat or implement it as a separate slice.

Model variance is integration evidence, not benchmark evidence.

The spread between provider estimates shows that the plans are executable but not calibrated. It must not be described as model quality, accuracy, superiority, or benchmark evidence.
