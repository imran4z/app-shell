-- ==== 0004 - profiles ====
-- Second example entity: a "profile" is a named container you enrich over
-- time - free-form attributes (key/value), tags, and a draft -> published ->
-- archived lifecycle. It exists to demonstrate the list->detail page
-- pattern and JSONB-payload editing end to end. Replace with your app's
-- real container entity; keep the conventions.

CREATE TABLE IF NOT EXISTS profiles (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    summary     TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'published', 'archived')),
    tags        JSONB NOT NULL DEFAULT '[]'::jsonb,
    attributes  JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_status ON profiles (status);
CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles (created_at DESC);

DROP TRIGGER IF EXISTS trg_profiles_touch ON profiles;
CREATE TRIGGER trg_profiles_touch
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
