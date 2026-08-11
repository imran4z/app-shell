"""Shared fixtures (BLUEPRINT.md §11).

- `pg_container`: one session-scoped testcontainers Postgres (skips
  cleanly when Docker or the lib is missing).
- `engine`: per-test engine that monkeypatches the two lru_cached
  factories in storage/db.py, so all in-package callers transparently hit
  the container. Teardown calls drop_all(engine) - never a second
  hand-maintained table list.
- `fake_anthropic`: a hand-rolled SDK-surface fake so the real wrapper,
  sanitizers, and pydantic validation all execute; only the network is faked.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture(scope="session")
def pg_container():
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed")
    try:
        with PostgresContainer("postgres:16-alpine") as pg:
            yield pg
    except Exception as exc:  # noqa: BLE001 - docker unavailable
        pytest.skip(f"could not start postgres container: {exc}")


@pytest.fixture
def engine(pg_container, monkeypatch):
    import sqlalchemy

    from appshell.storage import db as db_module
    from appshell.storage.migrator import apply_migrations, drop_all

    url = pg_container.get_connection_url(driver="psycopg")
    eng = sqlalchemy.create_engine(url, pool_pre_ping=True, future=True)

    from functools import lru_cache

    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=eng, expire_on_commit=False, future=True)
    monkeypatch.setattr(db_module, "connect", lru_cache(maxsize=1)(lambda: eng))
    monkeypatch.setattr(db_module, "_session_factory", lru_cache(maxsize=1)(lambda: factory))

    apply_migrations(eng)  # exercise the real migration path
    yield eng
    drop_all(eng)  # the fixture reuses drop_all - no duplicate table list
    eng.dispose()


# --- Fake Anthropic client -----------------------------------------------


class _FakeStream:
    """Mimics anthropic's messages.stream() context manager surface."""

    def __init__(self, text: str, model: str):
        self._text = text
        self._model = model

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        yield from (self._text[i : i + 8] for i in range(0, len(self._text), 8))

    def get_final_message(self):
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self._text)],
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=len(self._text) // 4,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
            stop_reason="end_turn",
            model=self._model,
        )


class FakeAnthropicClient:
    """Canned-response fake reproducing the SDK surface the wrapper uses."""

    def __init__(self, canned: str = '{"ok": true}'):
        self.canned = canned
        self.calls: list[dict] = []
        outer = self

        class _Messages:
            def stream(self, **request):
                outer.calls.append(request)
                return _FakeStream(outer.canned, request.get("model", "fake"))

        self.messages = _Messages()


@pytest.fixture
def fake_anthropic():
    return FakeAnthropicClient()
