"""Users resource routes - the app's own account directory.

Same conventions as items/profiles, plus one extra: translating the DB's
UNIQUE(email) violation into a 409 the UI can show.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError

from appshell.schemas import AppUser, UserRole, UserStatus
from appshell.storage import UserRepository, session_scope

router = APIRouter(prefix="/api/users", tags=["users"])
_repo = UserRepository()


# --- DTOs ----------------------------------------------------------------


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    role: UserRole = UserRole.MEMBER


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = None


class UserStatusRequest(BaseModel):
    status: UserStatus


class UserListResponse(BaseModel):
    entries: list[AppUser]
    total: int
    limit: int
    offset: int


class UserStatsResponse(BaseModel):
    counts: dict[str, int]
    total: int


def _get_or_404(user_id: str) -> AppUser:
    with session_scope() as session:
        user = _repo.get(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"user {user_id} not found")
    return user


# --- Routes (literal before parameterized) -------------------------------


@router.get("/stats", response_model=UserStatsResponse)
def user_stats() -> UserStatsResponse:
    with session_scope() as session:
        counts = _repo.counts_by_status(session)
    return UserStatsResponse(counts=counts, total=sum(counts.values()))


@router.get("", response_model=UserListResponse)
def list_users(
    role: UserRole | None = None,
    status: UserStatus | None = None,
    q: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> UserListResponse:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    with session_scope() as session:
        entries, total = _repo.list(
            session, role=role, status=status, q=q, limit=limit, offset=offset
        )
    return UserListResponse(entries=entries, total=total, limit=limit, offset=offset)


@router.post("", response_model=AppUser, status_code=201)
def invite_user(body: UserCreateRequest) -> AppUser:
    user = AppUser(name=body.name, email=body.email, role=body.role)
    try:
        with session_scope() as session:
            _repo.upsert(session, user)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409, detail=f"a user with email {body.email} already exists"
        ) from exc
    return _get_or_404(user.id)


@router.get("/{user_id}", response_model=AppUser)
def get_user(user_id: str) -> AppUser:
    return _get_or_404(user_id)


@router.patch("/{user_id}", response_model=AppUser)
def update_user(user_id: str, body: UserUpdateRequest) -> AppUser:
    user = _get_or_404(user_id)
    if body.name is not None:
        user.name = body.name
    if body.role is not None:
        user.role = body.role
    with session_scope() as session:
        _repo.upsert(session, user)
    return _get_or_404(user_id)


@router.post("/{user_id}/status", response_model=AppUser)
def set_user_status(user_id: str, body: UserStatusRequest) -> AppUser:
    with session_scope() as session:
        if not _repo.set_status(session, user_id, body.status):
            raise HTTPException(status_code=404, detail=f"user {user_id} not found")
    return _get_or_404(user_id)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str) -> None:
    with session_scope() as session:
        if not _repo.delete(session, user_id):
            raise HTTPException(status_code=404, detail=f"user {user_id} not found")
