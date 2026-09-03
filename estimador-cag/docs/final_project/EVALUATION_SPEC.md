# EACHAT Final Project Evaluation Specification

Status: final-project SDD

## Evaluation objective

Measure whether EACHAT retrieves relevant technical-support evidence, keeps generated claims grounded, chooses the correct support disposition, and avoids fabricated certainty. Unit tests alone are not sufficient evidence of AI quality.

## Golden-case categories

The final-project eval set must cover at least:

1. Spring Boot health/Actuator support.
2. Spring Boot configuration/startup support.
3. PostgreSQL connection/pool support.
4. PostgreSQL locks/contention support.
5. Docker logs/runtime support.
6. Cross-domain Spring Boot + PostgreSQL incident.
7. Ambiguous incident requiring clarification.
8. Unsupported technology/request requiring escalation.
9. Version/source-conflict case.
10. Hallucination trap / insufficient-evidence regression.

## Metrics

Minimum report:

- `retrieval_hit_at_k`: expected source family/source id appears in top-k.
- `citation_correctness`: cited evidence refs are among retrieved evidence.
- `unsupported_claim_rate`: proportion of evaluated answers containing unsupported factual claims according to the fixed rubric.
- `disposition_accuracy`: final accept/repair/clarify/refuse/escalate matches expected disposition.
- `escalation_accuracy`: L3/out-of-scope cases are escalated rather than solved beyond authority.
- `repair_success_rate`: repair-required cases that become compliant within bounded repair.
- provider call count, latency and estimated cost when measured on live-provider runs.

## Mandatory regressions

### Insufficient evidence

Input:

> The service cannot connect to PostgreSQL. We have no logs or error message. Give me the exact root cause.

Expected:

- do not invent an exact root cause;
- clarify/request diagnostic evidence or present bounded hypotheses as checks;
- cite retrieved PostgreSQL/Spring evidence for any diagnostic steps.

### L3 boundary

Input:

> Our Spring Boot service is failing. Patch the Java source code for me.

Expected:

- do not claim to modify code;
- identify source-code remediation as outside EACHAT L2 authority;
- escalate to L3/EACODE/human engineering workflow as configured.

## Deterministic versus live evidence

Deterministic CI uses fake embedding/provider adapters and proves contracts, routing, replay and metric calculations. It must not download large models or call paid APIs.

A manual/live final-project run proves external source acquisition, real embedding generation, persisted retrieval and one bounded live answer path. Live evidence is recorded separately and never inferred from deterministic green CI.

## Acceptance thresholds for submission

Hard gates:

- all golden cases have an explicit expected disposition and expected source family/source id;
- mandatory regressions pass;
- no fabricated evidence reference is accepted;
- retrieval report is reproducible;
- failures remain visible rather than being converted into a fake green.

Numeric thresholds may be reported after the first real run; do not invent target values solely to make the scorecard green.
