"""Assistant tool catalog - BLUEPRINT.md §9 / contract #4.

Each tool is two independent pieces: a module-level raw Anthropic tool-def
dict (no decorators, no framework) and an executor `_exec_x(args, session)`.
Registries split READONLY / MUTATING; NEEDS_APPROVAL gates the human-in-
the-loop pause. `execute_tool` NEVER throws - unknown tools and executor
exceptions become ({"error": ...}, True) so the model can recover.

Result contract: JSON-serializable and BOUNDED - the agent re-sends every
tool_result each iteration, so a 50KB blob costs 50KB x N. list tools take
a clamped `limit` (default 20, max 100) and return slim rows.

Replace the item tools with your domain's; keep the registry shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from appshell.schemas import AppUser, Item, ItemState, Profile, ProfileStatus, UserRole, UserStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

_logger = structlog.get_logger()

# Shared clamped-limit schema fragment. Enum values generated from the
# pydantic schema at import so tool schemas can't drift from the contract.
_LIMIT = {
    "type": "integer",
    "description": "Max rows to return (1-100).",
    "default": 20,
}
_STATE_ENUM = [s.value for s in ItemState]


# --- list_items ----------------------------------------------------------

TOOL_LIST_ITEMS = {
    "name": "list_items",
    "description": (
        "List items, newest first. Optionally filter by lifecycle state or a "
        "title substring. Returns slim rows (id, title, state, updated_at)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "state": {"type": "string", "enum": _STATE_ENUM},
            "q": {"type": "string", "description": "Title substring filter."},
            "limit": _LIMIT,
        },
    },
}


def _exec_list_items(args: dict[str, Any], session: Session) -> Any:
    from appshell.storage import ItemRepository

    limit = max(1, min(int(args.get("limit", 20) or 20), 100))  # re-clamp server-side
    state = ItemState(args["state"]) if args.get("state") in _STATE_ENUM else None
    entries, total = ItemRepository().list(
        session, state=state, q=args.get("q") or None, limit=limit, offset=0
    )
    return {
        "total": total,
        "items": [
            {
                "id": it.id,
                "title": it.title,
                "state": it.state.value,
                "updated_at": it.updated_at.isoformat() if it.updated_at else None,
            }
            for it in entries
        ],
    }


# --- get_item_stats ------------------------------------------------------

TOOL_GET_ITEM_STATS = {
    "name": "get_item_stats",
    "description": "Count of items per lifecycle state, plus the total.",
    "input_schema": {"type": "object", "properties": {}},
}


def _exec_get_item_stats(args: dict[str, Any], session: Session) -> Any:
    from appshell.storage import ItemRepository

    counts = ItemRepository().counts_by_state(session)
    return {"counts": counts, "total": sum(counts.values())}


# --- list_profiles -------------------------------------------------------

_STATUS_ENUM = [s.value for s in ProfileStatus]

TOOL_LIST_PROFILES = {
    "name": "list_profiles",
    "description": (
        "List profiles (name containers with attributes/tags and a draft/"
        "published/archived lifecycle). Returns slim rows."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": _STATUS_ENUM},
            "q": {"type": "string", "description": "Name substring filter."},
            "limit": _LIMIT,
        },
    },
}


def _exec_list_profiles(args: dict[str, Any], session: Session) -> Any:
    from appshell.storage import ProfileRepository

    limit = max(1, min(int(args.get("limit", 20) or 20), 100))
    status = ProfileStatus(args["status"]) if args.get("status") in _STATUS_ENUM else None
    entries, total = ProfileRepository().list(
        session, status=status, q=args.get("q") or None, limit=limit, offset=0
    )
    return {
        "total": total,
        "profiles": [
            {
                "id": p.id,
                "name": p.name,
                "status": p.status.value,
                "tags": p.tags,
                "attributes": p.attributes,
            }
            for p in entries
        ],
    }


# --- create_profile (mutating, approval-gated) ---------------------------

TOOL_CREATE_PROFILE = {
    "name": "create_profile",
    "description": (
        "Create a new draft profile. Requires the user's approval before it "
        "runs. Attributes are key->value strings."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Profile display name."},
            "summary": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "attributes": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["name"],
    },
}


def _exec_create_profile(args: dict[str, Any], session: Session) -> Any:
    from appshell.storage import ProfileRepository

    name = str(args.get("name", "")).strip()[:120]
    if not name:
        return {"error": "name is required"}
    profile = Profile(
        name=name,
        summary=str(args.get("summary", ""))[:2000],
        tags=[str(t)[:40] for t in (args.get("tags") or [])][:20],
        attributes={str(k)[:80]: str(v)[:2000] for k, v in (args.get("attributes") or {}).items()},
    )
    ProfileRepository().upsert(session, profile)
    return {"created": {"id": profile.id, "name": profile.name, "status": profile.status.value}}


# --- list_users ----------------------------------------------------------

_ROLE_ENUM = [r.value for r in UserRole]
_USER_STATUS_ENUM = [s.value for s in UserStatus]

TOOL_LIST_USERS = {
    "name": "list_users",
    "description": "List the app's users (accounts) with role and status.",
    "input_schema": {
        "type": "object",
        "properties": {
            "role": {"type": "string", "enum": _ROLE_ENUM},
            "status": {"type": "string", "enum": _USER_STATUS_ENUM},
            "q": {"type": "string", "description": "Name/email substring filter."},
            "limit": _LIMIT,
        },
    },
}


def _exec_list_users(args: dict[str, Any], session: Session) -> Any:
    from appshell.storage import UserRepository

    limit = max(1, min(int(args.get("limit", 20) or 20), 100))
    role = UserRole(args["role"]) if args.get("role") in _ROLE_ENUM else None
    status = UserStatus(args["status"]) if args.get("status") in _USER_STATUS_ENUM else None
    entries, total = UserRepository().list(
        session, role=role, status=status, q=args.get("q") or None, limit=limit, offset=0
    )
    return {
        "total": total,
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": str(u.email),
                "role": u.role.value,
                "status": u.status.value,
            }
            for u in entries
        ],
    }


# --- invite_user (mutating, approval-gated) ------------------------------

TOOL_INVITE_USER = {
    "name": "invite_user",
    "description": (
        "Add a user to the app's directory in 'invited' status. Requires the "
        "user's approval before it runs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string", "description": "Unique email handle."},
            "role": {"type": "string", "enum": _ROLE_ENUM, "default": "member"},
        },
        "required": ["name", "email"],
    },
}


def _exec_invite_user(args: dict[str, Any], session: Session) -> Any:
    from appshell.storage import UserRepository

    repo = UserRepository()
    try:
        user = AppUser(
            name=str(args.get("name", "")).strip()[:120],
            email=str(args.get("email", "")).strip(),
            role=UserRole(args["role"]) if args.get("role") in _ROLE_ENUM else UserRole.MEMBER,
        )
    except Exception as exc:  # noqa: BLE001 - pydantic message is the useful part
        return {"error": f"invalid user: {exc}"}
    if repo.get_by_email(session, str(user.email)) is not None:
        return {"error": f"a user with email {user.email} already exists"}
    repo.upsert(session, user)
    return {"invited": {"id": user.id, "name": user.name, "email": str(user.email)}}


# --- create_item (mutating, approval-gated) ------------------------------

TOOL_CREATE_ITEM = {
    "name": "create_item",
    "description": "Create a new item. Requires the user's approval before it runs.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "One-line item title."},
        },
        "required": ["title"],
    },
}


def _exec_create_item(args: dict[str, Any], session: Session) -> Any:
    from appshell.storage import ItemRepository

    title = str(args.get("title", "")).strip()[:200]
    if not title:
        return {"error": "title is required"}
    item = Item(title=title, detail={"created_by": "assistant"})
    ItemRepository().upsert(session, item)
    return {"created": {"id": item.id, "title": item.title, "state": item.state.value}}


# --- set_item_state (mutating, approval-gated) ---------------------------

TOOL_SET_ITEM_STATE = {
    "name": "set_item_state",
    "description": (
        "Move an item to a new lifecycle state. Requires the user's approval before it runs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string"},
            "state": {"type": "string", "enum": _STATE_ENUM},
        },
        "required": ["item_id", "state"],
    },
}


def _exec_set_item_state(args: dict[str, Any], session: Session) -> Any:
    from appshell.storage import ItemRepository

    if args.get("state") not in _STATE_ENUM:
        return {"error": f"state must be one of {_STATE_ENUM}"}
    ok = ItemRepository().set_state(session, str(args.get("item_id", "")), ItemState(args["state"]))
    if not ok:
        return {"error": f"item {args.get('item_id')} not found"}
    return {"updated": {"id": args["item_id"], "state": args["state"]}}


# --- Registries ----------------------------------------------------------

TOOLS_READONLY: list[dict[str, Any]] = [
    TOOL_LIST_ITEMS,
    TOOL_GET_ITEM_STATS,
    TOOL_LIST_PROFILES,
    TOOL_LIST_USERS,
]
TOOLS_MUTATING: list[dict[str, Any]] = [
    TOOL_CREATE_ITEM,
    TOOL_SET_ITEM_STATE,
    TOOL_CREATE_PROFILE,
    TOOL_INVITE_USER,
]
TOOLS_ALL: list[dict[str, Any]] = TOOLS_READONLY + TOOLS_MUTATING

MUTATING_TOOL_NAMES: frozenset[str] = frozenset(t["name"] for t in TOOLS_MUTATING)
NEEDS_APPROVAL_TOOL_NAMES: frozenset[str] = MUTATING_TOOL_NAMES

EXECUTORS: dict[str, Callable[[dict[str, Any], Session], Any]] = {
    "list_items": _exec_list_items,
    "get_item_stats": _exec_get_item_stats,
    "list_profiles": _exec_list_profiles,
    "create_item": _exec_create_item,
    "set_item_state": _exec_set_item_state,
    "create_profile": _exec_create_profile,
    "list_users": _exec_list_users,
    "invite_user": _exec_invite_user,
}


def execute_tool(name: str, args: dict[str, Any], session: Session) -> tuple[Any, bool]:
    """Run one tool. Returns (result, is_error). Never raises - the model
    sees {"error": ...} and recovers."""
    executor = EXECUTORS.get(name)
    if executor is None:
        return {"error": f"unknown tool: {name}"}, True
    try:
        return executor(args or {}, session), False
    except Exception as exc:  # noqa: BLE001 - contract: tools never throw
        _logger.warning("assistant.tool_failed", tool=name, error=str(exc)[:300])
        return {"error": f"{type(exc).__name__}: {exc}"}, True
