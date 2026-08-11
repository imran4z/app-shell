"""Profile - the template's container entity (list -> detail pattern).

A profile is a named thing you enrich over time: attributes, tags, and a
publish lifecycle. Same contract rules as Item: the JSON serialization is
the on-disk format; enums are closed vocabularies; every field described.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProfileStatus(str, Enum):
    """Publish lifecycle for a profile."""

    DRAFT = "draft"  # being assembled; freely editable
    PUBLISHED = "published"  # visible/consumable; edits should be deliberate
    ARCHIVED = "archived"  # kept for history; hidden from default lists


def new_profile_id() -> str:
    """Opaque unique id. TEXT natural key in the DB."""
    return f"prof_{uuid.uuid4().hex[:12]}"


class Profile(BaseModel):
    """A named container enriched with attributes and tags over time."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=new_profile_id, description="Opaque unique id, `prof_<hex>`.")
    name: str = Field(
        description="Display name shown in lists and the detail header.", max_length=120
    )
    summary: str = Field(default="", description="Short free-text description.", max_length=2000)
    status: ProfileStatus = Field(
        default=ProfileStatus.DRAFT, description="Publish lifecycle; see ProfileStatus."
    )
    tags: list[str] = Field(
        default_factory=list, description="Free-form labels; deduped, order preserved."
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Key -> value facts added over time (the enrichment surface).",
    )
    created_at: datetime | None = Field(
        default=None, description="Set by the DB on insert; None before first persist."
    )
    updated_at: datetime | None = Field(
        default=None, description="Maintained by the touch_updated_at trigger."
    )
