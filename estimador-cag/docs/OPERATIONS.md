# EACHAT Operations

## Probes

- `/startup`: lifespan and durable stores initialized.
- `/health`: cheap local liveness, no DB/provider I/O.
- `/ready`: runtime and conversation store composed successfully; production startup already fails closed on durable-state failure.
- `/version`: service/version/Git SHA.

## Restart model

The application process/container is disposable. PostgreSQL holds authoritative checkpoints and encrypted conversation history. The existing canary recreates the app container against the same database and validates recovery.

## Operational gaps before production

Real RDS backup/restore, Spot interruption, database failover behavior, bounded load/concurrency limits, provider timeout/rate-limit exercises, dashboards, alerts, SLOs and tenant-aware audit identity remain required.
