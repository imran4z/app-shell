-- ==== 0002 - llm_calls ====
-- One row per model call made through observability/llm_client.call_anthropic.
-- Powers cost dashboards and debugging ("which agent burned the tokens?").
-- Writes are best-effort: the wrapper never lets a failed insert break the
-- primary path. Append-only; no FKs so it survives deletes elsewhere.

CREATE TABLE IF NOT EXISTS llm_calls (
    id             BIGSERIAL PRIMARY KEY,
    generation_id  TEXT NOT NULL,
    agent_name     TEXT NOT NULL,
    model          TEXT NOT NULL,
    pipeline_id    TEXT,
    phase          TEXT,
    prompt_template TEXT,
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens  INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd       NUMERIC(12, 6) NOT NULL DEFAULT 0,
    ttft_ms        INTEGER,
    duration_ms    INTEGER,
    error_type     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_calls_agent_name ON llm_calls (agent_name);
CREATE INDEX IF NOT EXISTS idx_llm_calls_created_at ON llm_calls (created_at DESC);
