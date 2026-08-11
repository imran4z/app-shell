"""Item - the template's example domain entity.

The JSON serialization of these models is the on-disk format (JSONB columns
and API payloads alike). Every field carries a description= because these
schemas double as LLM-facing documentation when they render into prompts.

Replace Item with your app's real entities; keep the conventions:
str-Enum closed vocabularies, ConfigDict, descriptions on every field.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ItemState(str, Enum):
    """Closed lifecycle vocabulary for an item.

    Enums are the contract downstream code (and any LLM) must hit -
    sanitizers coerce toward them, the DB CHECK constraint enforces them.
    """

    PENDING = "pending"  # created, nothing has happened yet
    RUNNING = "running"  # actively being worked on
    DONE = "done"  # finished successfully
    FAILED = "failed"  # finished unsuccessfully; detail explains why


def new_item_id() -> str:
    """Opaque unique id. TEXT in the DB - natural key, not BIGSERIAL."""
    return f"item_{uuid.uuid4().hex[:12]}"


class Item(BaseModel):
    """A single unit of work / record in the example domain."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=new_item_id, description="Opaque unique id, `item_<hex>`.")
    title: str = Field(description="Human-readable one-line name shown in lists.", max_length=200)
    state: ItemState = Field(
        default=ItemState.PENDING, description="Lifecycle state; see ItemState."
    )
    detail: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form JSONB payload - the artifact body. Schema it per-app.",
    )
    created_at: datetime | None = Field(
        default=None, description="Set by the DB on insert; None before first persist."
    )
    updated_at: datetime | None = Field(
        default=None, description="Maintained by the touch_updated_at trigger."
    )
