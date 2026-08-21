# EACODE Operations

## Probes

- `/startup`: signing authority and durable schema initialization completed.
- `/health`: cheap process liveness; no PostgreSQL/provider call.
- `/ready`: startup completed with verified PostgreSQL authority schema.
- `/version`: safe service/version/Git SHA.

## Database lifecycle

`python -m energy_core.postgres_beta_store migrate` applies the explicit additive authority migration. Application startup verifies the schema but does not silently invent it.

The PostgreSQL integration workflow creates/authorizes/executes a proposal, destroys the application container, recreates it against the same database and verifies the completed authority record survives.

## Remaining operational gates

Real RDS backup/restore, schema rollback rehearsal, EC2 Spot interruption, load/concurrency characterization, dashboards, alerts, SLOs and external identity-provider availability.
