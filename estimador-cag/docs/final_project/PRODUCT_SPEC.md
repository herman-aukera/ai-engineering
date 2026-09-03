# EACHAT Final Project Product Specification

Status: final-project SDD
Branch: `finalproject-GG`
Domain: Technical Support / Software Operations

## Product

**EACHAT — Energy-Aware AI Engineering Support Assistant** is an evidence-grounded L2 support assistant for engineers operating Java/Spring Boot backend services. It triages technical questions, retrieves authoritative documentation, generates a candidate answer, critiques the candidate against grounding/scope/safety constraints, applies bounded repair, and clarifies or escalates when evidence or authority is insufficient.

## Target user

L2 application-support engineers and backend engineers responsible for Spring Boot services backed by PostgreSQL and deployed in Docker containers.

## Supported V1 scope

- Spring Boot runtime: startup, configuration/profiles, Actuator, health/readiness, REST/runtime symptoms.
- PostgreSQL: connections, pools, sessions, locks, transactions, slow-query symptoms, monitoring and relevant limits.
- Docker: container startup/state, logs, networking/ports, environment configuration, volumes, health checks and resource symptoms.
- Observability: logs, Actuator endpoints, health/readiness, metrics and PostgreSQL diagnostic views.

## Explicitly out of scope

Santander/proprietary systems, customer/payment support, corporate infrastructure, Active Directory, network operations, cybersecurity incident response, Kubernetes, Kafka, frontend/mobile, business-domain logic and arbitrary source-code repair.

## Support authority

EACHAT models an L2 boundary:

- `accept`: evidence is sufficient for an L2 answer.
- `repair`: the candidate violates grounding/quality constraints and is regenerated once within budget.
- `clarify`: required diagnostic information is missing.
- `reject` / `refuse`: hard constraints or safety policy prevent the proposed answer.
- `escalate`: L3/source-code remediation, specialist authority, unsupported technology or unavailable current evidence is required.

## Primary journey

```text
question / incident
→ interpret + policy
→ classify evidence need
→ retrieve authoritative support evidence
→ generate candidate
→ critic panel
→ Energy score
→ deterministic disposition
→ bounded repair / clarify / escalate
→ answer + evidence + Energy Card + safe trace
```

## Success criteria

1. Real public support documents are acquired from a committed allowlisted manifest.
2. Ingestion is reproducible and preserves provenance.
3. Documents are chunked and embedded.
4. Embeddings/chunks are persisted in PostgreSQL and retrieved by vector similarity.
5. Retrieved evidence flows through the existing EACHAT candidate/critic/decision graph.
6. Unsupported or under-specified requests do not produce fabricated certainty.
7. A reproducible eval set includes retrieval, grounding, disposition and regression evidence.
8. FastAPI + browser demo are usable, and the submission has a public URL or a 2–3 minute video.

## Non-goals for the deadline

ANN/vector-extension optimization, reranking, Kubernetes, enterprise OIDC, production SLOs, large-scale crawling, EACODE integration and production-scale incident automation are post-deadline work unless a mandatory acceptance test exposes a blocker.
