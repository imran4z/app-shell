"""Repository round-trip against an ephemeral Postgres (testcontainers).

Run with `just test-integration`. Exercises the real migrations, the
trigger, and every ItemRepository method.
"""

import pytest
from sqlalchemy.orm import Session

from appshell.schemas import Item, ItemState
from appshell.storage.repositories import ItemRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def session(engine):
    with Session(engine, expire_on_commit=False) as s:
        yield s
        s.commit()


def test_upsert_get_roundtrip(session):
    repo = ItemRepository()
    item = Item(title="First", detail={"a": 1})
    repo.upsert(session, item)
    session.commit()

    got = repo.get(session, item.id)
    assert got is not None
    assert got.title == "First"
    assert got.detail == {"a": 1}
    assert got.created_at is not None


def test_list_filter_and_pagination(session):
    repo = ItemRepository()
    for i in range(5):
        repo.upsert(session, Item(title=f"Widget {i}", state=ItemState.DONE))
    repo.upsert(session, Item(title="Other", state=ItemState.PENDING))
    session.commit()

    entries, total = repo.list(session, state=ItemState.DONE, limit=2, offset=0)
    assert total == 5
    assert len(entries) == 2

    entries, total = repo.list(session, q="widget")
    assert total == 5


def test_state_transition_and_touch_trigger(session):
    repo = ItemRepository()
    item = Item(title="Mutable")
    repo.upsert(session, item)
    session.commit()
    before = repo.get(session, item.id)

    assert repo.set_state(session, item.id, ItemState.RUNNING)
    session.commit()
    after = repo.get(session, item.id)
    assert after.state is ItemState.RUNNING
    assert after.updated_at >= before.updated_at  # touch_updated_at fired

    assert not repo.set_state(session, "item_missing", ItemState.DONE)


def test_counts_by_state_reports_zeroes(session):
    repo = ItemRepository()
    repo.upsert(session, Item(title="One", state=ItemState.FAILED))
    session.commit()
    counts = repo.counts_by_state(session)
    assert counts["failed"] == 1
    assert counts["pending"] == 0
    assert set(counts) == {s.value for s in ItemState}


def test_delete(session):
    repo = ItemRepository()
    item = Item(title="Doomed")
    repo.upsert(session, item)
    session.commit()
    assert repo.delete(session, item.id)
    assert repo.get(session, item.id) is None
    assert not repo.delete(session, item.id)
