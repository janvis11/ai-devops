-- kafka/init-db.sql
-- Initializes PostgreSQL schema for devops.ai platform.
-- Runs automatically on first container start via docker-entrypoint-initdb.d/

-- ── Agent audit table (populated by Kafka Connect JDBC sink) ─────────────────
CREATE TABLE IF NOT EXISTS agent_actions (
    action_id       VARCHAR(64) PRIMARY KEY,
    pod_name        VARCHAR(255),
    namespace       VARCHAR(128),
    action_type     VARCHAR(64),   -- restart, scale, patch_memory, evict
    triggered_by    VARCHAR(128),  -- alert name
    severity        VARCHAR(32),
    classification  TEXT,
    diagnosis       TEXT,
    decision        TEXT,
    outcome         VARCHAR(32),   -- success, failed, skipped
    llm_latency_ms  INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    metadata        JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_actions_pod_name  ON agent_actions(pod_name);
CREATE INDEX IF NOT EXISTS idx_agent_actions_namespace ON agent_actions(namespace);
CREATE INDEX IF NOT EXISTS idx_agent_actions_created_at ON agent_actions(created_at DESC);

-- ── LangGraph checkpoints table ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id    VARCHAR(128),
    checkpoint   JSONB,
    metadata     JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id)
);

-- ── Dev env requests (from Backstage) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS env_requests (
    request_id   VARCHAR(64) PRIMARY KEY,
    env_name     VARCHAR(128),
    requester    VARCHAR(128),
    status       VARCHAR(32) DEFAULT 'pending',
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    synced_at    TIMESTAMPTZ
);
