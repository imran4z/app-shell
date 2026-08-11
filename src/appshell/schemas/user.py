"""AppUser - the app's own user/account record.

The template ships no auth (wire your IdP per-app); this is the durable
account record: who exists, what they may do (role), and whether the
account is live (status). Email is the unique natural handle, normalized
to lowercase at the schema boundary so the DB UNIQUE constraint means
what users expect.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRole(str, Enum):
    """Coarse permission tier. Enforce in routes/tools as the app grows."""

    ADMIN = "admin"  # manages users and settings
    MEMBER = "member"  # normal read-write usage
    VIEWER = "viewer"  # read-only


class UserStatus(str, Enum):
    """Account lifecycle."""

    INVITED = "invited"  # record exists; user hasn't shown up yet
    ACTIVE = "active"  # normal, usable account
    DISABLED = "disabled"  # locked out; kept for history/audit


def new_user_id() -> str:
    """Opaque unique id. TEXT natural key in the DB."""
    return f"user_{uuid.uuid4().hex[:12]}"


class AppUser(BaseModel):
    """One account in the app's user directory."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=new_user_id, description="Opaque unique id, `user_<hex>`.")
    name: str = Field(description="Display name.", max_length=120)
    email: EmailStr = Field(description="Unique handle; normalized to lowercase.")
    role: UserRole = Field(default=UserRole.MEMBER, description="Permission tier; see UserRole.")
    status: UserStatus = Field(
        default=UserStatus.INVITED, description="Account lifecycle; see UserStatus."
    )
    last_seen_at: datetime | None = Field(
        default=None, description="Set by the app on activity; None until first seen."
    )
    created_at: datetime | None = Field(
        default=None, description="Set by the DB on insert; None before first persist."
    )
    updated_at: datetime | None = Field(
        default=None, description="Maintained by the touch_updated_at trigger."
    )

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, v: str) -> str:
        return v.lower()
