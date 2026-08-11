-- ==== 0005 - users ====
-- The app's own user directory: every customer/team account the app
-- knows about. No auth/passwords in the template (wire your IdP or auth
-- flow per-app); this is the account record everything else will
-- eventually reference. Email is the natural unique handle.

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    role          TEXT NOT NULL DEFAULT 'member'
                  CHECK (role IN ('admin', 'member', 'viewer')),
    status        TEXT NOT NULL DEFAULT 'invited'
                  CHECK (status IN ('invited', 'active', 'disabled')),
    last_seen_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_status ON users (status);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

DROP TRIGGER IF EXISTS trg_users_touch ON users;
CREATE TRIGGER trg_users_touch
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
