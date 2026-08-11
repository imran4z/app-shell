"""Assistant API surface (BLUEPRINT.md §9).

SSE vocabulary: delta, tool_call, tool_result, approval_required,
turn_persisted, cancelled, done, error. The SSE connection is only a
viewer - aborting it never stops the run (cancel is a server call).

Handlers here are async (they start background tasks / stream), unlike
the plain-sync resource routes - that's the one sanctioned exception.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from appshell.api import assistant_runs
from appshell.storage import ConversationRepository, TurnRepository, session_scope

router = APIRouter(prefix="/api/assistant", tags=["assistant"])
_convos = ConversationRepository()
_turns = TurnRepository()


# --- DTOs ----------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: int | None = None


class ResumeRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


class ConversationSummary(BaseModel):
    id: int
    title: str
    status: str
    created_at: str
    last_message_at: str


# --- Conversations -------------------------------------------------------


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations() -> list[dict[str, Any]]:
    with session_scope() as s:
        return _convos.list(s)


@router.get("/conversations/{conversation_id}/turns")
def list_turns(conversation_id: int) -> list[dict[str, Any]]:
    with session_scope() as s:
        if _convos.get(s, conversation_id) is None:
            raise HTTPException(404, f"conversation {conversation_id} not found")
        return _turns.list(s, conversation_id)


@router.post("/conversations/{conversation_id}/archive", status_code=204)
def archive_conversation(conversation_id: int) -> None:
    with session_scope() as s:
        if not _convos.archive(s, conversation_id):
            raise HTTPException(404, f"conversation {conversation_id} not found")


# --- Runs ----------------------------------------------------------------


@router.get("/runs")
def runs() -> list[dict[str, Any]]:
    return assistant_runs.list_runs()


@router.post("/chat")
async def chat(body: ChatRequest) -> EventSourceResponse:
    """Persist the user turn, start (or reject on) a run, stream the tail."""
    from appshell.agents.assistant import pending_tool_calls, run_assistant_loop_sync

    conversation_id = body.conversation_id
    # 409 BEFORE persisting the user turn - a second send while a run is
    # active must not enqueue a duplicate turn.
    if conversation_id is not None and assistant_runs.get_active_run(conversation_id):
        raise HTTPException(409, "a run is already active for this conversation")

    with session_scope() as s:
        if conversation_id is None:
            conversation_id = _convos.create(s, title=body.message[:80])
        elif _convos.get(s, conversation_id) is None:
            raise HTTPException(404, f"conversation {conversation_id} not found")
        if pending_tool_calls(_turns.list(s, conversation_id)):
            raise HTTPException(
                409, "conversation is awaiting an approval decision - resolve it first"
            )
        _turns.add(s, conversation_id, "user", body.message)
        _convos.touch(s, conversation_id, title=body.message)

    cid = conversation_id
    run, created = assistant_runs.start_run(cid, lambda r: run_assistant_loop_sync(r, cid))
    if not created:
        raise HTTPException(409, "a run is already active for this conversation")
    return _sse(run, after=0, conversation_id=cid)


@router.post("/conversations/{conversation_id}/resume")
async def resume(conversation_id: int, body: ResumeRequest) -> EventSourceResponse:
    """Approve or reject the pending tool calls, then continue the loop."""
    from appshell.agents.assistant import pending_tool_calls, run_assistant_loop_sync

    if assistant_runs.get_active_run(conversation_id):
        raise HTTPException(409, "a run is already active for this conversation")
    with session_scope() as s:
        if _convos.get(s, conversation_id) is None:
            raise HTTPException(404, f"conversation {conversation_id} not found")
        if not pending_tool_calls(_turns.list(s, conversation_id)):
            raise HTTPException(409, "nothing is awaiting approval")

    decision = body.decision
    run, created = assistant_runs.start_run(
        conversation_id,
        lambda r: run_assistant_loop_sync(r, conversation_id, resume_decision=decision),
    )
    if not created:
        raise HTTPException(409, "a run is already active for this conversation")
    return _sse(run, after=0, conversation_id=conversation_id)


@router.get("/conversations/{conversation_id}/run/events")
async def run_events(conversation_id: int, after: int = 0) -> EventSourceResponse:
    """Reattach to a live (or recently finished) run's event tail."""
    run = assistant_runs.get_run(conversation_id)
    if run is None:
        raise HTTPException(404, "no run for this conversation")
    return _sse(run, after=after, conversation_id=conversation_id)


@router.post("/conversations/{conversation_id}/run/cancel")
def cancel(conversation_id: int) -> dict[str, bool]:
    return {"cancelled": assistant_runs.cancel_run(conversation_id)}


def _sse(
    run: assistant_runs.AssistantRun, *, after: int, conversation_id: int
) -> EventSourceResponse:
    async def gen() -> AsyncIterator[dict[str, str]]:
        # First frame tells a fresh client which conversation it's in.
        yield {"event": "meta", "data": f'{{"conversation_id": {conversation_id}}}'}
        async for ev in assistant_runs.tail(run, after):
            yield {"event": ev["event"], "data": ev["data"], "id": str(ev["seq"])}

    return EventSourceResponse(gen())
