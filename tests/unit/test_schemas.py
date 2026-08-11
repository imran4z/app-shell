"""Schema contract tests - the JSON serialization IS the on-disk format."""

import json

import pytest
from pydantic import ValidationError

from appshell.schemas import Item, ItemState


def test_item_defaults():
    item = Item(title="Hello")
    assert item.id.startswith("item_")
    assert item.state is ItemState.PENDING
    assert item.detail == {}
    assert item.created_at is None


def test_item_round_trips_through_json():
    item = Item(title="Round trip", state=ItemState.RUNNING, detail={"k": [1, 2]})
    restored = Item.model_validate(json.loads(item.model_dump_json()))
    assert restored == item


def test_state_is_a_closed_vocabulary():
    with pytest.raises(ValidationError):
        Item(title="bad", state="exploded")  # type: ignore[arg-type]


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        Item(title="x", surprise=True)  # type: ignore[call-arg]


def test_title_max_length_enforced():
    with pytest.raises(ValidationError):
        Item(title="x" * 201)


def test_app_user_email_normalized_and_validated():
    from appshell.schemas import AppUser, UserRole, UserStatus

    user = AppUser(name="Ada Lovelace", email="Ada@Example.COM")
    assert user.email == "ada@example.com"
    assert user.role is UserRole.MEMBER
    assert user.status is UserStatus.INVITED

    with pytest.raises(ValidationError):
        AppUser(name="Bad", email="not-an-email")
