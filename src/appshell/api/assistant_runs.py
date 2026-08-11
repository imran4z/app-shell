"""In-memory registry of background assistant runs (BLUEPRINT.md §9).

Each conversation has at most ONE active run - an asyncio task driving the
agent loop in a worker thread - plus an append-only, seq-numbered event
buffer. HTTP responses are mere *tails* of the buffer (replay from a seq,
then follow live), so dropping a connection never kills a run, and
reopening a running conversation reattaches mid-stream.

Why in-memory only: full turns are persisted to Postgres after every loop
iteration, and build_messages() self-heals any tool_use orphaned by a
crash/restart. The buffer holds only the ephemeral token stream - durable
state never lives here.

Thread-safety: the loop body runs in a worker thread (the SDK call is
blocking), so emit() appends under the GIL and wakes tailers via
loop.call_soon_threadsafe - asyncio.Event is not thread-safe on its own.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

import structlog

_logger = structlog.get_logger()

TERMINAL_STATUSES = frozenset({"done", "awaiting_approval", "failed", "cancelled"})
TERMINAL_EVENTS = frozenset({"done", "error", "cancelled", "approval_required"})

# Finished runs linger so the UI poller can observe the running->terminal
# transition and a late reattach can still replay the tail.
FINISHED_RETENTION_S = 120.0
_TAIL_WAIT_S = 30.0


@dataclass
class AssistantRun:
    """One background agent-loop execution for a conversation."""

    conversation_id: int
    run_id: str = field(default_factory=lambda: uuid4().hex)
    status: str = "running"  # running | awaiting_approval | done | failed | cancelled
    events: list[dict[str, Any]] = field(default_factory=list)
    seq: int = 0
    task: asyncio.Task[None] | None = None
    cancel_requested: threading.Event = field(default_factory=threading.Event)
    finished_at: float | None = None
    _loop: asyncio.AbstractEventLoop | None = None
    _wakeup: asyncio.Event = field(default_factory=asyncio.Event)

    def emit(self, event: str, data: str) -> None:
        """Append an event and wake every tailer. Safe from any thread.
        Once terminal, only terminal events pass - a lingering worker that
        keeps pushing deltas after a cancel is silently dropped."""
        if self.status in TERMINAL_STATUSES and event not in TERMINAL_EVENTS:
            return
        self.seq += 1
        self.events.append({"seq": self.seq, "event": event, "data": data})
        self._wake()

    def finish(self, status: str) -> None:
        self.status = status
        self.finished_at = time.monotonic()
        self._wake()

    def is_active(self) -> bool:
        return self.status == "running"

    def _wake(self) -> None:
        # Broadcast: swap in a fresh Event, set the old one on the loop
        # thread. Every tailer holds a reference to the pre-swap Event.
        def _do() -> None:
            wake, self._wakeup = self._wakeup, asyncio.Event()
            wake.set()

        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            _do()
        else:
            loop.call_soon_threadsafe(_do)


_runs: dict[int, AssistantRun] = {}


def reset() -> None:
    """Test hook - drop all registry state."""
    _runs.clear()


def start_run(
    conversation_id: int,
    loop_body: Callable[[AssistantRun], None],
) -> tuple[AssistantRun, bool]:
    """Start the agent loop for a conversation as a background task.

    One active run per conversation: if one is already running it is
    returned with created=False - callers reattach (or 409) instead of
    racing a second loop over the same turn history. `loop_body` is a
    SYNC callable; it executes via asyncio.to_thread."""
    existing = _runs.get(conversation_id)
    if existing is not None and existing.is_active():
        return existing, False
    run = AssistantRun(conversation_id=conversation_id)
    run._loop = asyncio.get_running_loop()
    run.task = asyncio.create_task(_drive(run, loop_body))
    _runs[conversation_id] = run
    return run, True


async def _drive(run: AssistantRun, loop_body: Callable[[AssistantRun], None]) -> None:
    """Execute the loop; guarantee a terminal status + terminal event no
    matter how it exits."""
    try:
        await asyncio.to_thread(loop_body, run)
    except asyncio.CancelledError:
        run.finish("cancelled")
        run.emit("cancelled", json.dumps({"conversation_id": run.conversation_id}))
        raise
    except Exception as exc:  # noqa: BLE001 - terminal event carries it to the UI
        _logger.exception(
            "assistant.run_failed", conversation_id=run.conversation_id, run_id=run.run_id
        )
        run.finish("failed")
        run.emit("error", str(exc))
    else:
        last_event = run.events[-1]["event"] if run.events else None
        final = run.status if run.status in TERMINAL_STATUSES else "done"
        run.finish(final)
        if last_event not in TERMINAL_EVENTS:
            run.emit("done", json.dumps({"conversation_id": run.conversation_id}))


def get_run(conversation_id: int) -> AssistantRun | None:
    return _runs.get(conversation_id)


def get_active_run(conversation_id: int) -> AssistantRun | None:
    run = _runs.get(conversation_id)
    return run if run is not None and run.is_active() else None


def cancel_run(conversation_id: int) -> bool:
    """Request cancellation. Returns False when nothing is active."""
    run = get_active_run(conversation_id)
    if run is None or run.task is None:
        return False
    run.cancel_requested.set()
    run.task.cancel()
    return True


def list_runs(now: float | None = None) -> list[dict[str, Any]]:
    """Active runs plus recently finished ones - the UI poller diffs
    snapshots to fire completion toasts."""
    now = time.monotonic() if now is None else now
    out: list[dict[str, Any]] = []
    for run in _runs.values():
        if (
            not run.is_active()
            and run.finished_at is not None
            and now - run.finished_at > FINISHED_RETENTION_S
        ):
            continue
        out.append(
            {
                "run_id": run.run_id,
                "conversation_id": run.conversation_id,
                "status": run.status,
            }
        )
    return out


async def tail(run: AssistantRun, after: int = 0) -> AsyncIterator[dict[str, Any]]:
    """Replay buffered events with seq > after, then follow live until the
    run is terminal and fully drained. Any number of concurrent tailers."""
    cursor = after
    while True:
        # Snapshot the wakeup BEFORE scanning so an emit landing between
        # scan and wait still wakes us (no missed-event race).
        wake = run._wakeup
        while cursor < run.seq:
            for ev in run.events:
                if ev["seq"] > cursor:
                    cursor = ev["seq"]
                    yield ev
        if run.status in TERMINAL_STATUSES and cursor >= run.seq:
            return
        try:
            await asyncio.wait_for(wake.wait(), timeout=_TAIL_WAIT_S)
        except TimeoutError:
            continue
