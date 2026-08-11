"""The assistant agent loop - BLUEPRINT.md §9.

Runs inside an AssistantRun (see api/assistant_runs.py). The whole loop is
synchronous (the anthropic SDK call is blocking) and executes in a worker
thread via asyncio.to_thread; every DB touch opens its own session_scope
(sessions never cross threads).

Loop shape per iteration:
  1. Rebuild `messages` from ALL persisted turns; heal orphaned tool_use.
  2. Stream one model call with tools=TOOLS_ALL, emitting `delta` events.
  3. No tool_use in the final message -> persist assistant turn, done.
  4. Else persist the turn WITH tool_calls, then resolve each call:
     approval-gated -> emit approval_required, status awaiting_approval,
     STOP (the paused state is recoverable purely from the DB: last turn
     is assistant-with-tool_calls and no tool turn follows). Otherwise
     execute, emit tool_call/tool_result, batch into one `tool` turn.
Rails: hard iteration cap, declined tools tell the model not to retry.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

import structlog

from appshell.agents.assistant_tools import (
    NEEDS_APPROVAL_TOOL_NAMES,
    TOOLS_ALL,
    execute_tool,
)
from appshell.observability.llm_client import DEFAULT_MODEL, call_anthropic
from appshell.storage import ConversationRepository, TurnRepository, session_scope

if TYPE_CHECKING:
    from appshell.api.assistant_runs import AssistantRun

_logger = structlog.get_logger()

MAX_ITERATIONS = 5
MAX_TOKENS = 4096  # generous so structured edits can't truncate mid-JSON

SYSTEM_PROMPT = """\
You are the in-app assistant for App Shell. You can inspect and operate the
app through your tools; the user sees your text in a side drawer.

Rules:
- Prefer tools over guessing. Read state before mutating it.
- Mutating tools pause for the user's approval - propose them when useful,
  and explain what you're about to do in one short sentence first.
- If a tool result says "declined", do not retry it without a new
  instruction from the user.
- Keep answers short and concrete. When you mention an app page, give its
  path (e.g. /items) so the UI can link it.
"""


def approvals_enabled() -> bool:
    return os.environ.get("APPSHELL_ASSISTANT_APPROVALS", "on").lower() not in {
        "off",
        "0",
        "false",
    }


# --- Message reconstruction ----------------------------------------------


def build_messages(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """DB turns -> Anthropic messages. Heals orphaned tool_use blocks (a
    crash mid-batch otherwise wedges the conversation - the API rejects
    tool_use without a matching tool_result)."""
    messages: list[dict[str, Any]] = []
    for turn in turns:
        role, content = turn["role"], turn["content"] or ""
        if role == "user":
            messages.append({"role": "user", "content": content})
        elif role == "assistant":
            blocks: list[dict[str, Any]] = []
            if content:
                blocks.append({"type": "text", "text": content})
            for call in turn.get("tool_calls") or []:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call.get("input", {}),
                    }
                )
            if blocks:
                messages.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            results = [
                {
                    "type": "tool_result",
                    "tool_use_id": r["tool_use_id"],
                    "content": r.get("content", ""),
                    "is_error": bool(r.get("is_error")),
                }
                for r in turn.get("tool_results") or []
            ]
            if results:
                messages.append({"role": "user", "content": results})

    # Heal: assistant tool_use with no following tool_result.
    for i, msg in enumerate(messages):
        if msg["role"] != "assistant" or not isinstance(msg["content"], list):
            continue
        call_ids = [b["id"] for b in msg["content"] if b.get("type") == "tool_use"]
        if not call_ids:
            continue
        answered: set[str] = set()
        if i + 1 < len(messages) and isinstance(messages[i + 1].get("content"), list):
            answered = {
                b.get("tool_use_id")
                for b in messages[i + 1]["content"]
                if b.get("type") == "tool_result"
            }
        missing = [cid for cid in call_ids if cid not in answered]
        if missing:
            heal = {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": cid,
                        "content": json.dumps({"error": "interrupted before execution"}),
                        "is_error": True,
                    }
                    for cid in missing
                ],
            }
            messages.insert(i + 1, heal)
    return messages


def pending_tool_calls(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tool calls awaiting approval: last turn is assistant-with-tool_calls
    and no tool turn follows. This is the whole paused-state contract."""
    if not turns:
        return []
    last = turns[-1]
    if last["role"] == "assistant" and last.get("tool_calls"):
        return list(last["tool_calls"])
    return []


# --- The loop (sync; runs in a worker thread) ----------------------------


def run_assistant_loop_sync(
    run: AssistantRun,
    conversation_id: int,
    *,
    resume_decision: str | None = None,
) -> None:
    """Drive the agent loop to a terminal state. resume_decision handles a
    conversation paused on approval: 'approve' executes the pending calls,
    'reject' records declined results; either way the loop then continues.
    """
    import anthropic

    if not os.environ.get("ANTHROPIC_API_KEY"):
        run.finish("failed")
        run.emit("error", "ANTHROPIC_API_KEY is not set - add it to .env and restart.")
        return
    client = anthropic.Anthropic()
    turn_repo = TurnRepository()
    convo_repo = ConversationRepository()

    def load_turns() -> list[dict[str, Any]]:
        with session_scope() as s:
            return turn_repo.list(s, conversation_id)

    turns = load_turns()

    # Resolve a pending approval pause before (or instead of) sampling.
    pending = pending_tool_calls(turns)
    if pending:
        decision = resume_decision or "reject"
        results = _resolve_calls(pending, run, approved=(decision == "approve"))
        with session_scope() as s:
            turn_repo.add(s, conversation_id, "tool", tool_results=results)
            convo_repo.touch(s, conversation_id)
        run.emit("turn_persisted", json.dumps({"role": "tool"}))
        turns = load_turns()

    for _ in range(MAX_ITERATIONS):
        if run.cancel_requested.is_set():
            return
        messages = build_messages(turns)
        response, _gen = call_anthropic(
            client,
            {
                "model": DEFAULT_MODEL,
                "max_tokens": MAX_TOKENS,
                "system": [
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": messages,
                "tools": TOOLS_ALL,
            },
            agent_name="assistant",
            on_text=lambda chunk: run.emit("delta", chunk),
        )

        text = "".join(b.text for b in response.content if b.type == "text")
        calls = [
            {"id": b.id, "name": b.name, "input": b.input}
            for b in response.content
            if b.type == "tool_use"
        ]

        with session_scope() as s:
            turn_repo.add(s, conversation_id, "assistant", text, tool_calls=calls or None)
            convo_repo.touch(s, conversation_id)
        run.emit("turn_persisted", json.dumps({"role": "assistant"}))

        if not calls:
            run.finish("done")
            run.emit("done", json.dumps({"conversation_id": conversation_id}))
            return

        # Approval gate: any gated call pauses the WHOLE batch (recoverable
        # purely from the DB - see pending_tool_calls).
        if approvals_enabled() and any(c["name"] in NEEDS_APPROVAL_TOOL_NAMES for c in calls):
            run.finish("awaiting_approval")
            run.emit("approval_required", json.dumps({"calls": calls}))
            return

        results = _resolve_calls(calls, run, approved=True)
        with session_scope() as s:
            turn_repo.add(s, conversation_id, "tool", tool_results=results)
        run.emit("turn_persisted", json.dumps({"role": "tool"}))
        turns = load_turns()

    run.finish("done")
    run.emit("done", json.dumps({"reason": "iteration_cap", "cap": MAX_ITERATIONS}))


def _resolve_calls(
    calls: list[dict[str, Any]], run: AssistantRun, *, approved: bool
) -> list[dict[str, Any]]:
    """Execute (or decline) a batch of tool calls, emitting events as we go.
    Each execution opens its OWN session - sessions never cross threads."""
    results: list[dict[str, Any]] = []
    for call in calls:
        run.emit("tool_call", json.dumps(call))
        if not approved:
            payload: Any = {
                "declined": True,
                "message": "The user declined this action. Do not retry it "
                "without a new instruction.",
            }
            is_error = False
        else:
            with session_scope() as s:
                payload, is_error = execute_tool(call["name"], call.get("input") or {}, s)
        content = json.dumps(payload)[:20_000]  # bounded - re-sent every iteration
        results.append({"tool_use_id": call["id"], "content": content, "is_error": is_error})
        run.emit(
            "tool_result",
            json.dumps(
                {"id": call["id"], "name": call["name"], "result": payload, "is_error": is_error}
            ),
        )
    return results
