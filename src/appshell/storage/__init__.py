"""Storage layer - engine factory, migration runner, repositories.

Four files, no ORM models, no Alembic, no generic CRUD: it keeps the
surface auditable. See BLUEPRINT.md §6 for the full contract.
"""

from appshell.storage.db import build_dsn, connect, reset_engine_cache, session_scope
from appshell.storage.migrator import apply_migrations, drop_all
from appshell.storage.repositories import (
    ConversationRepository,
    ItemRepository,
    LlmCallRepository,
    ProfileRepository,
    TurnRepository,
    UserRepository,
)

__all__ = [
    "ConversationRepository",
    "ItemRepository",
    "LlmCallRepository",
    "ProfileRepository",
    "TurnRepository",
    "UserRepository",
    "apply_migrations",
    "build_dsn",
    "connect",
    "drop_all",
    "reset_engine_cache",
    "session_scope",
]
