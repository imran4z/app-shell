"""Migration hygiene checks that don't need a database."""

import re

from appshell.storage.migrator import _migration_files


def test_migrations_discoverable_and_lexically_ordered():
    files = _migration_files()
    assert files, "no migration files found in the package"
    names = [f.name for f in files]
    assert names == sorted(names)


def test_migration_names_follow_convention():
    for f in _migration_files():
        assert re.match(r"^\d{4}_[a-z0-9_]+\.sql$", f.name), f.name


def test_migrations_are_rerunnable_sql():
    """Convention: CREATE TABLE/INDEX must be IF NOT EXISTS so re-runs
    of a partially-applied migration don't explode."""
    for f in _migration_files():
        sql = f.read_text().upper()
        for stmt in ("CREATE TABLE", "CREATE INDEX"):
            for idx in _find_all(sql, stmt):
                assert sql[idx : idx + len(stmt) + 14].startswith(f"{stmt} IF NOT EXISTS"), (
                    f"{f.name}: `{stmt}` without IF NOT EXISTS"
                )


def _find_all(haystack: str, needle: str):
    start = 0
    while (idx := haystack.find(needle, start)) != -1:
        yield idx
        start = idx + 1
