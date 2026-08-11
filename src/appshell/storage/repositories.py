"""Repository classes - the only place raw SQL lives.

Conventions (firm):
  - All methods take an explicit `Session`; repos NEVER commit. Callers own
    the transaction via `session_scope()`.
  - Narrow surfaces: upsert/get/list/delete + explicit state-transition
    helpers. No generic CRUD base class.
  - Raw SQL via sqlalchemy.text() + bound params; JSONB via bindparam.
  - Reads return hydrated pydantic models for artifact tables; plain dicts
    for log/telemetry tables.

Adding a persisted entity? Follow the four-step contract:
migration file -> drop_all() registration -> repo class here -> storage
__init__ export.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from appshell.schemas import AppUser, Item, ItemState, Profile, ProfileStatus, UserRole, UserStatus


def _to_jsonable(value: Any) -> Any:
    """Round-trip through pydantic-aware JSON so datetimes/enums serialize."""
    if hasattr(value, "model_dump_json"):
        return json.loads(value.model_dump_json())
    return value


# ==== Items ====


class ItemRepository:
    """Persistence for the example `items` table. Replace per-app."""

    def upsert(self, session: Session, item: Item) -> Item:
        """Insert or update by id. Caller commits via session_scope()."""
        session.execute(
            text(
                """
                INSERT INTO items (id, title, state, detail)
                VALUES (:id, :title, :state, :detail)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    state = EXCLUDED.state,
                    detail = EXCLUDED.detail
                """
            ).bindparams(bindparam("detail", type_=JSONB)),
            {
                "id": item.id,
                "title": item.title,
                "state": item.state.value,
                "detail": _to_jsonable(item.detail),
            },
        )
        return item

    def get(self, session: Session, item_id: str) -> Item | None:
        row = session.execute(
            text(
                "SELECT id, title, state, detail, created_at, updated_at FROM items WHERE id = :id"
            ),
            {"id": item_id},
        ).first()
        return self._hydrate(row) if row else None

    def list(
        self,
        session: Session,
        *,
        state: ItemState | None = None,
        q: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[Item], int]:
        """Filtered page of items plus the total count for pagination."""
        where = ["TRUE"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if state is not None:
            where.append("state = :state")
            params["state"] = state.value
        if q:
            where.append("title ILIKE :q")
            params["q"] = f"%{q}%"
        clause = " AND ".join(where)

        total = session.execute(
            text(f"SELECT COUNT(*) FROM items WHERE {clause}"),  # noqa: S608
            params,
        ).scalar_one()
        rows = session.execute(
            text(
                f"SELECT id, title, state, detail, created_at, updated_at "
                f"FROM items WHERE {clause} "  # noqa: S608
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        ).all()
        return [self._hydrate(r) for r in rows], int(total)

    def set_state(self, session: Session, item_id: str, state: ItemState) -> bool:
        """Explicit state transition. Returns False when the id is unknown."""
        result = session.execute(
            text("UPDATE items SET state = :state WHERE id = :id"),
            {"id": item_id, "state": state.value},
        )
        return int(getattr(result, "rowcount", 0)) > 0

    def counts_by_state(self, session: Session) -> dict[str, int]:
        """State -> count map for KPI tiles. Missing states report 0."""
        rows = session.execute(text("SELECT state, COUNT(*) FROM items GROUP BY state")).all()
        counts = {s.value: 0 for s in ItemState}
        counts.update({row[0]: int(row[1]) for row in rows})
        return counts

    def delete(self, session: Session, item_id: str) -> bool:
        """Delete one item. Nothing cascades - items own no children."""
        result = session.execute(text("DELETE FROM items WHERE id = :id"), {"id": item_id})
        return int(getattr(result, "rowcount", 0)) > 0

    @staticmethod
    def _hydrate(row: Any) -> Item:
        return Item(
            id=row[0],
            title=row[1],
            state=ItemState(row[2]),
            detail=row[3] or {},
            created_at=row[4],
            updated_at=row[5],
        )


# ==== LLM calls (telemetry - plain dicts, append-only) ====


class LlmCallRepository:
    """Row-per-model-call ledger written best-effort by the LLM wrapper."""

    def record(self, session: Session, call: dict[str, Any]) -> None:
        session.execute(
            text(
                """
                INSERT INTO llm_calls (
                    generation_id, agent_name, model, pipeline_id, phase,
                    prompt_template, input_tokens, output_tokens,
                    cache_read_tokens, cache_write_tokens, cost_usd,
                    ttft_ms, duration_ms, error_type
                ) VALUES (
                    :generation_id, :agent_name, :model, :pipeline_id, :phase,
                    :prompt_template, :input_tokens, :output_tokens,
                    :cache_read_tokens, :cache_write_tokens, :cost_usd,
                    :ttft_ms, :duration_ms, :error_type
                )
                """
            ),
            {
                "generation_id": call.get("generation_id", ""),
                "agent_name": call.get("agent_name", ""),
                "model": call.get("model", ""),
                "pipeline_id": call.get("pipeline_id"),
                "phase": call.get("phase"),
                "prompt_template": call.get("prompt_template"),
                "input_tokens": call.get("input_tokens", 0),
                "output_tokens": call.get("output_tokens", 0),
                "cache_read_tokens": call.get("cache_read_tokens", 0),
                "cache_write_tokens": call.get("cache_write_tokens", 0),
                "cost_usd": call.get("cost_usd", 0),
                "ttft_ms": call.get("ttft_ms"),
                "duration_ms": call.get("duration_ms"),
                "error_type": call.get("error_type"),
            },
        )

    def list_recent(self, session: Session, *, limit: int = 50) -> list[dict[str, Any]]:
        rows = session.execute(
            text(
                "SELECT generation_id, agent_name, model, input_tokens, output_tokens, "
                "cost_usd, ttft_ms, duration_ms, error_type, created_at "
                "FROM llm_calls ORDER BY created_at DESC LIMIT :limit"
            ),
            {"limit": max(1, min(limit, 500))},
        ).all()
        return [
            {
                "generation_id": r[0],
                "agent_name": r[1],
                "model": r[2],
                "input_tokens": r[3],
                "output_tokens": r[4],
                "cost_usd": float(r[5]),
                "ttft_ms": r[6],
                "duration_ms": r[7],
                "error_type": r[8],
                "created_at": r[9].isoformat() if r[9] else None,
            }
            for r in rows
        ]


# ==== Assistant (conversations + turns - plain dicts) ====


class ConversationRepository:
    """Assistant conversation lifecycle. Turns cascade on delete."""

    def create(self, session: Session, *, title: str = "New conversation") -> int:
        row = session.execute(
            text("INSERT INTO assistant_conversations (title) VALUES (:t) RETURNING id"),
            {"t": title[:200]},
        ).first()
        return int(row[0])  # type: ignore[index]

    def get(self, session: Session, conversation_id: int) -> dict[str, Any] | None:
        row = session.execute(
            text(
                "SELECT id, title, status, created_at, last_message_at "
                "FROM assistant_conversations WHERE id = :id"
            ),
            {"id": conversation_id},
        ).first()
        if row is None:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "status": row[2],
            "created_at": row[3].isoformat(),
            "last_message_at": row[4].isoformat(),
        }

    def list(self, session: Session, *, limit: int = 50) -> list[dict[str, Any]]:
        rows = session.execute(
            text(
                "SELECT id, title, status, created_at, last_message_at "
                "FROM assistant_conversations WHERE status = 'active' "
                "ORDER BY last_message_at DESC LIMIT :limit"
            ),
            {"limit": max(1, min(limit, 200))},
        ).all()
        return [
            {
                "id": r[0],
                "title": r[1],
                "status": r[2],
                "created_at": r[3].isoformat(),
                "last_message_at": r[4].isoformat(),
            }
            for r in rows
        ]

    def touch(self, session: Session, conversation_id: int, *, title: str | None = None) -> None:
        """Bump last_message_at; optionally set the title (first user message)."""
        if title is not None:
            session.execute(
                text(
                    "UPDATE assistant_conversations SET last_message_at = NOW(), "
                    "title = :t WHERE id = :id AND title = 'New conversation'"
                ),
                {"id": conversation_id, "t": title[:80]},
            )
        session.execute(
            text("UPDATE assistant_conversations SET last_message_at = NOW() WHERE id = :id"),
            {"id": conversation_id},
        )

    def archive(self, session: Session, conversation_id: int) -> bool:
        result = session.execute(
            text("UPDATE assistant_conversations SET status = 'archived' WHERE id = :id"),
            {"id": conversation_id},
        )
        return int(getattr(result, "rowcount", 0)) > 0


class TurnRepository:
    """Append-only turn log. `tool` turns carry results for the preceding
    assistant turn's tool_calls, so replays read left-to-right."""

    def add(
        self,
        session: Session,
        conversation_id: int,
        role: str,
        content: str = "",
        *,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> int:
        row = session.execute(
            text(
                "INSERT INTO assistant_turns "
                "(conversation_id, role, content, tool_calls, tool_results) "
                "VALUES (:cid, :role, :content, :calls, :results) RETURNING id"
            ).bindparams(bindparam("calls", type_=JSONB), bindparam("results", type_=JSONB)),
            {
                "cid": conversation_id,
                "role": role,
                "content": content,
                "calls": tool_calls,
                "results": tool_results,
            },
        ).first()
        return int(row[0])  # type: ignore[index]

    def list(self, session: Session, conversation_id: int) -> list[dict[str, Any]]:
        rows = session.execute(
            text(
                "SELECT id, role, content, tool_calls, tool_results, created_at "
                "FROM assistant_turns WHERE conversation_id = :cid ORDER BY id"
            ),
            {"cid": conversation_id},
        ).all()
        return [
            {
                "id": r[0],
                "role": r[1],
                "content": r[2],
                "tool_calls": r[3],
                "tool_results": r[4],
                "created_at": r[5].isoformat(),
            }
            for r in rows
        ]


# ==== Profiles ====


class ProfileRepository:
    """Persistence for the example `profiles` table (list -> detail entity)."""

    def upsert(self, session: Session, profile: Profile) -> Profile:
        session.execute(
            text(
                """
                INSERT INTO profiles (id, name, summary, status, tags, attributes)
                VALUES (:id, :name, :summary, :status, :tags, :attributes)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    summary = EXCLUDED.summary,
                    status = EXCLUDED.status,
                    tags = EXCLUDED.tags,
                    attributes = EXCLUDED.attributes
                """
            ).bindparams(bindparam("tags", type_=JSONB), bindparam("attributes", type_=JSONB)),
            {
                "id": profile.id,
                "name": profile.name,
                "summary": profile.summary,
                "status": profile.status.value,
                "tags": profile.tags,
                "attributes": profile.attributes,
            },
        )
        return profile

    def get(self, session: Session, profile_id: str) -> Profile | None:
        row = session.execute(
            text(
                "SELECT id, name, summary, status, tags, attributes, created_at, updated_at "
                "FROM profiles WHERE id = :id"
            ),
            {"id": profile_id},
        ).first()
        return self._hydrate(row) if row else None

    def list(
        self,
        session: Session,
        *,
        status: ProfileStatus | None = None,
        q: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[Profile], int]:
        where = ["TRUE"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status is not None:
            where.append("status = :status")
            params["status"] = status.value
        if q:
            where.append("name ILIKE :q")
            params["q"] = f"%{q}%"
        clause = " AND ".join(where)

        total = session.execute(
            text(f"SELECT COUNT(*) FROM profiles WHERE {clause}"),  # noqa: S608
            params,
        ).scalar_one()
        rows = session.execute(
            text(
                f"SELECT id, name, summary, status, tags, attributes, created_at, updated_at "
                f"FROM profiles WHERE {clause} "  # noqa: S608
                f"ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        ).all()
        return [self._hydrate(r) for r in rows], int(total)

    def set_status(self, session: Session, profile_id: str, status: ProfileStatus) -> bool:
        result = session.execute(
            text("UPDATE profiles SET status = :status WHERE id = :id"),
            {"id": profile_id, "status": status.value},
        )
        return int(getattr(result, "rowcount", 0)) > 0

    def counts_by_status(self, session: Session) -> dict[str, int]:
        rows = session.execute(text("SELECT status, COUNT(*) FROM profiles GROUP BY status")).all()
        counts = {s.value: 0 for s in ProfileStatus}
        counts.update({row[0]: int(row[1]) for row in rows})
        return counts

    def delete(self, session: Session, profile_id: str) -> bool:
        """Delete one profile. Nothing cascades - profiles own no children."""
        result = session.execute(text("DELETE FROM profiles WHERE id = :id"), {"id": profile_id})
        return int(getattr(result, "rowcount", 0)) > 0

    @staticmethod
    def _hydrate(row: Any) -> Profile:
        return Profile(
            id=row[0],
            name=row[1],
            summary=row[2],
            status=ProfileStatus(row[3]),
            tags=row[4] or [],
            attributes=row[5] or {},
            created_at=row[6],
            updated_at=row[7],
        )


# ==== Users (the app's own account directory) ====


class UserRepository:
    """Persistence for the `users` table. Email is the unique handle -
    upsert conflicts on email surface as IntegrityError for the route to
    translate into a 409."""

    def upsert(self, session: Session, user: AppUser) -> AppUser:
        session.execute(
            text(
                """
                INSERT INTO users (id, name, email, role, status, last_seen_at)
                VALUES (:id, :name, :email, :role, :status, :last_seen_at)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    email = EXCLUDED.email,
                    role = EXCLUDED.role,
                    status = EXCLUDED.status,
                    last_seen_at = EXCLUDED.last_seen_at
                """
            ),
            {
                "id": user.id,
                "name": user.name,
                "email": str(user.email),
                "role": user.role.value,
                "status": user.status.value,
                "last_seen_at": user.last_seen_at,
            },
        )
        return user

    def get(self, session: Session, user_id: str) -> AppUser | None:
        row = session.execute(text(f"{self._SELECT} WHERE id = :id"), {"id": user_id}).first()
        return self._hydrate(row) if row else None

    def get_by_email(self, session: Session, email: str) -> AppUser | None:
        row = session.execute(
            text(f"{self._SELECT} WHERE email = :email"), {"email": email.lower()}
        ).first()
        return self._hydrate(row) if row else None

    def list(
        self,
        session: Session,
        *,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        q: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[AppUser], int]:
        where = ["TRUE"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if role is not None:
            where.append("role = :role")
            params["role"] = role.value
        if status is not None:
            where.append("status = :status")
            params["status"] = status.value
        if q:
            where.append("(name ILIKE :q OR email ILIKE :q)")
            params["q"] = f"%{q}%"
        clause = " AND ".join(where)

        total = session.execute(
            text(f"SELECT COUNT(*) FROM users WHERE {clause}"),  # noqa: S608
            params,
        ).scalar_one()
        rows = session.execute(
            text(
                f"{self._SELECT} WHERE {clause} "  # noqa: S608
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        ).all()
        return [self._hydrate(r) for r in rows], int(total)

    def set_role(self, session: Session, user_id: str, role: UserRole) -> bool:
        result = session.execute(
            text("UPDATE users SET role = :role WHERE id = :id"),
            {"id": user_id, "role": role.value},
        )
        return int(getattr(result, "rowcount", 0)) > 0

    def set_status(self, session: Session, user_id: str, status: UserStatus) -> bool:
        result = session.execute(
            text("UPDATE users SET status = :status WHERE id = :id"),
            {"id": user_id, "status": status.value},
        )
        return int(getattr(result, "rowcount", 0)) > 0

    def counts_by_status(self, session: Session) -> dict[str, int]:
        rows = session.execute(text("SELECT status, COUNT(*) FROM users GROUP BY status")).all()
        counts = {s.value: 0 for s in UserStatus}
        counts.update({row[0]: int(row[1]) for row in rows})
        return counts

    def delete(self, session: Session, user_id: str) -> bool:
        """Delete one user. Prefer status=disabled in real apps - delete
        exists for the template's demo loop."""
        result = session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        return int(getattr(result, "rowcount", 0)) > 0

    _SELECT = (
        "SELECT id, name, email, role, status, last_seen_at, created_at, updated_at FROM users"
    )

    @staticmethod
    def _hydrate(row: Any) -> AppUser:
        return AppUser(
            id=row[0],
            name=row[1],
            email=row[2],
            role=UserRole(row[3]),
            status=UserStatus(row[4]),
            last_seen_at=row[5],
            created_at=row[6],
            updated_at=row[7],
        )
