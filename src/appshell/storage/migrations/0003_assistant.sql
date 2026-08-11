-- ==== 0003 - assistant_conversations + assistant_turns ====
-- Persistence for the in-app AI assistant (⌘J drawer). Storing `tool` as
-- its own turn role means replays read left-to-right without re-execution
-- (BLUEPRINT.md §9). Turns cascade with their conversation; conversations
-- are archived, not deleted, from the UI.

CREATE TABLE IF NOT EXISTS assistant_conversations (
    id               BIGSERIAL PRIMARY KEY,
    title            TEXT NOT NULL DEFAULT 'New conversation',
    status           TEXT NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active', 'archived')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assistant_turns (
    id               BIGSERIAL PRIMARY KEY,
    conversation_id  BIGINT NOT NULL
                     REFERENCES assistant_conversations(id) ON DELETE CASCADE,
    role             TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content          TEXT NOT NULL DEFAULT '',
    tool_calls       JSONB,
    tool_results     JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assistant_turns_conversation_id
    ON assistant_turns (conversation_id, id);
