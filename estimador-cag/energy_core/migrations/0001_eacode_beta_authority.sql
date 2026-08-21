CREATE TABLE IF NOT EXISTS eacode_schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eacode_beta_demo_runs (
    proposal_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    result_json TEXT NOT NULL,
    result_hash CHAR(64) NOT NULL,
    execution_reserved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eacode_beta_demo_runs_owner
    ON eacode_beta_demo_runs(owner_id);

CREATE TABLE IF NOT EXISTS eacode_beta_demo_authorizations (
    receipt_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL REFERENCES eacode_beta_demo_runs(proposal_id) ON DELETE RESTRICT,
    actor TEXT NOT NULL,
    scope_hash CHAR(64) NOT NULL,
    nonce_hash CHAR(64) NOT NULL UNIQUE,
    issued_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    record_hash CHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eacode_beta_demo_authorizations_proposal
    ON eacode_beta_demo_authorizations(proposal_id);

INSERT INTO eacode_schema_migrations(version)
VALUES ('0001_eacode_beta_authority')
ON CONFLICT (version) DO NOTHING;
