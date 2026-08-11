-- ==== 0001 - items ====
-- Example domain entity shipped with the template. It exists so the walking
-- skeleton has one end-to-end resource (migration -> repo -> route -> list page)
-- demonstrating every storage convention. Replace it with your app's real
-- entities; keep the conventions (TEXT CHECK states, JSONB payloads,
-- TIMESTAMPTZ, touch_updated_at trigger, idx_<table>_<cols> naming).

CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS items (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    state       TEXT NOT NULL DEFAULT 'pending'
                CHECK (state IN ('pending', 'running', 'done', 'failed')),
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_items_state ON items (state);
CREATE INDEX IF NOT EXISTS idx_items_created_at ON items (created_at DESC);

DROP TRIGGER IF EXISTS trg_items_touch ON items;
CREATE TRIGGER trg_items_touch
    BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
