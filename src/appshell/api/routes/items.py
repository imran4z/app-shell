"""Items resource routes - the template's example of every route convention.

Conventions demonstrated (BLUEPRINT.md §5):
  - APIRouter with /api/<resource> prefix, one module per resource.
  - Plain sync handlers, zero Depends; repos instantiated directly;
    DB work inside `with session_scope()` blocks.
  - Local DTOs; response_model on every route.
  - Pagination clamped (never 422'd), {entries, total, limit, offset}
    envelope so one UI Pagination component serves everything.
  - Literal routes declared before /{param} routes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from appshell.schemas import Item, ItemState
from appshell.storage import ItemRepository, session_scope

router = APIRouter(prefix="/api/items", tags=["items"])
_repo = ItemRepository()


# --- DTOs ----------------------------------------------------------------


class ItemCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: dict[str, Any] = Field(default_factory=dict)


class ItemStateRequest(BaseModel):
    state: ItemState


class ItemListResponse(BaseModel):
    entries: list[Item]
    total: int
    limit: int
    offset: int


class ItemStatsResponse(BaseModel):
    counts: dict[str, int]
    total: int


# --- Routes (literal before parameterized) -------------------------------


@router.get("/stats", response_model=ItemStatsResponse)
def item_stats() -> ItemStatsResponse:
    with session_scope() as session:
        counts = _repo.counts_by_state(session)
    return ItemStatsResponse(counts=counts, total=sum(counts.values()))


@router.get("", response_model=ItemListResponse)
def list_items(
    state: ItemState | None = None,
    q: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> ItemListResponse:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    with session_scope() as session:
        entries, total = _repo.list(session, state=state, q=q, limit=limit, offset=offset)
    return ItemListResponse(entries=entries, total=total, limit=limit, offset=offset)


@router.post("", response_model=Item, status_code=201)
def create_item(body: ItemCreateRequest) -> Item:
    item = Item(title=body.title, detail=body.detail)
    with session_scope() as session:
        _repo.upsert(session, item)
    with session_scope() as session:
        return _repo.get(session, item.id) or item


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: str) -> Item:
    with session_scope() as session:
        item = _repo.get(session, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"item {item_id} not found")
    return item


@router.post("/{item_id}/state", response_model=Item)
def set_item_state(item_id: str, body: ItemStateRequest) -> Item:
    with session_scope() as session:
        if not _repo.set_state(session, item_id, body.state):
            raise HTTPException(status_code=404, detail=f"item {item_id} not found")
    with session_scope() as session:
        item = _repo.get(session, item_id)
    if item is None:  # deleted between the two transactions - treat as gone
        raise HTTPException(status_code=404, detail=f"item {item_id} not found")
    return item


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: str) -> None:
    with session_scope() as session:
        if not _repo.delete(session, item_id):
            raise HTTPException(status_code=404, detail=f"item {item_id} not found")
