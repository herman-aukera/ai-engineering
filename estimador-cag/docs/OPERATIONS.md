# Estimator Operations

## Probes

- `/startup`: application lifespan completed.
- `/health`: local process liveness; no DB/LLM I/O.
- `/ready`: unified runtime initialized and at least one real provider configured; no model call.
- `/version`: safe service/version/Git SHA.

## Failure expectations

A missing/unavailable durable graph runtime keeps readiness false. Provider outage during a request must produce bounded application failure rather than make health probes invoke the provider. PostgreSQL is authoritative; Redis must be treated as cache/runtime infrastructure according to the calling feature.

## Spot/restart model

Application compute is disposable. Store authoritative state outside the instance, use graceful SIGTERM/stop windows, bootstrap from an exact OCI digest and verify `/ready` before accepting traffic.

## Still required before production

Real RDS backup/restore, EC2/Spot replacement exercise, load/concurrency characterization, dashboards, alerts, SLOs, incident/runbook rehearsal and multi-tenant ownership proof.
