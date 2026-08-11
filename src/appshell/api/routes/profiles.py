"""Profiles resource routes - list->detail entity with an enrichment
surface (attributes/tags added over time) and a publish lifecycle.
Same conventions as items.py; additionally demonstrates read-modify-
upsert for JSONB payload edits.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from appshell.schemas import Profile, ProfileStatus
from appshell.storage import ProfileRepository, session_scope

router = APIRouter(prefix="/api/profiles", tags=["profiles"])
_repo = ProfileRepository()


# --- DTOs ----------------------------------------------------------------


class ProfileCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    summary: str = Field(default="", max_length=2000)
    tags: list[str] = Field(default_factory=list)


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = None


class ProfileStatusRequest(BaseModel):
    status: ProfileStatus


class AttributeRequest(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=2000)


class ProfileListResponse(BaseModel):
    entries: list[Profile]
    total: int
    limit: int
    offset: int


class ProfileStatsResponse(BaseModel):
    counts: dict[str, int]
    total: int


def _get_or_404(profile_id: str) -> Profile:
    with session_scope() as session:
        profile = _repo.get(session, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"profile {profile_id} not found")
    return profile


# --- Routes (literal before parameterized) -------------------------------


@router.get("/stats", response_model=ProfileStatsResponse)
def profile_stats() -> ProfileStatsResponse:
    with session_scope() as session:
        counts = _repo.counts_by_status(session)
    return ProfileStatsResponse(counts=counts, total=sum(counts.values()))


@router.get("", response_model=ProfileListResponse)
def list_profiles(
    status: ProfileStatus | None = None,
    q: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> ProfileListResponse:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    with session_scope() as session:
        entries, total = _repo.list(session, status=status, q=q, limit=limit, offset=offset)
    return ProfileListResponse(entries=entries, total=total, limit=limit, offset=offset)


@router.post("", response_model=Profile, status_code=201)
def create_profile(body: ProfileCreateRequest) -> Profile:
    profile = Profile(name=body.name, summary=body.summary, tags=_dedupe(body.tags))
    with session_scope() as session:
        _repo.upsert(session, profile)
    return _get_or_404(profile.id)


@router.get("/{profile_id}", response_model=Profile)
def get_profile(profile_id: str) -> Profile:
    return _get_or_404(profile_id)


@router.patch("/{profile_id}", response_model=Profile)
def update_profile(profile_id: str, body: ProfileUpdateRequest) -> Profile:
    profile = _get_or_404(profile_id)
    if body.name is not None:
        profile.name = body.name
    if body.summary is not None:
        profile.summary = body.summary
    if body.tags is not None:
        profile.tags = _dedupe(body.tags)
    with session_scope() as session:
        _repo.upsert(session, profile)
    return _get_or_404(profile_id)


@router.post("/{profile_id}/status", response_model=Profile)
def set_profile_status(profile_id: str, body: ProfileStatusRequest) -> Profile:
    with session_scope() as session:
        if not _repo.set_status(session, profile_id, body.status):
            raise HTTPException(status_code=404, detail=f"profile {profile_id} not found")
    return _get_or_404(profile_id)


@router.post("/{profile_id}/attributes", response_model=Profile)
def put_attribute(profile_id: str, body: AttributeRequest) -> Profile:
    """Add or overwrite one attribute (read-modify-upsert on the JSONB)."""
    profile = _get_or_404(profile_id)
    profile.attributes[body.key.strip()] = body.value
    with session_scope() as session:
        _repo.upsert(session, profile)
    return _get_or_404(profile_id)


@router.delete("/{profile_id}/attributes/{key}", response_model=Profile)
def delete_attribute(profile_id: str, key: str) -> Profile:
    profile = _get_or_404(profile_id)
    if key not in profile.attributes:
        raise HTTPException(status_code=404, detail=f"attribute {key!r} not found")
    del profile.attributes[key]
    with session_scope() as session:
        _repo.upsert(session, profile)
    return _get_or_404(profile_id)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str) -> None:
    with session_scope() as session:
        if not _repo.delete(session, profile_id):
            raise HTTPException(status_code=404, detail=f"profile {profile_id} not found")


def _dedupe(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        cleaned = tag.strip()[:40]
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            out.append(cleaned)
    return out[:20]
